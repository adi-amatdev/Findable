"""Turn a Firecrawl scrape result into a structured SEO + AEO audit.

SEO  = classic search-engine optimisation (titles, meta, canonical, links...).
AEO  = answer-engine / agent optimisation: how easily an LLM-based assistant
       (ChatGPT, Perplexity, Google AI Overviews...) can read, trust and cite
       the page. Signals: structured data, FAQ schema, clean chunkable text,
       question-style headings, provenance (author/date).
"""

from __future__ import annotations

import json
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

STATUS_WEIGHT = {"pass": 1.0, "warn": 0.5, "fail": 0.0}

ENTITY_TYPES = {
    "Organization", "Person", "WebSite", "WebPage", "Article", "BlogPosting",
    "NewsArticle", "Product", "BreadcrumbList", "Recipe", "HowTo", "Event",
    "LocalBusiness", "Review",
}


def _check(id: str, label: str, status: str, detail: str, recommendation: Optional[str] = None) -> dict:
    return {
        "id": id,
        "label": label,
        "status": status,  # pass | warn | fail | info
        "detail": detail,
        "recommendation": recommendation,
    }


def _score(checks: list[dict]) -> Optional[int]:
    scored = [c for c in checks if c["status"] in STATUS_WEIGHT]
    if not scored:
        return None
    total = sum(STATUS_WEIGHT[c["status"]] for c in scored)
    return round(100 * total / len(scored))


def _meta(soup: BeautifulSoup, *, name: str | None = None, prop: str | None = None) -> Optional[str]:
    attrs = {"name": name} if name else {"property": prop}
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _canonical(soup: BeautifulSoup) -> Optional[str]:
    for link in soup.find_all("link"):
        rels = [r.lower() for r in (link.get("rel") or [])]
        if "canonical" in rels:
            return link.get("href")
    return None


def _extract_jsonld(soup: BeautifulSoup) -> list[dict]:
    blocks: list[Any] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (tag.string or tag.get_text() or "").strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict) and "@graph" in parsed:
            graph = parsed["@graph"]
            blocks.extend(graph if isinstance(graph, list) else [graph])
        elif isinstance(parsed, list):
            blocks.extend(parsed)
        else:
            blocks.append(parsed)
    return [b for b in blocks if isinstance(b, dict)]


def _types(obj: dict) -> list[str]:
    t = obj.get("@type")
    if isinstance(t, list):
        return [str(x) for x in t]
    return [str(t)] if t else []


def _link_stats(url: str, links: list[str]) -> dict:
    host = urlparse(url).netloc.lower()
    internal = external = 0
    for link in links:
        try:
            netloc = urlparse(link).netloc.lower()
        except ValueError:
            continue
        if not netloc or netloc == host:
            internal += 1
        else:
            external += 1
    return {"total": len(links), "internal": internal, "external": external}


def build_audit(url: str, data: dict[str, Any], include_raw: bool = False) -> dict:
    metadata = data.get("metadata") or {}
    raw_html = data.get("rawHtml") or data.get("html") or ""
    markdown = data.get("markdown") or ""
    summary = data.get("summary")
    links = data.get("links") or []
    screenshot = data.get("screenshot")

    soup = BeautifulSoup(raw_html, "lxml")
    jsonld = _extract_jsonld(soup)
    sd_types = sorted({t for j in jsonld for t in _types(j)})

    seo_checks = _seo_checks(url, soup, metadata, markdown, links)
    aeo_checks = _aeo_checks(soup, markdown, summary, jsonld, sd_types)

    audit = {
        "url": url,
        "final_url": metadata.get("sourceURL") or metadata.get("url") or url,
        "status_code": metadata.get("statusCode"),
        "overview": {
            "title": metadata.get("title"),
            "description": metadata.get("description"),
            "language": metadata.get("language"),
            "word_count": len(markdown.split()) if markdown else 0,
            "summary": summary,
        },
        "seo": {"score": _score(seo_checks), "checks": seo_checks},
        "aeo": {
            "score": _score(aeo_checks),
            "checks": aeo_checks,
            "structured_data_types": sd_types,
        },
        "links": _link_stats(url, links),
    }
    if screenshot:
        audit["screenshot"] = screenshot
    if include_raw:
        audit["raw"] = data
    return audit


