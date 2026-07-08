---
title: components
description: Directory listing for progressive disclosure.
---

# components

## Concepts
- [aggregator](aggregator.md) -- Combines four AgentResults into the AI Readiness Score, sorts findings by impact/effort, and writes the executive summary via one LLM call.
- [api](api.md) -- HTTP entrypoint. Exposes the SiteFacts pipeline and the integrated audit bridge to agents-api; SSE/PDF routes remain planned.
- [cache](cache.md) -- URL-hash-keyed Redis store for crawl results, so re-runs never re-fetch and never waste Firecrawl credits.
- [crawl-fetch](crawl-fetch.md) -- Retrieves raw and rendered HTML, robots.txt, sitemap, and llms.txt for the target URL across three crawl tiers.
- [extraction](extraction.md) -- Parses raw and rendered HTML with no LLM to produce the SiteFacts object that all four agents read.
- [frontend](frontend.md) -- Minimal Next.js dashboard — story hero, four streaming agent columns with skeletons, and a report file-chip that opens a split pane with markdown/PDF export.
- [model-router](model-router.md) -- Selects which model and backend for each LLM role, with dual-backend routing (Ollama local + vLLM remote via tunnel) and Fireworks cloud fallback.
- [orchestrator](orchestrator.md) -- asyncio-based coordinator that drives the full audit lifecycle — crawl, extraction, agent fan-out, aggregation — and emits live status events.
- [pdf-export](pdf-export.md) -- Playwright prints the Next.js dashboard HTML to PDF, producing a portable report from the same layout used in the browser.
- [pipeline](pipeline.md) -- The implemented entrypoint that chains crawl+fetch and deterministic extraction to turn a URL into a SiteFacts object.
- [vllm-server](vllm-server.md) -- Remote vLLM instance running on a GPU Jupyter server, exposed to local Docker via a cloudflared or ngrok tunnel; not part of the local docker-compose stack.
