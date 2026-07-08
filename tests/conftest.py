"""Shared test fixtures: a canned RawCrawl and an offline fake crawler so the
whole pipeline runs without network, Firecrawl, or Redis."""

from __future__ import annotations

import pytest

from app.crawl.models import RawCrawl

RENDERED_HTML = """<!doctype html>
<html lang="en">
<head>
  <title>Best Trail Running Shoes 2026 — Field-Tested Guide</title>
  <meta name="description" content="An independent, field-tested guide to the best trail running shoes of 2026, reviewed over 600 miles of terrain.">
  <link rel="canonical" href="https://example.com/trail-shoes">
  <meta name="author" content="Jane Doe">
  <meta property="og:title" content="Best Trail Running Shoes 2026">
  <meta property="og:description" content="Field-tested guide">
  <meta property="og:image" content="https://example.com/img/hero.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta property="article:published_time" content="2026-05-01T08:00:00Z">
  <meta property="article:modified_time" content="2026-06-15T10:00:00Z">
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Article","author":{"@type":"Person","name":"Jane Doe"},"datePublished":"2026-05-01","dateModified":"2026-06-15"}
  </script>
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"FAQPage"}
  </script>
</head>
<body>
  <h1>Best Trail Running Shoes 2026</h1>
  <h2>How we tested</h2>
  <h2>Which shoe is best for beginners?</h2>
  <h3>Budget picks</h3>
  <p>Our team logged hundreds of miles across rocky, muddy, and alpine terrain to
  find shoes that hold up. We scored grip, cushioning, durability, and comfort on
  long efforts, then cross-checked against independent lab data before ranking.</p>
  <a href="/reviews/altra">Altra review</a>
  <a href="/reviews/hoka">Hoka review</a>
  <a href="https://brand.example.org/altra">Altra official</a>
  <a href="https://wikipedia.org/wiki/Trail_running">Trail running</a>
  <img src="a.jpg" alt="trail shoe">
</body>
</html>"""

MARKDOWN = (
    "Our team logged hundreds of miles across rocky, muddy, and alpine terrain to "
    "find shoes that hold up. We scored grip, cushioning, durability, and comfort "
    "on long efforts, then cross-checked against independent lab data before ranking."
)

ROBOTS_TXT = """User-agent: *
Allow: /
Sitemap: https://example.com/sitemap.xml

User-agent: PerplexityBot
Disallow: /
"""

SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/trail-shoes</loc></url>
  <url><loc>https://example.com/reviews/altra</loc></url>
</urlset>"""

LLMS_TXT = """# Example
> A field-tested running gear guide.
- [Trail shoes](https://example.com/trail-shoes)
- [Road shoes](https://example.com/road-shoes)
"""


def make_raw_crawl(*, js_gated: bool = False) -> RawCrawl:
    """A fully-populated RawCrawl. If js_gated, the raw (pre-JS) HTML is nearly
    empty so the extractor sees a high js_dependency_ratio."""
    raw_html = "<html><body></body></html>" if js_gated else RENDERED_HTML
    return RawCrawl(
        url="https://example.com/trail-shoes",
        final_url="https://example.com/trail-shoes",
        fetched_at="2026-07-08T00:00:00+00:00",
        http_status=200,
        latency_ms=180,
        redirects=0,
        content_type="text/html; charset=utf-8",
        rendered_html=RENDERED_HTML,
        markdown=MARKDOWN,
        metadata={"statusCode": 200, "sourceURL": "https://example.com/trail-shoes"},
        links=["https://example.com/reviews/altra", "https://wikipedia.org/wiki/Trail_running"],
        screenshot=None,
        raw_html=raw_html,
        robots_txt=ROBOTS_TXT,
        sitemap_xml=SITEMAP_XML,
        llms_txt=LLMS_TXT,
    )


class FakeCrawler:
    """Implements the Crawler protocol; returns a canned RawCrawl, no network."""

    def __init__(self, raw: RawCrawl):
        self._raw = raw

    async def crawl(self, url: str, refresh: bool = False) -> RawCrawl:
        return self._raw


@pytest.fixture
def raw_crawl() -> RawCrawl:
    return make_raw_crawl()
