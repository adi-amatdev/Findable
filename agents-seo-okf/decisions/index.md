---
title: decisions
description: Directory listing for progressive disclosure.
---

# decisions

## Concepts
- [derived-visibility](derived-visibility.md) -- The before/after visibility numbers are computed deterministically from SiteFacts signals, not measured via embedding/retrieval — locked for POC scope.
- [deterministic-llm-separation](deterministic-llm-separation.md) -- All parsing happens in plain code producing SiteFacts; LLMs only judge on top of the facts — never parse. Makes audits fast, cheap, and reproducible.
- [frontend-choice](frontend-choice.md) -- Open decision between Next.js (reference stack) and Native.Builder (team learning curve); the API contract is identical for both.
- [parallel-inference-amd](parallel-inference-amd.md) -- One vLLM server handles concurrent agent requests via continuous batching — not N model copies — which is how real GPU parallelism works and what makes the AMD/Gemma story defensible.
