"""
dry_run_streaming.py — live SSE streaming dry run.

Shows each agent's phase events in real time as they arrive, then prints
the completed AuditReport once all 4 agents finish.

Usage:
    python agents/dry_run_streaming.py [URL]
    python agents/dry_run_streaming.py https://example.com

Both services must be running:
    docker compose up   (or run each service locally)
"""
from __future__ import annotations

import asyncio
import json
import sys
import textwrap
import time

import httpx

BACKEND = "http://localhost:8000"
AGENTS  = "http://localhost:8080"
TEST_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

TIMEOUT_CRAWL  = 60.0   # pipeline.run() — Firecrawl may be slow
TIMEOUT_STREAM = 300.0  # total time waiting for all agents to finish
POLL_INTERVAL  = 2.0    # seconds between AuditReport poll attempts

AGENT_LABEL = {
    "crawlability":   "Crawlability ",
    "content_signal": "Content      ",
    "structured_data":"StructuredDat",
    "entity_topic":   "EntityTopic  ",
}

PHASE_LABEL = {
    "started":           "◌  starting...",
    "building_prompt":   "✎  building prompt",
    "llm_call":          "⚡  calling LLM",
    "retry":             "↺  retrying",
    "parsing_result":    "⋯  parsing result",
    "sub_agent_pass_1":  "🌐 sub-agent pass 1: seed crawl",
    "sub_agent_pass_2":  "🌐 sub-agent pass 2: deep crawl",
    "sub_agent_pass_3":  "🌐 sub-agent pass 3: synthesis",
    "judgment_call":     "⚡  judgment LLM call",
    "applying_hard_gates":"🔒 hard gate triggered",
    "complete":          "✓  complete",
    "error":             "✗  error",
}

# ANSI colours
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _print_event(event: dict) -> None:
    agent = event.get("agent", "?")
    phase = event.get("phase", "?")
    detail = event.get("detail", "")
    score  = event.get("score")

    label = AGENT_LABEL.get(agent, f"{agent:<13}")
    phase_str = PHASE_LABEL.get(phase, phase)

    colour = GREEN if phase == "complete" else (RED if phase == "error" else CYAN)
    score_str = f"  score={BOLD}{score}{RESET}" if score is not None else ""
    detail_str = f"  [{detail}]" if detail else ""

    print(f"  {_ts()}  {YELLOW}{label}{RESET}  {colour}{phase_str}{RESET}{detail_str}{score_str}")


# ── step 1 ────────────────────────────────────────────────────────────────────

def check_health() -> tuple[bool, bool]:
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"  {BOLD}Step 1 — Health checks{RESET}")
    backend_ok = agents_ok = False
    try:
        r = httpx.get(f"{BACKEND}/health", timeout=5)
        r.raise_for_status()
        print(f"  {GREEN}[OK]{RESET}  Backend  :{BACKEND}")
        backend_ok = True
    except Exception as exc:
        print(f"  {RED}[FAIL]{RESET} Backend  : {exc}")

    try:
        r = httpx.get(f"{AGENTS}/health", timeout=5)
        r.raise_for_status()
        print(f"  {GREEN}[OK]{RESET}  Agents   :{AGENTS}")
        agents_ok = True
    except Exception as exc:
        print(f"  {RED}[FAIL]{RESET} Agents   : {exc}")

    return backend_ok, agents_ok


# ── step 2 ────────────────────────────────────────────────────────────────────

def start_audit(url: str) -> tuple[str, dict[str, str]] | None:
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"  {BOLD}Step 2 — POST /api/audit/start  ({url}){RESET}")
    print(f"  Crawling via Firecrawl and registering agents…")
    t0 = time.monotonic()
    try:
        r = httpx.post(
            f"{BACKEND}/api/audit/start",
            json={"url": url},
            timeout=TIMEOUT_CRAWL,
        )
        r.raise_for_status()
        body = r.json()
        elapsed = time.monotonic() - t0
        audit_id  = body["audit_id"]
        agent_ids = body["agent_ids"]   # {"crawlability": "uuid", ...}
        print(f"  {GREEN}[OK]{RESET}  audit_id={audit_id[:8]}…  ({elapsed:.1f}s)")
        for name, aid in agent_ids.items():
            print(f"       {YELLOW}{name:<22}{RESET} agent_id={aid[:8]}…")
        return audit_id, agent_ids
    except httpx.HTTPStatusError as exc:
        print(f"  {RED}[FAIL]{RESET} HTTP {exc.response.status_code}: {exc.response.text[:200]}")
    except Exception as exc:
        print(f"  {RED}[FAIL]{RESET} {exc}")
    return None


