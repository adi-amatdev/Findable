"""
frontend_mock.py — simulates the complete frontend flow.

Mimics exactly what a React/JS frontend would do:
  1. POST /api/audit/start  → receive audit_id + agent_ids
  2. Open one SSE stream per agent → render live "thinking" panels
  3. Poll GET /api/audit/{audit_id} → render final AuditReport card

No browser required — renders a colour-coded terminal UI.
Useful for verifying the API contract before wiring up the real frontend.

Usage:
    python agents/frontend_mock.py [URL]
    python agents/frontend_mock.py https://anthropic.com

Both services must be running (docker compose up, or locally).
"""
from __future__ import annotations

import asyncio
import json
import sys
import textwrap
import time
from collections import defaultdict

import httpx

BACKEND  = "http://localhost:8000"
TEST_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

TIMEOUT_CRAWL  = 90.0   # time allowed for Firecrawl + audit start
TIMEOUT_AGENTS = 300.0  # time allowed for all agents to complete
POLL_INTERVAL  = 3.0

# ── terminal colours ──────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
CYAN   = "\033[36m"
MAGENTA= "\033[35m"

AGENT_COLOUR = {
    "crawlability":    BLUE,
    "content_signal":  GREEN,
    "structured_data": YELLOW,
    "entity_topic":    MAGENTA,
}

PHASE_ICON = {
    "started":             "○",
    "building_prompt":     "✎",
    "llm_call":            "⚡",
    "retry":               "↺",
    "parsing_result":      "⋯",
    "sub_agent_pass_1":    "1⃣",
    "sub_agent_pass_2":    "2⃣",
    "sub_agent_pass_3":    "3⃣",
    "judgment_call":       "⚡",
    "applying_hard_gates": "🔒",
    "complete":            "✓",
    "error":               "✗",
}


# ── "frontend" state tracker ──────────────────────────────────────────────────

class AgentPanel:
    """Represents one agent card in the frontend UI."""

    def __init__(self, name: str, agent_id: str) -> None:
        self.name     = name
        self.agent_id = agent_id
        self.phases: list[str] = []
        self.score: int | None = None
        self.done  = False
        self.error = False

    def receive_event(self, event: dict) -> None:
        phase  = event.get("phase", "?")
        detail = event.get("detail", "")
        score  = event.get("score")

        self.phases.append(phase)
        if score is not None:
            self.score = score
        if phase == "complete":
            self.done  = True
        if phase == "error":
            self.error = True
            self.done  = True

        self._print_line(phase, detail, score)

    def _print_line(self, phase: str, detail: str | None, score: int | None) -> None:
        colour = AGENT_COLOUR.get(self.name, CYAN)
        icon   = PHASE_ICON.get(phase, "•")
        ts     = time.strftime("%H:%M:%S")
        label  = f"{colour}{BOLD}{self.name:<16}{RESET}"

        score_str  = f"  {GREEN}score={score}{RESET}" if score is not None else ""
        detail_str = f"  {DIM}{detail}{RESET}"        if detail else ""

        if phase == "complete":
            print(f"  {ts}  {label}  {GREEN}{icon} {phase}{RESET}{score_str}")
        elif phase == "error":
            print(f"  {ts}  {label}  {RED}{icon} {phase}{RESET}{detail_str}")
        else:
            print(f"  {ts}  {label}  {icon} {phase}{detail_str}")


# ── network helpers ───────────────────────────────────────────────────────────

def _divider(title: str = "") -> None:
    if title:
        pad = max(0, 58 - len(title))
        print(f"\n{BOLD}── {title} {'─'*pad}{RESET}")
    else:
        print(f"\n{'─'*60}")


async def check_health(client: httpx.AsyncClient) -> bool:
    _divider("1. Health check")
    try:
        r = await client.get(f"{BACKEND}/health", timeout=5)
        r.raise_for_status()
        d = r.json()
        print(f"  {GREEN}✓{RESET}  Backend reachable")
        print(f"     firecrawl_configured={d.get('firecrawl_configured')}  "
              f"cache_connected={d.get('cache_connected')}")
        return True
    except Exception as exc:
        print(f"  {RED}✗{RESET}  Backend unreachable: {exc}")
        return False


