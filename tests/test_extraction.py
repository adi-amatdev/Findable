"""Deterministic extraction: RawCrawl -> SiteFacts."""

from __future__ import annotations

from app.extraction import build_site_facts

from .conftest import make_raw_crawl


def test_http_and_meta():
    facts = build_site_facts(make_raw_crawl())
    assert facts.http.status == 200
    assert facts.final_url == "https://example.com/trail-shoes"
    assert facts.html.title.startswith("Best Trail Running Shoes 2026")
    assert "field-tested guide" in facts.html.meta_description.lower()
    assert facts.html.canonical == "https://example.com/trail-shoes"
    assert facts.html.lang == "en"
    assert facts.html.word_count > 0


def test_heading_outline():
    facts = build_site_facts(make_raw_crawl())
    levels = [o.level for o in facts.html.outline]
    assert levels == [1, 2, 2, 3]


def test_open_graph_and_twitter():
    facts = build_site_facts(make_raw_crawl())
    assert facts.html.og.get("title") == "Best Trail Running Shoes 2026"
    assert "image" in facts.html.og
    assert facts.html.twitter.get("card") == "summary_large_image"


def test_robots_per_bot():
    facts = build_site_facts(make_raw_crawl())
    assert facts.robots.exists is True
    assert facts.robots.allows["GPTBot"] is True
    assert facts.robots.allows["ClaudeBot"] is True
    # PerplexityBot is explicitly disallowed from root.
    assert facts.robots.allows["PerplexityBot"] is False
    assert facts.robots.sitemap_refs == ["https://example.com/sitemap.xml"]


def test_sitemap():
    facts = build_site_facts(make_raw_crawl())
    assert facts.sitemap.exists is True
    assert facts.sitemap.valid is True
    assert facts.sitemap.url_count == 3


def test_llms_txt():
    facts = build_site_facts(make_raw_crawl())
    assert facts.llms_txt.exists is True
    assert facts.llms_txt.valid is True
    assert facts.llms_txt.has_summary is True
    assert facts.llms_txt.link_count == 2


def test_structured_data():
    facts = build_site_facts(make_raw_crawl())
    assert "Article" in facts.structured_data.schema_types
    assert "FAQPage" in facts.structured_data.schema_types
    assert facts.structured_data.jsonld_valid is True
    assert facts.structured_data.errors == []


def test_links():
    facts = build_site_facts(make_raw_crawl())
    assert facts.links.internal == 2
    assert facts.links.external == 2
    assert facts.links.outbound_citations == 2


def test_authorship():
    facts = build_site_facts(make_raw_crawl())
    assert facts.authorship.byline_present is True
    assert facts.authorship.author_schema is True
    assert facts.authorship.dates.published == "2026-05-01T08:00:00Z"


def test_render_server_rendered_is_visible():
    # raw == rendered -> ratio ~0 -> content visible without JS.
    facts = build_site_facts(make_raw_crawl())
    assert facts.render.js_dependency_ratio <= 0.5
    assert facts.render.content_visible_without_js is True


def test_render_js_gated_is_hidden():
    # raw HTML nearly empty -> high JS dependency -> not visible without JS.
    facts = build_site_facts(make_raw_crawl(js_gated=True))
    assert facts.render.js_dependency_ratio > 0.5
    assert facts.render.content_visible_without_js is False


def test_entities_present():
    facts = build_site_facts(make_raw_crawl())
    assert len(facts.entities_raw) > 0


def test_extraction_is_deterministic():
    a = build_site_facts(make_raw_crawl())
    b = build_site_facts(make_raw_crawl())
    assert a.model_dump() == b.model_dump()
