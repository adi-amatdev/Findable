# Update Log

## 2026-07-11 (production SSE lifecycle fix)
* **Fix**: Registered all per-agent SSE queues synchronously in `POST /audit/start`, before scheduling the audit task. This eliminates the deployment race where the browser could request a stream before the background task created its queue.
* **Fix**: Changed `agents-api` to one Uvicorn worker because stream queues and active audit results are process-local. Two workers could route audit creation and stream reads to different registries, causing repeated `404` stream failures.
* **Fix**: The backend SSE proxy now preserves upstream stream failures rather than turning a `404` into a `200` empty SSE response; the frontend closes any failed EventSource as offline, allowing its bounded report polling/fallback flow to complete rather than reconnecting forever.
* **Update**: Content Signal findings now reference Google's current [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) guidance for E-E-A-T.

## 2026-07-11 (frontend visual port)
* **Update**: Ported the verified frontend visual system from the UI experiment: procedural Three.js galaxy background, stage-aware processing pulses, revised homepage copy and deliverables, fixed brand mark, expanded audit context facts grid, visibility edge-state messaging, and compact expandable agent-result cards. Frontend dependencies now include `three` and `@types/three`; no backend contracts or environment examples changed.

## 2026-07-11 (Fireworks serverless fallback + guided JSON translation)
* **Fix**: Fireworks Gemma-family pages checked for this project (`gemma-4-26b-a4b-it`, `gemma-4-e4b`, `gemma-3-27b-it`) mark serverless as "Not supported", so the no-deployment Fireworks fallback defaults were changed to serverless models: heavy `accounts/fireworks/models/gpt-oss-120b`, light `accounts/fireworks/models/gpt-oss-20b`. Gemma Fireworks paths remain documented as optional on-demand deployment overrides.
* **Fix**: `AsyncLLMClient.chat_completion()` now treats `guided_json` by backend: keeps `guided_json` for vLLM, translates it to Fireworks `response_format: {"type":"json_schema", ...}`, and omits it for Ollama. Added tests for vLLM/Fireworks/Ollama payload construction.
* **Creation**: Added `docs/fireworks_serverless_pricing.md` with Fireworks serverless pricing, Gemma serverless availability findings, selected fallback models, and an approximate one-pass audit cost estimate (~$0.0062 using current token caps).

## 2026-07-11 (README architecture + Fireworks fallback + GPU deployment docs)
* **Update**: README rewritten with a full Mermaid architecture diagram covering frontend, backend, crawl/fetch, deterministic extraction, SiteFacts, agents-api, four agents, crawlability sub-agent, Model Router, vLLM/Fireworks/Ollama fallback, token logging, SSE, AuditReport, and PDF export.
* **Update**: Fireworks Gemma 4 paths (`accounts/fireworks/models/gemma-4-26b-a4b-it`, `accounts/fireworks/models/gemma-4-e4b`) documented as optional on-demand deployment overrides before the later serverless check changed no-deployment defaults to GPT OSS models. Updated `.env.example`, `agents/app/models/router.py`, `app/llm/roles.py`, `components/model-router.md`, and `external/fireworks-api.md`.
* **Update**: README now documents Gemma licensing split: Gemma 4 Apache 2.0 license page for Fireworks fallbacks; earlier local Gemma 2 weights under Google's Gemma Terms of Use.
* **Update**: README now embeds AMD SMI screenshots from `docs/assets/amd-smi/` showing idle, partial, and full GPU load, including full-load 100% utilization and ~43.7 GB VRAM usage.
* **Update**: vLLM setup docs now point to `vllm_hosting/` (`download_model.py`, `download_cloudflare.txt`, `start_service.sh`, `stop_service.sh`, `load_test.py`) instead of stale `server_files/serve.sh` references. `components/vllm-server.md` and `components/index.md` updated.

## 2026-07-11 (Gemma system-role fix + vLLM context length)
* **Fix**: Discovered via `token_benchmark.py` that Gemma's chat template rejects a `system`-role message ("System role not supported"), so every real agent call against vLLM was 400ing and silently falling back to Fireworks/Ollama. Fixed in `AsyncLLMClient.chat_completion()` (`agents/app/models/client.py`) — new `_merge_system_message()` folds a leading `system` message into the following `user` message before every request, for every caller uniformly. `components/model-router.md` documents this under "Gemma chat-template compatibility".
* **Note**: A second, separate issue found the same way — `content_signal` and `crawlability_judgment` request `max_tokens=3000` against a heavy vLLM server started with the vLLM default `max_model_len=4096`, which isn't enough combined with their ~1,000–1,100 token prompts. Not a code bug — it's a server startup flag. `components/vllm-server.md` documents the requirement and recommends `--max-model-len 6000` (sufficient given the agents' fixed prompt-truncation caps; 8192 is not necessary).

## 2026-07-11 (token usage tracking + homepage copy fix)
* **Creation**: Token usage logging added. Every LLM call routed through `ModelRouter.call_with_fallback()` now logs prompt/completion/total tokens (plus model, backend, agent, audit_id) to `agents/logs/token_usage.jsonl` via new `agents/app/token_logger.py` — closes the gap where the `report_writer` executive-summary call's token usage was read and discarded. New concepts: `components/token-logging.md`, `data/token-usage-record.md`.
* **Update**: `data/agent-result.md` schema gained `prompt_tokens`/`completion_tokens` fields alongside the existing `tokens` total (additive, backward-compatible).
* **Update**: `components/model-router.md` documents the new `agent`/`audit_id` params on `call_with_fallback` and the token-logging hook.
* **Creation**: `agents/scripts/token_benchmark.py` — CLI benchmark against the two vLLM endpoints (heavy + light) using real prompt-building code, reports average tokens per agent role and per model. `agents/scripts/token_report.py` reads the JSONL log back for running per-agent/per-model averages.
* **Fix**: Homepage "What is extracted" stat for JS dependency reworded from the formula fragment `"1 - raw / rendered text length ratio"` to plain language: `"Gap between raw HTML and JS-rendered text length"` (`frontend/app/page.tsx`). The underlying formula (`1 - raw_len/rendered_len` in `app/extraction/extractor.py`) is unchanged and intentional — only the homepage copy was unclear.

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
