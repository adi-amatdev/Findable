// Mirrors the backend SiteFacts contract (app/models/contracts.py).
// See agents-seo-okf/data/site-facts.md.

export const AI_BOTS = [
  "GPTBot",
  "ClaudeBot",
  "PerplexityBot",
  "OAI-SearchBot",
  "Google-Extended",
  "CCBot",
] as const;

export interface HttpFacts {
  status: number;
  latency_ms: number;
  redirects: number;
  content_type: string;
}

export interface RobotsFacts {
  exists: boolean;
  allows: Record<string, boolean>;
  sitemap_refs: string[];
}

export interface SitemapFacts {
  exists: boolean;
  valid: boolean;
  url_count: number;
}

export interface LlmsTxtFacts {
  exists: boolean;
  valid: boolean;
  has_summary: boolean;
  link_count: number;
  full_variant: boolean;
}

export interface RenderFacts {
  raw_text_len: number;
  rendered_text_len: number;
  js_dependency_ratio: number;
  content_visible_without_js: boolean;
}

export interface OutlineItem {
  level: number;
  text: string;
}

export interface HtmlFacts {
  title: string;
  meta_description: string;
  canonical: string;
  lang: string;
  outline: OutlineItem[];
  word_count: number;
  og: Record<string, string>;
  twitter: Record<string, string>;
}

export interface StructuredDataFacts {
  schema_types: string[];
  jsonld_valid: boolean;
  errors: string[];
}

export interface LinkFacts {
  internal: number;
  external: number;
  outbound_citations: number;
}

export interface Dates {
  published: string | null;
  modified: string | null;
}

export interface AuthorshipFacts {
  byline_present: boolean;
  author_schema: boolean;
  dates: Dates;
}

export interface Entity {
  text: string;
  label: string;
}

export interface AgentStatusEvent {
  agent_id: string;
  agent: string;
  phase: string;
  detail: string | null;
  score: number | null;
  ts: number;
}

export interface AuditStartResponse {
  audit_id: string;
  agent_ids: Record<string, string>;
}

export interface Finding {
  id: string;
  title: string;
  severity: number;
  effort: string;
  impact: number;
  detail: string;
  fix: string;
  evidence: string;
  ref_url: string;
}

export interface CrawlReport {
  depth: number;
  url: string;
  reachable: boolean;
  js_dependent: boolean;
  bot_blocked: string | null;
  notable_links: string[];
  summary: string;
}

export interface TrafficSignal {
  domain_rank: number | null;
  cloudflare_visits_estimate: string | null;
  source: string;
}

export interface KGNode {
  id: string;
  label: string;
  type: string;
}

export interface KGEdge {
  source: string;
  target: string;
  relation: string;
}

export interface AgentResult {
  agent: string;
  score: number;
  sub_scores: Record<string, number>;
  findings: Finding[];
  artifacts: Record<string, unknown>;
  traffic_signal: TrafficSignal | null;
  crawl_reports: CrawlReport[];
  model_used: string;
  latency_ms: number;
  tokens: number;
}

export interface VisibilityEstimate {
  gpt: number;
  claude: number;
  perplexity: number;
  gemini: number;
}

export interface Visibility {
  before: VisibilityEstimate;
  after: VisibilityEstimate;
}

export interface SiteCoverage {
  has_schema_pct: number;
  js_rendered_pct: number;
  meta_desc_pct: number;
  author_date_pct: number;
}

export interface SiteSummary {
  ai_readiness_score: number;
  coverage: SiteCoverage;
  robots: Record<string, unknown>;
  sitemap: Record<string, unknown>;
  llms_txt: Record<string, unknown>;
  systemic_fixes: Finding[];
}

export interface PageResult {
  url: string;
  role: string;
  ai_readiness_score: number;
  category_scores: Record<string, number>;
  visibility: Visibility;
  fixes: Finding[];
  agent_results: AgentResult[];
}

export interface AuditReport {
  url: string;
  ai_readiness_score: number;
  scores: Record<string, number>;
  visibility: {
    before: VisibilityEstimate;
    after: VisibilityEstimate;
  };
  findings: Finding[];
  summary: string;
  generated_at?: string;
  mock?: boolean;
  // Rich backend format (from real agents-api pipeline)
  scope?: { deep_pages: number; shallow_pages: number };
  site?: SiteSummary;
  pages?: PageResult[];
}

export interface SiteFacts {
  url: string;
  final_url: string;
  fetched_at: string;
  http: HttpFacts;
  robots: RobotsFacts;
  sitemap: SitemapFacts;
  llms_txt: LlmsTxtFacts;
  render: RenderFacts;
  html: HtmlFacts;
  structured_data: StructuredDataFacts;
  links: LinkFacts;
  authorship: AuthorshipFacts;
  entities_raw: Entity[];
  markdown: string;
}
