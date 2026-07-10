from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.models.router import router
from app.schemas import (
    AgentResult,
    AuditReport,
    Finding,
    PageResult,
    SiteCoverage,
    SiteFacts,
    SiteSummary,
    Visibility,
)
from app.scoring.rubric import category_scores, collect_findings, compute_score
from app.scoring.visibility import compute_after, compute_visibility

log = logging.getLogger(__name__)


def _systemic_findings(page_results: list[tuple[SiteFacts, list[AgentResult]]]) -> list[Finding]:
    if len(page_results) < 2:
        return []

    threshold = len(page_results) * 0.5
    title_counter: Counter = Counter()
    finding_by_title: dict[str, Finding] = {}

    for _, agent_results in page_results:
        seen: set[str] = set()
        for ar in agent_results:
            for f in ar.findings:
                if f.title not in seen:
                    title_counter[f.title] += 1
                    finding_by_title[f.title] = f
                    seen.add(f.title)

    return [
        finding_by_title[title]
        for title, count in title_counter.items()
        if count > threshold
    ][:5]


def build_summary_prompt(page_results: list[PageResult], site_score: int) -> str:
    findings_text = "\n".join(
        f"- [{f.severity}/5 severity, effort={f.effort}] {f.title}: {f.detail[:100]}"
        for page in page_results
        for f in page.fixes[:5]
    )
    return (
        f"You are writing an executive summary for an AI-search readiness audit.\n\n"
        f"Overall AI Readiness Score: {site_score}/100\n\n"
        f"Top findings across {len(page_results)} page(s):\n{findings_text}\n\n"
        f"Write a 3-4 sentence executive summary that:\n"
        f"1. States the overall readiness level and what it means\n"
        f"2. Names the 2-3 most impactful issues\n"
        f"3. Gives a sense of the effort required to improve\n\n"
        f"Be direct and specific. No filler. No markdown."
    )


async def _write_summary(page_results: list[PageResult], site_score: int) -> str:
    prompt = build_summary_prompt(page_results, site_score)
    try:
        response = await router.call_with_fallback(
            "report_writer",
            agent="report_writer",
            messages=[
                {"role": "system", "content": "You write concise, grounded audit summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        log.warning("Summary LLM call failed: %s", exc)
        return f"AI Readiness Score: {site_score}/100. Review the findings below for prioritised fixes."


async def aggregate(page_data: list[tuple[SiteFacts, list[AgentResult]]]) -> AuditReport:
    """
    Combine agent results into a final AuditReport.
    page_data: list of (SiteFacts, [4 AgentResults]); first item is landing page.
    """
    page_results: list[PageResult] = []

    for idx, (sitefacts, agent_results) in enumerate(page_data):
        score = compute_score(agent_results, sitefacts)
        cat_scores = category_scores(agent_results)
        findings = collect_findings(agent_results)
        before = compute_visibility(sitefacts)
        after = compute_after(sitefacts, findings)

        page_results.append(PageResult(
            url=sitefacts.url,
            role="landing" if idx == 0 else "follow_up",
            ai_readiness_score=score,
            category_scores=cat_scores,
            visibility=Visibility(before=before, after=after),
            fixes=findings,
            agent_results=agent_results,
        ))

    site_score = page_results[0].ai_readiness_score if page_results else 0
    landing_sf = page_data[0][0] if page_data else None

    coverage = SiteCoverage(
        has_schema_pct=1.0 if (landing_sf and landing_sf.structured_data.schema_types) else 0.0,
        js_rendered_pct=landing_sf.render.js_dependency_ratio if landing_sf else 0.0,
        meta_desc_pct=1.0 if (landing_sf and landing_sf.html.meta_description) else 0.0,
        author_date_pct=1.0 if (landing_sf and landing_sf.authorship.byline_present) else 0.0,
    )

    systemic = _systemic_findings(page_data)

    robots_summary: dict[str, Any] = {}
    if landing_sf:
        allows = landing_sf.robots.allows.model_dump(by_alias=True)
        blocked = [bot for bot, ok in allows.items() if not ok]
        robots_summary = {"blocks_ai_bots": blocked}

    summary = await _write_summary(page_results, site_score)

    return AuditReport(
        url=page_data[0][0].url if page_data else "",
        generated_at=datetime.now(timezone.utc).isoformat(),
        scope={"deep_pages": len(page_results), "shallow_pages": 0},
        summary=summary,
        site=SiteSummary(
            ai_readiness_score=site_score,
            coverage=coverage,
            robots=robots_summary,
            sitemap={"valid": landing_sf.sitemap.valid if landing_sf else False},
            llms_txt={"exists": landing_sf.llms_txt.exists if landing_sf else False},
            systemic_fixes=systemic,
        ),
        pages=page_results,
    )
