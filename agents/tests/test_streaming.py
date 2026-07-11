"""
Integration tests for the streaming endpoints:
  POST /audit/start
  GET  /agent/stream/{agent_id}
  GET  /audit/{audit_id}/result

Uses httpx.AsyncClient with ASGITransport — no live server needed.
Agents are mocked so no LLM or network calls are made.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport

import app.state as state
from app.main import app
from app.schemas import AgentStatusEvent
from .conftest import CANNED_SITEFACTS_DICT


def _client() -> httpx.AsyncClient:
    """Return an async httpx client wired directly to the FastAPI app."""
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── helpers ──────────────────────────────────────────────────────────────────

async def _post_start(client: httpx.AsyncClient, sf_dict: dict) -> dict:
    payload = {
        "sitefacts": sf_dict,
        "audit_id": "test-audit-1",
        "agent_ids": {
            "crawlability": "c-1",
            "content_signal": "cs-1",
            "structured_data": "sd-1",
            "entity_topic": "et-1",
        },
    }
    resp = await client.post("/audit/start", json=payload)
    resp.raise_for_status()
    return resp.json()


# ── POST /audit/start ─────────────────────────────────────────────────────────

async def test_audit_start_returns_ids_immediately(canned_sf_dict):
    with patch("app.main._run_agents_tracked", new_callable=AsyncMock):
        async with _client() as client:
            body = await _post_start(client, canned_sf_dict)

    assert body["audit_id"] == "test-audit-1"
    assert set(body["agent_ids"].keys()) == {
        "crawlability", "content_signal", "structured_data", "entity_topic"
    }
    for agent_id in body["agent_ids"].values():
        assert isinstance(agent_id, str)


async def test_audit_start_registers_queues(canned_sf_dict):
    with patch("app.main._run_agents_tracked", new_callable=AsyncMock) as mock:
        async with _client() as client:
            body = await _post_start(client, canned_sf_dict)
    # Queues must exist before the background task starts so an immediately
    # opened browser stream cannot race into a 404.
    mock.assert_called_once()
    for agent_id in body["agent_ids"].values():
        assert state.get_queue(agent_id) is not None


async def test_audit_start_rejects_invalid_body():
    async with _client() as client:
        resp = await client.post("/audit/start", json={"not": "a valid request"})
    assert resp.status_code == 422


# ── GET /agent/stream/{agent_id} ──────────────────────────────────────────────

async def test_agent_stream_404_for_unknown_id():
    async with _client() as client:
        resp = await client.get("/agent/stream/does-not-exist")
    assert resp.status_code == 404


async def test_agent_stream_returns_sse_content_type():
    agent_id = "stream-test-1"
    state.register_agent(agent_id)
    await state.close_agent(agent_id)  # sentinel → stream terminates immediately

    async with _client() as client:
        async with client.stream("GET", f"/agent/stream/{agent_id}") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


async def test_agent_stream_yields_single_event():
    agent_id = "stream-test-2"
    state.register_agent(agent_id)
    await state.emit(agent_id, AgentStatusEvent(
        agent_id=agent_id, agent="content_signal", phase="started",
    ))
    await state.close_agent(agent_id)

    lines: list[str] = []
    async with _client() as client:
        async with client.stream("GET", f"/agent/stream/{agent_id}") as resp:
            async for line in resp.aiter_lines():
                if line:
                    lines.append(line)

    event_lines = [l for l in lines if l.startswith("event:")]
    data_lines  = [l for l in lines if l.startswith("data:")]
    assert len(event_lines) == 1
    assert event_lines[0].strip() == "event: agent_status"
    assert len(data_lines) == 1
    event_data = json.loads(data_lines[0][5:])
    assert event_data["phase"] == "started"
    assert event_data["agent"] == "content_signal"
    assert event_data["agent_id"] == agent_id


async def test_agent_stream_yields_multiple_events():
    agent_id = "stream-test-3"
    state.register_agent(agent_id)
    phases = ["started", "building_prompt", "llm_call", "parsing_result", "complete"]
    for phase in phases:
        await state.emit(agent_id, AgentStatusEvent(
            agent_id=agent_id, agent="structured_data", phase=phase,
        ))
    await state.close_agent(agent_id)

    data_lines: list[str] = []
    async with _client() as client:
        async with client.stream("GET", f"/agent/stream/{agent_id}") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    data_lines.append(line)

    assert len(data_lines) == len(phases)
    received_phases = [json.loads(l[5:])["phase"] for l in data_lines]
    assert received_phases == phases


async def test_agent_stream_complete_event_carries_score():
    agent_id = "stream-test-4"
    state.register_agent(agent_id)
    await state.emit(agent_id, AgentStatusEvent(
        agent_id=agent_id, agent="entity_topic", phase="complete", score=91,
    ))
    await state.close_agent(agent_id)

    data_lines: list[str] = []
    async with _client() as client:
        async with client.stream("GET", f"/agent/stream/{agent_id}") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    data_lines.append(line)

    assert len(data_lines) == 1
    parsed = json.loads(data_lines[0][5:])
    assert parsed["score"] == 91
    assert parsed["phase"] == "complete"


# ── GET /audit/{audit_id}/result ──────────────────────────────────────────────

async def test_audit_result_202_when_not_started():
    async with _client() as client:
        resp = await client.get("/audit/never-started/result")
    assert resp.status_code == 202
    assert resp.json()["status"] == "running"


async def test_audit_result_returns_stored_report():
    state.store_result("audit-done", {"url": "https://example.com", "summary": "great"})
    async with _client() as client:
        resp = await client.get("/audit/audit-done/result")
    assert resp.status_code == 200
    assert resp.json()["url"] == "https://example.com"


async def test_audit_result_500_on_stored_exception():
    state.store_result("audit-failed", RuntimeError("agents crashed"))
    async with _client() as client:
        resp = await client.get("/audit/audit-failed/result")
    assert resp.status_code == 500
    assert "agents crashed" in resp.json()["detail"]
