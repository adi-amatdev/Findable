"""
dry_run_integration.py — end-to-end connectivity test: backend -> agents-api.

Tests:
  1. Backend health (http://localhost:8000/health)
  2. Agents health (http://localhost:8080/health)
  3. POST /api/sitefacts on backend  -> get SiteFacts JSON
  4. POST /audit on agents directly  -> get AuditReport  (direct path)
  5. POST /api/audit on backend      -> get AuditReport  (integrated path)

Usage:
    python agents/dry_run_integration.py [URL]
    python agents/dry_run_integration.py https://example.com

Both services must be running:
    docker compose up   (or run each service locally)
"""
from __future__ import annotations

import json
import sys
import textwrap
import time

import httpx

BACKEND  = "http://localhost:8000"
AGENTS   = "http://localhost:8080"
TEST_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

TIMEOUT_SITEFACTS = 60.0   # Firecrawl can be slow
TIMEOUT_AUDIT     = 180.0  # agents do LLM + crawl passes


# ── helpers ─────────────────────────────────────────────────────────────────

def _ok(label: str, detail: str = "") -> None:
    suffix = f"  {detail}" if detail else ""
    print(f"  [OK]   {label}{suffix}")

def _fail(label: str, detail: str = "") -> None:
    suffix = f"  {detail}" if detail else ""
    print(f"  [FAIL] {label}{suffix}")

