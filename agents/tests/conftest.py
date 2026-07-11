"""
Shared fixtures for agents test suite.

All fixtures avoid network, LLM calls, and Tranco downloads.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure `app` package is importable when running pytest from agents/
sys.path.insert(0, str(Path(__file__).parent.parent))

import app.state as state  # noqa: E402 — must be after sys.path fix
from app.schemas import SiteFacts  # noqa: E402


# ---------------------------------------------------------------------------
# Canned SiteFacts — all bots allowed, JS-rendered, good signals
# ---------------------------------------------------------------------------

CANNED_SITEFACTS_DICT = {
    "url": "https://example.com",
    "final_url": "https://example.com",
    "fetched_at": "2026-07-08T00:00:00Z",
    "http": {
        "status": 200,
        "latency_ms": 210.0,
        "redirects": 0,
        "content_type": "text/html; charset=utf-8",
    },
    "robots": {
        "exists": True,
        "allows": {
            "GPTBot": True,
            "ClaudeBot": True,
            "PerplexityBot": True,
            "OAI-SearchBot": True,
            "Google-Extended": True,
            "CCBot": True,
        },
        "sitemap_refs": ["https://example.com/sitemap.xml"],
    },
    "sitemap": {"exists": True, "valid": True, "url_count": 8},
    "llms_txt": {
        "exists": True,
        "valid": True,
        "has_summary": True,
        "link_count": 4,
        "full_variant": False,
    },
    "render": {
        "raw_text_len": 4800,
        "rendered_text_len": 5100,
        "js_dependency_ratio": 0.06,
        "content_visible_without_js": True,
    },
    "html": {
        "title": "Example — Field-Tested Guide",
        "meta_description": "A thorough, independently verified guide.",
        "canonical": "https://example.com",
        "lang": "en",
        "outline": [{"level": 1, "text": "Example"}],
        "word_count": 950,
        "og": {"title": "Example"},
        "twitter": {"card": "summary"},
    },
    "structured_data": {
        "schema_types": ["Article", "FAQPage"],
        "jsonld_valid": True,
        "errors": [],
    },
    "links": {"internal": 12, "external": 4, "outbound_citations": 3},
    "authorship": {
        "byline_present": True,
        "author_schema": True,
        "dates": {"published": "2026-01-15", "modified": "2026-06-20"},
    },
    "entities_raw": [
        {"text": "Python", "label": "PRODUCT"},
        {"text": "FastAPI", "label": "PRODUCT"},
        {"text": "Google", "label": "ORG"},
    ],
    "markdown": (
        "This is a thoroughly researched guide written by field experts with "
        "first-hand experience. Data sourced from independent lab testing."
    ),
}

# Minimal JSON that every agent's parse_result can handle gracefully
MOCK_LLM_JSON = {
    "score": 78,
    "sub_scores": {
        "experience": 80,
        "expertise": 78,
        "authority": 75,
        "trust": 79,
    },
    "commodity_content": False,
    "citation_worthy": True,
    "answer_front_loaded": False,
    "artifacts": {"knowledge_graph": {"nodes": [], "edges": []}},
    "findings": [],
}

MOCK_LLM_RESPONSE = {
    "choices": [
        {
            "message": {"content": str(__import__("json").dumps(MOCK_LLM_JSON))},
            "model": "test-model",
        }
    ],
    "usage": {"total_tokens": 50},
}


@pytest.fixture
def canned_sf() -> SiteFacts:
    """Pre-built SiteFacts object — no network."""
    return SiteFacts.model_validate(CANNED_SITEFACTS_DICT)


@pytest.fixture
def canned_sf_dict() -> dict:
    """Raw dict form — for sending as JSON body."""
    return CANNED_SITEFACTS_DICT


@pytest.fixture(autouse=True)
def clear_state():
    """Reset the in-process state between every test."""
    state._queues.clear()
    state._results.clear()
    state._queue_created_at.clear()
    state._result_created_at.clear()
    yield
    state._queues.clear()
    state._results.clear()
    state._queue_created_at.clear()
    state._result_created_at.clear()
