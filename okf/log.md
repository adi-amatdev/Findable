# Update Log

## 2026-07-08
* **Update**: SSE agent-streaming feature implemented. Added `state.py` (asyncio.Queue registry), `AgentStatusEvent` schema, phase-emitting agents, 3 routes on agents-api + 3 proxy routes on backend, 30 tests, dry-run scripts. `components/api.md` promoted to `implemented`. New concepts: `components/streaming.md`, `data/agent-status-event.md`. Bundle at 30 concepts.
* **Update**: Mock stream passthrough implemented. Added `MOCK_STREAM` flag, `mock.py` module, SSE branching in routes. New concept `components/mock-stream.md`. Bundle at 31 concepts.
* **Update**: Frontend built (status `partial`): story hero, SiteFacts strip, four SSE agent columns, report split pane with markdown/PDF export. `components/frontend.md` rewritten.
* **Update**: Full agents + integration layer built. All four agents and aggregator promoted to `implemented`. Scoring realigned per Google AI Optimization Guide. Model router dual-backend. Added `decisions/google-aio-alignment`. Bundle at 28 concepts.
* **Update**: Synced bundle to codebase. Added `status` field. Corrected cache (SQLite → Redis). Added `components/pipeline` and `decisions/scope-sitefacts-first`.
* **Creation**: Initial OKF bundle from `ARCHITECTURE.md`. 22 concepts across 6 domains.
