---
type: Infrastructure
title: vLLM GPU Server (Jupyter-hosted)
status: partial
description: Remote vLLM instance running on a GPU Jupyter server, exposed to local Docker via a cloudflared or ngrok tunnel; not part of the local docker-compose stack.
tags: [inference, vllm, gpu, cloudflared, jupyter, tunnel]
timestamp: 2026-07-08T00:00:00Z
---

# vLLM GPU Server (Jupyter-hosted)

The heavy-model inference backend. Runs on a remote Jupyter notebook server with GPU access, not on the developer's local machine. The [Model Router](/components/model-router.md) reaches it via a public HTTPS tunnel.

## Setup (from `agents/jupyter_vllm_setup.py`)

Run these steps in a Jupyter notebook on the GPU server:

```python
# 1. Start vLLM serving the heavy model
subprocess.Popen(["python", "-m", "vllm.entrypoints.openai.api_server",
                  "--model", "google/gemma-4-27b-it", "--port", "8000"])

# 2. Expose via cloudflared (no account required)
proc = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:8000"],
                        stderr=subprocess.PIPE)
# Parse tunnel URL from stderr — e.g. https://random-id.trycloudflare.com
```

The tunnel URL becomes `VLLM_URL` in the local `.env`.

## Models served

- **`LOCAL_HEAVY_MODEL`** (default: `google/gemma-4-27b-it`) — content signal, crawlability judgment, report writer.
- **`LOCAL_MID_MODEL`** (default: `Qwen/Qwen3-14B`) — structured data, entity topic.

## Fallback behaviour

If `VLLM_URL` is blank (tunnel not running), all heavy roles fall back to local Ollama automatically. The system still produces scores — at reduced quality since the light model handles all roles.

## Why not in docker-compose

The GPU server is a shared Jupyter machine, not a container the project controls. The tunnel pattern is what makes a non-containerised GPU accessible from inside a Docker network.

## Future: local AMD ROCm

The original architecture called for `rocm/vllm` as a local Docker container (see [Parallel Inference decision](/decisions/parallel-inference-amd.md)). That path remains valid for AMD GPU workstations and is still the production target; the Jupyter/tunnel approach is the interim development setup.

# Citations
[1] [vLLM continuous batching](https://blog.vllm.ai/2023/06/20/vllm.html)
[2] [cloudflared quick tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/)
