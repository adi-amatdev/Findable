"""Deterministic Extraction — turns a RawCrawl into a SiteFacts object.

No LLM. Design Principle 1 (Deterministic–LLM Separation): if a Python library
can answer it, it does not go to a model. See agents-seo-okf/components/extraction.md.
"""

from .extractor import build_site_facts

__all__ = ["build_site_facts"]
