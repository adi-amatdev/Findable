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
