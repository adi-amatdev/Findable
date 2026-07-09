---
type: Service
title: Next.js Frontend
status: implemented
description: Single-page Renaissance-themed dashboard with anime.js animations, SSE streaming agent columns, cancel/abort support, and a report dashboard with animated score gauge, visibility estimate, findings, and markdown/PDF export.
tags: [frontend, nextjs, react, sse, animejs, report-dashboard]
timestamp: 2026-07-09T00:00:00Z
---

# Next.js Frontend

Lives in `frontend/`. Single-page dashboard (plain CSS + anime.js for motion; no chart/CSS frameworks). Communicates with the [FastAPI layer](/components/api.md). Next.js App Router on Node 16 — see [Frontend Choice](/decisions/frontend-choice.md).

## Stage flow

The frontend progresses through five stages, each with animated entrance/exit transitions:

| Stage | What happens |
|---|---|
| `idle` | Story hero with URL form + four-beat narrative (Crawl → Facts → Judge → Report). Wiki side-panel opens on tap. |
| `crawling` | Spinner + "Crawling rendered + raw, extracting SiteFacts…" |
| `judging` | Four [agent](/agents/) columns streaming SSE events in real time. Continue button appears when all agents settle. |
| `generating` | Progress stepper (4 steps) with animated checkmark at completion. Lasts ~5 s then transitions to report. |
| `report` | Full [ReportDashboard](/components/ReportDashboard.md) with score gauge, findings, visibility estimate, site coverage, and per-agent results. |

## Detailed flow (as built)

1. **Story hero** — centered URL `input` + "Audit" button + a four-beat narrative explaining the product. Hero compresses via anime.js transition once an audit starts. Each story step can be tapped to open a `WikiModal` with educational content about crawl, facts, judges, and scoring.

2. **Crawl + facts** — `POST /api/sitefacts` runs the [SiteFacts Pipeline](/components/pipeline.md). A [FactsStrip](/components/FactsStrip.md) compresses the result to one dense line (HTTP status, blocked AI bots, JS-gated %, schema types, word count, llms.txt status).

3. **Four agent columns** — one per [agent](/agents/), each with a shimmering skeleton until the SSE stream produces events. Each column subscribes to `GET /agent/stream/{agent_id}` via `EventSource("agent_status")`. Events are parsed from the [AgentStatusEvent](/data/agent-status-event.md) wire format. Columns display phase names and detail text as they arrive. On `complete` or `error` the column marks itself `done`.

4. **Polling for the report** — when all four agents settle (phase `done` or `offline`), the frontend calls `GET /api/audit/{audit_id}` to fetch the [AuditReport](/data/audit-report.md). If the backend responds with `202 {"status":"running"}` (report not yet ready), it retries up to 10 times at 1.5 s intervals (~15 s total). After exhausting retries, it falls back to [composeFallbackReport](#composefallbackreport) which builds a report from the agents' SSE scores.

5. **Continue button** — after a 600 ms settle delay, a "Continue →" button appears. Clicking it collapses the agent columns with an anime.js stagger-out animation and transitions to the `generating` stage.

6. **Generating** — a 4-step progress indicator cycles every 1.1 s for ~5 s total (Crawl data → Content signal → Structuring report → Finalizing dashboard). When complete, an animated checkmark plays before transitioning to the report stage.

7. **Report dashboard** — mounts [ReportDashboard](https://github.com/anomalyco/Findable/frontend/components/ReportDashboard.tsx) with animated entrance from the right. The component renders the full [AuditReport](/data/audit-report.md) — animated score gauge, category score bars, visibility estimate, findings list, site coverage cards, and per-agent results with knowledge graph.

## Cancellation

During `crawling` or `judging` stages, the Audit button turns into a Cancel button (red styling). Clicking it:
- Aborts all in-flight HTTP requests via `AbortController.abort()`
- Closes all SSE streams via `EventSource.close()`
- Resets `auditIdRef`, agent state, and the `agentsDone`/`continueReady` flags
- Returns to `idle`

## composeFallbackReport

When the audit result API returns an error (or the report isn't ready after max retries), the frontend constructs a fallback [AuditReport](/data/audit-report.md) client-side:

- **Agent scores**: extracted from the SSE `score` field on each agent's `complete` phase. If an agent has no score, a random 40–80 value is assigned.
- **Weighted score**: formula matches the [AI Readiness Score](/scoring/ai-readiness-score.md) rubric: `0.30 × crawlability + 0.35 × content_signal + 0.15 × structured_data + 0.20 × entity_topic`.
- **Findings**: four hardcoded findings (JS dependency, robots.txt, author metadata, llms.txt) using [SiteFacts](/data/site-facts.md) data where available.
- **Visibility**: hardcoded before/after estimates (realistic defaults).
- **Scope**: `{ deep_pages: 4, shallow_pages: 0 }`.
- **Site coverage**: computed from facts (schema present, JS ratio, meta description, author/date).

## Deviations from the original architecture spec

- Per-agent **streaming text columns with skeletons** replace the spinner list.
- Stream path is `GET /agent/stream/{agent_id}` rather than `/api/audit/{id}/events`.
- Score card / radar / knowledge-graph panels are deferred until the [Aggregator](/components/aggregator.md) returns a real [AuditReport](/data/audit-report.md). The dashboard renders findings, scores, visibility, coverage, and agent results.
- PDF export is client-side `window.print()` for now; `GET /api/audit/{id}/report.pdf` ([PDF Export](/components/pdf-export.md)) remains the target.

## Live demo notes

- `MOCK_STREAM=true` on the backend lets the full frontend flow run without Firecrawl, agents-api, or any external AI service. See [Mock Stream Passthrough](/components/mock-stream.md).
- SSE streams require the backend at `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`).