async def start_audit(client: httpx.AsyncClient, url: str) -> tuple[str, dict[str, str]] | None:
    _divider("2. POST /api/audit/start")
    print(f"  URL: {url}")
    print(f"  Crawling + registering agents (may take ~10s)…")
    t0 = time.monotonic()
    try:
        r = await client.post(
            f"{BACKEND}/api/audit/start",
            json={"url": url},
            timeout=TIMEOUT_CRAWL,
        )
        r.raise_for_status()
        body = r.json()
        elapsed = time.monotonic() - t0

        audit_id  = body["audit_id"]
        agent_ids = body["agent_ids"]

        print(f"  {GREEN}✓{RESET}  Audit started ({elapsed:.1f}s)")
        print(f"  audit_id  = {audit_id}")
        print(f"  agent_ids = {{")
        for name, aid in agent_ids.items():
            c = AGENT_COLOUR.get(name, CYAN)
            print(f"    {c}{name:<22}{RESET}: {DIM}{aid}{RESET}")
        print(f"  }}")
        return audit_id, agent_ids
    except Exception as exc:
        print(f"  {RED}✗{RESET}  {exc}")
        return None


async def _consume_stream(
    panel: AgentPanel,
    client: httpx.AsyncClient,
    done_event: asyncio.Event,
) -> None:
    """Subscribe to one agent's SSE stream and feed events to its panel."""
    url = f"{BACKEND}/agent/stream/{panel.agent_id}"
    try:
        async with client.stream("GET", url, timeout=TIMEOUT_AGENTS) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    try:
                        event = json.loads(line[5:])
                        panel.receive_event(event)
                    except json.JSONDecodeError:
                        pass
    except Exception as exc:
        panel.receive_event({"phase": "error", "detail": str(exc)})
    finally:
        done_event.set()


async def stream_agents(agent_ids: dict[str, str]) -> dict[str, AgentPanel]:
    _divider("3. Subscribing to 4 SSE agent streams")
    print(f"  Each line below = one SSE event from an agent\n")

    panels: dict[str, AgentPanel] = {
        name: AgentPanel(name, aid) for name, aid in agent_ids.items()
    }
    done_events = {name: asyncio.Event() for name in agent_ids}

    # Use a single long-lived client for all 4 streams
    async with httpx.AsyncClient() as client:
        tasks = [
            asyncio.create_task(
                _consume_stream(panels[name], client, done_events[name]),
                name=f"sse-{name}",
            )
            for name in agent_ids
        ]
        await asyncio.gather(*[e.wait() for e in done_events.values()])
        await asyncio.gather(*tasks)

    return panels


def print_agent_summary(panels: dict[str, AgentPanel]) -> None:
    _divider("Agent completion summary")
    for name, panel in panels.items():
        c = AGENT_COLOUR.get(name, CYAN)
        status = f"{GREEN}✓ done  score={panel.score}{RESET}" if panel.done and not panel.error \
            else f"{RED}✗ error{RESET}"
        steps = " → ".join(panel.phases)
        print(f"  {c}{BOLD}{name:<22}{RESET} {status}")
        print(f"    {DIM}{textwrap.fill(steps, 70, subsequent_indent='    ')}{RESET}")


async def poll_report(client: httpx.AsyncClient, audit_id: str) -> dict | None:
    _divider("4. Polling GET /api/audit/{audit_id}")
    deadline = time.monotonic() + TIMEOUT_AGENTS
    attempt  = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            r = await client.get(f"{BACKEND}/api/audit/{audit_id}", timeout=10.0)
            if r.status_code == 202:
                print(f"  [attempt {attempt:>2}] {DIM}still running…{RESET}", end="\r")
                await asyncio.sleep(POLL_INTERVAL)
                continue
            r.raise_for_status()
            print(f"\n  {GREEN}✓{RESET}  Report ready after {attempt} poll(s)")
            return r.json()
        except Exception as exc:
            print(f"\n  {RED}✗{RESET}  Poll error: {exc}")
            return None
    print(f"\n  {RED}✗{RESET}  Timed out waiting for report")
    return None


