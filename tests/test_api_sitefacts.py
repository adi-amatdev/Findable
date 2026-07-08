"""API: POST /api/sitefacts end-to-end with an injected offline crawler."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_pipeline
from app.cache import get_cache
from app.config import get_settings
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
