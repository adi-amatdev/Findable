---
type: Data Contract
title: AuditReport
status: implemented
description: The final multi-page audit output — headline score, per-page deep results, site-wide coverage stats, before/after visibility, LLM-written executive summary, and an optional rich nested structure from the real agents-api pipeline.
tags: [data, contract, report, output]
timestamp: 2026-07-09T00:00:00Z
---

# AuditReport

Produced by the [Aggregator](/components/aggregator.md) (or by [composeFallbackReport](/components/frontend.md#composefallbackreport) when the backend is unreachable). Returned by `GET /api/audit/{id}` after the report is finalized. Rendered by the [Frontend](/components/frontend.md) [ReportDashboard](/components/ReportDashboard.md) and exported as markdown/PDF via client-side download helpers.

## Schema (frontend TypeScript type)

The frontend uses a flattened schema with optional rich nested fields:

```typescript
interface AuditReport {
  url: string;
  ai_readiness_score: number;
  scores: Record<string, number>;           // e.g. { crawlability: 55, content_signal: 70, ... }
  visibility: {
    before: { gpt: number; claude: number; perplexity: number; gemini: number };
    after:  { gpt: number; claude: number; perplexity: number; gemini: number };
  };
  findings: Finding[];                       // merged across all agents, sorted by impact/effort
  summary: string;                           // LLM-written or fallback summary
  generated_at?: string;                     // ISO 8601
  mock?: boolean;                            // true when from MOCK_STREAM mode

  // Rich backend format (from real agents-api pipeline, optional)
  scope?: { deep_pages: number; shallow_pages: number };
  site?: SiteSummary;                        // site-wide coverage stats + systemic fixes
  pages?: PageResult[];                      // per-page deep results
}
```

Where `Finding`, `SiteSummary`, and `PageResult` are:

```typescript
interface Finding {
  id: string; title: string; severity: number; effort: string; impact: number;
  detail: string; fix: string; evidence: string; ref_url: string;
}

interface SiteSummary {
  ai_readiness_score: number;
  coverage: { has_schema_pct: number; js_rendered_pct: number;
              meta_desc_pct: number; author_date_pct: number };
  robots: Record<string, unknown>;
  sitemap: Record<string, unknown>;
  llms_txt: Record<string, unknown>;
  systemic_fixes: Finding[];
}

interface PageResult {
  url: string; role: string;               // "landing" | "follow_up"
  ai_readiness_score: number;
  category_scores: Record<string, number>;
  visibility: Visibility;
  fixes: Finding[];                        // page findings sorted by impact/effort
  agent_results: AgentResult[];            // 4 × AgentResult
}
```

## Hero number

The dashboard shows `ai_readiness_score` (top-level field) as the headline. Per-page scores appear when the rich nested format (`pages[]`) is available. `site.coverage` feeds the site-health panel.

## Systemic vs page-specific findings

If a coverage stat is poor across most pages (e.g. `has_schema_pct < 0.3`), it collapses into a single `site.systemic_fixes` recommendation rather than repeating per page.

## Visibility estimate

`visibility.before` and `visibility.after` are produced by the [Before/After Visibility Estimate](/scoring/visibility-estimate.md) component.

## Mock mode

In mock mode (`MOCK_STREAM=true`), the mock backend returns a hardcoded `MOCK_REPORT` dict:
- Score 62 with realistic sub-scores (crawlability 55, content_signal 70, structured_data 68, entity_topic 58)
- 5 findings across all agents
- Visibility before/after based on the [Visibility Estimate](/scoring/visibility-estimate.md) signal table
- `mock: true` so callers can detect the mode

See [Mock Stream Passthrough](/components/mock-stream.md).

## Transform

The frontend applies `transformBackendReport` to normalize both backend formats (flat frontend format and the nested real agents-api format) into the unified `AuditReport` type used by [ReportDashboard](/components/frontend.md). The function detects the format by checking for the presence of `ai_readiness_score` at the top level vs nested inside `site`/`pages[0]`.
