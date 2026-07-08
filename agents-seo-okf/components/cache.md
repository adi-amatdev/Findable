---
type: Infrastructure
title: Cache / State Store
description: URL-hash-keyed store for RawCrawl blobs and AuditReports; SQLite for the hackathon, Redis-compatible for production.
tags: [cache, sqlite, redis, state]
timestamp: 2026-07-08T00:00:00Z
---

# Cache / State Store

Two things are cached, both keyed by URL hash:

- **`RawCrawl` blobs** — output of [Crawl & Fetch](/components/crawl-fetch.md). Makes re-runs and demo runs instant without re-fetching.
- **`AuditReport`s** — final output of the [Aggregator](/components/aggregator.md). Lets `GET /api/audit/{id}` return instantly on a cache hit, and allows the [PDF Export](/components/pdf-export.md) to fetch the report independently.

**Implementation:** SQLite for the hackathon (zero-ops, single-file). The interface is Redis-compatible so swapping in Redis for a production deploy is a one-line config change.

The [Orchestrator](/components/orchestrator.md) checks the cache as step 1 of every run and short-circuits to the aggregated report if a hit is found — this is what makes repeat and demo runs instant while also saving API credits on repeated URLs.
