---
type: Metric
title: AI Readiness Score
status: implemented
description: Deterministic 0–100 score combining four agent sub-scores with fixed weights and hard gates that cap the overall score on critical failures.
tags: [scoring, metric, rubric, google-aio]
timestamp: 2026-07-08T00:00:00Z
---

# AI Readiness Score

The headline metric of every audit. Deterministic and transparent — judges can re-run and inspect. Implemented in `agents/app/scoring/rubric.py`.

## Formula

```
AI Readiness Score = 100 × ( 0.30 × crawlability
                            + 0.35 × content_signal
                            + 0.15 × structured_data
                            + 0.20 × entity_topic )
```

Weights were updated to reflect the [Google AI Optimization Guide](/decisions/google-aio-alignment.md):
- `content_signal` raised to **35%** — Google identifies non-commodity, expert content as its #1 AI-search signal.
- `structured_data` lowered to **15%** — Google's guide explicitly states structured data is "not required for AI search."
- `crawlability` (30%) and `entity_topic` (20%) unchanged.

## Hard gates (applied before the formula)

| Gate | Effect |
|---|---|
| robots blocks *all* AI bots | crawlability capped at ~10; overall capped at ~35 |
| `content_visible_without_js == false` | crawlability capped at ~25 |
| HTTP status ≥ 400 | audit returns an error card, no score |
| `commodity_content == true` | `content_signal` score capped at 60 (applied in both agent and rubric) |

Commodity content (generic how-tos with no first-hand experience or unique data) can never score high on content quality regardless of other signals. See [Content Signal Agent](/agents/content-signal.md).

## Findings

Each agent's [AgentResult](/data/agent-result.md) carries findings with `severity`, `effort` (S/M/L), and `impact`. The [Aggregator](/components/aggregator.md) sorts the merged finding list by **impact ÷ effort** so the top items in the fix list are the cheapest big wins.

## Per-page vs site-level

Each deep-audited page gets its own score. The [AuditReport](/data/audit-report.md) shows the landing-page score as the hero number.

# Citations
[1] [Google AI Optimization Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
[2] [Google Search Essentials](https://developers.google.com/search/docs/essentials)
[3] [Google Quality Rater Guidelines](https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf)
