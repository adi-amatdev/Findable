"""
In-process state registry for agent streaming.

Holds two module-level dicts:
  _queues  — asyncio.Queue per agent_id (AgentStatusEvent | None sentinel)
  _results — AuditReport or exception per audit_id
"""
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas import AgentStatusEvent, AuditReport

_queues: dict[str, asyncio.Queue] = {}
_results: dict[str, Any] = {}
_queue_created_at: dict[str, float] = {}
_result_created_at: dict[str, float] = {}
_PENDING = object()
STATE_TTL_SECONDS = 60 * 60


def register_agent(agent_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[agent_id] = q
    _queue_created_at[agent_id] = time.monotonic()
    return q


def register_audit(audit_id: str) -> None:
    """Record an audit before its background task begins."""
    _results[audit_id] = _PENDING
    _result_created_at[audit_id] = time.monotonic()


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
    _result_created_at[audit_id] = time.monotonic()


def get_result(audit_id: str) -> Any:
    result = _results.get(audit_id)
    return None if result is _PENDING else result


def has_audit(audit_id: str) -> bool:
    return audit_id in _results


def prune_expired_state(ttl_seconds: float = STATE_TTL_SECONDS) -> None:
    """Bound memory used by completed/disconnected audit state."""
    cutoff = time.monotonic() - ttl_seconds
    for agent_id, created_at in list(_queue_created_at.items()):
        if created_at < cutoff:
            _queues.pop(agent_id, None)
            _queue_created_at.pop(agent_id, None)
    for audit_id, created_at in list(_result_created_at.items()):
        if created_at < cutoff:
            _results.pop(audit_id, None)
            _result_created_at.pop(audit_id, None)
