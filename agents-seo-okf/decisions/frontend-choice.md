---
type: Decision
title: Frontend Choice (Next.js vs Native.Builder)
description: Open decision between Next.js (reference stack) and Native.Builder (team learning curve); the API contract is identical for both.
tags: [decision, frontend, open]
timestamp: 2026-07-08T00:00:00Z
---

# Frontend Choice

## Status: open (as of architecture doc)

The team is learning Native.Builder. Next.js is the fallback and the reference stack used in this document. The actual choice is based on how the Native.Builder learning curve feels by Thursday of the build week.

## What's frozen regardless

The [API surface](/components/api.md) — four routes, SSE stream — is identical for both frontends. Whichever is chosen, the backend does not change.

## What the reference implementation uses

[Next.js + React](/components/frontend.md), Recharts for the radar chart, react-flow for the knowledge graph.
