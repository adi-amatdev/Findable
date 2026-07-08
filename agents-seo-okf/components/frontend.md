---
type: Service
title: Next.js Frontend
description: React dashboard showing the score card, category radar, knowledge-graph view, prioritized fix list, and live per-agent status spinners.
tags: [frontend, nextjs, react, sse]
timestamp: 2026-07-08T00:00:00Z
---

# Next.js Frontend

Serves the audit dashboard. Communicates with the [FastAPI layer](/components/api.md) over its four routes.

## Dashboard panels

- **Score card** — hero AI Readiness Score (landing-page number).
- **Category radar** — Recharts radar chart of the four sub-scores (crawlability, content, structured data, entity/topic).
- **Knowledge-graph view** — react-flow visualization of the entity graph returned by the [Entity & Topic agent](/agents/entity-topic.md).
- **Prioritized fix list** — findings sorted by impact ÷ effort, each with a severity badge, effort estimate, and link to an authoritative reference.
- **Per-agent status spinners** — driven by SSE events from `/api/audit/{id}/events`; one spinner per agent, shows `started` → `finished` in real time.
- **Site-health panel** — coverage stats (`has_schema_pct`, `js_rendered_pct`, `meta_desc_pct`, `author_date_pct`) and systemic recommendations from the Tier-3 shallow pass.
- **PDF export button** — triggers `GET /api/audit/{id}/report.pdf`.

## Rendering surface

The same layout is used for both the browser dashboard and the [PDF Export](/components/pdf-export.md) — Playwright prints the dashboard HTML, so there is one layout, two surfaces.

## Frontend choice decision

The architecture notes this was an open decision (Next.js vs Native.Builder); Next.js is the reference stack used here. See [Frontend Choice](/decisions/frontend-choice.md).
