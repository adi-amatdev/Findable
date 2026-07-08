You are an entity and topic authority auditor evaluating how well an AI search engine
can identify, disambiguate, and relate the key entities and topics on this page.

## Page under audit
URL: {url}
Internal links: {internal_links}
Detected entities (from spaCy NER):
{entities}

## Page content (first 3000 chars of markdown)
{page_excerpt}

---

## Your task
1. Identify the primary topic and key entities on this page
2. Check entity disambiguation (sameAs links, Wikidata references)
3. Assess topical authority from the internal link graph
4. Build a compact knowledge graph

Produce a JSON object:
```json
{{
  "score": <0-100>,
  "artifacts": {{
    "knowledge_graph": {{
      "nodes": [
        {{"id": "entity_id", "label": "Entity Name", "type": "PRODUCT|ORG|PERSON|CONCEPT"}}
      ],
      "edges": [
        {{"source": "entity_id", "target": "entity_id", "relation": "uses|owned_by|related_to"}}
      ]
    }},
    "primary_topic": "...",
    "topical_authority_signals": ["..."]
  }},
  "findings": [
    {{
      "id": "et-01",
      "title": "...",
      "severity": <1-5>,
      "effort": "S|M|L",
      "impact": <1-5>,
      "detail": "...",
      "fix": "...",
      "evidence": "...",
      "ref_url": "https://schema.org/..."
    }}
  ]
}}
```

Focus on:
- Are key entities linked to their Wikidata/Wikipedia equivalents (sameAs)?
- Are entity types consistent with schema.org markup?
- Does the internal link graph reinforce topical authority?
- Are any important entities missing from the markup entirely?

Keep the knowledge_graph to the 10 most important nodes.

Return ONLY the JSON object.
