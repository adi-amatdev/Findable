---
type: Data Contract
title: AgentResult
status: contract
description: The JSON output every agent returns — a score, sub-scores, a list of findings with severity/effort/impact, and optional artifacts.
tags: [data, contract, agent, findings]
timestamp: 2026-07-08T00:00:00Z
---

# AgentResult

Every one of the four [agents](/agents/) returns exactly this shape. The [Aggregator](/components/aggregator.md) consumes a list of four AgentResults to produce the [AuditReport](/data/audit-report.md).

## Schema

```jsonc
{
  "agent": "content_signal",
  "score": 62,
  "sub_scores": { "experience": 40, "expertise": 70, "authority": 65, "trust": 72 },
  "findings": [
    {
      "id": "cs-01",
      "title": "No first-hand experience signals",
      "severity": 4,
      "effort": "M",          // "S" | "M" | "L"
      "impact": 4,
      "detail": "...",
      "fix": "...",
      "evidence": "...",
      "ref_url": "https://developers.google.com/search/docs/..."
    }
  ],
  "artifacts": {},            // agent-specific; entity agent returns { "knowledge_graph": {...} }
  "model_used": "gemma-4-31b@fireworks",
  "latency_ms": 2100,
  "tokens": 1830
}
```

## Findings sort order

The [Aggregator](/components/aggregator.md) sorts all findings across all agents by **impact ÷ effort** so the top items in the fix list are the cheapest big wins. Every finding must include a `ref_url` pointing to an authoritative reference so recommendations are grounded, not invented.

## Effort values

- `S` — small (hours)
- `M` — medium (days)
- `L` — large (weeks/sprint)

## Implementation status

The contract is defined in code as a Pydantic model (`app/models/contracts.py`:
`AgentResult`, `Finding`, `Effort`), ready for the scaffolded [agents](/agents/)
to populate. No agent produces one yet.
