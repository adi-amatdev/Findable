"""Unit tests for agents/app/state.py — the in-process queue registry."""
from __future__ import annotations

import pytest

import app.state as state
from app.schemas import AgentStatusEvent


# ---------------------------------------------------------------------------
# Queue registry
# ---------------------------------------------------------------------------

async def test_register_creates_queue():
    q = state.register_agent("agent-1")
    assert q is not None
    assert state.get_queue("agent-1") is q


def test_get_queue_unknown_returns_none():
    assert state.get_queue("no-such-agent") is None


async def test_emit_puts_event():
    state.register_agent("agent-2")
    event = AgentStatusEvent(agent_id="agent-2", agent="content_signal", phase="started")
    await state.emit("agent-2", event)

    q = state.get_queue("agent-2")
    assert not q.empty()
    item = q.get_nowait()
    assert item.phase == "started"
    assert item.agent == "content_signal"


async def test_emit_noop_for_unknown_id():
    # Should not raise; just silently ignores an unknown agent_id
    event = AgentStatusEvent(agent_id="ghost", agent="crawlability", phase="started")
    await state.emit("ghost", event)   # no queue registered — must not raise


async def test_close_agent_puts_sentinel():
    state.register_agent("agent-3")
    await state.close_agent("agent-3")

    q = state.get_queue("agent-3")
    item = q.get_nowait()
    assert item is None   # sentinel value


async def test_close_noop_for_unknown_id():
    await state.close_agent("no-such")   # must not raise


async def test_emit_multiple_events_in_order():
    state.register_agent("agent-4")
    phases = ["started", "building_prompt", "llm_call", "complete"]
    for phase in phases:
        await state.emit("agent-4", AgentStatusEvent(
            agent_id="agent-4", agent="structured_data", phase=phase,
        ))
    await state.close_agent("agent-4")

    q = state.get_queue("agent-4")
    received = []
    while True:
        item = q.get_nowait()
        if item is None:
            break
        received.append(item.phase)

    assert received == phases


# ---------------------------------------------------------------------------
# Result registry
# ---------------------------------------------------------------------------

def test_get_result_returns_none_for_unknown():
    assert state.get_result("no-such-audit") is None


def test_store_and_get_result():
    state.store_result("audit-1", {"score": 82})
    assert state.get_result("audit-1") == {"score": 82}


def test_store_overwrites_previous():
    state.store_result("audit-2", "first")
    state.store_result("audit-2", "second")
    assert state.get_result("audit-2") == "second"