def _score_bar(score: int, width: int = 28) -> str:
    filled  = round(score / 100 * width)
    colour  = GREEN if score >= 70 else (YELLOW if score >= 50 else RED)
    return f"{colour}{'█' * filled}{'░' * (width - filled)}{RESET} {BOLD}{score}/100{RESET}"


def render_report_card(report: dict) -> None:
    _divider("5. AuditReport card (frontend render)")
    url   = report.get("url", "?")
    pages = report.get("pages", [])
    if not pages:
        print("  (empty report)")
        return

    page  = pages[0]
    score = page.get("ai_readiness_score", 0)
    cats  = page.get("category_scores", {})
    vis   = page.get("visibility", {})
    fixes = page.get("fixes", [])

    # Header card
    print(f"\n  ┌{'─'*56}┐")
    print(f"  │  {BOLD}AI Readiness Audit{RESET}{'':>37}│")
    print(f"  │  {DIM}{url[:52]}{RESET}{'':>{max(0,53-len(url[:52]))}}│")
    print(f"  ├{'─'*56}┤")
    print(f"  │  Overall score   {_score_bar(score, 20)}{'':>5}│")

    if cats:
        print(f"  │{'─'*56}│")
        for name, s in cats.items():
            label = name.replace("_", " ").title()[:16]
            bar   = _score_bar(s, 12)
            print(f"  │  {label:<18} {bar}{'':>1}│")

    print(f"  └{'─'*56}┘")

    # Visibility
    before = vis.get("before", {})
    after  = vis.get("after", {})
    if before:
        print(f"\n  {BOLD}Visibility — before → after fixes{RESET}")
        for bot in ("gpt", "claude", "perplexity", "gemini"):
            b = before.get(bot, 0)
            a = after.get(bot, b)
            arrow = f" → {GREEN}{a:.0%}{RESET}" if a > b else ""
            print(f"    {bot:<12} {b:.0%}{arrow}")

    # Top fixes
    if fixes:
        print(f"\n  {BOLD}Top {min(5, len(fixes))} fixes{RESET}")
        for i, f in enumerate(fixes[:5], 1):
            effort = f.get("effort", "?")
            title  = f.get("title", "")
            detail = f.get("detail", "")
            fix    = f.get("fix", "")
            print(f"\n  {i}. [{YELLOW}{effort}{RESET}] {BOLD}{title}{RESET}")
            if detail:
                print(f"     {textwrap.fill(detail, 68, subsequent_indent='     ')}")
            if fix:
                print(f"     {GREEN}Fix:{RESET} {textwrap.fill(fix, 64, subsequent_indent='          ')}")

    # Summary
    summary = report.get("summary", "")
    if summary:
        print(f"\n  {BOLD}Executive summary{RESET}")
        print(f"  {textwrap.fill(summary, 72, subsequent_indent='  ')}")

    print()


# ── main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"  {BOLD}Frontend Mock — {TEST_URL}{RESET}")
    print(f"  Simulating the complete frontend flow via API")
    print(f"{'═'*60}")

    async with httpx.AsyncClient() as client:
        ok = await check_health(client)
        if not ok:
            print(f"\n  {RED}Backend not reachable. Start with: docker compose up{RESET}\n")
            sys.exit(1)

        result = await start_audit(client, TEST_URL)
        if result is None:
            sys.exit(1)
        audit_id, agent_ids = result

    # Stream all 4 agents (uses its own client internally)
    panels = await stream_agents(agent_ids)
    print_agent_summary(panels)

    # Poll for the final report
    async with httpx.AsyncClient() as client:
        report = await poll_report(client, audit_id)

    if report:
        render_report_card(report)
    else:
        print(f"  {RED}No report available.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
