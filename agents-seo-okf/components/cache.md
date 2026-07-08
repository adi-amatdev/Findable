---
type: Infrastructure
title: Cache / State Store
status: implemented
description: URL-hash-keyed Redis store for crawl results, so re-runs never re-fetch and never waste Firecrawl credits.
tags: [cache, redis, state]
timestamp: 2026-07-08T00:00:00Z
---

# Cache / State Store

Keyed by a SHA-256 hash of the URL. On a hit the pipeline short-circuits the
network entirely, which makes re-runs and demo runs instant and saves Firecrawl
credits on repeated URLs.

## What is cached

- **`RawCrawl` blobs** — output of [Crawl & Fetch](/components/crawl-fetch.md).
  Implemented today.
- **`AuditReport`s** — planned, once the [Aggregator](/components/aggregator.md)
  exists.

## Implementation

**Redis** (async `redis-py`), `app/cache/store.py`. The spec left the choice open
("SQLite for the hackathon, Redis-compatible for production"); we went straight to
Redis to reuse the existing service. Behaviour:

- Check-first: [CrawlFetcher](/components/crawl-fetch.md) looks up the URL hash
  before crawling; `refresh: true` on the request bypasses it.
- **Graceful degradation** — any Redis error is swallowed and treated as a miss
  (or a no-op write), so a Redis outage slows the pipeline but never breaks it.
- **Persistence** — RDB snapshots on a named Docker volume auto-load on startup,
  so the cache survives `docker compose down` / `up`.
