from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class HttpInfo(BaseModel):
    status: int
    latency_ms: float
    redirects: int
    content_type: str = ""


class BotAllows(BaseModel):
    GPTBot: bool = True
    ClaudeBot: bool = True
    PerplexityBot: bool = True
    OAI_SearchBot: bool = Field(True, alias="OAI-SearchBot")
    Google_Extended: bool = Field(True, alias="Google-Extended")
    CCBot: bool = True

    model_config = {"populate_by_name": True}


class RobotsInfo(BaseModel):
    exists: bool
    allows: BotAllows
    sitemap_refs: list[str] = []


class SitemapInfo(BaseModel):
    exists: bool
    valid: bool
    url_count: int = 0


class LlmsTxtInfo(BaseModel):
    exists: bool
    valid: bool
    has_summary: bool
    link_count: int
    full_variant: bool


class RenderInfo(BaseModel):
    raw_text_len: int
    rendered_text_len: int
    js_dependency_ratio: float
    content_visible_without_js: bool


class HtmlInfo(BaseModel):
    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    lang: str = ""
    outline: list[dict[str, Any]] = []
    word_count: int = 0
    og: dict[str, str] = {}
    twitter: dict[str, str] = {}


class StructuredDataInfo(BaseModel):
    schema_types: list[str] = []
    jsonld_valid: bool = True
    errors: list[str] = []


class LinksInfo(BaseModel):
    internal: int = 0
    external: int = 0
    outbound_citations: int = 0


class DatesInfo(BaseModel):
    published: Optional[str] = None
    modified: Optional[str] = None


class AuthorshipInfo(BaseModel):
    byline_present: bool
    author_schema: bool
    dates: DatesInfo = DatesInfo()


class EntityRaw(BaseModel):
    text: str
    label: str


# ---------------------------------------------------------------------------
# SiteFacts — arrives as API input, never produced locally
# ---------------------------------------------------------------------------

class SiteFacts(BaseModel):
    url: str
    final_url: str
    fetched_at: str

    http: HttpInfo
    robots: RobotsInfo
    sitemap: SitemapInfo
    llms_txt: LlmsTxtInfo
    render: RenderInfo
    html: HtmlInfo
    structured_data: StructuredDataInfo
    links: LinksInfo
    authorship: AuthorshipInfo
    entities_raw: list[EntityRaw] = []

    # Accepts both 'page_markdown' and 'markdown' keys
    page_markdown: str = Field(default="", alias="markdown", validation_alias="markdown")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# CrawlReport — one depth-pass from the sub-agent
# ---------------------------------------------------------------------------

class CrawlReport(BaseModel):
    depth: int
    url: str
    reachable: bool
    js_dependent: bool
    bot_blocked: Optional[str] = None
    notable_links: list[str] = []
    summary: str


# ---------------------------------------------------------------------------
# Traffic signal
# ---------------------------------------------------------------------------

class TrafficSignal(BaseModel):
    domain_rank: Optional[int] = None
    cloudflare_visits_estimate: Optional[str] = None
    source: str  # "tranco" | "cloudflare" | "both" | "unavailable"


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    id: str
    title: str
    severity: int       # 1-5
    effort: str         # "S" | "M" | "L"
    impact: int         # 1-5
    detail: str
    fix: str
    evidence: str
    ref_url: str = ""


class AgentResult(BaseModel):
    agent: str
    score: int
    sub_scores: dict[str, int] = {}
    findings: list[Finding] = []
    artifacts: dict[str, Any] = {}
    traffic_signal: Optional[TrafficSignal] = None
    crawl_reports: list[CrawlReport] = []
    model_used: str = ""
    latency_ms: float = 0.0
    tokens: int = 0


# ---------------------------------------------------------------------------
# AuditReport
# ---------------------------------------------------------------------------

class VisibilityEstimate(BaseModel):
    gpt: float = 0.0
    claude: float = 0.0
    perplexity: float = 0.0
    gemini: float = 0.0


class Visibility(BaseModel):
    before: VisibilityEstimate
    after: VisibilityEstimate


class SiteCoverage(BaseModel):
    has_schema_pct: float = 0.0
    js_rendered_pct: float = 0.0
    meta_desc_pct: float = 0.0
    author_date_pct: float = 0.0


class SiteSummary(BaseModel):
    ai_readiness_score: int
    coverage: SiteCoverage
    robots: dict[str, Any] = {}
    sitemap: dict[str, Any] = {}
    llms_txt: dict[str, Any] = {}
    systemic_fixes: list[Finding] = []


class PageResult(BaseModel):
    url: str
    role: str
    ai_readiness_score: int
    category_scores: dict[str, int]
    visibility: Visibility
    fixes: list[Finding]
    agent_results: list[AgentResult]


class AuditReport(BaseModel):
    url: str
    generated_at: str
    scope: dict[str, int]
    summary: str
    site: SiteSummary
    pages: list[PageResult]
