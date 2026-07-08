---
type: Decision
title: Google AI Optimization Guide Alignment
status: implemented
description: Scoring weights, visibility signals, and agent prompts were updated to reflect Google's official AI Optimization Guide after finding divergences between the original spec and Google's published recommendations.
tags: [decision, scoring, google-aio, eeat, content, visibility]
timestamp: 2026-07-08T00:00:00Z
---

# Decision: Align Scoring with Google AI Optimization Guide

After reviewing Google's official AI Optimization Guide, the original scoring weights and signal assumptions were found to diverge from Google's published recommendations in several significant ways. This decision records what changed and why.

## What we found vs. what we had

| Topic | Original assumption | Google's actual guidance |
|---|---|---|
| `llms.txt` | Scored as meaningful signal across all AI systems | "Google Search does not use `llms.txt`" — explicitly stated |
| Structured data | 20% weight; framed as a primary signal | "Structured data isn't required for AI search" |
| Content quality | 30% weight; E-E-A-T framed as one of four equal signals | Non-commodity content is Google's **#1** AI-search signal |
| Page latency | Not in visibility scoring | "Reduce latency" listed as explicit AI agent accessibility requirement |
| Agentic accessibility | Not assessed | DOM structure + accessibility tree explicitly named as factors |

## Changes made

### Scoring weights (`agents/app/scoring/rubric.py`)

```
content_signal:  0.30 → 0.35   (Google's #1 signal)
structured_data: 0.20 → 0.15   (Google: "not required")
crawlability:    0.30 → 0.30   (unchanged)
entity_topic:    0.20 → 0.20   (unchanged)
```

### Commodity content cap (new)

If the Content Signal agent returns `commodity_content: true` (generic how-to, no first-hand experience, no proprietary data), the content score is **capped at 60** in both the agent and the rubric. Google's guide identifies non-commodity, expert content as the differentiating factor — commodity pages compete poorly in AI search regardless of other signals.

### Visibility estimate signals (`agents/app/scoring/visibility.py`)

- **Latency penalty added**: response > 5000 ms → ×0.70; > 3000 ms → ×0.85.
- **JS-gating stricter**: thresholds tightened to 0.10×/0.35×/0.60× (was 0.15×/0.40×/0.65×).
- **`llms.txt` scoped**: bonus (×1.03) applied **only** to Claude and Perplexity bots. Google and GPT bots are unaffected.
- **Schema.org bonus reduced**: ×1.05 (was ×1.10) — minor amplifier, not a primary driver.

### Prompts updated

- `prompts/content_signal.md` — added Step 1 commodity assessment; `commodity_content` field in JSON output; Google AIO Guide referenced directly.
- `prompts/structured_data.md` — three-tier weighting (meta 50%, schema 35%, llms.txt 15%); explicit note that Google doesn't use `llms.txt`.
- `prompts/crawlability_judgment.md` — added agentic accessibility section; latency cap (>5000 ms → score ≤ 80); references Google AIO Guide.

## What we kept

- The four-agent structure (crawlability, content, structured data, entity/topic) remains unchanged — Google's guide doesn't contradict this decomposition.
- Hard gates (bot block → score ≤ 35; JS-only → crawlability ≤ 25) remain — these reflect binary access failures, which Google's guide also treats as blockers.
- The [Derived Visibility design](/decisions/derived-visibility.md) remains locked.

# Citations
[1] [Google AI Optimization Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
