# agents

## Concepts
- [content-signal](content-signal.md) - Scores the page's Experience, Expertise, Authoritativeness, and Trust signals; flags commodity content; judges citation-worthiness and answer front-loading for AI search.
- [crawlability](crawlability.md) - Judges how much content is blocked or invisible to AI crawlers — robots.txt restrictions, JS-gated content, latency, sitemap gaps — via a 3-pass deterministic sub-agent plus one LLM judgment call.
- [entity-topic](entity-topic.md) - Maps the page's topic-to-entity graph, judges entity disambiguation (sameAs/Wikidata), and assesses topical authority via the internal link graph.
- [structured-data](structured-data.md) - Judges whether an AI can extract key facts from the page's meta tags, schema.org markup, and llms.txt; meta extraction is the primary signal per Google's AI Optimization Guide.
