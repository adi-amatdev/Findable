---
type: Service
title: Crawl and Fetch
status: implemented
description: Retrieves raw and rendered HTML, robots.txt, sitemap, and llms.txt for the target URL across three crawl tiers.
tags: [crawl, fetch, firecrawl, httpx]
timestamp: 2026-07-08T00:00:00Z
---

# Crawl and Fetch

Two fetchers working together, each call producing a `RawCrawl` blob cached by URL hash.

## Fetchers

- **[Firecrawl](/external/firecrawl.md)** — returns rendered HTML, clean markdown, metadata, internal links, and a screenshot in one call.
- **`httpx`** — fetches `/robots.txt`, `/sitemap.xml`, `/llms.txt`, and the **raw** (unrendered) HTML directly.

The raw + rendered pair is what enables the JS-dependency check inside [Deterministic Extraction](/components/extraction.md): `js_dependency_ratio = 1 - raw_text_len / rendered_text_len`.

## Three-tier scope

The audit is not single-page. It covers three tiers of pages:

| Tier | Pages | What runs | LLM calls |
|---|---|---|---|
| **1 — Landing (deep)** | 1 | crawl + extract + all 4 agents | 4 |
| **2 — Follow-up (deep)** | `MAX_DEEP_PAGES` (~4) | same full audit per page | 4 × pages |
| **3 — Site (shallow)** | `MAX_SHALLOW_PAGES` (~50, capped) | deterministic extract only | 0 |

Follow-up page candidates come from nav links, high-prominence internal links, and sitemap entries — then ranked by the [Orchestrator](/components/orchestrator.md)'s small LLM step.

The shallow Tier-3 pass produces site-wide coverage stats (`has_schema_pct`, `js_rendered_pct`, `meta_desc_pct`, `author_date_pct`) that feed the site-health panel in the [Frontend](/components/frontend.md) and drive systemic findings in the [AuditReport](/data/audit-report.md).

## Implementation status

Implemented in `app/crawl/`:
- `firecrawl.py` — async Firecrawl client (formats `markdown`, `rawHtml`, `links`).
- `fetch.py` — `httpx` `DirectFetcher` for raw HTML + `/robots.txt`, `/sitemap.xml`,
  `/llms.txt` (each best-effort, `None` on failure).
- `fetcher.py` — `CrawlFetcher.crawl(url)` runs both concurrently and returns a
  `RawCrawl`, cached by URL hash via [Cache](/components/cache.md).

**Scope built:** Tier-1 (landing page) only. Tier-2 follow-up ranking and the
Tier-3 shallow site pass are not implemented (they belong to the planned
[Orchestrator](/components/orchestrator.md)).

# Citations
[1] [Firecrawl docs](https://docs.firecrawl.dev)
