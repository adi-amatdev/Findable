# Update Log

## 2026-07-09 (frontend + pdf + docker fixes)
* **Update**: PDF export implemented. `app/pdf.py` added — `fpdf2`-based backend generator with Latin-1 sanitiser (`_s()`), dual-format normaliser (mock/real), colour-coded score, visibility table with multipliers, verbose findings. `GET /api/audit/{audit_id}/pdf` endpoint streams `application/pdf`. `fpdf2>=2.7` added to `pyproject.toml`. `components/pdf-export.md` rewritten from `planned`/Playwright to `implemented`/fpdf2.
* **Update**: Frontend score colours fixed. Category score bars now use score-based colours (red/amber/green) instead of hardwired per-agent colours. Agent result card borders also score-based. Agent column footer no longer displays intermediate score percentages.
* **Update**: Homepage copy audited and corrected. Brand name "Findable" added to header. WIKI "Three tiers" replaced with accurate "What is collected" (deep-pages/site-wide tiers are not built). WIKI Facts schema description corrected to "JSON-LD detection" (Microdata/RDFa not implemented).
* **Update**: Logo fixed. SVG moved to `public/mark.svg` (avoids Next.js App Router `icon.svg` reservation). Fixed `width="100%"` → `width="912" height="936"` for correct `<img>` rendering. Outer background path set to `transparent` so gold mark is visible on dark background.
* **Update**: Docker build fixed. API `Dockerfile` switched from `uv sync --frozen` (stale lockfile missing `fpdf2`) to direct `pip install` of all `pyproject.toml` deps. Frontend `Dockerfile` runner stage now copies `public/` directory (required in Next.js standalone output mode — was silently omitting all public assets).
* **Update**: TypeScript build errors fixed. `estimateVisibility()` closure narrowing: rebind `facts` to `const f` after null guard. `Object.fromEntries` cast routed through `unknown` for `VisibilityEstimate` type.
* **Update**: `components/frontend.md` deviations section updated for all above.

## 2026-07-09 (model router update)
* **Update**: Model router refactored for dual vLLM URLs. Split `VLLM_URL` (heavy, gemma-2-9b-it) + `VLLM_LIGHT_URL` (light, gemma-2-2b-it). Priority order changed to vLLM → Fireworks → Ollama. Startup probe (`probe_backends()`) replaces module-level flag. Fireworks models now configurable via env vars. Role→tier mapping: light roles = orchestrator, crawlability_subagent, structured_data, entity_topic; heavy roles = crawlability_judgment, content_signal, report_writer. `components/model-router.md` and `components/vllm-server.md` updated.

## 2026-07-09
* **Update**: Frontend promoted from `partial` to `implemented`. Full stage flow (idle → crawling → judging → generating → report) with anime.js transitions. ReportDashboard component with animated score gauge, category bars, visibility estimate, findings list, site coverage, per-agent results, and knowledge graph. Cancel button with AbortController. Fallback report composer from SSE scores. Polling with 202 retry for report readiness. `components/frontend.md` rewritten.
* **Update**: `data/audit-report.md` promoted from `planned` to `implemented`. Schema updated to reflect the actual flattened format with optional nested fields. `data/agent-result.md` promoted from `contract` to `implemented` with full TypeScript types, agent-specific artifacts, and implementation status across mock/real/fallback paths.
* **Update**: `decisions/frontend-choice.md` closed: Next.js 13.5 chosen. Status promoted from `planned` to `implemented`.
* **Update**: `decisions/derived-visibility.md` promoted from `planned` to `implemented` — deterministic visibility mapping is built and working.
* **Update**: `components/mock-stream.md` updated with `_REPORT_DELAY` timing config and frontend retry behaviour.
* **Update**: Bundle at 31 concepts. Timestamps updated to 2026-07-09.

## 2026-07-08
* **Update**: SSE agent-streaming feature implemented. Added `state.py` (asyncio.Queue registry), `AgentStatusEvent` schema, phase-emitting agents, 3 routes on agents-api + 3 proxy routes on backend, 30 tests, dry-run scripts. `components/api.md` promoted to `implemented`. New concepts: `components/streaming.md`, `data/agent-status-event.md`. Bundle at 30 concepts.
* **Update**: Mock stream passthrough implemented. Added `MOCK_STREAM` flag, `mock.py` module, SSE branching in routes. New concept `components/mock-stream.md`. Bundle at 31 concepts.
* **Update**: Frontend built (status `partial`): story hero, SiteFacts strip, four SSE agent columns, report split pane with markdown/PDF export. `components/frontend.md` rewritten.
* **Update**: Full agents + integration layer built. All four agents and aggregator promoted to `implemented`. Scoring realigned per Google AI Optimization Guide. Model router dual-backend. Added `decisions/google-aio-alignment`. Bundle at 28 concepts.
* **Update**: Synced bundle to codebase. Added `status` field. Corrected cache (SQLite → Redis). Added `components/pipeline` and `decisions/scope-sitefacts-first`.
* **Creation**: Initial OKF bundle from `ARCHITECTURE.md`. 22 concepts across 6 domains.