def _seo_checks(url, soup, metadata, markdown, links) -> list[dict]:
    checks: list[dict] = []

    # Title
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    title = title or metadata.get("title")
    tlen = len(title) if title else 0
    if not title:
        checks.append(_check("title", "Title tag", "fail", "No <title> found.",
                             "Add a unique, descriptive title of 30–60 characters."))
    elif 30 <= tlen <= 60:
        checks.append(_check("title", "Title tag", "pass", f'"{title}" ({tlen} chars).'))
    else:
        checks.append(_check("title", "Title tag", "warn", f'"{title}" ({tlen} chars).',
                             "Aim for 30–60 characters so it isn't truncated in results."))

    # Meta description
    desc = _meta(soup, name="description") or metadata.get("description")
    dlen = len(desc) if desc else 0
    if not desc:
        checks.append(_check("meta_description", "Meta description", "fail", "Missing.",
                             "Add a 70–160 character meta description."))
    elif 70 <= dlen <= 160:
        checks.append(_check("meta_description", "Meta description", "pass", f"{dlen} chars."))
    else:
        checks.append(_check("meta_description", "Meta description", "warn", f"{dlen} chars.",
                             "Aim for 70–160 characters."))

    # H1
    h1s = soup.find_all("h1")
    if len(h1s) == 1:
        checks.append(_check("h1", "Single H1", "pass", h1s[0].get_text(strip=True)[:120]))
    elif not h1s:
        checks.append(_check("h1", "Single H1", "fail", "No H1 found.",
                             "Add exactly one H1 describing the page topic."))
    else:
        checks.append(_check("h1", "Single H1", "warn", f"{len(h1s)} H1 tags.",
                             "Use a single H1 per page."))

    # Heading outline
    heads = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}
    checks.append(_check("headings", "Heading outline", "info",
                         ", ".join(f"{k}:{v}" for k, v in heads.items() if v) or "no headings"))

    # Canonical
    canonical = _canonical(soup)
    if canonical:
        checks.append(_check("canonical", "Canonical URL", "pass", canonical))
    else:
        checks.append(_check("canonical", "Canonical URL", "warn", "No canonical link.",
                             "Add <link rel=\"canonical\"> to prevent duplicate-content dilution."))

    # Robots
    robots = _meta(soup, name="robots")
    if robots and "noindex" in robots.lower():
        checks.append(_check("robots", "Robots meta", "fail", f'"{robots}" blocks indexing.',
                             "Remove noindex if this page should rank."))
    else:
        checks.append(_check("robots", "Robots meta", "pass",
                             robots or "Indexable (no restrictive robots meta)."))

    # Viewport
    if _meta(soup, name="viewport"):
        checks.append(_check("viewport", "Mobile viewport", "pass", "viewport meta present."))
    else:
        checks.append(_check("viewport", "Mobile viewport", "warn", "No viewport meta.",
                             "Add <meta name=\"viewport\"> for mobile-friendliness."))

    # Language
    lang = (soup.html.get("lang") if soup.html else None) or metadata.get("language")
    if lang:
        checks.append(_check("lang", "Language declared", "pass", str(lang)))
    else:
        checks.append(_check("lang", "Language declared", "warn", "No lang attribute.",
                             "Set <html lang> for search engines and assistive tech."))

    # Open Graph
    og = {p: _meta(soup, prop=f"og:{p}") for p in ("title", "description", "image")}
    present = [k for k, v in og.items() if v]
    if len(present) == 3:
        checks.append(_check("open_graph", "Open Graph", "pass",
                             "og:title, og:description, og:image present."))
    else:
        missing = [k for k in og if k not in present]
        checks.append(_check("open_graph", "Open Graph", "warn",
                             f"Missing: {', '.join(f'og:{m}' for m in missing)}.",
                             "Add the missing og: tags for rich link previews."))

    # Twitter card
    if _meta(soup, name="twitter:card"):
        checks.append(_check("twitter", "Twitter Card", "pass", _meta(soup, name="twitter:card")))
    else:
        checks.append(_check("twitter", "Twitter Card", "info", "No twitter:card meta.",
                             "Optional — add for tailored X/Twitter previews."))

    # Image alt text
    imgs = soup.find_all("img")
    missing_alt = [i for i in imgs if not (i.get("alt") or "").strip()]
    if not imgs:
        checks.append(_check("image_alt", "Image alt text", "info", "No <img> tags found."))
    elif not missing_alt:
        checks.append(_check("image_alt", "Image alt text", "pass",
                             f"All {len(imgs)} images have alt text."))
    else:
        checks.append(_check("image_alt", "Image alt text", "warn",
                             f"{len(missing_alt)}/{len(imgs)} images missing alt.",
                             "Add descriptive alt text for accessibility and image SEO."))

    # Content length
    wc = len(markdown.split()) if markdown else 0
    if wc >= 300:
        checks.append(_check("content_length", "Content depth", "pass", f"{wc} words."))
    elif wc > 0:
        checks.append(_check("content_length", "Content depth", "warn", f"{wc} words (thin).",
                             "Thin pages rank poorly; add meaningful depth."))
    else:
        checks.append(_check("content_length", "Content depth", "fail",
                             "No text content extracted.",
                             "Ensure content is in HTML, not locked behind JS/images."))

    # HTTPS
    if url.lower().startswith("https://"):
        checks.append(_check("https", "HTTPS", "pass", "Served over HTTPS."))
    else:
        checks.append(_check("https", "HTTPS", "fail", "Not HTTPS.",
                             "Serve over HTTPS — it's a ranking signal."))

    # HTTP status
    sc = metadata.get("statusCode")
    if sc and 200 <= sc < 300:
        checks.append(_check("status", "HTTP status", "pass", str(sc)))
    elif sc:
        checks.append(_check("status", "HTTP status", "warn", str(sc),
                             "Non-2xx status hurts crawlability."))

    return checks


