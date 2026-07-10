---
type: Service
title: Token Usage Logging
status: implemented
description: Every LLM call routed through the Model Router logs its prompt/completion/total token usage to a JSONL file, tagged by agent, model, and audit_id; a benchmark script and a report script read/write that same log.
tags: [tokens, logging, observability, model-router, benchmark]
timestamp: 2026-07-11T00:00:00Z
---

# Token Usage Logging

Closes a gap where LLM token consumption was read out of responses in a
few places but never persisted anywhere — there was no logs directory or
structured logging in the repo before this. Implemented in
`agents/app/token_logger.py`.

## Capture point

Instrumented at the single choke point every LLM call passes through:
[Model Router](/components/model-router.md)'s `call_with_fallback()` in
`agents/app/models/router.py`. This means `report_writer` (the
[Aggregator](/components/aggregator.md)'s executive-summary call) is now
captured too — previously its `usage` was read and discarded.

`call_with_fallback(role, *, agent=None, audit_id=None, **kwargs)` accepts
two new keyword params (popped before forwarding `**kwargs` to
`AsyncLLMClient.chat_completion`, so they never leak into the request
payload). On every successful response it extracts
`usage.prompt_tokens` / `usage.completion_tokens` / `usage.total_tokens`
and calls `log_token_usage(...)`.

Callers thread `agent` (the agent's display name) and `audit_id` through:
[BaseAgent](/agents/index.md).run(), `run_crawlability_agent()`, and
`aggregator._write_summary()`. `agents/app/main.py` generates a UUID
`audit_id` for the synchronous `/audit` and `/audit/batch` paths (which
had no audit_id concept before); the SSE-tracked `/audit/start` path
reuses the caller-supplied `audit_id`.

## Log format

See [Token Usage Record](/data/token-usage-record.md) for the JSONL schema.
File location defaults to `agents/logs/token_usage.jsonl`, overridable via
`TOKEN_LOG_PATH` env var. Writes are guarded by a `threading.Lock` so
concurrent `asyncio.gather`'d agents don't interleave partial lines.
`agents/logs/` is gitignored.

## AgentResult schema change

[AgentResult](/data/agent-result.md) gained `prompt_tokens` and
`completion_tokens` fields alongside the pre-existing `tokens` (total)
field — additive and backward-compatible.

## Standalone tooling

- `agents/scripts/token_benchmark.py` — CLI that hits the two vLLM
  endpoints (heavy + light) directly, bypassing Fireworks/Ollama fallback,
  using the *real* prompt-building code (`ContentSignalAgent.build_messages`,
  `StructuredDataAgent.build_messages`, `EntityTopicAgent.build_messages`,
  `_build_judgment_prompt`, `aggregator.build_summary_prompt`) against a
  canned [SiteFacts](/data/site-facts.md) fixture (`agents/tests/conftest.py`).
  Runs each of the 5 roles N times (`--runs`, default 5), prints a table of
  average prompt/completion/total tokens per role and model, and appends
  every run to the same `token_usage.jsonl` (tagged `audit_id=benchmark`).
- `agents/scripts/token_report.py` — reads `token_usage.jsonl` back and
  prints average/min/max tokens grouped by `agent` and by `model`, so
  real production averages accumulate over time (not just one benchmark
  run). Supports `--audit-id` to filter to a single audit or benchmark run.

## Why this design

Logging at the router layer (rather than in each agent) was chosen
specifically because it's the one place every call — including the
previously-untracked `report_writer` summary call — already passes
through, so no call site needed its own logging logic duplicated.