def _section(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

def _score_bar(score: int, width: int = 24) -> str:
    filled = round(score / 100 * width)
    return f"{'█' * filled}{'░' * (width - filled)} {score}/100"


# ── step 1: health checks ────────────────────────────────────────────────────

def check_health() -> tuple[bool, bool]:
    _section("Step 1 — Health checks")
    backend_ok = agents_ok = False

    try:
        r = httpx.get(f"{BACKEND}/health", timeout=5)
        r.raise_for_status()
        data = r.json()
        _ok("Backend  (port 8000)", f"firecrawl_configured={data.get('firecrawl_configured')}, cache={data.get('cache_connected')}")
        backend_ok = True
    except Exception as exc:
        _fail("Backend  (port 8000)", str(exc))

    try:
        r = httpx.get(f"{AGENTS}/health", timeout=5)
        r.raise_for_status()
        _ok("Agents   (port 8080)")
        agents_ok = True
    except Exception as exc:
        _fail("Agents   (port 8080)", str(exc))

    return backend_ok, agents_ok


# ── step 2: get SiteFacts from backend ───────────────────────────────────────

def get_sitefacts(url: str) -> dict | None:
    _section(f"Step 2 — POST /api/sitefacts  ({url})")
    print(f"  Crawling via Firecrawl… (up to {int(TIMEOUT_SITEFACTS)}s)")
    t0 = time.monotonic()
    try:
        r = httpx.post(
            f"{BACKEND}/api/sitefacts",
            json={"url": url},
            timeout=TIMEOUT_SITEFACTS,
        )
        r.raise_for_status()
        sf = r.json()
        elapsed = time.monotonic() - t0
        _ok(
            "SiteFacts received",
            f"{elapsed:.1f}s  |  HTTP {sf.get('http', {}).get('status')}  "
            f"|  words={sf.get('html', {}).get('word_count')}  "
            f"|  JS ratio={sf.get('render', {}).get('js_dependency_ratio', 0):.2f}",
        )
        return sf
    except httpx.HTTPStatusError as exc:
        _fail("SiteFacts", f"HTTP {exc.response.status_code}: {exc.response.text[:200]}")
    except Exception as exc:
        _fail("SiteFacts", str(exc))
    return None


# ── step 3: POST SiteFacts directly to agents ────────────────────────────────

def audit_direct(sf: dict) -> dict | None:
    _section("Step 3 — POST /audit on agents-api  (direct path)")
    print(f"  Running 4 agents + aggregator… (up to {int(TIMEOUT_AUDIT)}s)")
    t0 = time.monotonic()
    try:
        r = httpx.post(
            f"{AGENTS}/audit",
            content=json.dumps(sf),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_AUDIT,
        )
        r.raise_for_status()
        elapsed = time.monotonic() - t0
        report = r.json()
        _ok("AuditReport received", f"{elapsed:.1f}s")
        return report
    except httpx.HTTPStatusError as exc:
        _fail("audit direct", f"HTTP {exc.response.status_code}: {exc.response.text[:200]}")
    except Exception as exc:
        _fail("audit direct", str(exc))
    return None


# ── step 4: integrated path through backend ───────────────────────────────────

def audit_integrated(url: str) -> dict | None:
    _section(f"Step 4 — POST /api/audit on backend  (integrated path)")
    print(f"  Backend: crawl + forward to agents… (up to {int(TIMEOUT_SITEFACTS + TIMEOUT_AUDIT)}s)")
    t0 = time.monotonic()
    try:
        r = httpx.post(
            f"{BACKEND}/api/audit",
            json={"url": url},
            timeout=TIMEOUT_SITEFACTS + TIMEOUT_AUDIT,
        )
        r.raise_for_status()
        elapsed = time.monotonic() - t0
        report = r.json()
        _ok("AuditReport received via backend", f"{elapsed:.1f}s")
        return report
    except httpx.HTTPStatusError as exc:
        _fail("audit integrated", f"HTTP {exc.response.status_code}: {exc.response.text[:200]}")
    except Exception as exc:
        _fail("audit integrated", str(exc))
    return None


# ── report printer ────────────────────────────────────────────────────────────

def print_report(report: dict, label: str = "") -> None:
    if label:
        print(f"\n  [{label}]")
    pages = report.get("pages", [])
    if not pages:
        print("  (no pages in report)")
        return
    page = pages[0]
    score = page.get("ai_readiness_score", 0)
    print(f"\n  Overall: {_score_bar(score)}")

    cat = page.get("category_scores", {})
    if cat:
        print("  Category breakdown:")
        for name, s in cat.items():
            print(f"    {name:<22} {_score_bar(s, 16)}")

    vis = page.get("visibility", {})
    before = vis.get("before", {})
    after  = vis.get("after", {})
    if before:
        print("  Visibility (before → after top fixes):")
        for bot in ("gpt", "claude", "perplexity", "gemini"):
            b = before.get(bot, 0)
            a = after.get(bot, b)
            arrow = f"  →  {a:.0%}" if a != b else ""
            print(f"    {bot:<12} {b:.0%}{arrow}")

    fixes = page.get("fixes", [])
    if fixes:
        print(f"\n  Top {min(5, len(fixes))} findings:")
        for i, f in enumerate(fixes[:5], 1):
            print(f"\n  {i}. [{f.get('effort','?')}] {f.get('title','')}")
            print(f"     {textwrap.fill(f.get('detail',''), 68, subsequent_indent='     ')}")
            print(f"     Fix: {textwrap.fill(f.get('fix',''), 64, subsequent_indent='          ')}")

    summary = report.get("summary", "")
    if summary:
        print(f"\n  Summary:\n  {textwrap.fill(summary, 70, subsequent_indent='  ')}")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'='*60}")
    print(f"  Integration Dry Run — {TEST_URL}")
    print(f"{'='*60}")
    print(f"  Backend : {BACKEND}")
    print(f"  Agents  : {AGENTS}")

    backend_ok, agents_ok = check_health()

    if not backend_ok:
        print("\n  Backend is not reachable. Start it with: docker compose up api")
        sys.exit(1)

    if not agents_ok:
        print("\n  Agents-api is not reachable. Start it with: docker compose up agents-api")
        sys.exit(1)

    # Step 2: SiteFacts
    sf = get_sitefacts(TEST_URL)
    if sf is None:
        print("\n  Cannot proceed without SiteFacts.")
        sys.exit(1)

    # Step 3: direct call to agents (proves agents-api accepts backend's SiteFacts JSON)
    report_direct = audit_direct(sf)
    if report_direct:
        print_report(report_direct, "direct")
    else:
        print("  Skipping report print — direct audit failed.")

    # Step 4: integrated path through backend's /api/audit
    report_integrated = audit_integrated(TEST_URL)
    if report_integrated:
        # SiteFacts is cached so this is fast (no re-crawl)
        print_report(report_integrated, "integrated")

    _section("Summary")
    checks = [
        ("Backend health",            backend_ok),
        ("Agents health",             agents_ok),
        ("SiteFacts from backend",    sf is not None),
        ("Direct audit (agents-api)", report_direct is not None),
        ("Integrated audit (backend -> agents)", report_integrated is not None),
    ]
    for label, passed in checks:
        mark = "[OK]  " if passed else "[FAIL]"
        print(f"  {mark}  {label}")

    all_passed = all(p for _, p in checks)
    print(f"\n  {'All checks passed.' if all_passed else 'Some checks failed — see above.'}\n")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
