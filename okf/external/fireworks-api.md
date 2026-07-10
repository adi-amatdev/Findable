---
type: External Dependency
title: Fireworks API
status: implemented
description: Serverless cloud inference fallback using GPT OSS 120B for heavy roles and GPT OSS 20B for light roles; Gemma-family Fireworks models are documented as on-demand only.
tags: [external, inference, fireworks, serverless, fallback]
timestamp: 2026-07-11T00:00:00Z
---

# Fireworks API

The cloud inference fallback behind the [Model Router](/components/model-router.md), used when the AMD/vLLM endpoints are blank or fail the startup probe.

## Serverless defaults

| Tier | Model path | Serverless price | Roles |
|---|---|---|---|
| Heavy | `accounts/fireworks/models/gpt-oss-120b` | $0.15 input / $0.015 cached input / $0.60 output per 1M tokens | `crawlability_judgment`, `content_signal`, `report_writer` |
| Light | `accounts/fireworks/models/gpt-oss-20b` | $0.07 input / $0.035 cached input / $0.30 output per 1M tokens | `structured_data`, `entity_topic`, reserved light roles |

These two models can be called with only `FIREWORKS_KEY`; no dedicated deployment is required.

## Gemma-family check

The checked Fireworks Gemma-family pages mark serverless as "Not supported":

- `accounts/fireworks/models/gemma-4-26b-a4b-it`
- `accounts/fireworks/models/gemma-4-e4b`
- `accounts/fireworks/models/gemma-3-27b-it`

Those remain valid model paths for on-demand deployment if a deployment is later approved, but they are not the no-deployment fallback defaults.

## Guided JSON handling

The local vLLM path accepts `guided_json`; Fireworks uses OpenAI-compatible `response_format: { "type": "json_schema", ... }`. `AsyncLLMClient.chat_completion()` translates `guided_json` to Fireworks `json_schema` format when the backend URL is `api.fireworks.ai`, keeps `guided_json` for vLLM, and omits it for Ollama.

# Citations
[1] [Fireworks AI docs](https://docs.fireworks.ai)
[2] [Fireworks serverless pricing](https://docs.fireworks.ai/serverless/pricing)
[3] [Fireworks GPT OSS 120B](https://fireworks.ai/models/fireworks/gpt-oss-120b)
[4] [Fireworks GPT OSS 20B](https://fireworks.ai/models/fireworks/gpt-oss-20b)
[5] [Fireworks Gemma 4 26B A4B IT](https://fireworks.ai/models/fireworks/gemma-4-26b-a4b-it)
[6] [Fireworks Gemma 4 E4B](https://fireworks.ai/models/fireworks/gemma-4-e4b)
