---
type: Agent
title: Structured Data Agent
status: implemented
description: Judges whether an AI can extract key facts from the page's meta tags, schema.org markup, and llms.txt; meta extraction is the primary signal per Google's AI Optimization Guide.
tags: [agent, structured-data, schema, jsonld, llmstxt, google-aio]
timestamp: 2026-07-08T00:00:00Z
---

# Structured Data Agent

One of four concurrent agents in the [agent layer](/agents/). Implements the contract: **in** = [SiteFacts](/data/site-facts.md) + page markdown slice, **out** = [AgentResult](/data/agent-result.md). Implemented in `agents/app/agents/structured_data.py`.

## Deterministic inputs it reads

From [SiteFacts](/data/site-facts.md):
- `html.meta_description`, `html.title`, `html.og`, `html.twitter` — primary extraction signals
- `structured_data.schema_types`, `structured_data.jsonld_valid`, `structured_data.errors`
- `llms_txt.exists`, `llms_txt.valid`, `llms_txt.has_summary`, `llms_txt.link_count`

## LLM judgment

Runs one call via the [Model Router](/components/model-router.md) (primary: mid-weight model local). Prompt (`prompts/structured_data.md`) uses a three-tier weighting per the [Google AI Optimization Guide](/decisions/google-aio-alignment.md):

| Signal tier | Weight | Reasoning |
|---|---|---|
| Meta extraction (title, meta description, OG tags) | 50% | Primary way AI systems extract page context |
| Schema.org markup | 35% | Helpful but "not required" per Google's guide |
| llms.txt | 15% | Useful for Perplexity/Claude agentic tools; Google Search ignores it |

The prompt context states explicitly: "Google Search doesn't use llms.txt" and "Structured data isn't required for AI search" — both from Google's official guide.

## Note on `llms.txt`

Scored at 15% weight and used only as a Perplexity/Claude-tool signal. The [Visibility Estimate](/scoring/visibility-estimate.md) applies the `llms.txt` bonus only to Claude and Perplexity, not to Google or GPT.

## Weight in overall score

**15%** of the [AI Readiness Score](/scoring/ai-readiness-score.md) — reduced from 20% to reflect Google's guidance that structured data is an amplifier, not a primary signal.

# Citations
[1] [Google AI Optimization Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
[2] [schema.org](https://schema.org)
[3] [llms.txt spec](https://llmstxt.org)
