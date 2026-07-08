---
type: Agent
title: Entity and Topic Agent
description: Maps the page's topic-to-entity graph, judges entity disambiguation (sameAs/Wikidata), and assesses topical authority via the internal link graph.
tags: [agent, entity, topic, knowledge-graph, ner]
timestamp: 2026-07-08T00:00:00Z
---

# Entity and Topic Agent

One of four concurrent agents in the [agent layer](/agents/). Implements the contract: **in** = [SiteFacts](/data/site-facts.md) + page markdown slice, **out** = [AgentResult](/data/agent-result.md).

## Deterministic inputs it reads

From [SiteFacts](/data/site-facts.md):
- `entities_raw` — spaCy NER output: `[{ "text": "...", "label": "..." }]`
- `links.internal` — internal link graph for topical authority signals

## LLM judgment

Runs one call via the [Model Router](/components/model-router.md) (primary: Qwen3 14B local). The prompt asks:

- Build a topic → entity map / mini knowledge graph for this page.
- Are the key entities disambiguated? (Do they link to `sameAs`/Wikidata?)
- Does the internal link structure reinforce topical authority?

## Special artifact

This agent returns a `knowledge_graph` object in `AgentResult.artifacts`, which is what powers the react-flow graph visualization in the [Frontend](/components/frontend.md).

## Weight in overall score

20% of the [AI Readiness Score](/scoring/ai-readiness-score.md).
