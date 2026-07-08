---
type: Decision
title: Build the SiteFacts Pipeline First
status: implemented
description: The first build target is the deterministic URL→SiteFacts pipeline; agents, scoring, and aggregation are scaffolded on top.
tags: [decision, scope, milestone]
timestamp: 2026-07-08T00:00:00Z
---

# Build the SiteFacts Pipeline First

## Decision

The initial implementation delivers exactly the deterministic
[URL → SiteFacts pipeline](/components/pipeline.md) — [Crawl & Fetch](/components/crawl-fetch.md),
[Deterministic Extraction](/components/extraction.md), the
[SiteFacts](/data/site-facts.md) contract, and the [Cache](/components/cache.md).
Everything downstream is scaffolded, not implemented.

## Rationale

- SiteFacts is the single input every [agent](/agents/) reads. Getting it correct
  and reproducible first de-risks every layer above it.
- It is 100% deterministic and testable offline (no model, no API key), so it can
  be verified in CI. See [Deterministic–LLM Separation](/decisions/deterministic-llm-separation.md).
- Judges can inspect a real artifact (the SiteFacts JSON) immediately.

## Status vocabulary

Concepts in this bundle carry a `status` frontmatter field so the bundle reflects
build reality:

- `implemented` — code exists and is tested.
- `partial` — some of the concept is built (e.g. the [API](/components/api.md)).
- `scaffold` — a typed interface exists, no logic yet.
- `contract` — a data shape is defined in code but nothing produces it yet.
- `planned` — described in the spec only.

## What is scaffolded next

[Agents](/agents/) (interface in `app/agents/base.py`), the
[Model Router](/components/model-router.md) (route table in `app/llm/roles.py`),
then [scoring](/scoring/), the [Aggregator](/components/aggregator.md), and the
[Orchestrator](/components/orchestrator.md).
