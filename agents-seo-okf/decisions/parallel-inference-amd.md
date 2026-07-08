---
type: Decision
title: Parallel Inference on AMD
description: One vLLM server handles concurrent agent requests via continuous batching — not N model copies — which is how real GPU parallelism works and what makes the AMD/Gemma story defensible.
tags: [decision, architecture, principle, amd, vllm]
timestamp: 2026-07-08T00:00:00Z
---

# Parallel Inference on AMD

**Design Principle 2** — the second of two principles that shape the entire architecture.

## The rule

One [vLLM server on ROCm](/components/vllm-server.md) serves the local model. The four agents fire **concurrent async requests** that vLLM batches and runs together on the GPU via continuous batching.

## Why this, not N model copies

This is real parallelism. Spinning up three separate copies of the same model would:
- Waste VRAM (each copy holds its own weights).
- Under-utilize the GPU (each forward pass is smaller).
- Be harder to defend to judges who know how GPU inference works.

Continuous batching is what vLLM+ROCm is optimized for, and the nested fan-out in the [Orchestrator](/components/orchestrator.md) generates ~20 concurrent judgment calls that arrive at the server simultaneously — exactly the workload continuous batching handles well.

## Why it keeps the Gemma-prize story true

The Gemma 4 models serve *all* local roles. The AMD ROCm + vLLM + Gemma stack is the core reasoning engine. Fireworks (remote) handles only the two hardest roles as a fallback/quality boost — it doesn't dilute the AMD story.

## Implementation

The [Orchestrator](/components/orchestrator.md)'s nested `asyncio.gather` is what generates the concurrent burst. The [Model Router](/components/model-router.md) routes local calls to the single vLLM endpoint.
