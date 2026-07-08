---
type: Service
title: FastAPI Application Layer
description: HTTP entrypoint that accepts audit requests, streams live per-agent status over SSE, and serves the final report and PDF.
tags: [backend, api, sse]
timestamp: 2026-07-08T00:00:00Z
---

# FastAPI Application Layer

The FastAPI app is the single entrypoint for external callers. It exposes four routes:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/audit` | Accepts `{ "url": "..." }`, starts an audit run, returns `{ "audit_id": "..." }`. |
| `GET` | `/api/audit/{id}` | Returns the full [AuditReport](/data/audit-report.md) when the run is complete. |
| `GET` | `/api/audit/{id}/events` | SSE stream of per-agent `started` / `finished` status events driving the dashboard spinners. |
| `GET` | `/api/audit/{id}/report.pdf` | Playwright-rendered PDF of the dashboard. |

On receiving `POST /api/audit` the app spawns an async run in the [Orchestrator](/components/orchestrator.md) and returns immediately; all further progress is delivered over SSE.

Live status events are emitted by the orchestrator through the app as each of the four [agents](/agents/) transitions state. This lets the [Frontend](/components/frontend.md) show real-time per-agent spinners without polling.

**Implementation note.** SSE is served via `sse-starlette`. The app and orchestrator share an async event queue keyed by `audit_id`.

# Citations
[1] [sse-starlette](https://github.com/sysid/sse-starlette)
