"""HTTP request/response models for the API layer."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic.alias_generators import to_camel


class SiteFactsRequest(BaseModel):
    """Input for the implemented pipeline: a URL in, SiteFacts out."""

    url: HttpUrl
    refresh: bool = False  # bypass the cache and re-crawl


# ── Firecrawl passthrough (debug endpoint) ──
# Mirrors the Firecrawl scrape body 1:1; snake_case here, camelCase on the wire.


class _FirecrawlModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Location(_FirecrawlModel):
    country: Optional[str] = None
    languages: Optional[list[str]] = None


class ScrapeOptions(_FirecrawlModel):
    formats: list[str] = Field(default_factory=lambda: ["markdown", "links", "summary"])
    only_main_content: bool = True
    include_tags: Optional[list[str]] = None
    exclude_tags: Optional[list[str]] = None
    wait_for: int = 0
    timeout: int = 30000
    mobile: bool = False
    block_ads: bool = True
    remove_base64_images: bool = True
    skip_tls_verification: bool = False
    proxy: Optional[str] = None
    location: Optional[Location] = None


class ScrapeRequest(BaseModel):
    url: HttpUrl
    options: ScrapeOptions = Field(default_factory=ScrapeOptions)
    refresh: bool = False
