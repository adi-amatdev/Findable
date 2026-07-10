---
type: Data Contract
title: AgentResult
status: implemented
description: The JSON output every agent returns — a score, sub-scores, a list of findings with severity/effort/impact, and optional artifacts (knowledge_graph, traffic_signal, crawl_reports).
tags: [data, contract, agent, findings]
timestamp: 2026-07-11T00:00:00Z
---

# AgentResult

Every one of the four [agents](/agents/) returns exactly this shape. The [Aggregator](/components/aggregator.md) consumes a list of four AgentResults to produce the [AuditReport](/data/audit-report.md).

## Schema (frontend TypeScript type)

```typescript
interface AgentResult {
  agent: string;                              // "crawlability" | "content_signal" | "structured_data" | "entity_topic"
  score: number;                              // 0-100
  sub_scores: Record<string, number>;         // agent-specific sub-dimensions
  findings: Finding[];                        // findings with severity, effort, impact
  artifacts: Record<string, unknown>;          // agent-specific; entity agent returns { "knowledge_graph": {...} }
  traffic_signal: TrafficSignal | null;       // domain rank, cloudflare visits estimate
  crawl_reports: CrawlReport[];               // crawlability agent only
  model_used: string;                         // e.g. "accounts/fireworks/models/gemma-4-26b-a4b-it"
  latency_ms: number;                         // inference latency in ms
  tokens: number;                             // total tokens consumed (prompt + completion)
  prompt_tokens: number;                      // input/prompt tokens for the final judgment call
  completion_tokens: number;                  // output tokens for the final judgment call
}

interface Finding {
  id: string;                                 // e.g. "cs-01", "crawl-02"
  title: string;
  severity: number;                           // 1-5
  effort: string;                             // "S" | "M" | "L"
  impact: number;                             // 1-5
  detail: string;
  fix: string;
  evidence: string;
  ref_url: string;
}

interface TrafficSignal {
  domain_rank: number | null;
  cloudflare_visits_estimate: string | null;
  source: string;
}

interface CrawlReport {
  depth: number;
  url: string;
  reachable: boolean;
  js_dependent: boolean;
  bot_blocked: string | null;
  notable_links: string[];
  summary: string;
}
```

## Findings sort order

The [Aggregator](/components/aggregator.md) sorts all findings across all agents by **impact ÷ effort** so the top items in the fix list are the cheapest big wins. Every finding should include a `ref_url` pointing to an authoritative reference so recommendations are grounded, not invented.

## Effort values

- `S` — small (hours)
- `M` — medium (days)
- `L` — large (weeks/sprint)

## Implementation status

Defined as TypeScript types in `frontend/lib/types.ts`. The backend contract is defined as Pydantic models in `app/models/contracts.py` (`AgentResult`, `Finding`, `Effort`). AgentResults are produced:

- **Mock mode**: the `MOCK_REPORT` in `app/mock.py` includes findings with an `agent` field for attribution
- **Real mode**: each agent (in `agents/app/agents/`) returns its AgentResult through the [Model Router](/components/model-router.md)
- **Fallback**: the frontend's `composeFallbackReport` generates four synthetic AgentResults from SSE scores

Every underlying LLM call (including retries and the aggregator's `report_writer` call, which has no `AgentResult` to attach to) is separately persisted by [Token Usage Logging](/components/token-logging.md) — see [Token Usage Record](/data/token-usage-record.md) for the full per-call log, which is a superset of what ends up in `tokens`/`prompt_tokens`/`completion_tokens` here.

## Agent-specific artifacts

| Agent | Artifacts |
|---|---|
| crawlability | `crawl_reports[]` — per-page crawl results from the 3-pass sub-agent |
| content_signal | `commodity_content (bool)`, `citation_worthy (bool)`, `answer_front_loaded (bool)` |
| entity_topic | `knowledge_graph` — `{ nodes: [{id, label, type}], edges: [{source, target, relation}] }` |
| structured_data | schema validation results |
