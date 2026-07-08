// Small, dependency-free presentational primitives.

import type { ReactNode } from "react";

export type Tone = "good" | "bad" | "warn" | "neutral";

export function Card({
  title,
  hint,
  span,
  children,
}: {
  title: string;
  hint?: string;
  span?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={`card animate-in${span ? " span2" : ""}`}>
      <h3>{title}</h3>
      {hint ? <p className="hint">{hint}</p> : null}
      {children}
    </div>
  );
}

export function Stat({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="stat">
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

export function Chip({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  const cls = tone === "neutral" ? "chip" : `chip ${tone}`;
  return (
    <span className={cls}>
      {tone !== "neutral" ? <span className="dot" /> : null}
      {children}
    </span>
  );
}

export function Chips({ children }: { children: ReactNode }) {
  return <div className="chips">{children}</div>;
}

export function Bool({ value, yes = "yes", no = "no" }: { value: boolean; yes?: string; no?: string }) {
  return <Chip tone={value ? "good" : "bad"}>{value ? yes : no}</Chip>;
}

export function Meter({
  value,
  tone,
  caption,
}: {
  value: number; // 0..1
  tone: Tone;
  caption?: string;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const color =
    tone === "good"
      ? "var(--good)"
      : tone === "bad"
      ? "var(--bad)"
      : tone === "warn"
      ? "var(--warn)"
      : "var(--accent)";
  return (
    <div className="meter">
      <div className="label">
        <span className="big">{pct}%</span>
        {caption ? <span className="k" style={{ color: "var(--muted)" }}>{caption}</span> : null}
      </div>
      <div className="track">
        <div className="fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}
