# data

## Concepts
- [agent-result](agent-result.md) - The JSON output every agent returns — a score, sub-scores, a list of findings with severity/effort/impact, and optional artifacts (knowledge_graph, traffic_signal, crawl_reports).
- [agent-status-event](agent-status-event.md) - The SSE payload emitted by each agent during execution — one event per phase change, streamed to the frontend via GET /agent/stream/{agent_id}.
- [audit-report](audit-report.md) - The final multi-page audit output — headline score, per-page deep results, site-wide coverage stats, before/after visibility, LLM-written executive summary, and an optional rich nested structure from the real agents-api pipeline.
- [site-facts](site-facts.md) - The deterministic, LLM-free snapshot of a single page — every signal the four agents read, produced once by the extraction pipeline.
