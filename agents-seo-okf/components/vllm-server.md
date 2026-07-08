---
type: Infrastructure
title: vLLM on ROCm
description: Local model serving container running Gemma 4 E4B and 26B-A4B on AMD GPU via ROCm, with continuous batching for concurrent agent requests.
tags: [inference, amd, rocm, vllm, gemma]
timestamp: 2026-07-08T00:00:00Z
---

# vLLM on ROCm

The local inference layer. Uses AMD's prebuilt `rocm/vllm` Docker image so ROCm setup is not hand-rolled — `docker compose up` is the single launch command.

## Models served

Two models behind one vLLM instance, one OpenAI-compatible endpoint:

- **Gemma 4 E4B** — lightweight roles (orchestrator page-ranking, crawlability agent).
- **Gemma 4 26B-A4B** — mid-weight roles (structured data agent, E-E-A-T fallback).

## Why one vLLM server, not N model copies

This is the [Parallel Inference on AMD](/decisions/parallel-inference-amd.md) design principle. The [Orchestrator](/components/orchestrator.md)'s nested fan-out fires ~20 concurrent LLM requests; vLLM's continuous batching groups them into a single forward pass on the GPU. This is both more efficient and more defensible than spawning separate model copies.

## Deployment

Runs as a dedicated container in the `docker compose` stack alongside the app container. The [Model Router](/components/model-router.md) addresses it by Docker service hostname.

# Citations
[1] [vLLM continuous batching](https://blog.vllm.ai/2023/06/20/vllm.html)
[2] [AMD ROCm vLLM image](https://hub.docker.com/r/rocm/vllm)
