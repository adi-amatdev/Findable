"use client";

import { useEffect, useRef, useState } from "react";
import { animate, stagger } from "animejs";
import type { AuditReport, Finding } from "../lib/types";
import { API_BASE } from "../lib/api";

function severityLabel(s: number): string {
  if (s >= 4) return "critical";
  if (s >= 3) return "high";
  if (s >= 2) return "medium";
  return "low";
}

function severityTone(s: number): "bad" | "warn" | "good" {
  if (s >= 3) return "bad";
  if (s >= 2) return "warn";
  return "good";
}

function effortLabel(e: string): string {
  if (e === "S") return "quick fix";
  if (e === "M") return "moderate";
  return "large";
}

function hostname(u: string): string {
  try {
    return new URL(u).hostname.replace(/^www\./, "");
  } catch {
    return u;
  }
}

const AGENT_INFO: Record<string, { name: string; color: string }> = {
  crawlability: { name: "Crawlability", color: "var(--good)" },
  content_signal: { name: "Content Signal", color: "var(--accent)" },
  structured_data: { name: "Structured Data", color: "var(--warn)" },
  entity_topic: { name: "Entity & Topic", color: "var(--gold-2)" },
};

function AnimatedScore({ score, size = 120 }: { score: number; size?: number }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obj = { v: 0 };
    animate(obj, {
      v: [0, score],
      duration: 1200,
      ease: "outCubic",
      onUpdate: () => {
        el.textContent = String(Math.round(obj.v));
      },
    });
  }, [score]);

  const r = size * 0.42;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score / 100);
  const tone = score >= 80 ? "var(--good)" : score >= 50 ? "var(--warn)" : "var(--bad)";

  return (
    <div className="score-gauge" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="6" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={tone}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="score-arc"
        />
      </svg>
      <span className="score-value" ref={ref}>
        0
      </span>
    </div>
  );
}

function ScoreBar({
  label,
  score,
  max = 100,
  color,
  delay = 0,
}: {
  label: string;
  score: number;
  max?: number;
  color?: string;
  delay?: number;
}) {
  const fillRef = useRef<HTMLDivElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const fill = fillRef.current;
    const lbl = labelRef.current;
    if (!fill) return;

    setTimeout(() => {
      animate(fill, {
        scaleX: [0, score / max],
        duration: 600,
        ease: "outCubic",
      });
      if (lbl) {
        const obj = { v: 0 };
        animate(obj, {
          v: [0, score],
          duration: 600,
          ease: "outCubic",
          onUpdate: () => {
            lbl.textContent = String(Math.round(obj.v));
          },
        });
      }
    }, delay);
  }, [score, max, delay]);

  const c = color || (score >= 80 ? "var(--good)" : score >= 50 ? "var(--warn)" : "var(--bad)");

  return (
    <div className="score-bar">
      <div className="score-bar-head">
        <span className="score-bar-label">{label}</span>
        <span className="score-bar-value" ref={labelRef}>0</span>
      </div>
      <div className="score-bar-track">
        <div
          className="score-bar-fill"
          ref={fillRef}
          style={{ background: c, transform: "scaleX(0)", transformOrigin: "left" }}
        />
      </div>
    </div>
  );
}

function FindingCard({ finding, index }: { finding: Finding; index: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    animate(el, {
      translateY: [16, 0],
      opacity: [0, 1],
      duration: 400,
      delay: index * 60,
      ease: "outCubic",
    });
  }, [index]);

  const tone = severityTone(finding.severity);

  return (
    <div className="finding-card" ref={ref}>
      <div className="finding-head">
        <span className={`finding-severity ${tone}`}>{severityLabel(finding.severity)}</span>
        <span className="finding-effort">{effortLabel(finding.effort)}</span>
        <span className="finding-id">{finding.id}</span>
      </div>
      <strong className="finding-title">{finding.title}</strong>
      <p className="finding-detail">{finding.detail}</p>
      <details className="finding-fix">
        <summary>Suggested fix</summary>
        <p>{finding.fix}</p>
        {finding.evidence && <p className="finding-evidence"><em>Evidence:</em> {finding.evidence}</p>}
        {finding.ref_url && (
          <a href={finding.ref_url} target="_blank" rel="noreferrer" className="finding-ref">
            Reference &rarr;
          </a>
        )}
      </details>
    </div>
  );
}

