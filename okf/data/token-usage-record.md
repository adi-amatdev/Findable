---
type: Data Contract
title: Token Usage Record
status: implemented
description: One JSON line per LLM call, appended to agents/logs/token_usage.jsonl by the Model Router — the persistent record behind per-agent, per-model token averages.
tags: [data, contract, tokens, logging]
timestamp: 2026-07-11T00:00:00Z
---

# Token Usage Record

Written by `log_token_usage()` in [Token Usage Logging](/components/token-logging.md), one line per successful LLM call.

## Schema

```typescript
interface TokenUsageRecord {
  ts: number;                 // unix epoch seconds
  role: string;               // ModelRouter role, e.g. "content_signal", "report_writer"
  agent: string;               // agent display name (defaults to role if not supplied)
  model: string;               // served-model-name actually used, e.g. "heavy", "light"
  backend: string;             // base URL of the backend that served the call
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  audit_id: string | null;    // groups calls from the same audit; "benchmark" for token_benchmark.py runs
}
```

## Example line

```json
{"ts": 1783700000.1, "role": "content_signal", "agent": "content_signal", "model": "heavy", "backend": "https://heavy-tunnel.example.com", "prompt_tokens": 812, "completion_tokens": 194, "total_tokens": 1006, "latency_ms": 512.3, "audit_id": "b3f1..."}
```

## Consumers

- `agents/scripts/token_report.py` groups records by `agent` and by `model` and prints average/min/max `total_tokens`.
- `agents/scripts/token_benchmark.py` writes to this same file (tagged `audit_id="benchmark"`) so ad-hoc benchmark runs and real production traffic live in one queryable log.

## Roles observed

Matches the [Model Router](/components/model-router.md) role → tier table: `crawlability_judgment`, `content_signal`, `report_writer` (heavy); `structured_data`, `entity_topic` (light). `crawlability_subagent` and `orchestrator` never appear here — the crawlability sub-agent's 3-pass crawl is deterministic (no LLM call), and the `orchestrator` role is reserved but unused.
