---
type: Service
title: Model Router
status: implemented
description: Selects which model and backend for each LLM role. Dual vLLM endpoints (heavy + light) with Fireworks cloud fallback and Ollama as last resort. Backends are probed at startup.
tags: [inference, routing, failover, ollama, vllm, fireworks]
timestamp: 2026-07-09T00:00:00Z
---

# Model Router

Every agent and the aggregator calls through the router. Implemented in `agents/app/models/router.py`.

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
| `FIREWORKS_HEAVY_MODEL` | Fireworks model for heavy roles | `accounts/fireworks/models/gemma-4-27b-it` |
| `FIREWORKS_LIGHT_MODEL` | Fireworks model for light roles | `accounts/fireworks/models/gemma-4-e4b-it` |
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

## Current GPU models (server_files/serve.sh)

- **Light** (`VLLM_LIGHT_URL`): `google/gemma-2-2b-it`, served as `light`
- **Heavy** (`VLLM_URL`): `google/gemma-2-9b-it`, served as `heavy`

## Failover behaviour

`call_with_fallback(role, ...)` iterates the chain left to right. It catches `httpx.HTTPStatusError` (4xx/5xx) and `httpx.TransportError` (ConnectError, TimeoutException, etc.) — both trigger the next backend. Any other exception propagates immediately.

If all backends fail for a role, a `RuntimeError` is raised with a message listing all attempted models.

## Backends

- **vLLM (remote)** — two separate cloudflared tunnels, one per model size. See [vLLM server](/components/vllm-server.md).
- **[Fireworks](/external/fireworks-api.md)** — cloud fallback. Disabled when `LOCAL_ONLY=1` or `FIREWORKS_KEY` is empty.
- **Ollama** — local last resort. Probed at `/api/tags`.
