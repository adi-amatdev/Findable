---
type: Metric
title: AI Readiness Score
status: planned
description: Deterministic 0–100 score combining four agent sub-scores with fixed weights and hard gates that cap the overall score on critical failures.
tags: [scoring, metric, rubric]
timestamp: 2026-07-08T00:00:00Z
---

# AI Readiness Score

The headline metric of every audit. Deterministic and transparent — judges can re-run and inspect.

## Formula

```
AI Readiness Score = 100 × ( 0.30 × crawlability
                            + 0.30 × content
                            + 0.20 × structured_data
                            + 0.20 × entity_topic )
```

Weights reflect the relative importance of each dimension for AI-search visibility: crawlability and content quality are the biggest levers; structured data and entity signals are amplifiers.

## Hard gates (applied before the formula)

| Gate | Effect |
|---|---|
| robots blocks *all* AI bots | crawlability capped at ~10; overall capped at ~35 |
| `content_visible_without_js == false` | crawlability capped at ~25 |
| HTTP status ≥ 400 | audit returns an error card, no score |

These gates exist because some failures completely prevent AI crawlers from indexing the page, making the sub-score formula meaningless. The [Crawlability agent](/agents/crawlability.md) feeds the gate inputs.

## Findings

Each agent's [AgentResult](/data/agent-result.md) carries findings with `severity`, `effort` (S/M/L), and `impact`. The [Aggregator](/components/aggregator.md) sorts the merged finding list by **impact ÷ effort** so the top items in the fix list are the cheapest big wins.

## Per-page vs site-level

Each deep-audited page gets its own score. The [AuditReport](/data/audit-report.md) shows the landing-page score as the hero number. The Tier-3 shallow pass produces coverage stats, not scores.

# Citations
[1] [Google Search Essentials](https://developers.google.com/search/docs/essentials)
[2] [Google Quality Rater Guidelines](https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf)
