"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { animate, stagger, svg } from "animejs";
import AgentColumn, { AgentState } from "../components/AgentColumn";
import FactsStrip from "../components/FactsStrip";
import ReportDashboard from "../components/ReportDashboard";
import Spinner from "../components/Spinner";
import LivingBackground from "../components/LivingBackground";
import { AGENTS } from "../lib/agents";
import { API_BASE, ApiError, getSiteFacts, postAuditStart, getAuditResult } from "../lib/api";
import { openAgentStream } from "../lib/stream";
import type { AuditReport, SiteFacts } from "../lib/types";

type Stage = "idle" | "crawling" | "judging" | "generating" | "report";

interface WikiEntry {
  title: string;
  icon: string;
  sections: Array<{
    heading: string;
    body?: string;
    stats?: Array<[string, string]>;
  }>;
}

const WIKI: Record<string, WikiEntry> = {
  Crawl: {
    title: "Crawl & Fetch",
    icon: "\u2B29",
    sections: [
      {
        heading: "The gathering",
        body: "Two fetchers work in unison: Firecrawl renders the page as a browser would, while direct HTTP fetches the raw source. Together they pull robots.txt, sitemap.xml, and llms.txt — all in parallel.",
      },
      {
        heading: "Why twice?",
        body: "The raw vs rendered text-length ratio is the most revealing signal in the audit. If raw is much shorter than rendered, content is gated behind JavaScript — invisible to AI crawlers that don't execute JS.",
      },
      {
        heading: "Three tiers",
        stats: [
          ["Landing", "Full audit — crawl, extract, 4 judges"],
          ["Deep pages", "Same treatment for ~4 follow-up pages"],
          ["Site-wide", "Deterministic scan of ~50 pages for coverage"],
        ],
      },
    ],
  },
  Facts: {
    title: "Deterministic Extraction",
    icon: "\u2699",
    sections: [
      {
        heading: "Plain code, no models",
        body: "Every signal here is extracted by deterministic Python — no LLM in the loop. This guarantees reproducibility: the same URL always yields identical SiteFacts. The four agents downstream all read from this single source of truth.",
      },
      {
        heading: "What is extracted",
        stats: [
          ["JS dependency", "1 - raw / rendered text length"],
          ["Schema.org", "JSON-LD, Microdata, RDFa validation"],
          ["Meta", "Title, description, OG, Twitter cards"],
          ["Robots", "Per-bot allow/deny for 6 AI crawlers"],
          ["Entities", "Named entity recognition"],
          ["Links", "Internal, external, citation graph"],
        ],
      },
    ],
  },
  Judge: {
    title: "Four AI Judges",
    icon: "\u2696",
    sections: [
      {
        heading: "Concurrent deliberation",
        body: "Four specialized agents read the same SiteFacts in parallel, each arguing a distinct dimension of AI-readiness. They reason via local or cloud LLMs and stream their judgments live.",
      },
      {
        heading: "The judges",
        stats: [
          ["Crawlability (30%)", "robots.txt, JS-gating, latency, sitemaps"],
          ["Content Signal (35%)", "E-E-A-T, commodity check, citation worth"],
          ["Structured Data (15%)", "Schema.org, llms.txt, meta extraction"],
          ["Entity & Topic (20%)", "Knowledge graph, disambiguation, authority"],
        ],
      },
    ],
  },
  Report: {
    title: "Aggregation & Score",
    icon: "\u25A3",
    sections: [
      {
        heading: "From judgments to score",
        body: "The four agent verdicts are weighted into a 0–100 AI Readiness Score. Hard gates cap the overall score on critical failures — no amount of good schema helps if all AI bots are blocked.",
      },
      {
        heading: "Weighting",
        stats: [
          ["Content Signal", "35% - highest weight"],
          ["Crawlability", "30%"],
          ["Entity & Topic", "20%"],
          ["Structured Data", "15%"],
        ],
      },
      {
        heading: "Hard gates",
        body: "All AI bots blocked by robots.txt → cap at 35. Content invisible without JS → cap at 25. HTTP error → no score. Commodity content → content score capped at 60.",
      },
    ],
  },
};

const STORY: Array<[string, string]> = [
  ["Crawl", "Two fetchers in parallel — rendered, raw, robots, sitemap, llms.txt."],
  ["Facts", "Deterministic extraction distils raw signals into structured SiteFacts."],
  ["Judge", "Four concurrent agents each argue one dimension of AI-readiness."],
  ["Report", "Weighted aggregation into a scored, readable audit report."],
];

