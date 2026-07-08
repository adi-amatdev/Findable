---
type: Metric
title: Before/After Visibility Estimate
status: planned
description: Deterministic per-model visibility score (0–1) derived from SiteFacts signals, recomputed with blockers resolved to show the after-fixes projection.
tags: [scoring, visibility, estimate]
timestamp: 2026-07-08T00:00:00Z
---

# Before/After Visibility Estimate

The demo headline: "how likely is each chatbot to find and cite this page — before vs after your fixes."

## Approach: derived estimate only (locked)

A deterministic function maps [SiteFacts](/data/site-facts.md) signals → per-model visibility 0–1:

- Blocked bot → ~0 for that model.
- JS-only page (`content_visible_without_js == false`) → low across all models.
- Strong schema + allowed + server-rendered → high across all models.

The **after** number is computed by rerunning the same function with the top blockers resolved. Fast, honest as an *estimate*, and visually striking.

**A real retrieval simulation** (embed the page, generate questions, test if a model can answer) would give a *measured* before/after — noted as a post-POC direction, explicitly out of scope for this build.

See [Derived Visibility decision](/decisions/derived-visibility.md) for why this choice was locked.

## Output shape

Appears as `pages[*].visibility` in the [AuditReport](/data/audit-report.md):

```jsonc
"visibility": {
  "before": { "gpt": 0.30, "claude": 0.35, "perplexity": 0.25, "gemini": 0.40 },
  "after":  { "gpt": 0.85, "claude": 0.88, "perplexity": 0.80, "gemini": 0.90 }
}
```

Models covered: GPT (ChatGPT Search), Claude (Claude AI search), Perplexity, Gemini.
