---
type: Service
title: Deterministic Extraction
status: implemented
description: Parses raw and rendered HTML with no LLM to produce the SiteFacts object that all four agents read.
tags: [extraction, parsing, nlp, sitefacts]
timestamp: 2026-07-08T00:00:00Z
---

# Deterministic Extraction

No LLM. Builds the single source of truth every agent reads. Implements design principle 1: [Deterministic–LLM Separation](/decisions/deterministic-llm-separation.md).

## What it extracts

| Library | Output |
|---|---|
| `extruct` | JSON-LD, Microdata, RDFa, OpenGraph; schema.org type detection + validity |
| `lxml` / `selectolax` | title, meta description, canonical, lang, `h1..h3` outline, word count, link graph |
| Render diff | `js_dependency_ratio = 1 - raw_text_len / rendered_text_len` |
| `robots.txt` parse | Per-bot allow/deny for `GPTBot`, `ClaudeBot`, `PerplexityBot`, `OAI-SearchBot`, `Google-Extended`, `CCBot` |
| `spaCy` NER | Candidate entities (text + label) |

## The JS-dependency ratio

`js_dependency_ratio` is the highest-signal, most demoable finding in the whole system. A value near 1.0 means almost all content is injected by JavaScript — invisible to AI crawlers that don't execute JS. It is used by the [Crawlability agent](/agents/crawlability.md) and by the [AI Readiness Score](/scoring/ai-readiness-score.md) hard-gate logic.

## Output

All extracted fields are assembled into a [SiteFacts](/data/site-facts.md) object. This object is cached by URL hash (see [Cache](/components/cache.md)) and passed unchanged to all four agents.

**Rule of thumb from the architecture:** if a Python library can answer it, it does not go to a model.

## Implementation status

Implemented in `app/extraction/extractor.py` as `build_site_facts(RawCrawl) -> SiteFacts`.
Fully deterministic; the same `RawCrawl` always yields the same [SiteFacts](/data/site-facts.md).

Library choices differ from the spec's ideal, with drop-in seams left for the richer options:
- **Structured data:** BeautifulSoup JSON-LD parsing (not `extruct`) — covers the
  common case; Microdata/RDFa via `extruct` slots in behind `_structured_data()`.
- **Entities:** a capitalized-phrase heuristic (not `spaCy` NER) to stay
  dependency-light; `spaCy` slots in behind `_entities()`.
- **JS-render diff, robots per-bot parse, sitemap (lxml), llms.txt, HTML/meta,
  link graph, authorship** are all implemented as specified.
