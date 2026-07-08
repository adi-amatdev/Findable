"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { animate, stagger, svg } from "animejs";
import AgentColumn, { AgentState } from "../components/AgentColumn";
import FactsStrip from "../components/FactsStrip";
import ReportBar from "../components/ReportBar";
import Spinner from "../components/Spinner";
import LivingBackground from "../components/LivingBackground";
import { AGENTS } from "../lib/agents";
import { API_BASE, getSiteFacts } from "../lib/api";
import { openAgentStream } from "../lib/stream";
import type { SiteFacts } from "../lib/types";

type Stage = "idle" | "crawling" | "judging" | "report";

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
  const [report, setReport] = useState<string | null>(null);
  const [wiki, setWiki] = useState<string | null>(null);
  const closers = useRef<Array<() => void>>([]);
  const abortRef = useRef<AbortController | null>(null);
  const columnsRef = useRef<HTMLDivElement>(null);
  const decoRef = useRef<SVGSVGElement | null>(null);

  const patchAgent = useCallback((id: string, patch: Partial<AgentState>) => {
    setAgents((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  }, []);

  // Animate decorative line under hero
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

  // Stagger columns in
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

  // Collapse when all settled
  useEffect(() => {
    if (stage !== "judging") return;
    const states = AGENTS.map((a) => agents[a.id]?.phase);
    const settled = states.every((p) => p === "done" || p === "offline");
    if (!settled) return;

    const cols = columnsRef.current?.querySelectorAll(".agent-col");
    const finish = () => {
      setReport(composeReport(facts, agents));
      setStage("report");
    };
    if (cols && cols.length) {
      animate(cols, {
        translateY: [0, 20],
        opacity: [1, 0],
        scale: [1, 0.95],
        delay: stagger(80),
        duration: 450,
        ease: "easeInCubic",
        complete: finish,
      });
    } else {
      finish();
    }
  }, [agents, stage, facts]);

  // Animate report chip entrance
  useEffect(() => {
    if (stage !== "report") return;
    const chip = document.querySelector(".report-chip");
    if (chip) {
      animate(chip, {
        translateY: [28, 0],
        opacity: [0, 1],
        scale: [0.92, 1],
        duration: 700,
        ease: "spring(1, 80, 14)",
      });
    }
  }, [stage]);

  useEffect(() => () => closers.current.forEach((c) => c()), []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = url.trim();
    if (!value || stage === "crawling") return;

    setError(null);
    setFacts(null);
    setReport(null);
    setAgents(initialAgents());
    setStage("crawling");

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      const sf = await getSiteFacts(value, false, ac.signal);
      if (ac.signal.aborted) return;
      setFacts(sf);
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
      openAgentStream(API_BASE, a.id, {
        onToken: (text) =>
          setAgents((prev) => ({
            ...prev,
            [a.id]: {
              ...prev[a.id],
              phase: "streaming",
              text: prev[a.id].text + text,
            },
          })),
        onDone: () => patchAgent(a.id, { phase: "done" }),
        onOffline: (note) => patchAgent(a.id, { phase: "offline", note }),
      })
    );
  }

  function cancel() {
    abortRef.current?.abort();
    abortRef.current = null;
    closers.current.forEach((c) => c());
    closers.current = [];
    setStage("idle");
    setError(null);
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
            disabled={stage === "crawling" || stage === "judging"}
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
        <div className="agent-grid" ref={columnsRef}>
          {AGENTS.map((a) => (
            <AgentColumn key={a.id} meta={a} state={agents[a.id]} />
          ))}
        </div>
      )}

      {stage === "report" && report && (
        <ReportBar
          filename={reportFilename(facts?.final_url || url)}
          markdown={report}
        />
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

function reportFilename(u: string): string {
  try {
    return `findable-report-${new URL(u).hostname.replace(/^www\./, "")}.md`;
  } catch {
    return "findable-report.md";
  }
}

function composeReport(
  facts: SiteFacts | null,
  agents: Record<string, AgentState>
): string {
  const lines: string[] = [];
  const target = facts?.final_url || facts?.url || "unknown";
  lines.push("# Findable \u2014 AI Readiness Report");
  lines.push(
    "",
    `**Target:** ${target}`,
    `**Fetched:** ${facts?.fetched_at || "\u2014"}`,
    ""
  );

  if (facts) {
    const blocked = Object.entries(facts.robots.allows)
      .filter(([, ok]) => ok === false)
      .map(([bot]) => bot);
    lines.push("## Ground truth (SiteFacts)", "");
    lines.push(`- HTTP ${facts.http.status}, ${facts.http.latency_ms} ms`);
    lines.push(
      `- AI bots blocked: ${blocked.length ? blocked.join(", ") : "none"}`
    );
    lines.push(
      `- JS-gated content: ${Math.round(facts.render.js_dependency_ratio * 100)}%`
    );
    lines.push(
      `- Schema types: ${facts.structured_data.schema_types.join(", ") || "none"}`
    );
    lines.push(
      `- Word count: ${facts.html.word_count} \u00B7 Language: ${facts.html.lang || "\u2014"}`
    );
    lines.push(
      `- llms.txt: ${facts.llms_txt.exists ? "present" : "absent"} \u00B7 Sitemap URLs: ${facts.sitemap.url_count}`
    );
    lines.push("");
  }

  lines.push("## Agent judgments", "");
  for (const a of AGENTS) {
    const st = agents[a.id];
    lines.push(`### ${a.name} (${a.weight})`, "");
    if (st?.text) lines.push(st.text.trim(), "");
    else if (st?.phase === "offline")
      lines.push(
        "_Stream not yet live \u2014 judgment pending backend rollout._",
        ""
      );
    else lines.push("_No output._", "");
  }

  lines.push(
    "---",
    "_Generated by Findable. Deterministic facts, agent judgment on top._"
  );
  return lines.join("\n");
}
