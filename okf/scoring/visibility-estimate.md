---
type: Metric
title: Before/After Visibility Estimate
status: implemented
description: Deterministic per-model visibility score (0–1) derived from SiteFacts signals, recomputed with blockers resolved to show the after-fixes projection.
tags: [scoring, visibility, estimate, google-aio]
timestamp: 2026-07-08T00:00:00Z
---

# Before/After Visibility Estimate

The demo headline: "how likely is each chatbot to find and cite this page — before vs after your fixes." Implemented in `agents/app/scoring/visibility.py`.

## Approach: derived estimate only (locked)

A deterministic function maps [SiteFacts](/data/site-facts.md) signals → per-model visibility 0–1. See [Derived Visibility decision](/decisions/derived-visibility.md) for why this design was locked.

## Signal weights (per [Google AI Optimization Guide](/decisions/google-aio-alignment.md))

| Signal | Effect | Notes |
|---|---|---|
| Bot blocked in `robots.txt` | → 0.05 (near zero) | Hard block, overrides everything else |
| JS dependency ratio > 0.9 | × 0.10 | Content almost entirely JS-injected |
| JS dependency ratio > 0.7 | × 0.35 | Heavy JS gating |
| JS dependency ratio > 0.5 | × 0.60 | Moderate JS gating |
| HTTP status ≥ 400 | → 0.0 | Page not served |
| HTTP status 3xx | × 0.80 | Redirect chain |
| Latency > 5000 ms | × 0.70 | Google flags latency as an AI-agent access barrier |
| Latency > 3000 ms | × 0.85 | |
| Valid sitemap | × 1.06 | Helps AI crawlers discover and prioritise |
| Word count < 200 | × 0.70 | Thin content, rarely cited |
| Word count < 100 | × 0.40 | |
| Schema.org types present | × 1.05 | Minor boost — Google says "not required" |
| `llms.txt` valid | × 1.03 for Claude/Perplexity only | Google Search does not use `llms.txt` |

The **after** score reruns the same function with the top 3 findings' blockers resolved (e.g. a "robots block" finding sets that bot to allowed; a "JS render" finding reduces `js_ratio` by 0.65).

## Output shape

Appears as `pages[*].visibility` in the [AuditReport](/data/audit-report.md):

```jsonc
"visibility": {
  "before": { "gpt": 0.30, "claude": 0.35, "perplexity": 0.25, "gemini": 0.40 },
  "after":  { "gpt": 0.85, "claude": 0.88, "perplexity": 0.80, "gemini": 0.90 }
}
```

Models covered: GPT (ChatGPT Search), Claude (Claude AI search), Perplexity, Gemini.

# Citations
[1] [Google AI Optimization Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
