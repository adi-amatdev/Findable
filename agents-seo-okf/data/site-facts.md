---
type: Data Contract
title: SiteFacts
description: The deterministic, LLM-free snapshot of a single page — every signal the four agents read, produced once by the extraction pipeline.
tags: [data, contract, extraction, sitefacts]
timestamp: 2026-07-08T00:00:00Z
---

# SiteFacts

Produced by [Deterministic Extraction](/components/extraction.md) from the [Crawl & Fetch](/components/crawl-fetch.md) output. Cached by URL hash in [Cache](/components/cache.md). Passed unchanged to all four [agents](/agents/).

No LLM ever writes or modifies a SiteFacts object — only reads it.

## Schema

```jsonc
{
  "url": "...", "final_url": "...", "fetched_at": "ISO8601",
  "http":   { "status": 200, "latency_ms": 340, "redirects": 0, "content_type": "text/html" },
  "robots": { "exists": true,
              "allows": { "GPTBot": true, "ClaudeBot": true, "PerplexityBot": false,
                          "OAI-SearchBot": true, "Google-Extended": true, "CCBot": true },
              "sitemap_refs": ["..."] },
  "sitemap":  { "exists": true, "valid": true, "url_count": 812 },
  "llms_txt": { "exists": false, "valid": false, "has_summary": false,
                "link_count": 0, "full_variant": false },
  "render":   { "raw_text_len": 480, "rendered_text_len": 5120,
                "js_dependency_ratio": 0.91, "content_visible_without_js": false },
  "html":     { "title": "...", "meta_description": "...", "canonical": "...", "lang": "en",
                "outline": [{ "level": 1, "text": "..." }], "word_count": 1340,
                "og": { "...": "..." }, "twitter": { "...": "..." } },
  "structured_data": { "schema_types": ["Article", "Organization"], "jsonld_valid": true, "errors": [] },
  "links":    { "internal": 42, "external": 7, "outbound_citations": 3 },
  "authorship": { "byline_present": true, "author_schema": false,
                  "dates": { "published": "...", "modified": "..." } },
  "entities_raw": [{ "text": "ROCm", "label": "PRODUCT" }]
}
```

## Key field — `js_dependency_ratio`

`1 - raw_text_len / rendered_text_len`. Near 1.0 means content is JS-gated. This is the highest-signal, most demoable finding in the whole system and drives a [hard gate](/scoring/ai-readiness-score.md) in the score.
