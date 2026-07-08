---
type: Service
title: Model Router
status: implemented
description: Selects which model and backend for each LLM role, with dual-backend routing (Ollama local + vLLM remote via tunnel) and Fireworks cloud fallback.
tags: [inference, routing, failover, ollama, vllm]
timestamp: 2026-07-08T00:00:00Z
---

# Model Router

Every agent and the aggregator calls through the router. Implemented in `agents/app/models/router.py`.

## Dual-backend design

The router reads two env vars to decide where to send requests:

| Env var | Purpose | Set to |
|---|---|---|
| `OLLAMA_URL` | Local Ollama — always used for light roles | `http://host.docker.internal:11434` (Docker) or `http://localhost:11434` (local) |
| `VLLM_URL` | Remote vLLM on GPU server via cloudflared tunnel | Tunnel HTTPS URL from [vLLM server](/components/vllm-server.md). Leave blank to fall back to Ollama. |
| `FIREWORKS_KEY` | Cloud fallback for heaviest roles | Fireworks API key |
| `LOCAL_ONLY` | Disable all cloud calls | `1` to skip Fireworks entirely |

## Role assignments

| Role | Backend chain |
|---|---|
| Orchestrator, crawlability sub-agent | Ollama (light model: `LOCAL_LIGHT_MODEL`) |
| Crawlability judgment, structured data, entity topic | vLLM heavy → vLLM mid → Ollama light → Fireworks |
| Content Signal (E-E-A-T), report writer | vLLM heavy → Ollama light → Fireworks |

If `VLLM_URL` is blank, all heavy roles fall back to Ollama — the system runs fully local at reduced quality.

## Failover

Within the heavy chain: `HEAVY_MODEL` → `MID_MODEL` → `LIGHT_MODEL` → Fireworks (if key present). Each attempt uses the same OpenAI-compatible endpoint format; only the base URL and model string change.

## Backends

- **Ollama** — always local; light roles go here unconditionally.
- **vLLM (remote)** — GPU server running on a Jupyter notebook machine, exposed via [cloudflared tunnel](/components/vllm-server.md). Heavy roles go here when `VLLM_URL` is set.
- **[Fireworks](/external/fireworks-api.md)** — cloud fallback. Disabled when `LOCAL_ONLY=1`.
