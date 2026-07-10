---
type: Service
title: Model Router
status: implemented
description: Selects which model and backend for each LLM role. Dual vLLM endpoints (heavy + light) with Fireworks cloud fallback and Ollama as last resort. Backends are probed at startup.
tags: [inference, routing, failover, ollama, vllm, fireworks]
timestamp: 2026-07-11T00:00:00Z
---

# Model Router

Every agent and the aggregator calls through the router. Implemented in `agents/app/models/router.py`. The actual HTTP call and payload construction live one layer down, in `AsyncLLMClient.chat_completion()` (`agents/app/models/client.py`).

## Priority order

```
vLLM (remote GPU)  →  Fireworks API (cloud)  →  Ollama (local)
```

At FastAPI startup, `probe_backends()` makes a health-check request to each configured endpoint and sets a module-level `_backend_ok` dict. The fallback chain for every role is built from this dict at call time — stale or missing URLs are silently skipped rather than crashing.

## Configuration

| Env var | Purpose | Default |
|---|---|---|
| `VLLM_URL` | Heavy vLLM endpoint (cloudflared URL) | _(empty — tier skipped)_ |
| `VLLM_LIGHT_URL` | Light vLLM endpoint (cloudflared URL) | _(empty — tier skipped)_ |
| `VLLM_HEAVY_MODEL_NAME` | `--served-model-name` on heavy server | `heavy` |
| `VLLM_LIGHT_MODEL_NAME` | `--served-model-name` on light server | `light` |
| `FIREWORKS_KEY` | Fireworks API key | _(empty — tier skipped)_ |
| `FIREWORKS_HEAVY_MODEL` | Fireworks serverless model for heavy roles | `accounts/fireworks/models/gpt-oss-120b` |
| `FIREWORKS_LIGHT_MODEL` | Fireworks serverless model for light roles | `accounts/fireworks/models/gpt-oss-20b` |
| `OLLAMA_URL` | Local Ollama | `http://localhost:11434` |
| `LOCAL_LIGHT_MODEL` | Ollama model for light roles | `gemma4:e2b` |
| `LOCAL_HEAVY_MODEL` | Ollama model for heavy roles | `gemma4:e2b` |
| `LOCAL_ONLY` | Strip Fireworks from all chains | `0` |

## Role → tier mapping

| Role | Tier | Primary backend |
|---|---|---|
| `orchestrator` | light | `VLLM_LIGHT_URL` / `light` |
| `crawlability_subagent` | light | `VLLM_LIGHT_URL` / `light` |
| `structured_data` | light | `VLLM_LIGHT_URL` / `light` |
| `entity_topic` | light | `VLLM_LIGHT_URL` / `light` |
| `crawlability_judgment` | heavy | `VLLM_URL` / `heavy` |
| `content_signal` | heavy | `VLLM_URL` / `heavy` |
| `report_writer` | heavy | `VLLM_URL` / `heavy` |

## Current GPU models (`vllm_hosting/start_service.sh`)

- **Light** (`VLLM_LIGHT_URL`): `google/gemma-2-2b-it`, served as `light`
- **Heavy** (`VLLM_URL`): `google/gemma-2-9b-it`, served as `heavy`

## Fireworks serverless fallback models

- **Heavy roles** (`crawlability_judgment`, `content_signal`, `report_writer`): `accounts/fireworks/models/gpt-oss-120b`
- **Light roles** (`structured_data`, `entity_topic`, reserved orchestrator roles): `accounts/fireworks/models/gpt-oss-20b`

Fireworks' Gemma-family model pages checked for this project mark serverless as "Not supported", so the no-deployment fallback defaults use serverless GPT OSS models. If on-demand deployments are later approved, the Gemma paths remain available as optional overrides: `accounts/fireworks/models/gemma-4-26b-a4b-it` and `accounts/fireworks/models/gemma-4-e4b`.

## Failover behaviour

`call_with_fallback(role, ...)` iterates the chain left to right. It catches `httpx.HTTPStatusError` (4xx/5xx) and `httpx.TransportError` (ConnectError, TimeoutException, etc.) — both trigger the next backend. Any other exception propagates immediately.

If all backends fail for a role, a `RuntimeError` is raised with a message listing all attempted models.

## Gemma chat-template compatibility (system-role merge)

Gemma's chat template — used by all three backends here, since every tier serves a Gemma variant — rejects a `system`-role message outright (`"System role not supported"`, HTTP 400). Every agent builds `[{"role": "system", ...}, {"role": "user", ...}]` messages, so every vLLM call would 400 and silently fall through to Fireworks/Ollama.

Fixed in `AsyncLLMClient.chat_completion()` (`agents/app/models/client.py`) via `_merge_system_message()`: if the first message is `role: system`, its content is folded into the following `user` message (same combined text, one message instead of two) before the request is sent. Applies to every caller uniformly — no per-agent changes needed. Confirmed live: pre-fix, a content_signal call against the heavy vLLM tier 400'd with `"System role not supported"`; post-fix, the identical prompt returned a normal scored JSON response.

## Token usage logging

`call_with_fallback(role, *, agent=None, audit_id=None, **kwargs)` also accepts optional `agent`/`audit_id` params (popped before forwarding to `AsyncLLMClient.chat_completion`, never leaked into the request payload). On every successful response it extracts `usage.prompt_tokens`/`completion_tokens`/`total_tokens` and persists them via [Token Usage Logging](/components/token-logging.md) — this is the one choke point every LLM call passes through, so it's also where the previously-untracked `report_writer` call gets captured.

## Backends

- **vLLM (remote)** — two separate cloudflared tunnels, one per model size. See [vLLM server](/components/vllm-server.md).
- **[Fireworks](/external/fireworks-api.md)** — cloud fallback. Disabled when `LOCAL_ONLY=1` or `FIREWORKS_KEY` is empty.
- **Ollama** — local last resort. Probed at `/api/tags`.
