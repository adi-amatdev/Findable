---
type: Service
title: Model Router
status: scaffold
description: Selects which model and endpoint to use for each LLM role, with ordered failover and response caching, behind a single OpenAI-compatible interface.
tags: [inference, routing, failover]
timestamp: 2026-07-08T00:00:00Z
---

# Model Router

Every caller in the system (four agents, orchestrator page-ranker, aggregator writer) sends requests through the router. It presents one OpenAI-compatible interface; the model is a config string so failover is a one-line switch.

## Role assignments

| Role | Primary | Alt 1 | Alt 2 | Backup |
|---|---|---|---|---|
| Orchestrator (routing) | Gemma 4 E4B · local | Qwen3 4B · local | Llama 3.2 3B · local | Gemma 4 26B-A4B · Fireworks |
| Crawlability agent | Gemma 4 E4B · local | Qwen3 4B · local | Phi-4-mini · local | Gemma 4 E4B · Fireworks |
| Content Signal (E-E-A-T) | Gemma 4 31B · Fireworks | Qwen3 32B | gpt-oss-120b | Gemma 4 26B-A4B · local |
| Structured Data | Gemma 4 26B-A4B | Qwen3 14B · local | gpt-oss-20b · local | Gemma 4 E4B · local |
| Entity & Topic | Qwen3 14B · local | Gemma 4 26B-A4B | Llama 3.1 8B · local | Gemma 4 · Fireworks |
| Report Aggregator (writer) | Gemma 4 31B · Fireworks | Qwen3 32B | DeepSeek V3 | Gemma 4 E4B · local |

## Backends

- **Local** → [vLLM on ROCm](/components/vllm-server.md) serving Gemma 4 E4B + 26B-A4B behind one OpenAI-compatible HTTP endpoint.
- **Remote** → [Fireworks API](/external/fireworks-api.md) for the two hardest roles (E-E-A-T judgment, report writing).

## Failover policy

Primary → Alt 1 → Alt 2 → Backup, triggered on timeout or error. Response caching at the router level avoids repeat calls for identical prompts (important for cache-keyed demo runs).

## Implementation status

Scaffolded in `app/llm/`. The full role→model failover table above is already
encoded as data in `roles.py` (`Role` enum + `ROLE_ROUTES`); `router.py` defines
the `ModelRouter.complete()` interface but raises `NotImplementedError` until a
vLLM/Fireworks backend is wired and `LLM_ENABLED=true`.
