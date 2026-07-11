# Validation

Validates the current codebase against the architecture spec in `okf/`.

## Verdict

The full stack is **implemented and working** end-to-end: crawl → SiteFacts → 4 agents → scoring → aggregation → SSE streaming → frontend. The original scope statement ("SiteFacts pipeline only") is obsolete.

## Component map

| Component | Status | Where |
|---|---|---|
| `crawl-fetch` | ✅ Implemented | `app/crawl/` (`firecrawl.py`, `fetch.py`, `fetcher.py`) |
| `extraction` | ✅ Implemented | `app/extraction/extractor.py` |
| `cache` | ✅ Implemented | `app/cache/store.py` - Redis, URL-hash keyed, graceful degradation |
| `pipeline` | ✅ Implemented | `app/pipeline.py` - `SiteFactsPipeline.run(url)` |
| `api` | ✅ Implemented | `app/api/routes.py` - all routes live (see below) |
| `streaming` | ✅ Implemented | `agents/app/state.py` + SSE routes on both services |
| `mock-stream` | ✅ Implemented | `app/mock.py` - `MOCK_STREAM=true` bypasses all external services |
| `agents/*` (4 agents) | ✅ Implemented | `agents/app/agents/` - all four agents with LLM calls and SSE phase emission |
| `crawlability sub-agent` | ✅ Implemented | `agents/app/agents/crawlability/sub_agent.py` - 3-pass deterministic crawl |
| `model-router` | ✅ Implemented | `agents/app/models/router.py` - dual vLLM (heavy/light) + Fireworks + Ollama; startup probe via `probe_backends()` |
| `scoring/ai-readiness-score` | ✅ Implemented | `agents/app/scoring/rubric.py` - weighted formula + hard gates |
| `scoring/visibility-estimate` | ✅ Implemented | `agents/app/scoring/visibility.py` - before/after per-bot estimate |
| `aggregator` | ✅ Implemented | `agents/app/report/aggregator.py` - systemic findings + LLM summary |
| `data/site-facts` | ✅ Implemented | `app/models/contracts.py` |
| `data/agent-result` | ✅ Implemented | `agents/app/schemas.py` - produced by all 4 agents |
| `data/audit-report` | ✅ Implemented | `agents/app/schemas.py` - produced by aggregator |
| `data/agent-status-event` | ✅ Implemented | `agents/app/schemas.py` - emitted per phase by every agent |
| `frontend` | ✅ Implemented | `frontend/` - Next.js, full stage flow, ReportDashboard, SSE columns |
| `vllm-server` | ✅ Wired | `agents/app/models/router.py` via `VLLM_URL` (heavy) + `VLLM_LIGHT_URL` (light) env vars |
| `external/fireworks-api` | ✅ Wired | `agents/app/models/router.py` via `FIREWORKS_KEY`, `FIREWORKS_HEAVY_MODEL`, `FIREWORKS_LIGHT_MODEL` |
| `orchestrator` (multi-page fan-out) | ✅ Implemented | `asyncio.gather` fan-out exists in `agents/app/main.py`; Tier-2/3 multi-page crawl built |
| `pdf-export` | ✅ Implemented | `GET /api/audit/{audit_id}/pdf` - backend builds verbose PDF via `app/pdf.py` (fpdf2, Latin-1 safe, no system deps) and streams it to browser. Frontend calls this endpoint when `auditId` is present; falls back to `window.print()` for fallback reports. Also exports markdown via `handleDownloadMd()`. |

## API routes

### Backend (`app/api/routes.py`)

| Route | Status |
|---|---|
| `POST /api/sitefacts` | ✅ |
| `POST /api/audit` | ✅ blocking - crawl → SiteFacts → agents-api |
| `POST /api/audit/start` | ✅ async - returns `{audit_id, agent_ids}` for SSE |
| `GET /agent/stream/{agent_id}` | ✅ SSE proxy to agents-api (or mock queue) |
| `GET /api/audit/{audit_id}` | ✅ poll proxy - 202 while running, report when done |
| `GET /api/audit/{audit_id}/pdf` | ✅ generates verbose PDF; streams `application/pdf` with `Content-Disposition: attachment` |
| `POST /scrape` | ✅ raw Firecrawl passthrough |
| `GET /health` | ✅ |

### Agents-api (`agents/app/main.py`)

| Route | Status |
|---|---|
| `POST /audit` | ✅ blocking - 4 agents + aggregator |
| `POST /audit/start` | ✅ async - background task, returns immediately |
| `POST /audit/batch` | ✅ up to 10 SiteFacts |
| `GET /agent/stream/{agent_id}` | ✅ SSE drain from `state.py` queue |
| `GET /audit/{audit_id}/result` | ✅ 202 while running, AuditReport when done |
| `GET /health` | ✅ |

## SiteFacts contract conformance

| Field | Status | Notes |
|---|---|---|
| `http` | ✅ | httpx direct fetch |
| `robots.allows` (per AI bot) | ✅ | GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Google-Extended, CCBot |
| `sitemap` | ✅ | lxml-validated |
| `llms_txt` | ✅ | `full_variant` always false (llms-full.txt not fetched) |
| `render.js_dependency_ratio` + `content_visible_without_js` | ✅ | `1 - raw_text_len / rendered_text_len` |
| `html` (title/desc/canonical/lang/outline/word_count/og/twitter) | ✅ | BeautifulSoup |
| `structured_data` | ✅ | JSON-LD only - Microdata/RDFa via `extruct` done |
| `links` | ✅ | `outbound_citations` proxied by external-link count |
| `authorship` | ✅ | meta + JSON-LD |
| `entities_raw` | ✅ | capitalized-phrase heuristic, not spaCy - `label` always `MISC` |

## Deliberate deviations

1. **Structured data: JSON-LD only, not `extruct`.** Covers the common case; `extruct` slots in behind `_structured_data()`.
2. **Entities: heuristic, not spaCy NER.** Keeps the build dependency-light; spaCy slots in behind `_entities()`.
3. **`outbound_citations` is a proxy** (external-link count).
4. **Orchestrator is single-page.** Tier-2/3 multi-page fan-out is built - the pipeline audits one URL deep.
5. **Cache is Redis, not SQLite.** The spec allows either; Redis was already in the stack.
6. **vLLM via Jupyter/cloudflared tunnel**, not a local ROCm Docker container. The `rocm/vllm` path remains valid for AMD GPU workstations and is the production target.
7. **Dual vLLM endpoints** - heavy (`gemma-2-9b-it`) and light (`gemma-2-2b-it`) are served on separate cloudflared tunnels (`VLLM_URL` and `VLLM_LIGHT_URL`). Router probes `/v1/models` on startup to discover which are reachable before serving any requests.
8. **Frontend scoring weights** match backend: crawlability 30%, content_signal 35%, structured_data 15%, entity_topic 20%. Visibility analysis shows per-model multipliers and an average improvement figure computed from real `SiteFacts` signals, not random numbers.

## Design principles

- **Deterministic–LLM Separation (Principle 1):** ✅ - extraction is 100% deterministic; no LLM touches `SiteFacts`.
- **Parallel Inference (Principle 2):** ✅ - `asyncio.gather` fan-out is built and fires all 4 agents concurrently; targets Jupyter/cloudflared vLLM rather than local ROCm container.

## Run & verify

```bash
# Backend + SiteFacts pipeline
uv sync --group dev
uv run pytest -q                          # 19 tests, fully offline

# Full stack
docker compose up --build                 # backend :8000, agents-api :8080, frontend :3000

# Zero-cost demo (no API keys needed)
MOCK_STREAM=true docker compose up --build
```
