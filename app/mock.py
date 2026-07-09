"""
Mock-stream passthrough  (MOCK_STREAM=true).

When enabled:
  - POST /api/audit/start  skips Firecrawl and agents-api entirely.
  - A static SiteFacts snapshot is used in place of a real crawl.
  - Four fake SSE event timelines are emitted on realistic schedules.
  - A static AuditReport becomes available once the last agent "finishes".
  - Zero Firecrawl credits, zero LLM calls, zero agents-api traffic.

The SSE wire format and all endpoint paths are identical to the real pipeline,
so the frontend sees no difference.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import AsyncIterator

from .models.contracts import (
    AuthorshipFacts,
    Dates,
    Entity,
    HttpFacts,
    HtmlFacts,
    LinkFacts,
    LlmsTxtFacts,
    OutlineItem,
    RenderFacts,
    RobotsFacts,
    SiteFacts,
    SitemapFacts,
    StructuredDataFacts,
)

# ---------------------------------------------------------------------------
# In-process state  (process-lifetime; one dict per audit_id / agent_id)
# ---------------------------------------------------------------------------

_queues: dict[str, asyncio.Queue] = {}
_results: dict[str, dict | None] = {}


def register_agent(agent_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[agent_id] = q
    return q


def get_queue(agent_id: str) -> asyncio.Queue | None:
    return _queues.get(agent_id)


async def _emit(agent_id: str, payload: dict) -> None:
    q = _queues.get(agent_id)
    if q is not None:
        await q.put(payload)


async def _close(agent_id: str) -> None:
    q = _queues.get(agent_id)
    if q is not None:
        await q.put(None)


def store_result(audit_id: str, report: dict) -> None:
    _results[audit_id] = report


def get_result(audit_id: str) -> dict | None:
    return _results.get(audit_id)


def clear() -> None:
    """Remove all state (used in tests)."""
    _queues.clear()
    _results.clear()


# ---------------------------------------------------------------------------
# Static SiteFacts  (replaces the Firecrawl crawl)
# ---------------------------------------------------------------------------

MOCK_SITEFACTS = SiteFacts(
    url="https://mock.example.com",
    final_url="https://mock.example.com/",
    fetched_at="2026-07-08T00:00:00Z",
    http=HttpFacts(status=200, latency_ms=312, redirects=1, content_type="text/html"),
    robots=RobotsFacts(
        exists=True,
        allows={
            "GPTBot": True,
            "ClaudeBot": True,
            "PerplexityBot": True,
            "OAI-SearchBot": True,
            "Google-Extended": False,
            "CCBot": True,
        },
        sitemap_refs=["https://mock.example.com/sitemap.xml"],
    ),
    sitemap=SitemapFacts(exists=True, valid=True, url_count=87),
    llms_txt=LlmsTxtFacts(exists=False, valid=False, has_summary=False, link_count=0),
    render=RenderFacts(
        raw_text_len=1800,
        rendered_text_len=4400,
        js_dependency_ratio=0.59,
        content_visible_without_js=False,
    ),
    html=HtmlFacts(
        title="Example Domain — Products & Services",
        meta_description="We help companies grow. Trusted by 10,000 teams worldwide.",
        canonical="https://mock.example.com/",
        lang="en",
        outline=[
            OutlineItem(level=1, text="Welcome to Example"),
            OutlineItem(level=2, text="Our Products"),
            OutlineItem(level=2, text="Why Choose Us"),
            OutlineItem(level=3, text="Customer Stories"),
        ],
        word_count=640,
        og={"title": "Example Domain", "type": "website", "url": "https://mock.example.com/"},
        twitter={},
    ),
    structured_data=StructuredDataFacts(
        schema_types=["Organization", "WebSite"],
        jsonld_valid=True,
        errors=[],
    ),
    links=LinkFacts(internal=24, external=6, outbound_citations=2),
    authorship=AuthorshipFacts(
        byline_present=False,
        author_schema=False,
        dates=Dates(published=None, modified=None),
    ),
    entities_raw=[
        Entity(text="Example Domain", label="ORG"),
        Entity(text="United States", label="GPE"),
        Entity(text="2024", label="DATE"),
    ],
    markdown=(
        "# Welcome to Example\n\n"
        "We help companies grow. Trusted by 10,000 teams worldwide.\n\n"
        "## Our Products\n\n"
        "- Product Alpha — enterprise analytics\n"
        "- Product Beta — workflow automation\n\n"
        "## Why Choose Us\n\n"
        "Fast, reliable, and secure. Our platform scales with your business.\n\n"
        "### Customer Stories\n\n"
        "Learn how top companies use Example to increase productivity by 40%.\n"
    ),
)


# ---------------------------------------------------------------------------
# Static AuditReport  (replaces agents + aggregator)
# ---------------------------------------------------------------------------

MOCK_REPORT: dict = {
    "url": "https://mock.example.com",
    "ai_readiness_score": 62,
    "scores": {
        "crawlability": 55,
        "content_signal": 70,
        "structured_data": 68,
        "entity_topic": 58,
    },
    "visibility": {
        "before": {"gpt": 0.31, "claude": 0.28, "perplexity": 0.44, "gemini": 0.36},
        "after":  {"gpt": 0.67, "claude": 0.63, "perplexity": 0.72, "gemini": 0.65},
    },
    "findings": [
        {
            "id": "crawl-01",
            "agent": "crawlability",
            "title": "High JS dependency hides 59% of body text",
            "severity": 5,
            "effort": "L",
            "impact": 5,
            "detail": "js_dependency_ratio=0.59; content_visible_without_js=false.",
            "fix": "Implement server-side rendering (SSR) or add <noscript> fallback for critical content.",
        },
        {
            "id": "crawl-02",
            "agent": "crawlability",
            "title": "Google-Extended blocked in robots.txt",
            "severity": 4,
            "effort": "S",
            "impact": 4,
            "detail": "Google-Extended (Gemini's crawler) is disallowed site-wide.",
            "fix": "Remove or narrow the Google-Extended Disallow rule.",
        },
        {
            "id": "content-01",
            "agent": "content_signal",
            "title": "No author byline or publication dates on any page",
            "severity": 4,
            "effort": "M",
            "impact": 4,
            "detail": "byline_present=false, author_schema=false, dates.published=null.",
            "fix": "Add visible author bylines and ISO 8601 publication dates to all article pages.",
        },
        {
            "id": "struct-01",
            "agent": "structured_data",
            "title": "llms.txt not present",
            "severity": 3,
            "effort": "S",
            "impact": 3,
            "detail": "llms_txt.exists=false. AI agents that read llms.txt get no structured guidance.",
            "fix": "Create /llms.txt listing key pages and a plain-English site summary.",
        },
        {
            "id": "entity-01",
            "agent": "entity_topic",
            "title": "Brand entity missing from <title> tags",
            "severity": 3,
            "effort": "S",
            "impact": 3,
            "detail": "Primary entity 'Example Domain' is absent from page <title>.",
            "fix": "Prepend the brand name to <title> on all pages.",
        },
    ],
    "summary": (
        "The site scores 62/100 for AI readiness. The two highest-impact blockers are "
        "JS-heavy rendering (59% of content invisible to text-only AI crawlers) and a "
        "Google-Extended robots.txt block that shuts out Gemini entirely. Fixing those "
        "two issues alone is projected to raise the score to ~80 and double visibility "
        "across GPT, Claude, and Perplexity."
    ),
    "mock": True,
}


# ---------------------------------------------------------------------------
# Phase schedules
# ---------------------------------------------------------------------------

# Each entry: (delay_from_start_seconds, phase, detail, score)
_SCHEDULES: dict[str, list[tuple[float, str, str | None, int | None]]] = {
    "crawlability": [
        (0.0, "started",           None,                   None),
        (0.5, "sub_agent_pass_1",  "seed crawl",           None),
        (2.0, "sub_agent_pass_2",  "deep crawl 4 pages",   None),
        (3.5, "sub_agent_pass_3",  "cross-page synthesis", None),
        (4.3, "judgment_call",     "crawlability",         None),
        (5.2, "parsing_result",    None,                   None),
        (5.5, "complete",          None,                   55),
    ],
    "content_signal": [
        (0.0, "started",          None,             None),
        (0.3, "building_prompt",  None,             None),
        (0.8, "llm_call",         "content_signal", None),
        (3.6, "parsing_result",   None,             None),
        (3.8, "complete",         None,             70),
    ],
    "structured_data": [
        (0.0, "started",          None,              None),
        (0.2, "building_prompt",  None,              None),
        (0.6, "llm_call",         "structured_data", None),
        (2.3, "parsing_result",   None,              None),
        (2.5, "complete",         None,              68),
    ],
    "entity_topic": [
        (0.0, "started",          None,           None),
        (0.2, "building_prompt",  None,           None),
        (0.7, "llm_call",         "entity_topic", None),
        (4.0, "parsing_result",   None,           None),
        (4.2, "complete",         None,           58),
    ],
}

# How long after start() the report becomes available (just after the last agent)
_REPORT_DELAY = 4.0


# ---------------------------------------------------------------------------
# Background task: emit fake events, then store the report
# ---------------------------------------------------------------------------

async def _run_one_agent(agent_id: str, agent_name: str, started_at: float) -> None:
    schedule = _SCHEDULES[agent_name]
    elapsed = 0.0
    for (delay, phase, detail, score) in schedule:
        wait = delay - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        elapsed = delay
        payload = {
            "agent_id": agent_id,
            "agent": agent_name,
            "phase": phase,
            "detail": detail,
            "score": score,
            "ts": started_at + delay,
        }
        await _emit(agent_id, payload)
    await _close(agent_id)


async def run_mock_audit(audit_id: str, agent_ids: dict[str, str]) -> None:
    """
    Fire all four fake agent timelines in parallel, then store the mock report.
    Called via asyncio.create_task — runs in the background.
    """
    started_at = time.time()
    tasks = [
        asyncio.create_task(_run_one_agent(aid, name, started_at))
        for name, aid in agent_ids.items()
    ]
    # Wait for the last agent to finish, then store the report
    await asyncio.gather(*tasks)
    await asyncio.sleep(max(0.0, _REPORT_DELAY - (time.time() - started_at)))
    report = dict(MOCK_REPORT)
    report["url"] = f"[mock] requested via audit_id={audit_id}"
    store_result(audit_id, report)


# ---------------------------------------------------------------------------
# SSE generator  (consumed by GET /agent/stream/{agent_id} in mock mode)
# ---------------------------------------------------------------------------

async def sse_stream(agent_id: str) -> AsyncIterator[bytes]:
    q = get_queue(agent_id)
    if q is None:
        return
    while True:
        event = await q.get()
        if event is None:
            break
        yield f"event: agent_status\ndata: {json.dumps(event)}\n\n".encode()