def _aeo_checks(soup, markdown, summary, jsonld, sd_types) -> list[dict]:
    checks: list[dict] = []

    # Structured data (JSON-LD)
    if jsonld:
        checks.append(_check("structured_data", "Structured data (JSON-LD)", "pass",
                             f"{len(jsonld)} block(s): {', '.join(sd_types) or 'untyped'}."))
    else:
        checks.append(_check("structured_data", "Structured data (JSON-LD)", "fail",
                             "No JSON-LD found.",
                             "Add schema.org JSON-LD so answer engines can parse entities reliably."))

    # FAQ / QA schema
    if any(t in ("FAQPage", "QAPage") for t in sd_types):
        checks.append(_check("faq_schema", "FAQ / QA schema", "pass",
                             "Present — strong for direct-answer extraction."))
    else:
        checks.append(_check("faq_schema", "FAQ / QA schema", "info", "None.",
                             "Add FAQPage schema to Q&A content to win answer citations."))

    # Entity / E-E-A-T schema
    entity_hits = [t for t in sd_types if t in ENTITY_TYPES]
    if entity_hits:
        checks.append(_check("entity_schema", "Entity / E-E-A-T schema", "pass",
                             ", ".join(entity_hits)))
    else:
        checks.append(_check("entity_schema", "Entity / E-E-A-T schema", "warn",
                             "No Organization/Article/Product-type schema.",
                             "Describe the publishing entity and content type for trust signals."))

    # Question-style headings
    q_heads = [h.get_text(strip=True) for h in soup.find_all(["h2", "h3", "h4"])
               if h.get_text(strip=True).endswith("?")]
    if q_heads:
        checks.append(_check("question_headings", "Question-style headings", "pass",
                             f"{len(q_heads)} found — good for matching user queries."))
    else:
        checks.append(_check("question_headings", "Question-style headings", "info", "None.",
                             "Phrase some subheadings as the questions users ask assistants."))

    # Chunkability
    subheads = len(soup.find_all(["h2", "h3"]))
    if subheads >= 2:
        checks.append(_check("chunking", "Content chunking", "pass",
                             f"{subheads} H2/H3 sections — easy to segment."))
    else:
        checks.append(_check("chunking", "Content chunking", "warn",
                             f"{subheads} H2/H3 sections.",
                             "Break content into clear sections so agents can extract passages."))

    # Provenance (author / freshness)
    author = _meta(soup, name="author")
    published = _meta(soup, prop="article:published_time") or _meta(soup, name="date")
    if author or published:
        checks.append(_check("provenance", "Author / date signals", "pass",
                             f"author={author or '—'}, published={published or '—'}."))
    else:
        checks.append(_check("provenance", "Author / date signals", "warn",
                             "No author or publish-date meta.",
                             "Expose author and dates — answer engines favour attributable, fresh content."))

    # Machine-readable content
    wc = len(markdown.split()) if markdown else 0
    if wc >= 150:
        checks.append(_check("machine_content", "Agent-readable content", "pass",
                             f"{wc} words of clean, extractable text."))
    else:
        checks.append(_check("machine_content", "Agent-readable content", "warn",
                             f"Only {wc} words extracted.",
                             "Ensure key content is real HTML text, not images/JS-only."))

    # Auto summary (informational — what an engine might distil)
    if summary:
        checks.append(_check("summary", "Auto-summary preview", "info", summary[:280]))

    return checks
