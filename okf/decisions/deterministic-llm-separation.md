---
type: Decision
title: Deterministic–LLM Separation
description: All parsing happens in plain code producing SiteFacts; LLMs only judge on top of the facts — never parse. Makes audits fast, cheap, and reproducible.
status: implemented
tags: [decision, architecture, principle]
timestamp: 2026-07-08T00:00:00Z
---

# Deterministic–LLM Separation

**Design Principle 1** — the first of two principles that shape the entire architecture.

## The rule

All parsing — robots.txt, sitemap, `llms.txt`, JSON-LD/schema, meta tags, heading outline, JS-render check, NER — happens **once, in plain code**, producing a single [SiteFacts](/data/site-facts.md) object. LLMs never parse — they only *judge* on top of the facts.

> Rule of thumb: if a Python library can answer it, it does not go to a model.

## Why it matters

- **Fast** — extraction runs once per URL, cached by URL hash.
- **Cheap on API credits** — LLM calls are scoped to judgment only, not data retrieval.
- **Reproducible** — the same URL yields the same [SiteFacts](/data/site-facts.md) and thus the same score. Reproducibility is what makes a scoring tool trustworthy. This is a defensible answer to judge questions like "why should I trust this score?"

## Where this is enforced

[Deterministic Extraction](/components/extraction.md) is the implementation of this principle. The [Orchestrator](/components/orchestrator.md) ensures it runs exactly once per URL per deep-audit tier before any agent fires.
