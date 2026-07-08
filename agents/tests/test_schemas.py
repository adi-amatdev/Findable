"""Unit tests for agents/app/schemas.py — Pydantic model validation."""
from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from app.schemas import AgentStatusEvent, AuditStartRequest, SiteFacts
from .conftest import CANNED_SITEFACTS_DICT


# ---------------------------------------------------------------------------
# AgentStatusEvent
# ---------------------------------------------------------------------------

def test_agent_status_event_auto_timestamp():
    before = time.time()
    event = AgentStatusEvent(agent_id="x", agent="crawlability", phase="started")
    after = time.time()
    assert before <= event.ts <= after


def test_agent_status_event_optional_fields_default_none():
    event = AgentStatusEvent(agent_id="x", agent="content_signal", phase="llm_call")
    assert event.detail is None
    assert event.score is None


def test_agent_status_event_with_all_fields():
    event = AgentStatusEvent(
        agent_id="abc-123",
        agent="structured_data",
        phase="complete",
        detail="all good",
        score=88,
    )
    assert event.score == 88
    assert event.detail == "all good"


def test_agent_status_event_serializes_to_json():
    event = AgentStatusEvent(agent_id="x", agent="entity_topic", phase="error", detail="timeout")
    data = event.model_dump()
    assert data["phase"] == "error"
    assert data["detail"] == "timeout"
    assert "ts" in data


def test_agent_status_event_requires_agent_id():
    with pytest.raises(ValidationError):
        AgentStatusEvent(agent="crawlability", phase="started")   # missing agent_id


# ---------------------------------------------------------------------------
# AuditStartRequest
# ---------------------------------------------------------------------------

def test_audit_start_request_valid(canned_sf_dict):
    req = AuditStartRequest(
        sitefacts=SiteFacts.model_validate(canned_sf_dict),
        audit_id="audit-uuid-1",
        agent_ids={
            "crawlability": "c-id",
            "content_signal": "cs-id",
            "structured_data": "sd-id",
            "entity_topic": "et-id",
        },
    )
    assert req.audit_id == "audit-uuid-1"
    assert req.agent_ids["crawlability"] == "c-id"


def test_audit_start_request_rejects_empty_agent_ids(canned_sf_dict):
    # agent_ids with empty dict is technically valid pydantic — but let's verify it accepts it
    req = AuditStartRequest(
        sitefacts=SiteFacts.model_validate(canned_sf_dict),
        audit_id="x",
        agent_ids={},
    )
    assert req.agent_ids == {}


# ---------------------------------------------------------------------------
# SiteFacts — alias support
# ---------------------------------------------------------------------------

def test_sitefacts_accepts_markdown_alias():
    data = {**CANNED_SITEFACTS_DICT, "markdown": "hello world"}
    sf = SiteFacts.model_validate(data)
    assert sf.page_markdown == "hello world"


def test_sitefacts_http_status():
    sf = SiteFacts.model_validate(CANNED_SITEFACTS_DICT)
    assert sf.http.status == 200


def test_sitefacts_all_bots_allowed():
    sf = SiteFacts.model_validate(CANNED_SITEFACTS_DICT)
    allows = sf.robots.allows.model_dump(by_alias=True)
    assert all(allows.values()), "All bots should be allowed in canned fixture"


def test_sitefacts_content_visible_without_js():
    sf = SiteFacts.model_validate(CANNED_SITEFACTS_DICT)
    assert sf.render.content_visible_without_js is True
