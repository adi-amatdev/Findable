---
type: External Dependency
title: Fireworks API
status: implemented
description: Remote inference fallback serving Gemma 4 26B A4B IT for heavy roles and Gemma 4 E4B for light roles when the AMD/vLLM endpoints are unavailable.
tags: [external, inference, fireworks, gemma]
timestamp: 2026-07-11T00:00:00Z
---

# Fireworks API

The remote inference fallback behind the [Model Router](/components/model-router.md), used when the AMD/vLLM endpoints are blank or fail the startup probe.

## Selected models

| Tier | Model path | Roles |
|---|---|---|
| Heavy | `accounts/fireworks/models/gemma-4-26b-a4b-it` | `crawlability_judgment`, `content_signal`, `report_writer` |
| Light | `accounts/fireworks/models/gemma-4-e4b` | `structured_data`, `entity_topic`, reserved light roles |

Both are called through Fireworks' OpenAI-compatible inference endpoint, using the same request shape as the local [vLLM server](/components/vllm-server.md).

## License note

Gemma 4 has a Google-published Apache 2.0 license page. Earlier local Gemma 2 models are governed by Google's Gemma Terms of Use. Production operators must comply with the applicable Google/Hugging Face/Fireworks terms for the model and hosting path they choose.

# Citations
[1] [Fireworks AI docs](https://docs.fireworks.ai)
[2] [Fireworks Gemma 4 26B A4B IT](https://fireworks.ai/models/fireworks/gemma-4-26b-a4b-it)
[3] [Fireworks Gemma 4 E4B](https://fireworks.ai/models/fireworks/gemma-4-e4b)
[4] [Gemma Terms of Use](https://ai.google.dev/gemma/terms)
[5] [Gemma 4 Apache 2.0 license](https://ai.google.dev/gemma/apache_2)
