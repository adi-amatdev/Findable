"""Request/response models.

`ScrapeOptions` mirrors the Firecrawl scrape body 1:1. Fields are written in
snake_case for Python, and serialised to Firecrawl's camelCase via the alias
generator, so `model_dump(by_alias=True, exclude_none=True)` yields a payload
you can send to Firecrawl verbatim.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from pydantic.alias_generators import to_camel


class _FirecrawlModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Location(_FirecrawlModel):
    # Emulate a geo-location so you audit the page the way local users see it.
    country: Optional[str] = None            # ISO country code, e.g. "US"
    languages: Optional[list[str]] = None    # e.g. ["en-US"]


class ScrapeOptions(_FirecrawlModel):
    """The knobs Firecrawl exposes that matter for an SEO/AEO audit."""

    # Which representations to return. See the README for what each is good for.
    # markdown | html | rawHtml | links | summary | screenshot
    formats: list[str] = Field(default_factory=lambda: ["markdown", "links", "summary"])

    # True = strip nav/header/footer/ads (what a reader/agent focuses on).
    # False = keep the whole page (needed to inspect boilerplate & layout).
    only_main_content: bool = True

    include_tags: Optional[list[str]] = None   # only keep these CSS selectors/tags
    exclude_tags: Optional[list[str]] = None    # drop these CSS selectors/tags

    wait_for: int = 0            # ms to wait for JS to settle before capture
    timeout: int = 30000         # ms hard cap for the whole scrape
    mobile: bool = False         # emulate a mobile viewport
    block_ads: bool = True       # skip ad/tracker requests
    remove_base64_images: bool = True
    skip_tls_verification: bool = False

    # basic | stealth | auto — stealth helps on bot-protected sites (costs more).
    proxy: Optional[str] = None

    location: Optional[Location] = None


class ScrapeRequest(BaseModel):
    url: HttpUrl
    options: ScrapeOptions = Field(default_factory=ScrapeOptions)
    refresh: bool = False  # bypass the Redis cache and force a fresh scrape


class AuditRequest(BaseModel):
    """Minimal input — the audit picks the optimal Firecrawl formats for you."""

    url: HttpUrl
    wait_for: int = 0                     # bump for heavy client-rendered pages
    mobile: bool = False                  # audit the mobile render instead
    include_screenshot: bool = False       # also capture a full-page screenshot
    include_raw_result: bool = False       # attach the full Firecrawl payload
    refresh: bool = False                  # bypass the Redis cache and re-scrape
