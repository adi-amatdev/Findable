---
type: Data Contract
title: AgentStatusEvent
status: implemented
description: The SSE payload emitted by each agent during execution — one event per phase change, streamed to the frontend via GET /agent/stream/{agent_id}.
tags: [sse, streaming, schema, agents]
timestamp: 2026-07-08T00:00:00Z
---

# AgentStatusEvent

Pydantic model defined in `agents/app/schemas.py`. One instance is emitted to the agent's asyncio.Queue at each significant phase of execution.

## Schema

```python
class AgentStatusEvent(BaseModel):
    agent_id: str           # UUID assigned at audit start
    agent:    str           # "crawlability" | "content_signal" | "structured_data" | "entity_topic"
    phase:    str           # see phase table in /components/streaming.md
    detail:   str | None    # model role, pass note, gate name, error message
    score:    int | None    # only populated on "complete" phase
    ts:       float         # Unix timestamp (time.time())
```

## Example events

**Agent starting:**
```json
{"agent_id":"3f2a…","agent":"content_signal","phase":"started","detail":null,"score":null,"ts":1720000001.3}
```

**LLM call in progress:**
```json
{"agent_id":"3f2a…","agent":"content_signal","phase":"llm_call","detail":"content_signal","score":null,"ts":1720000003.1}
```

**Crawlability sub-agent pass:**
```json
{"agent_id":"8b1c…","agent":"crawlability","phase":"sub_agent_pass_2","detail":"deep crawl 4 pages","score":null,"ts":1720000005.6}
```

**Agent complete:**
```json
{"agent_id":"3f2a…","agent":"content_signal","phase":"complete","detail":null,"score":82,"ts":1720000009.4}
```

**Hard gate triggered:**
```json
{"agent_id":"8b1c…","agent":"crawlability","phase":"applying_hard_gates","detail":"all AI bots blocked → score capped at 10","score":null,"ts":1720000008.0}
```

## SSE wire format

```
event: agent_status
data: <AgentStatusEvent as JSON>

```

The `event:` line enables the browser's `EventSource` to filter by type:
```js
source.addEventListener("agent_status", (e) => {
    const event = JSON.parse(e.data);
    updateAgentPanel(event.agent, event.phase, event.score);
});
```

## Related

- [Agent SSE Streaming](/components/streaming.md) — full infrastructure description
- [FastAPI Application Layer](/components/api.md) — endpoint definitions
- [AuditReport](/data/audit-report.md) — the final output after all agents complete
