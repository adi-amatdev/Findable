---
type: Agent
title: Structured Data Agent
description: Judges whether an AI can extract key facts from the page's schema.org markup, llms.txt, and meta tags, and identifies missing or mismatched schema.
tags: [agent, structured-data, schema, jsonld, llmstxt]
timestamp: 2026-07-08T00:00:00Z
---

# Structured Data Agent

One of four concurrent agents in the [agent layer](/agents/). Implements the contract: **in** = [SiteFacts](/data/site-facts.md) + page markdown slice, **out** = [AgentResult](/data/agent-result.md).

## Deterministic inputs it reads

From [SiteFacts](/data/site-facts.md):
- `structured_data.schema_types`, `structured_data.jsonld_valid`, `structured_data.errors` (from `extruct`)
- `llms_txt.exists`, `llms_txt.valid`, `llms_txt.has_summary`, `llms_txt.link_count`, `llms_txt.full_variant`
- `html.og`, `html.twitter` (OpenGraph / Twitter meta)
- `html.meta_description`, `html.title`

## LLM judgment

Runs one call via the [Model Router](/components/model-router.md) (primary: Gemma 4 26B-A4B local). The prompt asks:

- Can an AI extract key facts from this page to answer a direct question?
- What schema types are missing that would help?
- Are there schema-vs-text mismatches?

## Note on `llms.txt`

Scored as a **minor, future-proofing signal**. Adoption is ~5–10% and major AI search crawlers largely skip it today; it matters most for agentic/dev-tool consumption. It does not drive the headline score.

## Weight in overall score

20% of the [AI Readiness Score](/scoring/ai-readiness-score.md).

# Citations
[1] [schema.org](https://schema.org)
[2] [llms.txt spec](https://llmstxt.org)