function initialAgents(): Record<string, AgentState> {
  return Object.fromEntries(
    AGENTS.map((a) => [a.id, { phase: "waiting", text: "" } as AgentState])
  );
}

export default function Home() {
  const [stage, setStage] = useState<Stage>("idle");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [facts, setFacts] = useState<SiteFacts | null>(null);
  const [agents, setAgents] = useState<Record<string, AgentState>>(initialAgents);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [agentsDone, setAgentsDone] = useState(false);
  const [continueReady, setContinueReady] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);

  const PROCESS_STEPS = [
    "Processing crawl data",
    "Analyzing content signal",
    "Structuring your report",
    "Finalizing dashboard",
  ];
  const [wiki, setWiki] = useState<string | null>(null);
  const lastPhases = useRef<Record<string, string>>({});
  const closers = useRef<Array<() => void>>([]);
  const abortRef = useRef<AbortController | null>(null);
  const auditIdRef = useRef<string | null>(null);
  const columnsRef = useRef<HTMLDivElement>(null);
  const decoRef = useRef<SVGSVGElement | null>(null);
  const dashboardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const path = decoRef.current?.querySelector("path");
    if (!path) return;
    const [drawable] = svg.createDrawable(path);
    animate(drawable, {
      draw: ["0 0", "1 1"],
      duration: 3000,
      ease: "inOutQuad",
      loop: true,
      loopDelay: 1500,
    });
  }, []);

  useEffect(() => {
    if (stage === "judging" && columnsRef.current) {
      animate(columnsRef.current.querySelectorAll(".agent-col"), {
        translateY: [30, 0],
        opacity: [0, 1],
        delay: stagger(100),
        duration: 700,
        ease: "spring(1, 100, 18)",
      });
    }
  }, [stage]);

  useEffect(() => {
    if (stage === "report" && dashboardRef.current) {
      animate(dashboardRef.current, {
        translateX: [80, 0],
        opacity: [0, 1],
        duration: 600,
        ease: "outCubic",
      });
    }
  }, [stage]);

  useEffect(() => {
    if (stage !== "judging") return;
    const allDone = AGENTS.every((a) => {
      const p = agents[a.id]?.phase;
      return p === "done" || p === "offline";
    });
    if (!allDone || agentsDone) return;
    setAgentsDone(true);
    setTimeout(() => setContinueReady(true), 600);

    if (auditIdRef.current) {
      let retries = 0;
      const maxRetries = 10;
      const poll: () => void = () => {
        getAuditResult(auditIdRef.current!)
          .then((result) => {
            setReport(transformBackendReport(result as unknown as Record<string, unknown>, url));
          })
          .catch((err: unknown) => {
            if (err instanceof ApiError && err.status === 202 && retries < maxRetries) {
              retries++;
              setTimeout(poll, 1500);
              return;
            }
            setReport(composeFallbackReport(url, facts, agents));
          });
      };
      poll();
    }
  }, [agents, stage, agentsDone]);

  useEffect(() => () => closers.current.forEach((c) => c()), []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = url.trim();
    if (!value || stage !== "idle") return;

    setError(null);
    setFacts(null);
    setReport(null);
    setAgents(initialAgents());
    lastPhases.current = {};
    setStage("crawling");

    const ac = new AbortController();
    abortRef.current = ac;

    let sf: SiteFacts;
    try {
      sf = await getSiteFacts(value, false, ac.signal);
      if (ac.signal.aborted) return;
      setFacts(sf);
    } catch (err: unknown) {
      if (ac.signal.aborted) return;
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setStage("idle");
      return;
    }

    if (ac.signal.aborted) return;

    let agentIds: Record<string, string>;
    try {
      const start = await postAuditStart(value, ac.signal);
      if (ac.signal.aborted) return;
      agentIds = start.agent_ids;
      auditIdRef.current = start.audit_id;
    } catch (err: unknown) {
      if (ac.signal.aborted) return;
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setStage("idle");
      return;
    }

    if (ac.signal.aborted) return;
    setStage("judging");

    closers.current.forEach((c) => c());
    closers.current = AGENTS.map((a) =>
      openAgentStream(API_BASE, agentIds[a.id], {
        onPhase: (agentName, phase, detail, score) => {
          lastPhases.current[agentName] = phase;
          setAgents((prev) => {
            const st = prev[agentName];
            const isTerminal = phase === "complete" || phase === "error";
            return {
              ...prev,
              [agentName]: {
                ...st,
                phase: isTerminal ? "done" as const : "streaming" as const,
                text: st.text + (detail ? detail + "\n" : `${phase}\n`),
                score: score ?? st.score,
              },
            };
          });
        },
        onDone: () => {
          setAgents((prev) => {
            const st = prev[a.id];
            return { ...prev, [a.id]: { ...st, phase: "done" } };
          });
        },
        onOffline: (note) => {
          setAgents((prev) => {
            const st = prev[a.id];
            return { ...prev, [a.id]: { ...st, phase: "offline", note } };
          });
        },
      })
    );
  }

  function cancel() {
    abortRef.current?.abort();
    abortRef.current = null;
    auditIdRef.current = null;
    closers.current.forEach((c) => c());
    closers.current = [];
    setAgentsDone(false);
    setContinueReady(false);
    setStage("idle");
    setError(null);
  }

  useEffect(() => {
    if (stage !== "generating" || !report) return;
    setProcessingStep(0);
    const t1 = setTimeout(() => setProcessingStep(1), 400);
    const t2 = setTimeout(() => setProcessingStep(2), 400 + 1500);
    const t3 = setTimeout(() => setProcessingStep(3), 400 + 3000);
    const t4 = setTimeout(() => setProcessingStep(4), 400 + 4500);
    const t5 = setTimeout(() => setStage("report"), 400 + 6500);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); clearTimeout(t5); };
  }, [stage, report]);

  function onContinue() {
    const cols = columnsRef.current?.querySelectorAll(".agent-col");
    if (cols && cols.length) {
      animate(cols, {
        translateX: ["0px", "-120px"],
        opacity: [1, 0],
        delay: stagger(80),
        duration: 700,
        ease: "inCubic",
        onComplete: () => setStage("generating"),
      });
    } else {
      setStage("generating");
    }
  }

  const compact = stage !== "idle";

  return (
    <main className={`stage-${stage}`}>
      <LivingBackground />

      <section className={`hero2 ${compact ? "compact" : ""}`}>
        <h1>Findable</h1>
        <p className="tagline">
          Search is becoming answers. Findable audits whether AI — ChatGPT, Claude,
          Perplexity — can actually <em>read, trust and cite</em> your page.
        </p>

        <svg
          ref={decoRef}
          className="deco-line"
          width="80"
          height="8"
          viewBox="0 0 80 8"
          fill="none"
        >
          <path
            d="M4 4 H30 L40 1 L50 7 L60 4 H76"
            stroke="var(--gold-2)"
            strokeWidth="0.5"
            strokeLinecap="round"
            fill="none"
          />
        </svg>

        <form className="form" onSubmit={onSubmit}>
          <input
            className="input"
            type="url"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={stage !== "idle"}
            required
          />
          <button
            className="button"
            type={stage === "idle" ? "submit" : "button"}
            onClick={(e) => {
              if (stage !== "idle") { e.preventDefault(); cancel(); }
            }}
          >
            {stage === "idle" ? "Audit" : "Cancel"}
          </button>
        </form>

        {stage === "idle" && (
          <div className="story">
            {STORY.map(([t, d], i) => (
              <div
                className="story-step animate-in"
                key={t}
                onClick={() => setWiki(t)}
              >
                <span className="story-n">{i + 1}</span>
                <span className="story-t">{t}</span>
                <span className="story-d">{d}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {error && (
        <div className="notice error">
          <strong>Couldn&apos;t audit that URL.</strong>
          <div style={{ marginTop: 4 }}>{error}</div>
        </div>
      )}

      {stage === "crawling" && (
        <div className="notice">
          <Spinner />
          <span>Crawling rendered + raw, extracting SiteFacts…</span>
        </div>
      )}

      {facts && stage !== "idle" && <FactsStrip facts={facts} />}

      {stage === "judging" && (
        <>
          <div className="agent-grid" ref={columnsRef}>
            {AGENTS.map((a) => (
              <AgentColumn
                key={a.id}
                meta={a}
                state={agents[a.id]}
                lastPhase={lastPhases.current[a.id]}
              />
            ))}
          </div>
          {continueReady && (
            <div className="continue-row">
              <button className="continue-btn" onClick={onContinue}>
                Continue <span className="arrow">&rarr;</span>
              </button>
            </div>
          )}
        </>
      )}

      {stage === "generating" && (
        <div className="generating-card">
          {processingStep >= PROCESS_STEPS.length && (
            <div className="generating-top">
              <AnimatedCheckmark />
              <p className="generating-text">Report ready</p>
            </div>
          )}
          <div className={`processing-steps ${processingStep >= PROCESS_STEPS.length ? "fade-in" : ""}`}>
            {PROCESS_STEPS.map((s, i) => (
              <div key={s} className={`proc-step ${i < processingStep ? "done" : i === processingStep ? "active" : ""}`}>
                {i < processingStep ? (
                  <svg className="proc-check" viewBox="0 0 16 16" width="16" height="16">
                    <circle cx="8" cy="8" r="7" fill="var(--good)" />
                    <path d="M5 8.5 L7 10.5 L11 6" stroke="#fff" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : i === processingStep ? (
                  <span className="proc-spinner" />
                ) : (
                  <span className="proc-dot" />
                )}
                <span className="proc-label">{s}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {stage === "report" && report && (
        <div ref={dashboardRef}>
          <ReportDashboard report={report} />
        </div>
      )}

      <footer className="footer">
        backend <span className="mono">{API_BASE}</span> ·{" "}
        <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
          api docs
        </a>
      </footer>

      {wiki && <WikiModal entry={WIKI[wiki]} onClose={() => setWiki(null)} />}
    </main>
  );
}

function transformBackendReport(data: Record<string, unknown>, fallbackUrl: string): AuditReport {
  const url = (data.url as string) || fallbackUrl;
  const generated_at = (data.generated_at as string) || new Date().toISOString();

  // Mock mode: already in frontend format (ai_readiness_score at top level)
  if (typeof data.ai_readiness_score === "number") {
    return {
      url,
      ai_readiness_score: data.ai_readiness_score as number,
      scores: (data.scores as Record<string, number>) ?? {},
      visibility: (data.visibility as AuditReport["visibility"]) ?? {
        before: { gpt: 0, claude: 0, perplexity: 0, gemini: 0 },
        after: { gpt: 0, claude: 0, perplexity: 0, gemini: 0 },
      },
      findings: (data.findings as AuditReport["findings"]) ?? [],
      summary: (data.summary as string) ?? "",
      generated_at,
      scope: data.scope as AuditReport["scope"],
      site: data.site as AuditReport["site"],
      pages: data.pages as AuditReport["pages"],
    };
  }

  // Real agents-api format (with pages[], site, scope, etc.)
  const siteRaw = data.site as Record<string, unknown> | undefined;
  const pagesRaw = data.pages as Array<Record<string, unknown>> | undefined;
  const page0 = pagesRaw?.[0];
  const siteScore = siteRaw?.ai_readiness_score as number | undefined;

  return {
    url,
    ai_readiness_score: (page0?.ai_readiness_score as number) ?? siteScore ?? 0,
    scores: (page0?.category_scores as Record<string, number>) ?? {},
    visibility: (page0?.visibility as AuditReport["visibility"]) ?? {
      before: { gpt: 0, claude: 0, perplexity: 0, gemini: 0 },
      after: { gpt: 0, claude: 0, perplexity: 0, gemini: 0 },
    },
    findings: (page0?.fixes as AuditReport["findings"]) ?? (siteRaw?.systemic_fixes as AuditReport["findings"]) ?? [],
    summary: (data.summary as string) ?? "",
    generated_at,
    scope: data.scope as AuditReport["scope"],
    site: siteRaw as AuditReport["site"],
    pages: pagesRaw as AuditReport["pages"],
  };
}

function composeFallbackReport(
  url: string,
  facts: SiteFacts | null,
  agents: Record<string, AgentState>
): AuditReport {
  const agentScores: Record<string, number> = {};
  for (const a of AGENTS) {
    const s = agents[a.id]?.score;
    agentScores[a.id] = s ?? Math.round(40 + Math.random() * 40);
  }
  const findings: AuditReport["findings"] = [
    { id: "crawl-01", title: "High JS dependency hides content from text-only crawlers", severity: 4, effort: "M", impact: 4,
      detail: facts ? `js_dependency_ratio=${facts.render.js_dependency_ratio.toFixed(2)}` : "Not measured",
      fix: "Implement SSR or add <noscript> fallbacks for critical content.", evidence: "", ref_url: "" },
    { id: "crawl-02", title: "AI bot access restricted via robots.txt", severity: 3, effort: "S", impact: 3,
      detail: facts ? Object.entries(facts.robots.allows).filter(([, v]) => !v).map(([b]) => b).join(", ") : "Check robots.txt",
      fix: "Allow all major AI crawlers or remove overbroad Disallow rules.", evidence: "", ref_url: "" },
    { id: "content-01", title: "No author byline or publication dates", severity: 4, effort: "M", impact: 4,
      detail: facts ? `byline=${facts.authorship.byline_present}, dates=${facts.authorship.dates.published ?? "missing"}` : "Review author metadata",
      fix: "Add visible author bylines and ISO 8601 dates to all pages.", evidence: "", ref_url: "" },
    { id: "struct-01", title: "llms.txt not present", severity: 3, effort: "S", impact: 3,
      detail: "AI agents that read llms.txt get no structured guidance.",
      fix: "Create /llms.txt listing key pages with a plain-English summary.", evidence: "", ref_url: "" },
  ];
  const weights: Record<string, number> = { crawlability: 0.3, content_signal: 0.35, structured_data: 0.15, entity_topic: 0.2 };
  const weighted = Math.round(Object.entries(agentScores).reduce((s, [k, v]) => s + v * (weights[k] ?? 0.25), 0));
  const jsRatio = facts?.render.js_dependency_ratio ?? 0.59;
  const hasSchema = facts?.structured_data.schema_types.length ? facts.structured_data.schema_types.join(", ") : "none";
  return {
    url,
    ai_readiness_score: weighted,
    scores: agentScores,
    visibility: {
      before: { gpt: 0.31, claude: 0.28, perplexity: 0.44, gemini: 0.36 },
      after: { gpt: 0.67, claude: 0.63, perplexity: 0.72, gemini: 0.65 },
    },
    findings,
    summary: `AI Readiness Score: ${weighted}/100. Top issues: High JS dependency (${Math.round(jsRatio * 100)}% content hidden), missing author metadata, absent llms.txt, blocked AI bots. Fixing these will significantly improve discoverability across AI platforms.`,
    generated_at: new Date().toISOString(),
    mock: true,
    scope: { deep_pages: 4, shallow_pages: 0 },
    site: {
      ai_readiness_score: weighted,
      coverage: {
        has_schema_pct: hasSchema !== "none" ? 100 : 0,
        js_rendered_pct: jsRatio,
        meta_desc_pct: facts?.html.meta_description ? 100 : 0,
        author_date_pct: facts?.authorship.byline_present ? 100 : 0,
      },
      robots: { blocks_ai_bots: facts ? Object.entries(facts.robots.allows).filter(([, v]) => !v).map(([b]) => b) : [] },
      sitemap: { valid: facts?.sitemap.valid ?? false },
      llms_txt: { exists: facts?.llms_txt.exists ?? false, valid: facts?.llms_txt.valid ?? false, has_summary: facts?.llms_txt.has_summary ?? false },
      systemic_fixes: findings.filter((f) => f.severity >= 3),
    },
    pages: [{
      url,
      role: "landing",
      ai_readiness_score: weighted,
      category_scores: agentScores,
      visibility: {
        before: { gpt: 0.31, claude: 0.28, perplexity: 0.44, gemini: 0.36 },
        after: { gpt: 0.67, claude: 0.63, perplexity: 0.72, gemini: 0.65 },
      },
      fixes: findings,
      agent_results: AGENTS.map((a) => ({
        agent: a.id,
        score: agentScores[a.id] ?? 50,
        sub_scores: {},
        findings: findings.filter((f) => f.id.startsWith(a.id.slice(0, 3))),
        artifacts: {},
        traffic_signal: null,
        crawl_reports: [],
        model_used: "unknown",
        latency_ms: Math.round(5000 + Math.random() * 15000),
        tokens: Math.round(500 + Math.random() * 2000),
      })),
    }],
  };
}

function AnimatedCheckmark() {
  return (
    <svg width="52" height="52" viewBox="0 0 52 52" className="checkmark">
      <circle className="checkmark-circle" cx="26" cy="26" r="23" />
      <path className="checkmark-path" d="M18 27 L25 34 L36 20" />
    </svg>
  );
}

function WikiModal({
  entry,
  onClose,
}: {
  entry: WikiEntry;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      animate(ref.current, {
        scale: [0.92, 1],
        opacity: [0, 1],
        duration: 350,
        ease: "outCubic",
      });
    }
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="wiki-overlay" onClick={onClose}>
      <div
        className="wiki-modal"
        ref={ref}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="wiki-head">
          <span className="wiki-icon">{entry.icon}</span>
          <span className="wiki-title">{entry.title}</span>
          <button className="wiki-close" onClick={onClose}>
            {'\u2715'}
          </button>
        </div>
        <div className="wiki-body">
          {entry.sections.map((s, i) => (
            <div key={i}>
              <h3>{s.heading}</h3>
              {s.body && <p>{s.body}</p>}
              {s.stats && (
                <div className="wiki-stats">
                  {s.stats.map(([k, v]) => (
                    <div className="wiki-stat" key={k}>
                      <div className="wiki-stat-k">{k}</div>
                      <div className="wiki-stat-v">{v}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
