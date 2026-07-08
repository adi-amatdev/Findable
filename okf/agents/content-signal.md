---
type: Agent
title: Content Signal Agent (E-E-A-T)
status: implemented
description: Scores the page's Experience, Expertise, Authoritativeness, and Trust signals; flags commodity content; judges citation-worthiness and answer front-loading for AI search.
tags: [agent, content, eeat, citation, commodity, google-aio]
timestamp: 2026-07-08T00:00:00Z
---

# Content Signal Agent (E-E-A-T)

One of four concurrent agents in the [agent layer](/agents/). Implements the contract: **in** = [SiteFacts](/data/site-facts.md) + page markdown slice, **out** = [AgentResult](/data/agent-result.md). Implemented in `agents/app/agents/content_signal.py`.

## Deterministic inputs it reads

From [SiteFacts](/data/site-facts.md):
- `authorship.byline_present`, `authorship.author_schema`, `authorship.dates`
- `links.outbound_citations`
- `html.word_count`

## LLM judgment

Runs one call via the [Model Router](/components/model-router.md) (primary: heavy model on vLLM or Fireworks — hardest E-E-A-T judgment role). Prompt (`prompts/content_signal.md`) structured per the [Google AI Optimization Guide](/decisions/google-aio-alignment.md):

**Step 1 — Commodity vs. non-commodity assessment** (new):
Is this generic commodity content (standard how-to, repeated advice, no first-hand experience or unique data) or non-commodity (unique expertise, proprietary research, first-hand experience)? Returns `commodity_content: true/false`.

**Step 2 — E-E-A-T scoring**:
- Score Experience / Expertise / Authoritativeness / Trust on sub-scales.
- Is this page citation-worthy for an AI search engine?
- Are direct answers front-loaded (GEO — Generative Engine Optimization)?
- Missing byline on advice content → severity 4 finding.

## Commodity content cap

If `commodity_content == true`, the agent caps its own score at 60. The [AI Readiness Score](/scoring/ai-readiness-score.md) rubric enforces the same cap redundantly. Commodity pages cannot earn a high AI readiness score regardless of other signals — Google's guide identifies non-commodity content as its #1 AI-search signal.

## Sub-scores returned

`AgentResult.sub_scores` includes `experience`, `expertise`, `authority`, `trust`.
`AgentResult.artifacts` includes `commodity_content`, `citation_worthy`, `answer_front_loaded`.

## Weight in overall score

**35%** of the [AI Readiness Score](/scoring/ai-readiness-score.md) — raised from 30% to reflect Google's prioritisation of content quality.

# Citations
[1] [Google AI Optimization Guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
[2] [Google E-E-A-T guidelines](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
[3] [Google Quality Rater Guidelines](https://static.googleusercontent.com/media/guidelines.raterhub.com/en//searchqualityevaluatorguidelines.pdf)
