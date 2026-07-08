---
type: External Dependency
title: Firecrawl
status: implemented
description: Crawl service that returns rendered HTML, clean markdown, metadata, links, and a screenshot in one call; used for all deep-audit page fetches.
tags: [external, crawl, firecrawl]
timestamp: 2026-07-08T00:00:00Z
---

# Firecrawl

Used by [Crawl & Fetch](/components/crawl-fetch.md) for deep-audited pages (Tier 1 and Tier 2).

## What it returns per call

- Rendered HTML (JavaScript executed)
- Clean markdown
- Metadata
- Internal links
- Screenshot

This rendered output is paired with the raw HTML fetched directly by `httpx` to compute `js_dependency_ratio` in [Deterministic Extraction](/components/extraction.md).

## Deployment

Self-hosted Docker or via Firecrawl cloud API — both present the same interface to the app. The choice has no effect on the rest of the architecture.

# Citations
[1] [Firecrawl docs](https://docs.firecrawl.dev)
