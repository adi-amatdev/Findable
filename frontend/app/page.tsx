"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import anime from "animejs";
import AgentColumn, { AgentState } from "../components/AgentColumn";
import FactsStrip from "../components/FactsStrip";
import ReportBar from "../components/ReportBar";
import { AGENTS } from "../lib/agents";
import { API_BASE, getSiteFacts } from "../lib/api";
import { openAgentStream } from "../lib/stream";
import type { SiteFacts } from "../lib/types";

type Stage = "idle" | "crawling" | "judging" | "report";

const STORY: Array<[string, string]> = [
  ["Crawl", "We fetch the page twice — rendered and raw — plus robots.txt, sitemap and llms.txt."],
  ["Facts", "Plain code distils it into SiteFacts: deterministic, reproducible, no model in the loop."],
  ["Judge", "Four agents read the same facts in parallel and argue their dimension of AI-readiness."],
  ["Report", "Their findings aggregate into one scored report you can read, share, or export."],
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
  const closers = useRef<Array<() => void>>([]);
  const columnsRef = useRef<HTMLDivElement>(null);

  const patchAgent = useCallback((id: string, patch: Partial<AgentState>) => {
    setAgents((prev) => ({ ...prev, [id]: { ...prev[id], ...patch } }));
  }, []);

  // Stagger the columns in when judging begins.
  useEffect(() => {
    if (stage === "judging" && columnsRef.current) {
      anime({
        targets: columnsRef.current.querySelectorAll(".agent-col"),
        translateY: [26, 0],
        opacity: [0, 1],
        delay: anime.stagger(90),
        duration: 620,
        easing: "cubicBezier(0.22, 1, 0.36, 1)",
      });
    }
  }, [stage]);

  // When every agent reaches a terminal phase, collapse into the report chip.
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
      anime({
        targets: cols,
        translateY: [0, 18],
        opacity: [1, 0],
        scale: [1, 0.96],
        delay: anime.stagger(70),
        duration: 420,
        easing: "easeInCubic",
        complete: finish,
      });
    } else {
      finish();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agents, stage]);

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

    try {
      const sf = await getSiteFacts(value, false);
      setFacts(sf);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setStage("idle");
      return;
    }

    setStage("judging");

    // One stream per judge — GET {API_BASE}/agent/stream/{agent_id}.
    closers.current.forEach((c) => c());
    closers.current = AGENTS.map((a) =>
      openAgentStream(API_BASE, a.id, {
        onToken: (text) =>
          setAgents((prev) => ({
            ...prev,
            [a.id]: { ...prev[a.id], phase: "streaming", text: prev[a.id].text + text },
          })),
        onDone: () => patchAgent(a.id, { phase: "done" }),
        onOffline: (note) => patchAgent(a.id, { phase: "offline", note }),
      })
    );
  }

  const compact = stage !== "idle";

  return (
    <main className={`stage-${stage}`}>
      <section className={`hero2 ${compact ? "compact" : ""}`}>
        <h1>Findable</h1>
        <p className="tagline">
          Search is becoming answers. Findable audits whether AI — ChatGPT, Claude,
          Perplexity — can actually <em>read, trust and cite</em> your page.
        </p>

        <form className="form" onSubmit={onSubmit}>
          <input
            className="input"
            type="url"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
          <button className="button" type="submit" disabled={stage === "crawling"}>
            {stage === "crawling" ? "Crawling…" : "Audit"}
          </button>
        </form>

        {stage === "idle" && (
          <div className="story">
            {STORY.map(([t, d], i) => (
              <div className="story-step animate-in" key={t}>
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
          <span className="spinner" /> &nbsp; Crawling rendered + raw, extracting SiteFacts…
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
        <ReportBar filename={reportFilename(facts?.final_url || url)} markdown={report} />
      )}

      <footer className="footer">
        backend <span className="mono">{API_BASE}</span> ·{" "}
        <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">api docs</a>
      </footer>
    </main>
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
  lines.push(`# Findable — AI Readiness Report`);
  lines.push(``, `**Target:** ${target}`, `**Fetched:** ${facts?.fetched_at || "—"}`, ``);

  if (facts) {
    const blocked = Object.entries(facts.robots.allows)
      .filter(([, ok]) => ok === false)
      .map(([bot]) => bot);
    lines.push(`## Ground truth (SiteFacts)`, ``);
    lines.push(`- HTTP ${facts.http.status}, ${facts.http.latency_ms} ms`);
    lines.push(`- AI bots blocked: ${blocked.length ? blocked.join(", ") : "none"}`);
    lines.push(`- JS-gated content: ${Math.round(facts.render.js_dependency_ratio * 100)}%`);
    lines.push(`- Schema types: ${facts.structured_data.schema_types.join(", ") || "none"}`);
    lines.push(`- Word count: ${facts.html.word_count} · Language: ${facts.html.lang || "—"}`);
    lines.push(`- llms.txt: ${facts.llms_txt.exists ? "present" : "absent"} · Sitemap URLs: ${facts.sitemap.url_count}`);
    lines.push(``);
  }

  lines.push(`## Agent judgments`, ``);
  for (const a of AGENTS) {
    const st = agents[a.id];
    lines.push(`### ${a.name} (${a.weight})`, ``);
    if (st?.text) lines.push(st.text.trim(), ``);
    else if (st?.phase === "offline")
      lines.push(`_Stream not yet live — judgment pending backend rollout._`, ``);
    else lines.push(`_No output._`, ``);
  }

  lines.push(`---`, `_Generated by Findable. Deterministic facts, agent judgment on top._`);
  return lines.join("\n");
}
