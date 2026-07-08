"""
AI Readiness Score rubric.

Weights reflect Google's AI Optimization Guide (2024):
- Content quality (E-E-A-T, non-commodity) is Google's #1 signal → 35%
- Crawlability (indexable, no JS-gating, bot access) → 30%
- Entity/topic coverage (query fan-out relies on topic depth) → 20%
- Structured data → 15% (Google explicitly says "not required for AI search")
"""
from __future__ import annotations

from app.schemas import AgentResult, Finding, SiteFacts

WEIGHTS = {
    "crawlability":   0.30,
    "content_signal": 0.35,   # up from 0.30 — Google's #1 signal
    "structured_data": 0.15,  # down from 0.20 — Google says "not required"
    "entity_topic":   0.20,
}

EFFORT_WEIGHT = {"S": 1, "M": 2, "L": 4}


def compute_score(agent_results: list[AgentResult], sitefacts: SiteFacts) -> int:
    scores: dict[str, int] = {ar.agent: ar.score for ar in agent_results}

    # Apply commodity content penalty: if content agent flagged commodity content,
    # cap its contribution (the agent itself already caps score at 60, but we
    # also reduce its weight contribution to protect the overall score accuracy)
    content_result = next((ar for ar in agent_results if ar.agent == "content_signal"), None)
    if content_result and content_result.artifacts.get("commodity_content"):
        scores["content_signal"] = min(scores["content_signal"], 60)

    raw = sum(WEIGHTS.get(agent, 0) * score for agent, score in scores.items())
    overall = round(raw)

    # Hard gates
    all_blocked = not any(sitefacts.robots.allows.model_dump(by_alias=True).values())
    if all_blocked:
        overall = min(overall, 35)

    if not sitefacts.render.content_visible_without_js:
        crawl_score = scores.get("crawlability", 100)
        if crawl_score > 25:
            scores["crawlability"] = 25
            raw = sum(WEIGHTS.get(a, 0) * s for a, s in scores.items())
            overall = round(raw)

    return max(0, min(100, overall))


def category_scores(agent_results: list[AgentResult]) -> dict[str, int]:
    return {ar.agent: ar.score for ar in agent_results}


def sort_findings(findings: list[Finding]) -> list[Finding]:
    """Sort by impact / effort_weight descending — cheapest big wins first."""
    def priority(f: Finding) -> float:
        return f.impact / EFFORT_WEIGHT.get(f.effort, 2)
    return sorted(findings, key=priority, reverse=True)


def collect_findings(agent_results: list[AgentResult]) -> list[Finding]:
    all_findings: list[Finding] = []
    for ar in agent_results:
        all_findings.extend(ar.findings)
    return sort_findings(all_findings)