function VisibilityBlock({ visibility }: { visibility: AuditReport["visibility"] }) {
  const models = [
    { key: "gpt" as const, label: "GPT-4o" },
    { key: "claude" as const, label: "Claude" },
    { key: "perplexity" as const, label: "Perplexity" },
    { key: "gemini" as const, label: "Gemini" },
  ];

  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    animate(ref.current.querySelectorAll(".vis-bar-fill"), {
      scaleX: [0, 1],
      duration: 700,
      ease: "outCubic",
      delay: stagger(80),
    });
  }, []);

  const multipliers = models.map((m) => {
    const b = visibility.before[m.key];
    const a = visibility.after[m.key];
    return b > 0 ? a / b : a > 0 ? Infinity : 1;
  });
  const avgMultiplier =
    multipliers.filter(isFinite).reduce((s, x) => s + x, 0) /
    (multipliers.filter(isFinite).length || 1);

  return (
    <div className="visibility-block" ref={ref}>
      <h3 className="section-title">Visibility Analysis</h3>
      <p className="section-sub">
        Estimated likelihood each AI model finds and cites this page — before and after top fixes
      </p>
      <div className="vis-grid">
        {models.map((m, i) => {
          const before = visibility.before[m.key] * 100;
          const after = visibility.after[m.key] * 100;
          const mult = multipliers[i];
          return (
            <div className="vis-col" key={m.key}>
              <span className="vis-model">{m.label}</span>
              <div className="vis-bars">
                <div className="vis-bar">
                  <span className="vis-lbl">before</span>
                  <div className="vis-track">
                    <div
                      className="vis-bar-fill before"
                      style={{ width: `${before}%`, transform: "scaleX(0)", transformOrigin: "left" }}
                    />
                  </div>
                  <span className="vis-pct">{Math.round(before)}%</span>
                </div>
                <div className="vis-bar">
                  <span className="vis-lbl">after</span>
                  <div className="vis-track">
                    <div
                      className="vis-bar-fill after"
                      style={{ width: `${after}%`, transform: "scaleX(0)", transformOrigin: "left" }}
                    />
                  </div>
                  <span className="vis-pct">{Math.round(after)}%</span>
                </div>
              </div>
              <span className="vis-mult">
                {isFinite(mult) ? `${mult.toFixed(1)}x` : `+${Math.round(after)}pp`} improvement
              </span>
            </div>
          );
        })}
      </div>
      <div className="vis-avg">
        Average improvement across all AI platforms:&nbsp;
        <strong>{avgMultiplier.toFixed(1)}x</strong>
      </div>
    </div>
  );
}

