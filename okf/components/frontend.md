---
type: Service
title: Next.js Frontend
status: partial
description: Minimal Next.js dashboard — story hero, four streaming agent columns with skeletons, and a report file-chip that opens a split pane with markdown/PDF export.
tags: [frontend, nextjs, react, sse, animejs]
timestamp: 2026-07-08T00:00:00Z
---

# Next.js Frontend

Lives in `frontend/`. Single-page dashboard (plain CSS + anime.js for motion;
no chart/CSS frameworks). Communicates with the
[FastAPI layer](/components/api.md). Active during `crawling` or `judging`
stages turns the Audit button into a Cancel button (red styling) that aborts
the fetch and closes all SSE streams.

## Flow (as built)

1. **Story hero** — centered URL form plus a four-beat narrative
   (Crawl → Facts → Judge → Report) explaining the product; hero compresses via
   animated transition once an audit starts.
2. **Facts strip** — `POST /api/sitefacts` result compressed to one dense line
   (HTTP, blocked AI bots, JS-gated %, schema types, words, llms.txt).
3. **Four agent columns** — one per [agent](/agents/), each with a shimmering
   skeleton until its stream produces tokens. Each column subscribes to
   **`GET /agent/stream/{agent_id}`** (SSE). Events tolerated: plain-text tokens,
   `{type: token|status|result|done}` JSON. Endpoint is not live yet; columns
   degrade to an honest "stream offline" state.
4. **Report chip** — when all four agents settle, the columns collapse
   (anime.js stagger) into a Claude-style file bar. Clicking opens a **split
   pane** rendering the aggregated markdown report, with **↓ .md** and **↓ PDF**
   (print-pipeline) export.

## Deviations from the original spec

- Per-agent **streaming text columns with skeletons** replace the spinner list;
  stream path is `/agent/stream/{agent_id}` rather than `/api/audit/{id}/events`.
- Score card / radar / knowledge-graph panels are deferred until the
  [Aggregator](/components/aggregator.md) returns a real
  [AuditReport](/data/audit-report.md); the report currently renders as markdown
  composed client-side from SiteFacts + streamed judgments.
- PDF export is client-side print for now; `GET /api/audit/{id}/report.pdf`
  ([PDF Export](/components/pdf-export.md)) remains the target.

## Frontend choice decision

Next.js (App Router, pinned 13.5 for Node 16). See
[Frontend Choice](/decisions/frontend-choice.md).
