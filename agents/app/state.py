"""
In-process state registry for agent streaming.

Holds two module-level dicts:
  _queues  — asyncio.Queue per agent_id (AgentStatusEvent | None sentinel)
  _results — AuditReport or exception per audit_id
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas import AgentStatusEvent, AuditReport

_queues: dict[str, asyncio.Queue] = {}
_results: dict[str, Any] = {}


def register_agent(agent_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[agent_id] = q
    return q


async def emit(agent_id: str, event: "AgentStatusEvent") -> None:
    q = _queues.get(agent_id)
    if q is not None:
        await q.put(event)


async def close_agent(agent_id: str) -> None:
    q = _queues.get(agent_id)
    if q is not None:
        await q.put(None)


def get_queue(agent_id: str) -> asyncio.Queue | None:
    return _queues.get(agent_id)


def store_result(audit_id: str, result: Any) -> None:
    _results[audit_id] = result


def get_result(audit_id: str) -> Any:
    return _results.get(audit_id)
