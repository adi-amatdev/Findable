from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from app.agents.crawlability.sub_agent import run_sub_agent
from app.models.router import router
from app.schemas import AgentResult, CrawlReport, Finding, SiteFacts, TrafficSignal

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "crawlability_judgment.md"

AGENT_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "severity": {"type": "integer", "minimum": 1, "maximum": 5},
                    "effort": {"type": "string", "enum": ["S", "M", "L"]},
                    "impact": {"type": "integer", "minimum": 1, "maximum": 5},
                    "detail": {"type": "string"},
                    "fix": {"type": "string"},
                    "evidence": {"type": "string"},
                    "ref_url": {"type": "string"},
                },
                "required": ["id", "title", "severity", "effort", "impact", "detail", "fix", "evidence"],
            },
        },
    },
    "required": ["score", "findings"],
}


async def _get_tranco_traffic(url: str) -> TrafficSignal:
    """Get Tranco rank for the landing domain."""
    from app.agents.crawlability.tools import estimate_page_traffic_impl
    try:
        result = await estimate_page_traffic_impl(url)
        return TrafficSignal(
            domain_rank=result.get("tranco_rank"),
            source="tranco",
        )
    except Exception:
        return TrafficSignal(source="unavailable")


def _build_judgment_prompt(
    sitefacts: SiteFacts,
    crawl_reports: list[CrawlReport],
    traffic_signal: TrafficSignal,
) -> str:
    template = _PROMPT_PATH.read_text(encoding="utf-8")

    reports_text = "\n\n".join(
        f"### Pass {r.depth} — {r.url}\n"
        f"- Reachable: {r.reachable}\n"
        f"- JS-dependent: {r.js_dependent}\n"
        f"- Bot blocked: {r.bot_blocked or 'none'}\n"
        f"- Notable links: {', '.join(r.notable_links[:5]) or 'none'}\n"
        f"- Summary: {r.summary}"
        for r in crawl_reports
    )

    traffic_text = (
        f"Domain rank (Tranco): {traffic_signal.domain_rank or 'not in top 1M'}\n"
        f"Traffic estimate: {traffic_signal.cloudflare_visits_estimate or 'n/a'}\n"
        f"Source: {traffic_signal.source}"
    )

    all_blocked = not any(sitefacts.robots.allows.model_dump(by_alias=True).values())
    js_gated = not sitefacts.render.content_visible_without_js
    http_error = sitefacts.http.status >= 400

    return template.format(
        url=sitefacts.url,
        http_status=sitefacts.http.status,
        latency_ms=sitefacts.http.latency_ms,
        js_ratio=sitefacts.render.js_dependency_ratio,
        content_visible=sitefacts.render.content_visible_without_js,
        robots_allows=json.dumps(sitefacts.robots.allows.model_dump(by_alias=True), indent=2),
        sitemap_valid=sitefacts.sitemap.valid,
        sitemap_url_count=sitefacts.sitemap.url_count,
        schema_types=", ".join(sitefacts.structured_data.schema_types) or "none",
        crawl_reports=reports_text or "No sub-agent reports available.",
        traffic=traffic_text,
        gate_all_blocked=all_blocked,
        gate_js_gated=js_gated,
        gate_http_error=http_error,
    )


async def run_crawlability_agent(sitefacts: SiteFacts) -> AgentResult:
    t0 = time.monotonic()

    # Run sub-agent (3-pass crawl) and traffic estimation concurrently
    crawl_reports, traffic_signal = await asyncio.gather(
        run_sub_agent(sitefacts, max_depth=3),
        _get_tranco_traffic(sitefacts.url),
        return_exceptions=True,
    )

    if isinstance(crawl_reports, Exception):
        log.warning("Sub-agent failed: %s", crawl_reports)
        crawl_reports = []
    if isinstance(traffic_signal, Exception):
        log.warning("Traffic estimation failed: %s", traffic_signal)
        traffic_signal = TrafficSignal(source="unavailable")

    prompt = _build_judgment_prompt(sitefacts, crawl_reports, traffic_signal)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a crawlability auditor evaluating how well AI search crawlers "
                "can access and index a website. Respond only with valid JSON matching "
                "the requested schema."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    response = await router.call_with_fallback(
        "crawlability_judgment",
        messages=messages,
        response_format={"type": "json_object"},
        guided_json=AGENT_RESULT_SCHEMA,
        temperature=0.1,
        max_tokens=3000,
    )

    latency_ms = (time.monotonic() - t0) * 1000
    model_used = response["choices"][0].get("model", "unknown")
    tokens = response.get("usage", {}).get("total_tokens", 0)

    from app.models.client import _strip_markdown_fences
    raw_text = _strip_markdown_fences(response["choices"][0]["message"]["content"] or "{}")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        log.warning("Crawlability agent returned invalid JSON; using fallback.")
        data = {"score": 50, "findings": []}

    findings = [Finding(**f) for f in data.get("findings", [])]
    score = max(0, min(100, int(data.get("score", 50))))

    # Hard gates
    all_blocked = not any(sitefacts.robots.allows.model_dump(by_alias=True).values())
    if all_blocked:
        score = min(score, 10)
    elif not sitefacts.render.content_visible_without_js:
        score = min(score, 25)

    return AgentResult(
        agent="crawlability",
        score=score,
        findings=findings,
        traffic_signal=traffic_signal,
        crawl_reports=crawl_reports if isinstance(crawl_reports, list) else [],
        model_used=model_used,
        latency_ms=round(latency_ms, 1),
        tokens=tokens,
    )
