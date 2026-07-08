---
type: Service
title: Orchestrator
description: asyncio-based coordinator that drives the full audit lifecycle — crawl, extraction, agent fan-out, aggregation — and emits live status events.
tags: [backend, asyncio, orchestration]
timestamp: 2026-07-08T00:00:00Z
---

# Orchestrator

Plain `asyncio`. Owns the audit run end-to-end once the [API](/components/api.md) fires it.

## Sequence per run

1. **Cache check** — look up URL hash in [Cache](/components/cache.md); return cached report if hit.
2. **Crawl + extract landing page** — call [Crawl & Fetch](/components/crawl-fetch.md), then [Deterministic Extraction](/components/extraction.md) to produce [SiteFacts](/data/site-facts.md).
3. **Select Tier-2 follow-up pages** — small local model ranks candidate nav/sitemap links; falls back to a heuristic (nav + top-linked pages) if the model call fails.
4. **Launch Tier-3 shallow pass** — deterministic-only fetch over up to `MAX_SHALLOW_PAGES` (~50) pages, concurrent, no LLM.
5. **Nested fan-out** — `asyncio.gather` over deep pages (landing + ~4 follow-ups); each page runs `asyncio.gather` over its four [agents](/agents/) concurrently.  This produces ~20 concurrent LLM judgment calls that vLLM batches on GPU.
6. **Aggregate** — pass all `AgentResult`s to the [Aggregator](/components/aggregator.md).
7. **Emit status events** throughout via the [API](/components/api.md) SSE queue.

## LLM sub-role

The orchestrator itself makes one small LLM call: step 3 page ranking. Every other LLM call belongs to the agents or aggregator.

## Key parameters

- `MAX_DEEP_PAGES` (~4) — number of follow-up pages for a full 4-agent pass.
- `MAX_SHALLOW_PAGES` (~50, capped) — ceiling on the deterministic site crawl.

Both are tuned against real latency on demo sites once AMD hardware is in hand.
