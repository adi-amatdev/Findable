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
