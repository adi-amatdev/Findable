---
title: components
description: Directory listing for progressive disclosure.
---

# components

## Concepts
- [aggregator](aggregator.md) -- Combines four AgentResults into the AI Readiness Score, sorts findings by impact/effort, and writes the executive summary via one LLM call.
- [api](api.md) -- HTTP entrypoint that accepts audit requests, streams live per-agent status over SSE, and serves the final report and PDF.
- [cache](cache.md) -- URL-hash-keyed store for RawCrawl blobs and AuditReports; SQLite for the hackathon, Redis-compatible for production.
- [crawl-fetch](crawl-fetch.md) -- Retrieves raw and rendered HTML, robots.txt, sitemap, and llms.txt for the target URL across three crawl tiers.
- [extraction](extraction.md) -- Parses raw and rendered HTML with no LLM to produce the SiteFacts object that all four agents read.
- [frontend](frontend.md) -- React dashboard showing the score card, category radar, knowledge-graph view, prioritized fix list, and live per-agent status spinners.
- [model-router](model-router.md) -- Selects which model and endpoint to use for each LLM role, with ordered failover and response caching, behind a single OpenAI-compatible interface.
- [orchestrator](orchestrator.md) -- asyncio-based coordinator that drives the full audit lifecycle — crawl, extraction, agent fan-out, aggregation — and emits live status events.
- [pdf-export](pdf-export.md) -- Playwright prints the Next.js dashboard HTML to PDF, producing a portable report from the same layout used in the browser.
- [vllm-server](vllm-server.md) -- Local model serving container running Gemma 4 E4B and 26B-A4B on AMD GPU via ROCm, with continuous batching for concurrent agent requests.
