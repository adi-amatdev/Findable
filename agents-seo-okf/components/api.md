---
type: Service
title: FastAPI Application Layer
status: partial
description: HTTP entrypoint. Today it exposes the URL→SiteFacts pipeline; the spec's audit/SSE/PDF routes are planned.
tags: [backend, api, sse]
timestamp: 2026-07-08T00:00:00Z
---

# FastAPI Application Layer

The FastAPI app is the single entrypoint for external callers.

## Implemented routes (today)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/sitefacts` | Accepts `{ "url": "..." }`, runs the pipeline, returns a [SiteFacts](/data/site-facts.md) object. `refresh: true` bypasses the [Cache](/components/cache.md). |
| `POST` | `/scrape` | Raw [Firecrawl](/external/firecrawl.md) passthrough — debug utility. |
| `GET` | `/health` | Liveness + Firecrawl/cache status. |

Wired in `app/api/` (`routes.py`, `deps.py`); the pipeline dependency is
overridable so tests inject an offline crawler.

## Planned routes (spec target, not built)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/audit` | Start an async audit run, return `{ "audit_id": "..." }`. |
| `GET` | `/api/audit/{id}` | The full [AuditReport](/data/audit-report.md) when complete. |
| `GET` | `/api/audit/{id}/events` | SSE stream of per-agent `started`/`finished` events. |
| `GET` | `/api/audit/{id}/report.pdf` | [PDF](/components/pdf-export.md) of the dashboard. |

These depend on the [Orchestrator](/components/orchestrator.md), [agents](/agents/),
and [Aggregator](/components/aggregator.md), none of which are built yet. When
built, SSE is served via `sse-starlette` and the app + orchestrator share an
async event queue keyed by `audit_id`.

# Citations
[1] [sse-starlette](https://github.com/sysid/sse-starlette)
