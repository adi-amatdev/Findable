---
type: Service
title: SiteFacts Pipeline
status: implemented
description: The implemented entrypoint that chains crawl+fetch and deterministic extraction to turn a URL into a SiteFacts object.
tags: [backend, pipeline, sitefacts]
timestamp: 2026-07-08T00:00:00Z
---

# SiteFacts Pipeline

The one end-to-end path that is fully built today: `app/pipeline.py`
(`SiteFactsPipeline.run(url)`), exposed as `POST /api/sitefacts` by the
[API](/components/api.md).

## Sequence

1. [Crawl & Fetch](/components/crawl-fetch.md) → `RawCrawl` (Firecrawl rendered +
   `httpx` raw / robots.txt / sitemap.xml / llms.txt), cached by URL hash in the
   [Cache](/components/cache.md).
2. [Deterministic Extraction](/components/extraction.md) → [SiteFacts](/data/site-facts.md).

No LLM is involved — this is the deterministic core the [agents](/agents/) will
read. It is a single-page (Tier-1) path; the multi-tier fan-out described by the
[Orchestrator](/components/orchestrator.md) is not built.

## Design principle

Implements [Deterministic–LLM Separation](/decisions/deterministic-llm-separation.md):
all parsing happens here in plain code; nothing downstream re-parses. The crawler
dependency is injectable, so the whole pipeline runs offline in tests.

See [scope-sitefacts-first](/decisions/scope-sitefacts-first.md) for why the build
stops here.
