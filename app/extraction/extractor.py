"""Deterministic extraction: RawCrawl -> SiteFacts.

Every field is derived in plain code (BeautifulSoup / lxml / regex). No LLM.
The same RawCrawl always yields the same SiteFacts - reproducibility is what
makes the downstream score trustworthy.

Scoping notes (vs the spec's ideal libraries):
- Structured data uses BeautifulSoup JSON-LD parsing; `extruct` (Microdata/RDFa)
  is the richer target and slots in behind `_structured_data()`.
- `entities_raw` is a lightweight capitalized-phrase heuristic; `spaCy` NER is
  the target and slots in behind `_entities()`.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from lxml import etree

from ..crawl.models import RawCrawl
from ..models.contracts import (
    AI_BOTS,
    AuthorshipFacts,
    Dates,
    Entity,
    HtmlFacts,
    HttpFacts,
    LinkFacts,
    LlmsTxtFacts,
    OutlineItem,
    RenderFacts,
    RobotsFacts,
    SiteFacts,
    SitemapFacts,
    StructuredDataFacts,
)


def build_site_facts(raw: RawCrawl) -> SiteFacts:
    primary_html = raw.rendered_html or raw.raw_html or ""
    soup = BeautifulSoup(primary_html, "lxml")

    jsonld = _parse_jsonld(soup)

    return SiteFacts(
        url=raw.url,
        final_url=raw.final_url or raw.url,
        fetched_at=raw.fetched_at,
        http=HttpFacts(
            status=raw.http_status,
            latency_ms=raw.latency_ms,
            redirects=raw.redirects,
            content_type=raw.content_type,
        ),
        robots=_robots(raw.robots_txt),
        sitemap=_sitemap(raw.sitemap_xml),
        llms_txt=_llms_txt(raw.llms_txt),
        render=_render(raw.raw_html, raw.rendered_html),
        html=_html(soup, raw.markdown),
        structured_data=_structured_data(jsonld),
        links=_links(raw.final_url or raw.url, soup, raw.links),
        authorship=_authorship(soup, jsonld),
        entities_raw=_entities(soup),
        markdown=raw.markdown,
    )


# ─────────────────────────── robots.txt ───────────────────────────


def _robots(text: Optional[str]) -> RobotsFacts:
    if text is None:
        # No robots.txt => nothing disallowed => all bots allowed.
        return RobotsFacts(exists=False, allows={b: True for b in AI_BOTS}, sitemap_refs=[])

    ua_rules: dict[str, list[tuple[str, str]]] = {}
    sitemaps: list[str] = []
    pending_uas: list[str] = []
    last_was_ua = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()

        if field == "user-agent":
            if not last_was_ua:
                pending_uas = []
            pending_uas.append(value.lower())
            ua_rules.setdefault(value.lower(), [])
            last_was_ua = True
        elif field == "sitemap":
            sitemaps.append(value)
            last_was_ua = False
        elif field in ("disallow", "allow"):
            for ua in pending_uas:
                ua_rules.setdefault(ua, []).append((field, value))
            last_was_ua = False
        else:
            last_was_ua = False

    def blocked_from_root(bot: str) -> bool:
        rules = ua_rules.get(bot.lower())
        if rules is None:
            rules = ua_rules.get("*")
        if not rules:
            return False
        blocked = False
        for directive, value in rules:
            if directive == "disallow" and value == "/":
                blocked = True
            elif directive == "allow" and value in ("/", ""):
                blocked = False
        return blocked

    allows = {b: (not blocked_from_root(b)) for b in AI_BOTS}
    return RobotsFacts(exists=True, allows=allows, sitemap_refs=sitemaps)


# ─────────────────────────── sitemap.xml ───────────────────────────


def _sitemap(xml: Optional[str]) -> SitemapFacts:
    if xml is None:
        return SitemapFacts(exists=False)
    try:
        root = etree.fromstring(xml.encode("utf-8"))
        tag = etree.QName(root).localname.lower()
        valid = tag in ("urlset", "sitemapindex")
        url_count = len(root.findall(".//{*}loc"))
        return SitemapFacts(exists=True, valid=valid, url_count=url_count)
    except (etree.XMLSyntaxError, ValueError):
        return SitemapFacts(exists=True, valid=False, url_count=0)


# ─────────────────────────── llms.txt ───────────────────────────


def _llms_txt(text: Optional[str]) -> LlmsTxtFacts:
    if text is None:
        return LlmsTxtFacts(exists=False)
    lines = text.splitlines()
    valid = any(ln.strip().startswith("# ") for ln in lines[:5])
    has_summary = any(ln.strip().startswith("> ") for ln in lines)
    link_count = len(re.findall(r"\]\(", text))
    return LlmsTxtFacts(
        exists=True, valid=valid, has_summary=has_summary,
        link_count=link_count, full_variant=False,
    )


# ─────────────────────────── render diff ───────────────────────────


def _render(raw_html: str, rendered_html: str) -> RenderFacts:
    raw_len = len(_visible_text(raw_html)) if raw_html else 0
    rendered_len = len(_visible_text(rendered_html)) if rendered_html else raw_len
    if rendered_len <= 0:
        rendered_len = raw_len

    ratio = 0.0
    if rendered_len > 0:
        ratio = max(0.0, round(1 - raw_len / rendered_len, 4))
    # If less than half the rendered text exists pre-JS, content is JS-gated.
    visible = ratio <= 0.5
    return RenderFacts(
        raw_text_len=raw_len,
        rendered_text_len=rendered_len,
        js_dependency_ratio=ratio,
        content_visible_without_js=visible,
    )


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


# ─────────────────────────── HTML facts ───────────────────────────


def _html(soup: BeautifulSoup, markdown: str) -> HtmlFacts:
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    outline = [
        OutlineItem(level=int(h.name[1]), text=h.get_text(strip=True))
        for h in soup.find_all(["h1", "h2", "h3"])
        if h.get_text(strip=True)
    ]

    og = {
        (t.get("property") or "")[3:]: (t.get("content") or "").strip()
        for t in soup.find_all("meta", attrs={"property": re.compile(r"^og:", re.I)})
        if t.get("content")
    }
    twitter = {
        (t.get("name") or "")[8:]: (t.get("content") or "").strip()
        for t in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)})
        if t.get("content")
    }

    return HtmlFacts(
        title=title,
        meta_description=_meta(soup, name="description") or "",
        canonical=_canonical(soup) or "",
        lang=(soup.html.get("lang") if soup.html else "") or "",
        outline=outline,
        word_count=len(markdown.split()) if markdown else 0,
        og=og,
        twitter=twitter,
    )


def _meta(soup: BeautifulSoup, *, name: str) -> Optional[str]:
    tag = soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _meta_prop(soup: BeautifulSoup, prop: str) -> Optional[str]:
    tag = soup.find("meta", attrs={"property": prop})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _canonical(soup: BeautifulSoup) -> Optional[str]:
    for link in soup.find_all("link"):
        rels = [r.lower() for r in (link.get("rel") or [])]
        if "canonical" in rels:
            return link.get("href")
    return None


# ─────────────────────────── structured data ───────────────────────────


def _parse_jsonld(soup: BeautifulSoup) -> list[dict]:
    blocks: list[Any] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        rawtext = (tag.string or tag.get_text() or "").strip()
        if not rawtext:
            continue
        try:
            parsed = json.loads(rawtext)
        except (ValueError, TypeError):
            blocks.append({"__parse_error__": True})
            continue
        if isinstance(parsed, dict) and "@graph" in parsed:
            graph = parsed["@graph"]
            blocks.extend(graph if isinstance(graph, list) else [graph])
        elif isinstance(parsed, list):
            blocks.extend(parsed)
        else:
            blocks.append(parsed)
    return [b for b in blocks if isinstance(b, dict)]


def _structured_data(jsonld: list[dict]) -> StructuredDataFacts:
    errors = ["invalid JSON-LD block" for b in jsonld if b.get("__parse_error__")]
    valid_blocks = [b for b in jsonld if not b.get("__parse_error__")]
    types: list[str] = []
    for b in valid_blocks:
        t = b.get("@type")
        if isinstance(t, list):
            types.extend(str(x) for x in t)
        elif t:
            types.append(str(t))
    return StructuredDataFacts(
        schema_types=sorted(set(types)),
        jsonld_valid=bool(valid_blocks) and not errors,
        errors=errors,
    )


# ─────────────────────────── links ───────────────────────────


def _links(base_url: str, soup: BeautifulSoup, firecrawl_links: list[str]) -> LinkFacts:
    host = urlparse(base_url).netloc.lower()

    hrefs: list[str] = []
    for a in soup.find_all("a", href=True):
        hrefs.append(urljoin(base_url, a["href"]))
    if not hrefs and firecrawl_links:
        hrefs = firecrawl_links

    internal = external = 0
    for href in hrefs:
        try:
            netloc = urlparse(href).netloc.lower()
        except ValueError:
            continue
        if not netloc or netloc == host:
            internal += 1
        elif href.startswith("http"):
            external += 1
    # Heuristic proxy: outbound citations ≈ external links (spec target: links
    # inside article content pointing to authoritative sources).
    return LinkFacts(internal=internal, external=external, outbound_citations=external)


# ─────────────────────────── authorship ───────────────────────────


def _authorship(soup: BeautifulSoup, jsonld: list[dict]) -> AuthorshipFacts:
    meta_author = _meta(soup, name="author")
    schema_author = any("author" in b for b in jsonld)
    rel_author = soup.find("a", attrs={"rel": re.compile(r"author", re.I)}) is not None
    byline = bool(meta_author or schema_author or rel_author)

    published = _meta_prop(soup, "article:published_time")
    modified = _meta_prop(soup, "article:modified_time")
    for b in jsonld:
        published = published or _as_str(b.get("datePublished"))
        modified = modified or _as_str(b.get("dateModified"))

    return AuthorshipFacts(
        byline_present=byline,
        author_schema=schema_author,
        dates=Dates(published=published, modified=modified),
    )


def _as_str(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


# ─────────────────────────── entities (heuristic) ───────────────────────────

_STOPWORDS = {"The", "This", "That", "These", "Those", "And", "But", "For", "With", "From"}


def _entities(soup: BeautifulSoup, limit: int = 15) -> list[Entity]:
    """Lightweight placeholder for spaCy NER: distinct capitalized phrases."""
    text = " ".join(
        h.get_text(" ", strip=True) for h in soup.find_all(["title", "h1", "h2", "h3"])
    )
    candidates = re.findall(r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*)\b", text)
    seen: list[str] = []
    for c in candidates:
        c = c.strip()
        if c and c not in _STOPWORDS and c not in seen:
            seen.append(c)
        if len(seen) >= limit:
            break
    return [Entity(text=c, label="MISC") for c in seen]
