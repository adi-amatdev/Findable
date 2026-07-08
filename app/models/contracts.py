"""Canonical data contracts (see agents-seo-okf/data/).

Only `SiteFacts` (and its sub-models) is produced by the implemented pipeline.
`AgentResult` and `AuditReport` are defined here as the target contracts the
scaffolded agent/aggregation layers will implement later — they are not built yet.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

# AI crawlers whose robots.txt allow/deny state we track (spec: extraction).
AI_BOTS: tuple[str, ...] = (
    "GPTBot",
    "ClaudeBot",
    "PerplexityBot",
    "OAI-SearchBot",
    "Google-Extended",
    "CCBot",
)


# ─────────────────────────── SiteFacts (IMPLEMENTED) ───────────────────────────
# Mirrors agents-seo-okf/data/site-facts.md. Produced once per URL by
# deterministic extraction; no LLM ever writes it.


class HttpFacts(BaseModel):
    status: int = 0
    latency_ms: int = 0
    redirects: int = 0
    content_type: str = ""


class RobotsFacts(BaseModel):
    exists: bool = False
    # Per-bot allow/deny for the AI crawlers in AI_BOTS.
    allows: dict[str, bool] = Field(default_factory=dict)
    sitemap_refs: list[str] = Field(default_factory=list)


class SitemapFacts(BaseModel):
    exists: bool = False
    valid: bool = False
    url_count: int = 0


class LlmsTxtFacts(BaseModel):
    exists: bool = False
    valid: bool = False
    has_summary: bool = False
    link_count: int = 0
    full_variant: bool = False  # whether an llms-full.txt style variant was found


class RenderFacts(BaseModel):
    raw_text_len: int = 0
    rendered_text_len: int = 0
    # 1 - raw/rendered. Near 1.0 => content is JS-injected, invisible to AI crawlers.
    js_dependency_ratio: float = 0.0
    content_visible_without_js: bool = True


class OutlineItem(BaseModel):
    level: int
    text: str


class HtmlFacts(BaseModel):
    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    lang: str = ""
    outline: list[OutlineItem] = Field(default_factory=list)
    word_count: int = 0
    og: dict[str, str] = Field(default_factory=dict)
    twitter: dict[str, str] = Field(default_factory=dict)


class StructuredDataFacts(BaseModel):
    schema_types: list[str] = Field(default_factory=list)
    jsonld_valid: bool = False
    errors: list[str] = Field(default_factory=list)


class LinkFacts(BaseModel):
    internal: int = 0
    external: int = 0
    outbound_citations: int = 0


class Dates(BaseModel):
    published: Optional[str] = None
    modified: Optional[str] = None


class AuthorshipFacts(BaseModel):
    byline_present: bool = False
    author_schema: bool = False
    dates: Dates = Field(default_factory=Dates)


class Entity(BaseModel):
    text: str
    label: str


class SiteFacts(BaseModel):
    """The single source of truth every agent reads. No LLM writes this."""

    url: str
    final_url: str = ""
    fetched_at: str = ""  # ISO8601
    http: HttpFacts = Field(default_factory=HttpFacts)
    robots: RobotsFacts = Field(default_factory=RobotsFacts)
    sitemap: SitemapFacts = Field(default_factory=SitemapFacts)
    llms_txt: LlmsTxtFacts = Field(default_factory=LlmsTxtFacts)
    render: RenderFacts = Field(default_factory=RenderFacts)
    html: HtmlFacts = Field(default_factory=HtmlFacts)
    structured_data: StructuredDataFacts = Field(default_factory=StructuredDataFacts)
    links: LinkFacts = Field(default_factory=LinkFacts)
    authorship: AuthorshipFacts = Field(default_factory=AuthorshipFacts)
    entities_raw: list[Entity] = Field(default_factory=list)
    # The page markdown slice agents read alongside the facts (spec: agent contract).
    markdown: str = ""


# ─────────────────── Downstream contracts (SCAFFOLD targets, not built) ───────────────────
# Defined so the scaffolded agent/aggregation packages have a typed interface to
# code against. See agents-seo-okf/data/agent-result.md and audit-report.md.


class Effort(str, Enum):
    S = "S"  # hours
    M = "M"  # days
    L = "L"  # weeks/sprint


class Finding(BaseModel):
    id: str
    title: str
    severity: int  # 1-5
    effort: Effort
    impact: int  # 1-5
    detail: str = ""
    fix: str = ""
    evidence: str = ""
    ref_url: str = ""


class AgentResult(BaseModel):
    agent: str
    score: int
    sub_scores: dict[str, int] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    model_used: str = "heuristic"
    latency_ms: int = 0
    tokens: int = 0
