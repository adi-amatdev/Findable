---
type: Service
title: FastAPI Application Layer
status: partial
description: HTTP entrypoint. Exposes the SiteFacts pipeline and the integrated audit bridge to agents-api; SSE/PDF routes remain planned.
tags: [backend, api, sse, integration]
timestamp: 2026-07-08T00:00:00Z
---

# FastAPI Application Layer

The FastAPI app is the single entrypoint for external callers. Wired in `app/api/` (`routes.py`, `deps.py`); the pipeline dependency is overridable so tests inject an offline crawler.

## Implemented routes

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/sitefacts` | Accepts `{ "url": "..." }`, runs the pipeline, returns a [SiteFacts](/data/site-facts.md) object. `refresh: true` bypasses the [Cache](/components/cache.md). |
| `POST` | `/api/audit` | Crawls URL → SiteFacts → forwards to the [agents-api service](/components/aggregator.md) via `AGENTS_URL`, returns a full [AuditReport](/data/audit-report.md). SiteFacts is served from Cache on repeated calls so no re-crawl cost. |
| `POST` | `/scrape` | Raw [Firecrawl](/external/firecrawl.md) passthrough — debug utility. |
| `GET` | `/health` | Liveness + Firecrawl/cache status. |

## Integration bridge — `POST /api/audit`

`AGENTS_URL` in the backend config points at the agents-api service (`http://agents-api:8080` in docker-compose, `http://localhost:8080` in local dev). The route:

1. Calls `SiteFactsPipeline.run(url)` — served from Redis cache if already crawled.
2. POSTs the SiteFacts JSON (`sf.model_dump_json()`) to `{AGENTS_URL}/audit` via httpx with a 120 s timeout.
3. Returns the AuditReport from agents-api directly to the caller.

Errors from agents-api surface as HTTP 502. If `AGENTS_URL` is blank the route returns 503.

## Planned routes (spec target, not built)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/audit/{id}` | Persisted AuditReport by ID (requires async job store). |
| `GET` | `/api/audit/{id}/events` | SSE stream of per-agent events. |
| `GET` | `/api/audit/{id}/report.pdf` | [PDF export](/components/pdf-export.md). |

# Citations
[1] [sse-starlette](https://github.com/sysid/sse-starlette)