function KnowledgeGraph({
  artifacts,
}: {
  artifacts: Record<string, unknown>;
}) {
  const kg = artifacts?.knowledge_graph as
    | { nodes: Array<{ id: string; label: string; type: string }>; edges: Array<{ source: string; target: string; relation: string }> }
    | undefined;

  if (!kg?.nodes?.length) return null;

  return (
    <div className="kg-block">
      <h3 className="section-title">Knowledge Graph</h3>
      <p className="section-sub">Entities identified on the page</p>
      <div className="kg-grid">
        {kg.nodes.map((n) => (
          <span className="kg-node" key={n.id}>
            <span className="kg-label">{n.label}</span>
            <span className="kg-type">{n.type}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function CoverageCard({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const tone = pct >= 80 ? "var(--good)" : pct >= 40 ? "var(--warn)" : "var(--bad)";
  return (
    <div className="coverage-card">
      <span className="cov-value" style={{ color: tone }}>{pct}%</span>
      <span className="cov-label">{label}</span>
    </div>
  );
}

export default function ReportDashboard({ report, auditId }: { report: AuditReport; auditId?: string }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [showAllFindings, setShowAllFindings] = useState(false);

  const score = report.ai_readiness_score ?? 0;

  useEffect(() => {
    if (!rootRef.current) return;
    animate(rootRef.current.querySelectorAll(".dashboard-section"), {
      translateY: [20, 0],
      opacity: [0, 1],
      delay: stagger(80),
      duration: 500,
      ease: "outCubic",
    });
  }, []);

  function handleDownloadMd() {
    let md = `# AI Readiness Audit Report\n\n`;
    md += `**Target:** ${report.url}  \n`;
    md += `**Score:** ${report.ai_readiness_score ?? "—"}/100  \n`;
    md += `**Date:** ${report.generated_at ? new Date(report.generated_at).toLocaleString() : "—"}\n\n`;
    md += `---\n\n`;
    if (report.summary) {
      md += `## Executive Summary\n\n${report.summary}\n\n---\n\n`;
    }
    if (report.scores) {
      md += `## Category Scores\n\n`;
      md += `| Category | Score |\n|----------|------:|\n`;
      for (const [id, s] of Object.entries(report.scores)) {
        md += `| ${AGENT_INFO[id]?.name || id} | ${s}/100 |\n`;
      }
      md += `\n---\n\n`;
    }
    if (report.visibility) {
      md += `## Visibility Analysis\n\n`;
      md += `| Platform | Before | After | Improvement |\n|----------|-------:|------:|------------:|\n`;
      for (const [platform, before] of Object.entries(report.visibility.before)) {
        const after = report.visibility.after[platform as keyof typeof report.visibility.after];
        const mult = before > 0 ? after / before : 0;
        const label = platform === "gpt" ? "GPT-4o" : platform.charAt(0).toUpperCase() + platform.slice(1);
        md += `| ${label} | ${(before * 100).toFixed(0)}% | ${(after * 100).toFixed(0)}% | ${mult > 0 ? mult.toFixed(1) + "x" : "—"} |\n`;
      }
      const vals = Object.entries(report.visibility.before).map(([p, b]) => {
        const a = report.visibility.after[p as keyof typeof report.visibility.after];
        return b > 0 ? a / b : 0;
      }).filter((x) => x > 0);
      const avg = vals.reduce((s, x) => s + x, 0) / (vals.length || 1);
      md += `\n> Average improvement: **${avg.toFixed(1)}x** across all AI platforms\n\n---\n\n`;
    }
    if (report.findings?.length) {
      md += `## Findings (${report.findings.length})\n\n`;
      for (const f of report.findings) {
        const sevLabel = f.severity >= 4 ? "Critical" : f.severity >= 3 ? "High" : f.severity >= 2 ? "Medium" : "Low";
        md += `### ${f.title}\n\n`;
        md += `- **Severity:** ${sevLabel} (${f.severity}/5)\n`;
        md += `- **Effort:** ${f.effort === "S" ? "Quick fix" : f.effort === "M" ? "Moderate" : "Large"}\n`;
        md += `- **Impact:** ${f.impact}/5\n\n`;
        if (f.detail) md += `${f.detail}\n\n`;
        if (f.fix) md += `**Recommendation:** ${f.fix}\n\n`;
        if (f.evidence) md += `*Evidence: ${f.evidence}*\n\n`;
        if (f.ref_url) md += `*Reference: ${f.ref_url}*\n\n`;
        md += `---\n\n`;
      }
    }
    md += `---\n*Generated by Findable — AI Readiness Audit*`;
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `findable-${hostname(report.url)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleDownloadPdf() {
    if (auditId) {
      // Backend-generated PDF — proper layout, all findings, verbose
      const a = document.createElement("a");
      a.href = `${API_BASE}/api/audit/${auditId}/pdf`;
      a.download = `findable-${hostname(report.url)}.pdf`;
      a.click();
    } else {
      // Fallback: browser print (no auditId available — e.g., pre-SSE fallback report)
      const win = window.open("", "_blank");
      if (!win) return;
      const vis = report.visibility;
      const visRows = vis
        ? Object.entries(vis.before).map(([k, v]) => {
            const a = vis.after[k as keyof typeof vis.after];
            const mult = v > 0 ? (a / v).toFixed(1) + "x" : "—";
            const label = k === "gpt" ? "GPT-4o" : k.charAt(0).toUpperCase() + k.slice(1);
            return `<tr><td>${label}</td><td>${(v * 100).toFixed(0)}%</td><td>${(a * 100).toFixed(0)}%</td><td>${mult}</td></tr>`;
          }).join("")
        : "";
      const findingsHtml = report.findings?.length
        ? `<h2>Findings (${report.findings.length})</h2>${report.findings.map((f) => {
            const sevLabel = f.severity >= 4 ? "Critical" : f.severity >= 3 ? "High" : f.severity >= 2 ? "Medium" : "Low";
            return `<div class="finding"><h3>${f.title}</h3><p class="meta">${sevLabel} &middot; ${f.effort === "S" ? "Quick fix" : f.effort === "M" ? "Moderate" : "Large"} &middot; Impact ${f.impact}/5</p>${f.detail ? `<p>${f.detail}</p>` : ""}${f.fix ? `<p><strong>Recommendation:</strong> ${f.fix}</p>` : ""}${f.evidence ? `<p><em>Evidence:</em> ${f.evidence}</p>` : ""}${f.ref_url ? `<p><a href="${f.ref_url}">${f.ref_url}</a></p>` : ""}</div>`;
          }).join("")}`
        : "";
      const agentRows = report.scores
        ? Object.entries(report.scores).map(([id, s]) => `<tr><td>${AGENT_INFO[id]?.name || id}</td><td>${s}/100</td></tr>`).join("")
        : "";
      win.document.write(`<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Findable Report — ${hostname(report.url)}</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#1a1a1a;line-height:1.6}
  h1{font-size:22px;border-bottom:2px solid #d4af37;padding-bottom:8px;margin-bottom:4px}
  h2{font-size:16px;margin-top:28px;margin-bottom:8px}
  table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13px}
  th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #ddd}
  th{background:#f7f7f7;font-weight:600}
  .finding{border:1px solid #e0e0e0;border-radius:6px;padding:12px 14px;margin:10px 0}
  .finding h3{margin:0 0 3px;font-size:14px}
  .meta{font-size:11px;color:#666;margin:0 0 8px}
  .score{font-size:52px;font-weight:700;color:#d4af37;margin:10px 0 4px}
  .footer{margin-top:36px;font-size:11px;color:#aaa;border-top:1px solid #eee;padding-top:10px}
  @media print{body{margin:0;padding:18px}}
</style></head><body>
<h1>Findable — AI Readiness Audit Report</h1>
<p style="font-size:13px;color:#555"><strong>Target:</strong> ${report.url}<br><strong>Date:</strong> ${report.generated_at ? new Date(report.generated_at).toLocaleString() : "—"}</p>
<div class="score">${report.ai_readiness_score ?? "—"}<span style="font-size:18px;color:#888;font-weight:400"> / 100</span></div>
${report.summary ? `<h2>Executive Summary</h2><p style="font-size:13px">${report.summary}</p>` : ""}
${agentRows ? `<h2>Category Scores</h2><table><tr><th>Category</th><th>Score</th></tr>${agentRows}</table>` : ""}
${visRows ? `<h2>Visibility Analysis</h2><table><tr><th>Platform</th><th>Before</th><th>After</th><th>Improvement</th></tr>${visRows}</table>` : ""}
${findingsHtml}
<div class="footer">Generated by Findable &mdash; AI Readiness Audit</div>
<script>window.print();window.close();</script>
</body></html>`);
      win.document.close();
    }
  }

  const allFindings: Finding[] = report.findings ?? [];
  const displayedFindings = showAllFindings ? allFindings : allFindings.slice(0, 5);

  const agentScores = report.scores
    ? Object.entries(report.scores).map(([id, s]) => ({
        id,
        ...(AGENT_INFO[id] || { name: id, color: "var(--accent)" }),
        score: s,
      }))
    : [];

  return (
    <div className="report-dashboard" ref={rootRef}>
      <div className="dashboard-section">
        <div className="report-header">
          <div className="report-url-row">
            <span className="report-url">{hostname(report.url)}</span>
            {report.generated_at && <span className="report-date">{new Date(report.generated_at).toLocaleString()}</span>}
          </div>
          <div className="report-toolbar">
            <button className="download-btn" onClick={handleDownloadMd}>
              Download MD
            </button>
            <button className="download-btn" onClick={handleDownloadPdf}>
              Download PDF
            </button>
          </div>
        </div>
      </div>

      <div className="dashboard-section">
        <div className="score-hero">
          <AnimatedScore score={score} />
          <div className="score-hero-text">
            <h2>AI Readiness Score</h2>
            <p className="score-summary">
              {score >= 80
                ? "Well optimised for AI discovery. Minor improvements can further strengthen your position."
                : score >= 50
                  ? "Moderate AI readiness. Addressing the findings below will significantly improve discoverability."
                  : "Poor AI readiness. Critical issues are preventing AI agents from properly understanding your content."}
            </p>
          </div>
        </div>
      </div>

      {report.summary && (
        <div className="dashboard-section">
          <div className="summary-card">
            <h3 className="section-title">Executive Summary</h3>
            <p className="summary-text">{report.summary}</p>
          </div>
        </div>
      )}

      {agentScores.length > 0 && (
        <div className="dashboard-section">
          <h3 className="section-title">Category Scores</h3>
          <div className="scores-strip">
            {agentScores.map((as, i) => (
              <ScoreBar
                key={as.id}
                label={as.name}
                score={as.score}
                delay={i * 80}
              />
            ))}
          </div>
        </div>
      )}

      {report.visibility && (
        <div className="dashboard-section">
          <VisibilityBlock visibility={report.visibility} />
        </div>
      )}

      {allFindings.length > 0 && (
        <div className="dashboard-section">
          <h3 className="section-title">
            Findings ({allFindings.length})
            {allFindings.length > 5 && !showAllFindings && (
              <button className="ghost-btn" onClick={() => setShowAllFindings(true)}>
                Show all
              </button>
            )}
          </h3>
          <div className="findings-list">
            {displayedFindings.map((f, i) => (
              <FindingCard key={f.id} finding={f} index={i} />
            ))}
          </div>
        </div>
      )}

      {report.site?.coverage && (
        <div className="dashboard-section">
          <h3 className="section-title">Site Coverage</h3>
          <p className="section-sub">Scan-level metrics across crawled pages</p>
          <div className="coverage-grid">
            <CoverageCard label="Schema markup" value={report.site.coverage.has_schema_pct} />
            <CoverageCard label="JS-rendered content" value={report.site.coverage.js_rendered_pct} />
            <CoverageCard label="Meta descriptions" value={report.site.coverage.meta_desc_pct} />
            <CoverageCard label="Author / date present" value={report.site.coverage.author_date_pct} />
          </div>
        </div>
      )}

      {report.pages?.map((page, pi) => (
        <div key={pi} className="dashboard-section">
          <h3 className="section-title">Agent Results — {page.role}</h3>
          <p className="section-sub">{page.url}</p>
          <div className="agent-results">
            {page.agent_results.map((ar, ai) => {
              const info = AGENT_INFO[ar.agent] || { name: ar.agent, color: "var(--accent)" };
              const kg = ar.artifacts?.knowledge_graph as
                | { nodes: Array<{ id: string; label: string; type: string }>; edges: Array<{ source: string; target: string; relation: string }> }
                | undefined;
              return (
                <div key={ai} className="agent-result-card" style={{ borderColor: ar.score >= 80 ? "var(--good)" : ar.score >= 50 ? "var(--warn)" : "var(--bad)" }}>
                  <div className="ar-head">
                    <span className="ar-name">{info.name}</span>
                    <span className="ar-score">{ar.score}/100</span>
                  </div>
                  {ar.sub_scores && Object.keys(ar.sub_scores).length > 0 && (
                    <div className="ar-subscores">
                      {Object.entries(ar.sub_scores).map(([k, v]) => (
                        <span key={k} className="ar-subscore">{k}: <strong>{v}</strong></span>
                      ))}
                    </div>
                  )}
                  <div className="ar-meta">
                    {ar.model_used !== "unknown" && <span>Model: {ar.model_used}</span>}
                    {ar.latency_ms > 0 && <span>Latency: {(ar.latency_ms / 1000).toFixed(1)}s</span>}
                    {ar.tokens > 0 && <span>Tokens: {ar.tokens.toLocaleString()}</span>}
                  </div>
                  {ar.findings && ar.findings.length > 0 && (
                    <div className="ar-findings">
                      {ar.findings.slice(0, 2).map((f) => (
                        <div key={f.id} className="ar-finding">{f.title}</div>
                      ))}
                      {ar.findings.length > 2 && <div className="ar-more">+{ar.findings.length - 2} more</div>}
                    </div>
                  )}
                  {kg && <KnowledgeGraph artifacts={ar.artifacts} />}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
