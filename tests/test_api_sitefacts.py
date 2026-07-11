"""API: POST /api/sitefacts end-to-end with an injected offline crawler."""

from __future__ import annotations

import pytest
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import routes
from app.api.deps import get_pipeline
from app.cache import get_cache
from app.config import Settings, get_settings
from app.main import app
from app.models.contracts import SiteFacts
from app.pipeline import SiteFactsPipeline

from .conftest import FakeCrawler, make_raw_crawl


@pytest.fixture
def client():
    def _offline_pipeline():
        return SiteFactsPipeline(get_settings(), get_cache(), crawler=FakeCrawler(make_raw_crawl()))

    app.dependency_overrides[get_pipeline] = _offline_pipeline
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_sitefacts_endpoint(client):
    resp = client.post("/api/sitefacts", json={"url": "https://example.com/trail-shoes"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["url"] == "https://example.com/trail-shoes"
    assert body["http"]["status"] == 200
    assert "Article" in body["structured_data"]["schema_types"]
    assert body["robots"]["allows"]["PerplexityBot"] is False
    assert body["sitemap"]["url_count"] == 3
    assert body["llms_txt"]["has_summary"] is True


def test_sitefacts_rejects_bad_url(client):
    resp = client.post("/api/sitefacts", json={"url": "not-a-url"})
    assert resp.status_code == 422  # pydantic HttpUrl validation


def test_agent_payload_bounds_markdown(client):
    raw = client.post("/api/sitefacts", json={"url": "https://example.com/trail-shoes"}).json()
    raw["markdown"] = "x" * (routes.MAX_AGENT_MARKDOWN_CHARS + 1)

    payload = routes._agent_sitefacts_payload(SiteFacts.model_validate(raw))

    assert len(payload["markdown"]) == routes.MAX_AGENT_MARKDOWN_CHARS


async def test_agent_stream_proxy_preserves_upstream_404(monkeypatch):
    """A missing agent stream must not be disguised as a 200 SSE response."""
    class FakeClient:
        async def send(self, request, *, stream):
            assert stream is True
            return httpx.Response(404, request=request, json={"detail": "Unknown agent_id"})

        def build_request(self, method, url):
            return httpx.Request(method, url)

        async def aclose(self):
            pass

    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda **_: FakeClient())

    with pytest.raises(HTTPException) as exc_info:
        await routes.agent_stream_proxy(
            "missing-agent", Settings(agents_url="http://agents-api:8080")
        )

    assert exc_info.value.status_code == 404
    assert "Unknown agent_id" in exc_info.value.detail


async def test_agent_stream_proxy_handles_midstream_transport_failure(monkeypatch):
    """An agents-api restart must close SSE cleanly, not crash the API app."""
    class BrokenResponse:
        def raise_for_status(self):
            pass

        async def aiter_bytes(self):
            raise httpx.RemoteProtocolError("upstream closed")
            yield b""  # pragma: no cover - makes this an async generator

        async def aclose(self):
            pass

    class FakeClient:
        def build_request(self, method, url):
            return httpx.Request(method, url)

        async def send(self, request, *, stream):
            return BrokenResponse()

        async def aclose(self):
            pass

    monkeypatch.setattr(routes.httpx, "AsyncClient", lambda **_: FakeClient())
    stream = await routes.agent_stream_proxy(
        "agent-id", Settings(agents_url="http://agents-api:8080")
    )

    assert [chunk async for chunk in stream.body_iterator] == []
