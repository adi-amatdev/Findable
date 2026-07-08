"""
Before/after AI visibility estimate per bot.

Signal weights follow Google's AI Optimization Guide (2024):
- Bot permissions and JS-gating are the strongest signals (binary blockers)
- Page experience (latency, content structure) is a secondary access signal
- Structured data is a minor boost — NOT a major visibility driver per Google
- llms.txt: NOT used by Google Search (guide explicitly states this)
           kept as a tiny bonus for Perplexity/Claude-specific visibility only
"""
from __future__ import annotations

from app.schemas import Finding, SiteFacts, Visibility, VisibilityEstimate

_BOT_FIELD = {
    "gpt":        "GPTBot",
    "claude":     "ClaudeBot",
    "perplexity": "PerplexityBot",
    "gemini":     "Google-Extended",
}


def _base_score(sitefacts: SiteFacts, bot_key: str) -> float:
    allows = sitefacts.robots.allows.model_dump(by_alias=True)
    bot_field = _BOT_FIELD[bot_key]

    # Hard block — near zero regardless of other signals
    if not allows.get(bot_field, True):
        return 0.05

    score = 1.0

    # JS-gating (Google confirms this is a major barrier for AI crawlers)
    js_ratio = sitefacts.render.js_dependency_ratio
    if js_ratio > 0.9:
        score *= 0.10
    elif js_ratio > 0.7:
        score *= 0.35
    elif js_ratio > 0.5:
        score *= 0.60

    # HTTP status
    if sitefacts.http.status >= 400:
        return 0.0
    if sitefacts.http.status >= 300:
        score *= 0.80

    # Page experience — latency (Google: "reduce latency" for agent access)
    latency = sitefacts.http.latency_ms
    if latency > 5000:
        score *= 0.70
    elif latency > 3000:
        score *= 0.85

    # Sitemap — helps AI crawlers discover and prioritise pages
    if sitefacts.sitemap.valid:
        score = min(1.0, score * 1.06)

    # Thin content penalty (word count < 200 is almost never cited)
    if sitefacts.html.word_count < 200:
        score *= 0.70
    elif sitefacts.html.word_count < 100:
        score *= 0.40

    # Structured data — minor boost per Google's guide (helpful but not required)
    if sitefacts.structured_data.schema_types:
        score = min(1.0, score * 1.05)

    # llms.txt: only applies to Claude and Perplexity (Google ignores it per their guide)
    if bot_key in ("claude", "perplexity") and sitefacts.llms_txt.exists and sitefacts.llms_txt.valid:
        score = min(1.0, score * 1.03)

    return round(min(1.0, max(0.0, score)), 2)


def compute_visibility(sitefacts: SiteFacts) -> VisibilityEstimate:
    return VisibilityEstimate(
        gpt=_base_score(sitefacts, "gpt"),
        claude=_base_score(sitefacts, "claude"),
        perplexity=_base_score(sitefacts, "perplexity"),
        gemini=_base_score(sitefacts, "gemini"),
    )


def compute_after(sitefacts: SiteFacts, findings: list[Finding]) -> VisibilityEstimate:
    """
    Estimate visibility after the top fixes are applied.
    Only resolves signals that have concrete evidence of change.
    """
    allows = sitefacts.robots.allows.model_dump(by_alias=True).copy()
    js_ratio = sitefacts.render.js_dependency_ratio
    has_schema = bool(sitefacts.structured_data.schema_types)
    has_sitemap = sitefacts.sitemap.valid
    latency = sitefacts.http.latency_ms

    for f in findings[:3]:
        t = f.title.lower()
        if any(w in t for w in ("robot", "block", "bot", "crawl permission")):
            for k in allows:
                allows[k] = True
        if any(w in t for w in ("js", "javascript", "render", "server-side")):
            js_ratio = max(0.0, js_ratio - 0.65)
        if any(w in t for w in ("schema", "structured data", "json-ld")):
            has_schema = True
        if "sitemap" in t:
            has_sitemap = True
        if any(w in t for w in ("latency", "speed", "slow")):
            latency = min(latency, 1500)

    scores: dict[str, float] = {}
    for bot_key, bot_field in _BOT_FIELD.items():
        if not allows.get(bot_field, True):
            s = 0.05
        else:
            s = 1.0
            if js_ratio > 0.9:
                s *= 0.10
            elif js_ratio > 0.7:
                s *= 0.35
            elif js_ratio > 0.5:
                s *= 0.60
            if sitefacts.http.status >= 400:
                s = 0.0
            if latency > 5000:
                s *= 0.70
            elif latency > 3000:
                s *= 0.85
            if has_sitemap:
                s = min(1.0, s * 1.06)
            if sitefacts.html.word_count < 200:
                s *= 0.70
            if has_schema:
                s = min(1.0, s * 1.05)
        scores[bot_key] = round(min(1.0, max(0.0, s)), 2)

    return VisibilityEstimate(**scores)
