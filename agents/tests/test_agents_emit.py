"""
Tests that verify each agent emits the correct SSE status events.

LLM calls (router.call_with_fallback) are mocked — no actual model needed.
Sub-agent HTTP crawls are also mocked for the crawlability agent.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

import app.state as state
from app.agents.base import BaseAgent
from app.agents.content_signal import ContentSignalAgent
from app.agents.structured_data import StructuredDataAgent
from app.agents.entity_topic import EntityTopicAgent
from app.agents.crawlability.agent import run_crawlability_agent
from app.schemas import AgentStatusEvent, CrawlReport, SiteFacts, TrafficSignal


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_llm_response(json_body: dict) -> dict:
    return {
        "choices": [
            {"message": {"content": json.dumps(json_body)}, "model": "test-model"}
        ],
        "usage": {"total_tokens": 20},
    }


MOCK_RESPONSE = _make_llm_response({
    "score": 80,
    "sub_scores": {"experience": 80, "expertise": 80, "authority": 80, "trust": 80},
    "commodity_content": False,
    "citation_worthy": True,
    "answer_front_loaded": False,
    "artifacts": {},
    "findings": [],
})


def _drain_phases(agent_id: str) -> list[str]:
    """Synchronously drain a queue and return all emitted phases (not sentinel)."""
    q = state.get_queue(agent_id)
    phases = []
    while not q.empty():
        item = q.get_nowait()
        if item is None:
            break
        phases.append(item.phase)
    return phases


# ── BaseAgent (ContentSignalAgent as proxy) ───────────────────────────────────

async def test_base_agent_emits_started(canned_sf):
    agent_id = "cs-emit-1"
    state.register_agent(agent_id)

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(return_value=MOCK_RESPONSE)
        await ContentSignalAgent().run(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "started" in phases


async def test_base_agent_emits_building_prompt(canned_sf):
    agent_id = "cs-emit-2"
    state.register_agent(agent_id)

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(return_value=MOCK_RESPONSE)
        await ContentSignalAgent().run(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "building_prompt" in phases


async def test_base_agent_emits_llm_call(canned_sf):
    agent_id = "cs-emit-3"
    state.register_agent(agent_id)

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(return_value=MOCK_RESPONSE)
        await ContentSignalAgent().run(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "llm_call" in phases


async def test_base_agent_emits_complete_with_score(canned_sf):
    agent_id = "cs-emit-4"
    state.register_agent(agent_id)

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(return_value=MOCK_RESPONSE)
        result = await ContentSignalAgent().run(canned_sf, agent_id=agent_id)

    q = state.get_queue(agent_id)
    events: list[AgentStatusEvent] = []
    while not q.empty():
        item = q.get_nowait()
        if item is not None:
            events.append(item)

    complete_events = [e for e in events if e.phase == "complete"]
    assert len(complete_events) == 1
    assert complete_events[0].score == result.score


async def test_base_agent_emits_error_on_llm_failure(canned_sf):
    agent_id = "cs-emit-5"
    state.register_agent(agent_id)

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        with pytest.raises(RuntimeError):
            await ContentSignalAgent().run(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "error" in phases


async def test_base_agent_emits_retry_on_second_attempt(canned_sf):
    agent_id = "cs-emit-6"
    state.register_agent(agent_id)

    call_count = 0
    async def _fail_first(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient error")
        return MOCK_RESPONSE

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = _fail_first
        await ContentSignalAgent().run(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "retry" in phases
    assert "complete" in phases


async def test_base_agent_no_emit_without_agent_id(canned_sf):
    """When agent_id is None, state is never touched."""
    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(return_value=MOCK_RESPONSE)
        await ContentSignalAgent().run(canned_sf)  # no agent_id

    assert len(state._queues) == 0   # nothing was registered


async def test_structured_data_emits_all_phases(canned_sf):
    agent_id = "sd-emit-1"
    state.register_agent(agent_id)

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(return_value=MOCK_RESPONSE)
        await StructuredDataAgent().run(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    for expected in ("started", "building_prompt", "llm_call", "parsing_result", "complete"):
        assert expected in phases, f"Missing phase: {expected}"


async def test_entity_topic_emits_complete(canned_sf):
    agent_id = "et-emit-1"
    state.register_agent(agent_id)

    with patch("app.agents.base.router") as mock_router:
        mock_router.call_with_fallback = AsyncMock(return_value=MOCK_RESPONSE)
        result = await EntityTopicAgent().run(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "complete" in phases


# ── Crawlability agent ────────────────────────────────────────────────────────

MOCK_CRAWL_REPORTS = [
    CrawlReport(depth=1, url="https://example.com", reachable=True,
                js_dependent=False, summary="Seed OK"),
    CrawlReport(depth=2, url="https://example.com", reachable=True,
                js_dependent=False, summary="Deep crawl OK"),
    CrawlReport(depth=3, url="https://example.com", reachable=True,
                js_dependent=False, summary="Synthesis OK"),
]

CRAWLABILITY_LLM_RESPONSE = _make_llm_response({
    "score": 85,
    "findings": [],
})


async def test_crawlability_emits_started(canned_sf):
    agent_id = "cr-emit-1"
    state.register_agent(agent_id)

    with (
        patch("app.agents.crawlability.agent.run_sub_agent", AsyncMock(return_value=MOCK_CRAWL_REPORTS)),
        patch("app.agents.crawlability.agent._get_tranco_traffic", AsyncMock(return_value=TrafficSignal(source="tranco"))),
        patch("app.agents.crawlability.agent.router") as mock_router,
    ):
        mock_router.call_with_fallback = AsyncMock(return_value=CRAWLABILITY_LLM_RESPONSE)
        await run_crawlability_agent(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "started" in phases


async def test_crawlability_emits_sub_agent_pass1(canned_sf):
    agent_id = "cr-emit-2"
    state.register_agent(agent_id)

    with (
        patch("app.agents.crawlability.agent.run_sub_agent", AsyncMock(return_value=MOCK_CRAWL_REPORTS)),
        patch("app.agents.crawlability.agent._get_tranco_traffic", AsyncMock(return_value=TrafficSignal(source="tranco"))),
        patch("app.agents.crawlability.agent.router") as mock_router,
    ):
        mock_router.call_with_fallback = AsyncMock(return_value=CRAWLABILITY_LLM_RESPONSE)
        await run_crawlability_agent(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "sub_agent_pass_1" in phases


async def test_crawlability_emits_judgment_call(canned_sf):
    agent_id = "cr-emit-3"
    state.register_agent(agent_id)

    with (
        patch("app.agents.crawlability.agent.run_sub_agent", AsyncMock(return_value=MOCK_CRAWL_REPORTS)),
        patch("app.agents.crawlability.agent._get_tranco_traffic", AsyncMock(return_value=TrafficSignal(source="tranco"))),
        patch("app.agents.crawlability.agent.router") as mock_router,
    ):
        mock_router.call_with_fallback = AsyncMock(return_value=CRAWLABILITY_LLM_RESPONSE)
        await run_crawlability_agent(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "judgment_call" in phases


async def test_crawlability_emits_hard_gate_when_all_bots_blocked(canned_sf_dict):
    """When robots.txt blocks all AI bots, the hard-gate event fires."""
    blocked_dict = {
        **canned_sf_dict,
        "robots": {
            "exists": True,
            "allows": {
                "GPTBot": False,
                "ClaudeBot": False,
                "PerplexityBot": False,
                "OAI-SearchBot": False,
                "Google-Extended": False,
                "CCBot": False,
            },
            "sitemap_refs": [],
        },
    }
    sf_blocked = SiteFacts.model_validate(blocked_dict)

    agent_id = "cr-emit-4"
    state.register_agent(agent_id)

    with (
        patch("app.agents.crawlability.agent.run_sub_agent", AsyncMock(return_value=MOCK_CRAWL_REPORTS)),
        patch("app.agents.crawlability.agent._get_tranco_traffic", AsyncMock(return_value=TrafficSignal(source="tranco"))),
        patch("app.agents.crawlability.agent.router") as mock_router,
    ):
        mock_router.call_with_fallback = AsyncMock(return_value=CRAWLABILITY_LLM_RESPONSE)
        result = await run_crawlability_agent(sf_blocked, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "applying_hard_gates" in phases
    assert result.score <= 10   # hard gate cap


async def test_crawlability_emits_complete(canned_sf):
    agent_id = "cr-emit-5"
    state.register_agent(agent_id)

    with (
        patch("app.agents.crawlability.agent.run_sub_agent", AsyncMock(return_value=MOCK_CRAWL_REPORTS)),
        patch("app.agents.crawlability.agent._get_tranco_traffic", AsyncMock(return_value=TrafficSignal(source="tranco"))),
        patch("app.agents.crawlability.agent.router") as mock_router,
    ):
        mock_router.call_with_fallback = AsyncMock(return_value=CRAWLABILITY_LLM_RESPONSE)
        await run_crawlability_agent(canned_sf, agent_id=agent_id)

    phases = _drain_phases(agent_id)
    assert "complete" in phases
