# Backend validation against `agents-seo-okf/`

Validates the current backend against the architecture spec in `agents-seo-okf/`
(OKF bundle: 9 components, 4 agents, 3 data contracts, 2 scoring metrics, 2
external deps, 4 decisions).

**Scope of this build (per request):** implement the pipeline **`URL → Firecrawl
(+ direct fetch) → SiteFacts`** and nothing beyond it. Everything downstream of
`SiteFacts` is scaffolded, not implemented.

## Verdict

The implemented slice **conforms** to the spec's front half — Crawl & Fetch,
Deterministic Extraction, the `SiteFacts` contract, and the Cache — including the
core design principle (Deterministic–LLM Separation: all parsing in plain code,
no LLM). Downstream layers (agents, model router, scoring, aggregation,
orchestrator, SSE API) are **scaffolded with typed interfaces** so they drop onto
the implemented base without rework.

## Component-by-component mapping

| Spec component | Status | Where |
|---|---|---|
| `crawl-fetch` (Firecrawl + httpx: robots/sitemap/llms.txt, raw+rendered) | ✅ Implemented | `app/crawl/` (`firecrawl.py`, `fetch.py`, `fetcher.py`) |
| `extraction` (deterministic → SiteFacts) | ✅ Implemented | `app/extraction/extractor.py` |
| `data/site-facts` (SiteFacts contract) | ✅ Implemented | `app/models/contracts.py` |
| `cache` (URL-hash keyed, Redis) | ✅ Implemented | `app/cache/store.py` |
| `api` (HTTP entrypoint) | 🟡 Partial | `app/api/` — `POST /api/sitefacts` implemented; spec's `/api/audit` + SSE not built (no report yet) |
| `data/agent-result`, `data/audit-report` | 🟡 Contract only | `app/models/contracts.py` (`AgentResult` defined; `AuditReport` deferred) |
| `agents/*` (4 agents) | ⬜ Scaffold | `app/agents/base.py` (interface only) |
| `model-router` | ⬜ Scaffold | `app/llm/` (`roles.py` = real route table; `router.py` = interface) |
| `scoring/*` (AI Readiness, Visibility) | ⬜ Not built | — (documented as next layer) |
| `aggregator` | ⬜ Not built | — |
| `orchestrator` (asyncio fan-out, tiers) | ⬜ Not built | pipeline is single-page landing only |
| `vllm-server`, `external/fireworks-api` | ⬜ Not built | config placeholders in `app/config.py` |
| `frontend`, `pdf-export` | ⬜ Out of scope | backend-only build |

## `SiteFacts` contract conformance

Every field in `agents-seo-okf/data/site-facts.md` is produced:

| Field | Status | Notes |
|---|---|---|
| `http` (status/latency/redirects/content_type) | ✅ | from the direct httpx fetch |
| `robots.allows` (per AI bot) | ✅ | parses robots.txt groups for GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Google-Extended, CCBot |
| `sitemap` (exists/valid/url_count) | ✅ | lxml-validated |
| `llms_txt` (exists/valid/has_summary/link_count) | ✅ | `full_variant` always false (llms-full.txt not fetched) |
| `render.js_dependency_ratio` + `content_visible_without_js` | ✅ | `1 − raw_text_len/rendered_text_len` (raw = httpx, rendered = Firecrawl) |
| `html` (title/desc/canonical/lang/outline/word_count/og/twitter) | ✅ | BeautifulSoup |
| `structured_data` (schema_types/jsonld_valid/errors) | 🟡 | **JSON-LD only** — see deviations |
| `links` (internal/external/outbound_citations) | 🟡 | `outbound_citations` ≈ external-link count (heuristic proxy) |
| `authorship` (byline/author_schema/dates) | ✅ | meta + JSON-LD |
| `entities_raw` | 🟡 | **heuristic**, not spaCy — see deviations |

## Deliberate scoping deviations (and why)

1. **Structured data: BeautifulSoup JSON-LD, not `extruct`.** The spec calls for
   `extruct` (JSON-LD + Microdata + RDFa + OpenGraph). JSON-LD covers the large
   majority of real-world schema; `extruct` is a light drop-in behind
   `_structured_data()` when Microdata/RDFa coverage is needed.
2. **Entities: capitalized-phrase heuristic, not `spaCy` NER.** spaCy adds a
   heavy model download; the heuristic keeps the build fast and dependency-light.
   Swap in behind `_entities()`.
3. **`outbound_citations` is a proxy** (external-link count) rather than
   "citations inside article content."
4. **Single page only.** The spec's Tier-2/Tier-3 multi-page crawl lives in the
   (unbuilt) orchestrator; the pipeline audits one URL.
5. **Cache is Redis, not SQLite.** The spec allows either ("Redis-compatible");
   this reuses the existing Redis service.

## Design-principle check

- **Deterministic–LLM Separation (Principle 1):** ✅ enforced — extraction is
  100% deterministic; no LLM touches `SiteFacts`. Same URL → same `SiteFacts`.
- **Parallel Inference on AMD (Principle 2):** ⬜ N/A yet (no inference layer).

## Run & verify

```bash
uv sync --group dev
uv run pytest -q                 # 19 tests: extraction, cache, API
uv run uvicorn app.main:app --reload
# POST /api/sitefacts {"url": "..."}  ->  SiteFacts
```
