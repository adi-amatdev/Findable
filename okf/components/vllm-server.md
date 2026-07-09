---
type: Infrastructure
title: vLLM GPU Server
status: partial
description: Two remote vLLM instances (light + heavy) running on an AMD GPU server, each exposed via a separate cloudflared tunnel and consumed by the Model Router.
tags: [inference, vllm, gpu, cloudflared, rocm, tunnel]
timestamp: 2026-07-09T00:00:00Z
---

# vLLM GPU Server

Two separate vLLM processes run on the AMD Radeon PRO W7900 server (48 GB VRAM), each behind its own cloudflared tunnel. The [Model Router](/components/model-router.md) selects between them based on role tier (light vs heavy).

## Hardware

AMD Radeon PRO W7900 · 48 GB VRAM · ROCm 7.2.1 · vLLM pre-installed.

## Models and ports

| Label | Model | Port | VRAM cap | env var |
|---|---|---|---|---|
| `light` | `google/gemma-2-2b-it` | 8000 | 10% (~4 GB) | `VLLM_LIGHT_URL` |
| `heavy` | `google/gemma-2-9b-it` | 8001 | 58% (~27 GB) | `VLLM_URL` |

Models are served with `--served-model-name light` / `--served-model-name heavy` so the model identifier in API requests is simply `"light"` or `"heavy"`.

## Setup (`server_files/`)

```bash
# 1. Download models to /workspace/models/
python server_files/download_models.py

# 2. Start both vLLM servers + cloudflared tunnels
bash server_files/serve.sh
```

When both servers are ready, `serve.sh` prints:
```
VLLM_URL=https://<heavy-tunnel>.trycloudflare.com
# VLLM_LIGHT_URL=https://<light-tunnel>.trycloudflare.com
```

Paste these into `Findable-repo/.env` and restart the agents-api container.

## Fallback behaviour

If either URL is blank or the server is unreachable (detected at startup probe), the [Model Router](/components/model-router.md) falls through to Fireworks API → Ollama automatically. The system still produces scores at reduced quality.

## Keeping the server alive

```bash
tmux new -s findable
bash server_files/serve.sh
# Ctrl+B then D to detach
```

## Load testing

```bash
python server_files/load_test.py \
  --heavy-url https://<heavy-tunnel>.trycloudflare.com \
  --light-url https://<light-tunnel>.trycloudflare.com
```

# Citations
[1] [vLLM continuous batching](https://blog.vllm.ai/2023/06/20/vllm.html)
[2] [cloudflared quick tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/)
