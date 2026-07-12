# components

## Concepts
- [aggregator](aggregator.md) -- Combines four AgentResults into the AI Readiness Score, sorts findings by impact/effort, and writes the executive summary via one LLM call.
- [api](api.md) -- HTTP entrypoint. Exposes the SiteFacts pipeline, the integrated audit bridge, and the SSE agent-streaming routes. PDF export remains planned.
- [cache](cache.md) -- URL-hash-keyed Redis store for crawl results, so re-runs never re-fetch and never waste Firecrawl credits.
- [crawl-fetch](crawl-fetch.md) -- Retrieves raw and rendered HTML, robots.txt, sitemap, and llms.txt for the target URL across three crawl tiers.
- [extraction](extraction.md) -- Parses raw and rendered HTML with no LLM to produce the SiteFacts object that all four agents read.
- [frontend](frontend.md) -- Single-page gold-on-black AI-readiness dashboard with a Three.js galaxy background, SSE agent streaming, cancel/abort support, and an interactive report dashboard.
- [mock-stream](mock-stream.md) -- A zero-cost development mode (MOCK_STREAM=true) that bypasses Firecrawl and agents entirely, substituting static fixtures and a timed SSE emitter so the frontend streaming UI can be built without consuming any API credits.
- [model-router](model-router.md) -- Selects which model and backend for each LLM role. Dual vLLM endpoints (heavy + light) with Fireworks cloud fallback and Ollama as last resort. Backends are probed at startup.
- [orchestrator](orchestrator.md) -- asyncio-based coordinator that drives the full audit lifecycle — crawl, extraction, agent fan-out, aggregation — and emits live status events.
- [pdf-export](pdf-export.md) -- Backend endpoint generates a verbose, self-contained PDF using fpdf2 (no system deps, Latin-1 safe) and streams it directly to the browser on click.
- [pipeline](pipeline.md) -- The implemented entrypoint that chains crawl+fetch and deterministic extraction to turn a URL into a SiteFacts object.
- [rate-limiter](rate-limiter.md) -- In-memory sliding-window rate limiter applied as ASGI middleware. Limits requests per client IP with configurable whitelist, lazy + periodic expired-entry cleanup.
- [streaming](streaming.md) -- Server-Sent Events infrastructure that lets clients watch each agent's thinking in real time — from phase start to LLM call to completion — without polling a blocking endpoint.
- [token-logging](token-logging.md) -- Every LLM call routed through the Model Router logs its prompt/completion/total token usage to a JSONL file, tagged by agent, model, and audit_id; a benchmark script and a report script read/write that same log.
- [vllm-server](vllm-server.md) -- Two remote vLLM instances (light + heavy) running on an AMD GPU server, each exposed via a separate cloudflared tunnel and consumed by the Model Router.
