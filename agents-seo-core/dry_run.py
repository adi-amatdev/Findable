"""
dry_run.py — run the full agent + aggregator pipeline against a pre-built SiteFacts.

Usage:
    python dry_run.py <path-to-sitefacts.json>

The sub-agent does REAL http crawling (httpx + Tranco). No stubs.
All LLM calls go to local Ollama (gemma4:e2b) unless overridden.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import textwrap
import time
from pathlib import Path

# Environment for local-only run
os.environ.setdefault("LOCAL_ONLY", "1")
os.environ.setdefault("LOCAL_BACKEND", "ollama")
os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
os.environ.setdefault("LOCAL_LIGHT_MODEL", "gemma4:e2b")
os.environ.setdefault("LOCAL_HEAVY_MODEL", "gemma4:e2b")
os.environ.setdefault("LOCAL_MID_MODEL", "gemma4:e2b")

sys.path.insert(0, str(Path(__file__).parent))

from app.schemas import AgentResult, AuditReport, SiteFacts


# ---------------------------------------------------------------------------
# Load SiteFacts from JSON file
# ---------------------------------------------------------------------------

def load_sitefacts(path: str) -> SiteFacts:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    # Accept both 'markdown' and 'page_markdown' keys
    if "markdown" in raw and "page_markdown" not in raw:
        raw["page_markdown"] = raw.pop("markdown")
    return SiteFacts.model_validate(raw)


# ---------------------------------------------------------------------------
# Run agents (real sub-agent crawl, real Tranco, real LLM calls)
# ---------------------------------------------------------------------------

async def run_all_agents(sitefacts: SiteFacts) -> list[AgentResult]:
    from app.agents.crawlability.agent import run_crawlability_agent
    from app.agents.content_signal import ContentSignalAgent
    from app.agents.entity_topic import EntityTopicAgent
    from app.agents.structured_data import StructuredDataAgent

    print(f"\n{'='*60}")
    print(f"  DRY RUN - {sitefacts.url}")
    print(f"{'='*60}\n")
    print("  Sub-agent will crawl live pages via httpx + Tranco.")
    print("  This may take 30-60 seconds for the crawlability pass.\n")

    results: list[AgentResult] = []
    agent_tasks = [
        ("crawlability",    run_crawlability_agent(sitefacts)),
        ("content_signal",  ContentSignalAgent().run(sitefacts)),
        ("structured_data", StructuredDataAgent().run(sitefacts)),
        ("entity_topic",    EntityTopicAgent().run(sitefacts)),
    ]

    for name, coro in agent_tasks:
        print(f"  [ ] Running {name} agent ...", end="", flush=True)
        t0 = time.monotonic()
        try:
            result = await coro
            elapsed = time.monotonic() - t0
            print(f"\r  [OK] {name:<22} score={result.score}  ({elapsed:.1f}s)")
            results.append(result)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            print(f"\r  [FAIL] {name:<20} ({elapsed:.1f}s): {exc}")
            results.append(AgentResult(agent=name, score=50))

    return results


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

async def run_aggregator(sitefacts: SiteFacts, agent_results: list[AgentResult]) -> AuditReport:
    # Stub the executive summary LLM call in LOCAL_ONLY mode to avoid Fireworks
    import app.report.aggregator as agg_mod
    _orig = agg_mod._write_summary

    async def _local_summary(page_results, site_score):
        top_issues = [f.title for p in page_results for f in p.fixes[:3]]
        return (
            f"AI Readiness Score: {site_score}/100. "
            f"Top issues: {', '.join(top_issues[:3]) or 'none identified'}. "
            f"(Local dry-run — executive summary LLM call skipped.)"
        )

    agg_mod._write_summary = _local_summary
    try:
        from app.report.aggregator import aggregate
        return await aggregate([(sitefacts, agent_results)])
    finally:
        agg_mod._write_summary = _orig


# ---------------------------------------------------------------------------
# Pretty-print report
# ---------------------------------------------------------------------------

SEVERITY_LABEL = {1: "LOW", 2: "LOW", 3: "MED", 4: "HIGH", 5: "CRIT"}
EFFORT_LABEL   = {"S": "small", "M": "medium", "L": "large"}


def _bar(score: int, width: int = 30) -> str:
    filled = round(score / 100 * width)
    return f"{'#' * filled}{'-' * (width - filled)} {score}/100"


def print_report(report: AuditReport) -> None:
    page = report.pages[0]

    print(f"\n{'='*62}")
    print(f"  AI READINESS REPORT - {report.url}")
    print(f"{'='*62}")
    print(f"\n  Overall score   {_bar(page.ai_readiness_score)}")

    print(f"\n  Category breakdown:")
    for cat, score in page.category_scores.items():
        label = cat.replace("_", " ").title()
        print(f"    {label:<22} {_bar(score, 20)}")

    print(f"\n  AI Visibility estimate:")
    before = page.visibility.before
    after  = page.visibility.after
    for bot in ("gpt", "claude", "perplexity", "gemini"):
        b = getattr(before, bot)
        a = getattr(after, bot)
        delta = f"  -> {a:.0%} after fixes" if a > b else ""
        print(f"    {bot:<12} {b:.0%}{delta}")

    print(f"\n  Site signals:")
    sf_summary = {
        "Robots.txt":  "[YES] exists" if report.site.robots else "[NO]  missing",
        "Sitemap":     "[YES] valid"  if report.site.sitemap.get("valid") else "[NO]  invalid/missing",
        "llms.txt":    "[YES] exists" if report.site.llms_txt.get("exists") else "[NO]  missing",
    }
    for k, v in sf_summary.items():
        print(f"    {k:<18} {v}")

    # Sub-agent crawl reports
    crawl_agent = next((ar for ar in page.agent_results if ar.agent == "crawlability"), None)
    if crawl_agent and crawl_agent.crawl_reports:
        print(f"\n  Sub-agent crawl reports ({len(crawl_agent.crawl_reports)} pass(es)):")
        for cr in crawl_agent.crawl_reports:
            print(f"    Pass {cr.depth} -- {cr.url}")
            print(f"      Reachable: {cr.reachable}  JS-dependent: {cr.js_dependent}  Bot-blocked: {cr.bot_blocked or 'none'}")
            if cr.notable_links:
                print(f"      Top links: {', '.join(cr.notable_links[:3])}")
            print(f"      {textwrap.fill(cr.summary, 70, subsequent_indent='      ')}")

    # Top findings
    print(f"\n  Top findings (impact/effort ratio):")
    for i, f in enumerate(page.fixes[:10], 1):
        sev    = SEVERITY_LABEL.get(f.severity, "?")
        effort = EFFORT_LABEL.get(f.effort, f.effort)
        print(f"\n  {i:>2}. [{sev}] {f.title}  (effort={effort}, impact={f.impact}/5)")
        print(f"      {textwrap.fill(f.detail, 72, subsequent_indent='      ')}")
        print(f"      Fix: {textwrap.fill(f.fix, 68, subsequent_indent='           ')}")
        if f.ref_url:
            print(f"      Ref: {f.ref_url}")

    # Knowledge graph
    entity_agent = next((ar for ar in page.agent_results if ar.agent == "entity_topic"), None)
    if entity_agent and entity_agent.artifacts.get("knowledge_graph"):
        kg = entity_agent.artifacts["knowledge_graph"]
        nodes = kg.get("nodes", [])
        edges = kg.get("edges", [])
        print(f"\n  Knowledge graph: {len(nodes)} nodes, {len(edges)} edges")
        for n in nodes[:6]:
            print(f"    * {n.get('label','?')} ({n.get('type','?')})")

    print(f"\n  Executive summary:")
    print(f"  {textwrap.fill(report.summary, 72, subsequent_indent='  ')}")
    print(f"\n{'='*62}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "message.txt"
    if not Path(path).exists():
        path = str(Path(__file__).parent.parent / path)

    print(f"Loading SiteFacts from: {path}")
    sitefacts = load_sitefacts(path)
    print(f"  URL:    {sitefacts.url}")
    print(f"  HTTP:   {sitefacts.http.status} | JS ratio: {sitefacts.render.js_dependency_ratio:.3f} | Words: {sitefacts.html.word_count}")
    print(f"  Schema: {sitefacts.structured_data.schema_types or 'none'}")
    print(f"  Entities: {len(sitefacts.entities_raw)}")

    agent_results = await run_all_agents(sitefacts)
    report = await run_aggregator(sitefacts, agent_results)
    print_report(report)

    out_path = Path(__file__).parent / "dry_run_report.json"
    out_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(f"Full report saved -> {out_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
