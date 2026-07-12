---
type: Service
title: FastAPI Application Layer
status: implemented
description: HTTP entrypoint. Exposes the SiteFacts pipeline, the integrated audit bridge, and the SSE agent-streaming routes. PDF export remains planned.
tags: [backend, api, sse, integration, streaming]
timestamp: 2026-07-11T00:00:00Z
---

# FastAPI Application Layer

The FastAPI app is the single entrypoint for external callers. Wired in `app/api/` (`routes.py`, `deps.py`); the pipeline dependency is overridable so tests inject an offline crawler.

## Implemented routes

### Backend (`app/api/routes.py`)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/sitefacts` | Accepts `{ "url": "..." }`, runs the pipeline, returns a [SiteFacts](/data/site-facts.md) object. `refresh: true` bypasses the [Cache](/components/cache.md). |
| `POST` | `/api/audit` | Crawls URL → SiteFacts → forwards to agents-api (`POST /audit`), returns full [AuditReport](/data/audit-report.md). Blocking. |
| `POST` | `/api/audit/start` | Async variant: crawls URL → SiteFacts → fires agents in background. Returns `{audit_id, agent_ids}` immediately so the client can subscribe to SSE streams. |
| `GET`  | `/agent/stream/{agent_id}` | SSE proxy — transparently forwards the agents-api stream for one agent to the browser. See [Streaming](/components/streaming.md). |
| `GET`  | `/api/audit/{audit_id}` | Poll proxy — returns `AuditReport` or `202 {"status":"running"}` while agents are still running. |
| `POST` | `/scrape` | Raw [Firecrawl](/external/firecrawl.md) passthrough — debug utility. |
| `GET`  | `/health` | Liveness + Firecrawl/cache status. |

### Agents-api (`agents/app/main.py`)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/audit` | Blocking: run 4 agents + aggregator, return AuditReport. |
| `POST` | `/audit/start` | Async: accept `AuditStartRequest` (SiteFacts + audit_id + agent_ids), start background task, return immediately. |
| `GET`  | `/agent/stream/{agent_id}` | SSE stream of [AgentStatusEvents](/data/agent-status-event.md) for one agent. Closes when agent emits its sentinel. |
| `GET`  | `/audit/{audit_id}/result` | Returns AuditReport or `202` while still running. |
| `POST` | `/audit/batch` | Run pipeline on up to 10 SiteFacts, one AuditReport each. |
| `GET`  | `/health` | Liveness. |

## Rate limiting

All routes pass through the [IP-Based Rate Limiter](/components/rate-limiter.md) middleware. Limits are per client IP (default: 5 requests / 12 h). Whitelisted IPs (e.g. `127.0.0.1`) bypass the limiter entirely. Disable with `RATE_LIMIT_ENABLED=false`.

## Streaming flow (`POST /api/audit/start`)

Before forwarding SiteFacts to agents-api, the API limits the markdown field to
12,000 characters. The agents already use smaller prompt slices, so this avoids
copying arbitrarily large page content into the inference container without
removing any facts used by their judgments.

`AGENTS_URL` in the backend config points at the agents-api service. The async audit flow:

1. `SiteFactsPipeline.run(url)` — served from Redis cache if already crawled.
2. Backend generates `audit_id` (UUID) + 4 `agent_ids` (one UUID per agent).
3. POSTs `AuditStartRequest` (`{sitefacts, audit_id, agent_ids}`) to `{AGENTS_URL}/audit/start` with a 10 s timeout. Agents-api starts a background task and returns immediately.
4. Backend returns `{audit_id, agent_ids}` to the caller.
5. Caller subscribes to `GET /agent/stream/{agent_id}` for each agent.
6. Caller polls `GET /api/audit/{audit_id}` for the final report.

## Mock stream mode (`MOCK_STREAM=true`)

When `MOCK_STREAM=true` is set, the three streaming routes (`/api/audit/start`, `/agent/stream/{agent_id}`, `/api/audit/{audit_id}`) branch into a zero-cost passthrough: Firecrawl and agents-api are skipped entirely, static fixtures are used, and SSE events are emitted on a realistic schedule from an in-process background task. All other routes remain on the real path. See [Mock Stream Passthrough](/components/mock-stream.md) for full details.

## Blocking flow (`POST /api/audit`)

Legacy/direct path: backend crawls, forwards SiteFacts JSON to `{AGENTS_URL}/audit` with a 120 s timeout, returns the full AuditReport synchronously. No streaming. Unchanged from the previous version.

## Planned

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/audit/{id}/report.pdf` | [PDF export](/components/pdf-export.md). |

# Citations
[1] [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
[2] [SSE specification (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
