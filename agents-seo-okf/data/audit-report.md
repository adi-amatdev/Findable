---
type: Data Contract
title: AuditReport
description: The final multi-page audit output — headline score, per-page deep results, site-wide coverage stats, before/after visibility, and an LLM-written executive summary.
tags: [data, contract, report, output]
timestamp: 2026-07-08T00:00:00Z
---

# AuditReport

Produced by the [Aggregator](/components/aggregator.md). Returned by `GET /api/audit/{id}`. Rendered by the [Frontend](/components/frontend.md) and exported as PDF by [PDF Export](/components/pdf-export.md).

## Schema

```jsonc
{
  "url": "...", "generated_at": "ISO8601",
  "scope": { "deep_pages": 5, "shallow_pages": 48 },
  "summary": "LLM-written executive summary grounded in the findings",

  "site": {
    "ai_readiness_score": 58,
    "coverage": { "has_schema_pct": 0.32, "js_rendered_pct": 0.61,
                  "meta_desc_pct": 0.74, "author_date_pct": 0.40 },
    "robots": { "blocks_ai_bots": ["PerplexityBot"] },
    "sitemap": { "valid": true },
    "llms_txt": { "exists": false },
    "systemic_fixes": []   // issues affecting most pages → one recommendation each
  },

  "pages": [
    {
      "url": "...", "role": "landing",   // "landing" | "follow_up"
      "ai_readiness_score": 58,
      "category_scores": { "crawlability": 45, "content": 62,
                           "structured_data": 70, "entity_topic": 55 },
      "visibility": {
        "before": { "gpt": 0.30, "claude": 0.35, "perplexity": 0.25, "gemini": 0.40 },
        "after":  { "gpt": 0.85, "claude": 0.88, "perplexity": 0.80, "gemini": 0.90 }
      },
      "fixes": [],            // page findings sorted by impact/effort
      "agent_results": []     // 4 × AgentResult
    }
  ]
}
```

## Hero number

The dashboard shows `pages[0].ai_readiness_score` (the landing page) as the headline. Per-page scores appear in a breakdown panel; `site.coverage` feeds the separate site-health panel.

## Systemic vs page-specific findings

If a coverage stat is poor across most pages (e.g. `has_schema_pct < 0.3`), it collapses into a single `site.systemic_fixes` recommendation rather than repeating per page.

## Visibility estimate

`pages[*].visibility.before` and `.after` are produced by the [Before/After Visibility Estimate](/scoring/visibility-estimate.md) component.
