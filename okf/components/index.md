# components

## Concepts
- [aggregator](aggregator.md) - Combines four AgentResults into the AI Readiness Score, sorts findings by impact/effort, and writes the executive summary via one LLM call.
- [api](api.md) - HTTP entrypoint. Exposes SiteFacts, blocking/async audits, SSE proxying, result polling, mock stream mode, and PDF export.
- [cache](cache.md) - URL-hash-keyed Redis store for crawl results, so re-runs never re-fetch and never waste Firecrawl credits.
- [crawl-fetch](crawl-fetch.md) - Retrieves raw and rendered HTML, robots.txt, sitemap, and llms.txt for the target URL.
- [extraction](extraction.md) - Parses raw and rendered HTML with no LLM to produce the SiteFacts object that all four agents read.
- [frontend](frontend.md) - Single-page Renaissance-themed dashboard with anime.js animations, SSE streaming agent columns, cancel/abort support, and report export.
- [mock-stream](mock-stream.md) - Zero-cost development mode that bypasses Firecrawl and agents while preserving the frontend streaming contract.
- [model-router](model-router.md) - Selects which model and backend for each LLM role, with dual vLLM endpoints, Fireworks Gemma 4 fallback, Ollama fallback, and token logging.
- [orchestrator](orchestrator.md) - Planned asyncio coordinator for multi-page crawl, extraction, agent fan-out, aggregation, and live status events.
- [pdf-export](pdf-export.md) - Backend fpdf2 endpoint generates a verbose PDF report and streams it to the browser.
- [pipeline](pipeline.md) - The implemented entrypoint that chains crawl+fetch and deterministic extraction to turn a URL into a SiteFacts object.
- [streaming](streaming.md) - Server-Sent Events infrastructure that lets clients watch each agent's thinking in real time.
- [token-logging](token-logging.md) - Every LLM call routed through the Model Router logs token usage to JSONL, tagged by agent, model, and audit_id.
- [vllm-server](vllm-server.md) - Two remote vLLM instances running on an AMD GPU server, exposed by cloudflared tunnels and managed by vllm_hosting scripts.
