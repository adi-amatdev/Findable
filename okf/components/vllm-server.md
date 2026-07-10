---
type: Infrastructure
title: vLLM GPU Server
status: partial
description: Two remote vLLM instances (light + heavy) running on an AMD GPU server, each exposed via a separate cloudflared tunnel and consumed by the Model Router.
tags: [inference, vllm, gpu, cloudflared, rocm, tunnel]
timestamp: 2026-07-11T00:00:00Z
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

## Context length (`max_model_len`)

Heavy roles (`content_signal`, `crawlability_judgment`) request `max_tokens=3000` output. Their prompts are bounded by fixed truncation caps in the agent code (e.g. `page_markdown[:4000]` in `content_signal.py`) to roughly ~1,000–1,100 input tokens for a realistic page, so combined input+output tops out around ~4,100–4,500 tokens in the worst case. A server started with the vLLM default `max_model_len=4096` will 400 on these two roles specifically (`"...requested 3000 output tokens. However, the model's context length is only 4096 tokens..."`) — every other role fits comfortably under 4096. Start the heavy server with `--max-model-len 6000` (or higher) to clear this with headroom; there's no need to go as high as 8192 given the fixed truncation caps upstream.

## Setup (`vllm_hosting/`)

```bash
# 1. Download models to /workspace/models/
python vllm_hosting/download_model.py --dir /workspace/models

# 2. Start both vLLM servers + cloudflared tunnels
bash vllm_hosting/start_service.sh
```

When both servers are ready, `start_service.sh` prints:
```
VLLM_URL=https://<heavy-tunnel>.trycloudflare.com
VLLM_LIGHT_URL=https://<light-tunnel>.trycloudflare.com
```

Paste these into `Findable-repo/.env` and restart the agents-api container.

The `vllm_hosting/` folder also includes:
- `download_cloudflare.txt` for installing/resuming the `cloudflared` binary download.
- `stop_service.sh` for cleaning up vLLM/cloudflared processes.
- `load_test.py` for health, latency, audit-pattern concurrency, and sustained-load checks.

## Fallback behaviour

If either URL is blank or the server is unreachable (detected at startup probe), the [Model Router](/components/model-router.md) falls through to Fireworks API → Ollama automatically. The system still produces scores at reduced quality.

## Keeping the server alive

```bash
tmux new -s findable
bash vllm_hosting/start_service.sh
# Ctrl+B then D to detach
```

## Load testing

```bash
python vllm_hosting/load_test.py \
  --heavy-url https://<heavy-tunnel>.trycloudflare.com \
  --light-url https://<light-tunnel>.trycloudflare.com
```

# Citations
[1] [vLLM continuous batching](https://blog.vllm.ai/2023/06/20/vllm.html)
[2] [cloudflared quick tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/)
