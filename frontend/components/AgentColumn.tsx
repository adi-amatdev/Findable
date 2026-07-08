"use client";

import { useEffect, useRef } from "react";
import type { AgentMeta } from "../lib/agents";

export type AgentPhase = "waiting" | "streaming" | "done" | "offline";

export interface AgentState {
  phase: AgentPhase;
  text: string;
  note?: string;
}

const PHASE_LABEL: Record<AgentPhase, string> = {
  waiting: "listening",
  streaming: "judging",
  done: "done",
  offline: "stream offline",
};

export default function AgentColumn({
  meta,
  state,
}: {
  meta: AgentMeta;
  state: AgentState;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);

  // Follow the stream as it grows.
  useEffect(() => {
    const el = bodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [state.text]);

  return (
    <div className={`agent-col phase-${state.phase}`} data-agent={meta.id}>
      <div className="agent-head">
        <span className={`status-dot ${state.phase}`} />
        <span className="agent-name">{meta.name}</span>
        <span className="agent-weight">{meta.weight}</span>
      </div>
      <p className="agent-role">{meta.role}</p>

      <div className="agent-body" ref={bodyRef}>
        {state.phase === "waiting" && (
          <div className="skeleton" aria-label="waiting for agent stream">
            <div className="bone w80" />
            <div className="bone w95" />
            <div className="bone w60" />
            <div className="bone w90" />
            <div className="bone w70" />
          </div>
        )}
        {state.phase === "offline" && (
          <p className="agent-note">{state.note}</p>
        )}
        {state.text && <pre className="agent-text">{state.text}</pre>}
      </div>

      <div className="agent-foot">{PHASE_LABEL[state.phase]}</div>
    </div>
  );
}