# ── step 3 — stream 4 agents in parallel ─────────────────────────────────────

async def _stream_one_agent(agent_id: str, done_event: asyncio.Event) -> None:
    """Subscribe to GET /agent/stream/{agent_id} and print events until closed."""
    url = f"{BACKEND}/agent/stream/{agent_id}"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_STREAM)) as client:
            async with client.stream("GET", url) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            event = json.loads(line[5:])
                            _print_event(event)
                        except json.JSONDecodeError:
                            pass
    except Exception as exc:
        print(f"  {RED}[stream error]{RESET} agent_id={agent_id[:8]}…: {exc}")
    finally:
        done_event.set()


async def stream_all_agents(agent_ids: dict[str, str]) -> None:
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"  {BOLD}Step 3 — Live SSE streams (all 4 agents){RESET}")
    print(f"  Events appear below as agents progress…\n")

    done_events = {name: asyncio.Event() for name in agent_ids}
    tasks = [
        asyncio.create_task(
            _stream_one_agent(agent_id, done_events[name]),
            name=f"stream-{name}",
        )
        for name, agent_id in agent_ids.items()
    ]

    # Wait until all streams close (each closes when its agent emits its sentinel)
    await asyncio.gather(*[e.wait() for e in done_events.values()])
    await asyncio.gather(*tasks)


# ── step 4 — poll for final report ───────────────────────────────────────────

async def poll_for_report(audit_id: str) -> dict | None:
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"  {BOLD}Step 4 — Polling for AuditReport{RESET}")
    deadline = time.monotonic() + TIMEOUT_STREAM
    attempt = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        while time.monotonic() < deadline:
            attempt += 1
            try:
                resp = await client.get(f"{BACKEND}/api/audit/{audit_id}")
                if resp.status_code == 202:
                    print(f"  [attempt {attempt}] still running…", end="\r")
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                resp.raise_for_status()
                report = resp.json()
                print(f"  {GREEN}[OK]{RESET}  AuditReport received after {attempt} poll(s).")
                return report
            except Exception as exc:
                print(f"  {RED}[FAIL]{RESET} poll error: {exc}")
                return None
    print(f"  {RED}[TIMEOUT]{RESET} Report not ready after {TIMEOUT_STREAM}s.")
    return None


# ── report summary ────────────────────────────────────────────────────────────

def _bar(score: int, width: int = 24) -> str:
    filled = round(score / 100 * width)
    return f"{'█' * filled}{'░' * (width - filled)} {score}/100"


def print_report_summary(report: dict) -> None:
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"  {BOLD}AI READINESS REPORT — {report.get('url', '?')}{RESET}")
    print(f"{'═'*60}")
    pages = report.get("pages", [])
    if not pages:
        print("  (no pages in report)")
        return
    page = pages[0]
    score = page.get("ai_readiness_score", 0)
    colour = GREEN if score >= 70 else (YELLOW if score >= 50 else RED)
    print(f"\n  Overall score   {colour}{_bar(score)}{RESET}")

    cats = page.get("category_scores", {})
    if cats:
        print(f"\n  Category breakdown:")
        for name, s in cats.items():
            c = GREEN if s >= 70 else (YELLOW if s >= 50 else RED)
            print(f"    {name.replace('_',' ').title():<24} {c}{_bar(s, 18)}{RESET}")

    summary = report.get("summary", "")
    if summary:
        print(f"\n  Executive summary:")
        print(f"  {textwrap.fill(summary, 72, subsequent_indent='  ')}")
    print(f"\n{'═'*60}\n")


# ── main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"  {BOLD}Streaming Dry Run — {TEST_URL}{RESET}")
    print(f"{'='*60}")
    print(f"  Backend : {BACKEND}")
    print(f"  Agents  : {AGENTS}")

    backend_ok, agents_ok = check_health()
    if not backend_ok or not agents_ok:
        print(f"\n  {RED}One or more services unreachable. Start with: docker compose up{RESET}\n")
        sys.exit(1)

    result = start_audit(TEST_URL)
    if result is None:
        sys.exit(1)
    audit_id, agent_ids = result

    # Stream SSE and poll for report concurrently
    stream_task = asyncio.create_task(stream_all_agents(agent_ids))
    await stream_task   # wait for all 4 SSE streams to close

    report = await poll_for_report(audit_id)
    if report:
        print_report_summary(report)
    else:
        print(f"  {RED}No report available.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
