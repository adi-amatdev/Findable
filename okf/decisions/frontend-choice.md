---
type: Decision
title: Frontend Choice (Next.js chosen over Native.Builder)
description: Next.js 13.5 (App Router) was chosen as the frontend framework. The API contract is framework-agnostic.
status: implemented
tags: [decision, frontend, nextjs]
timestamp: 2026-07-09T00:00:00Z
---

# Frontend Choice

## Decision: Next.js

The frontend was built with **Next.js 13.5 (App Router)** on Node.js 16. Native.Builder was evaluated but the team chose Next.js for familiarity and the faster iteration cycle given the hackathon timeline.

## What the implementation uses

[Next.js + React](/components/frontend.md) in `frontend/` — single-page dashboard with plain CSS + anime.js for motion. No chart or CSS frameworks. The [ReportDashboard](https://github.com/anomalyco/Findable/frontend/components/ReportDashboard.tsx) component handles all report rendering without external visualization libraries.

## What's frozen regardless

The [API surface](/components/api.md) — `POST /api/sitefacts`, `POST /api/audit/start`, `GET /agent/stream/{agent_id}`, `GET /api/audit/{audit_id}` — is framework-agnostic. The frontend choice has no effect on the backend architecture.
