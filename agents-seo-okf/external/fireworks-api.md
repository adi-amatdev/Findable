---
type: External Dependency
title: Fireworks API
description: Remote inference endpoint serving Gemma 4 31B for the two heaviest LLM roles — E-E-A-T judgment and executive summary writing.
tags: [external, inference, fireworks, gemma]
timestamp: 2026-07-08T00:00:00Z
---

# Fireworks API

The remote inference backend, used for the two roles that benefit most from the larger model:

1. **[Content Signal (E-E-A-T) agent](/agents/content-signal.md)** — nuanced judgment on authoritativeness and citation-worthiness.
2. **[Aggregator](/components/aggregator.md) report writer** — synthesizes all findings into an executive summary.

## Model

Gemma 4 31B (the full-size variant). Called through the [Model Router](/components/model-router.md) via an OpenAI-compatible HTTP endpoint — same interface as the local [vLLM server](/components/vllm-server.md), so swapping endpoints is a config string change.

## License note

Gemma models ship under the **Gemma Terms of Use** (permissive, but not Apache 2.0). This is the correct answer if a judge asks about model licensing.

# Citations
[1] [Fireworks AI docs](https://docs.fireworks.ai)
[2] [Gemma Terms of Use](https://ai.google.dev/gemma/terms)
