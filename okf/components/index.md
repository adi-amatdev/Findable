# components

## Concepts
- [aggregator](aggregator.md) - Combines four AgentResults into the AI Readiness Score, sorts findings by impact/effort, and writes the executive summary via one LLM call.
- [api](api.md) - HTTP entrypoint. Exposes the SiteFacts pipeline, the integrated audit bridge, and the SSE agent-streaming routes. PDF export remains planned.
- [cache](cache.md) - URL-hash-keyed Redis store for crawl results, so re-runs never re-fetch and never waste Firecrawl credits.
- [crawl-fetch](crawl-fetch.md) - Retrieves raw and rendered HTML, robots.txt, sitemap, and llms.txt for the target URL across three crawl tiers.
- [extraction](extraction.md) - Parses raw and rendered HTML with no LLM to produce the SiteFacts object that all four agents read.
- [frontend](frontend.md) - Minimal Next.js dashboard — story hero, four streaming agent columns with skeletons, and a report file-chip that opens a split pane with markdown/PDF export.
- [mock-stream](mock-stream.md) - A zero-cost development mode (MOCK_STREAM=true) that bypasses Firecrawl and agents entirely, substituting static fixtures and a timed SSE emitter so the frontend streaming UI can be built without consuming any API credits.
- [model-router](model-router.md) - Selects which model and backend for each LLM role, with dual-backend routing (Ollama local + vLLM remote via tunnel) and Fireworks cloud fallback.
- [orchestrator](orchestrator.md) - asyncio-based coordinator that drives the full audit lifecycle — crawl, extraction, agent fan-out, aggregation — and emits live status events.
- [pdf-export](pdf-export.md) - Playwright prints the Next.js dashboard HTML to PDF, producing a portable report from the same layout used in the browser.
- [pipeline](pipeline.md) - The implemented entrypoint that chains crawl+fetch and deterministic extraction to turn a URL into a SiteFacts object.
- [streaming](streaming.md) - Server-Sent Events infrastructure that lets clients watch each agent's thinking in real time — from phase start to LLM call to completion — without polling a blocking endpoint.
- [vllm-server](vllm-server.md) - Remote vLLM instance running on a GPU Jupyter server, exposed to local Docker via a cloudflared or ngrok tunnel; not part of the local docker-compose stack.
