"""Agent layer — SCAFFOLD (not implemented).

The four concurrent agents each take SiteFacts (+ the page markdown slice) and
return an AgentResult (see agents-seo-okf/agents/). They are the next layer to
build on top of the implemented SiteFacts pipeline:

- crawlability     (30% of score) — robots / JS-gating / sitemap blockers
- content_signal   (30%)          — E-E-A-T, citation-worthiness (GEO)
- structured_data  (20%)          — schema.org / llms.txt / meta extractability
- entity_topic     (20%)          — entity graph + topical authority

Only the base interface is defined here.
"""

from .base import BaseAgent

__all__ = ["BaseAgent"]
