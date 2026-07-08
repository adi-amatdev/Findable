---
type: Service
title: Agent SSE Streaming
status: implemented
description: Server-Sent Events infrastructure that lets clients watch each agent's thinking in real time — from phase start to LLM call to completion — without polling a blocking endpoint.
tags: [sse, streaming, agents, real-time, frontend]
timestamp: 2026-07-08T00:00:00Z
---

# Agent SSE Streaming

Each of the 4 agents ([Crawlability](/agents/crawlability.md), [Content Signal](/agents/content-signal.md), [Structured Data](/agents/structured-data.md), [Entity Topic](/agents/entity-topic.md)) emits status events to an in-process queue as it executes. A dedicated SSE endpoint drains that queue and pushes events to connected clients.

## Why SSE (not WebSocket)

- **Unidirectional** — agents push status; the browser never sends mid-stream messages.
- **HTTP/1.1** — no protocol upgrade; works through the standard httpx proxy chain between backend and agents-api.
- **Browser-native** — `EventSource` API needs no library.
- **Simple proxy** — `httpx.AsyncClient.stream()` forwards bytes transparently.

## Infrastructure (`agents/app/state.py`)

Module-level dicts — one per FastAPI worker process, process-lifetime:

```python
_queues:  dict[str, asyncio.Queue[AgentStatusEvent | None]]
_results: dict[str, AuditReport | BaseException]
```

| Function | Description |
|---|---|
| `register_agent(agent_id)` | Creates a new asyncio.Queue for the agent; returns it. |
| `emit(agent_id, event)` | Puts an [AgentStatusEvent](/data/agent-status-event.md) into the queue. No-op if agent_id unknown. |
| `close_agent(agent_id)` | Puts `None` sentinel — SSE stream terminates. |
| `get_queue(agent_id)` | Returns the queue or `None` if unregistered. |
| `store_result(audit_id, result)` | Stores completed AuditReport or exception. |
| `get_result(audit_id)` | Returns stored result or `None` if still running. |

## Event phases

All 4 agents share a common phase vocabulary. Crawlability has additional sub-agent phases.

| Phase | Who emits | Detail field |
|---|---|---|
| `started` | all agents | — |
| `building_prompt` | BaseAgent subclasses | — |
| `llm_call` | all agents | role name |
| `retry` | BaseAgent | attempt number |
| `parsing_result` | all agents | — |
| `sub_agent_pass_1` | crawlability | "seed crawl" |
| `sub_agent_pass_2` | crawlability | "deep crawl N pages" |
| `sub_agent_pass_3` | crawlability | "cross-page synthesis" |
| `judgment_call` | crawlability | role name |
| `applying_hard_gates` | crawlability | gate description |
| `complete` | all agents | — (`score` field populated) |
| `error` | all agents | exception message |

## Wire format

Standard SSE; each event is two lines + blank:

```
event: agent_status
data: {"agent_id":"<uuid>","agent":"content_signal","phase":"llm_call","detail":"content_signal","ts":1720000000.1}

```

## Agent ID assignment

`POST /api/audit/start` on the backend generates 4 UUIDs before contacting agents-api:

```python
agent_ids = {name: str(uuid.uuid4()) for name in
    ["crawlability", "content_signal", "structured_data", "entity_topic"]}
```

These are passed to agents-api in the `AuditStartRequest` body, which registers them in `state.py` before spawning the `asyncio.gather` task. The frontend receives all 4 IDs in the `POST /api/audit/start` response and can subscribe to all 4 streams in parallel.

## SSE proxy (backend → agents-api)

`GET /agent/stream/{agent_id}` on the backend is a transparent byte-for-byte proxy:

```python
async with client.stream("GET", f"{agents_url}/agent/stream/{agent_id}") as resp:
    async for chunk in resp.aiter_bytes():
        yield chunk
```

`timeout=None` ensures the connection stays alive for the duration of the agent run.

## Tests

The `agents/tests/` suite covers:
- `test_state.py` — unit tests for all state module functions
- `test_streaming.py` — endpoint tests (SSE content-type, event ordering, 404 on unknown id, 202 while running)
- `test_agents_emit.py` — verifies each agent emits the correct phases in order (mocked LLM + sub-agent)

## Tools

| Script | Purpose |
|---|---|
| `agents/dry_run_streaming.py` | End-to-end streaming dry run. Hits live services, shows SSE events in terminal as they arrive, then prints the final AuditReport. |
| `agents/frontend_mock.py` | Full frontend simulation. Renders a colour-coded terminal UI of agent panels + final report card — the exact flow a React frontend would follow. |
