---
type: Agent
title: Content Signal Agent (E-E-A-T)
status: scaffold
description: Scores the page's Experience, Expertise, Authoritativeness, and Trust signals; judges citation-worthiness and answer front-loading for AI search.
tags: [agent, content, eeat, citation]
timestamp: 2026-07-08T00:00:00Z
---

# Content Signal Agent (E-E-A-T)

One of four concurrent agents in the [agent layer](/agents/). Implements the contract: **in** = [SiteFacts](/data/site-facts.md) + page markdown slice, **out** = [AgentResult](/data/agent-result.md).

## Deterministic inputs it reads

From [SiteFacts](/data/site-facts.md):
- `authorship.byline_present`, `authorship.author_schema`, `authorship.dates`
- `links.outbound_citations`
- `html.word_count`

## LLM judgment

Runs one call via the [Model Router](/components/model-router.md) (primary: **Gemma 4 31B on [Fireworks](/external/fireworks-api.md)** — this is one of the two "hardest job" roles that go to the larger remote model). The prompt asks:

- Score Experience / Expertise / Authoritativeness / Trust on sub-scales.
- Is this page citation-worthy for an AI search engine?
- Are direct answers front-loaded (GEO — Generative Engine Optimization)?
- Provide concrete rewrite tips.

## Sub-scores returned

`AgentResult.sub_scores` includes `experience`, `expertise`, `authority`, `trust`.

## Weight in overall score

30% of the [AI Readiness Score](/scoring/ai-readiness-score.md).

# Citations
[1] [Google E-E-A-T guidelines](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
[2] [Google Quality Rater Guidelines](https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf)
