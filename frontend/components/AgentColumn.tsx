"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";
import type { AgentMeta } from "../lib/agents";

export type AgentPhase = "waiting" | "streaming" | "done" | "offline";

export interface AgentState {
  phase: AgentPhase;
  text: string;
  note?: string;
  score?: number;
}

const PHASE_LABEL: Record<string, string> = {
  waiting: "listening",
  started: "starting",
  building_prompt: "preparing prompt",
  llm_call: "querying model",
  retry: "retrying",
  parsing_result: "parsing",
  sub_agent_pass_1: "sub-agent pass 1",
  sub_agent_pass_2: "sub-agent pass 2",
  sub_agent_pass_3: "sub-agent pass 3",
  judgment_call: "judgment call",
  applying_hard_gates: "applying gates",
  complete: "done",
  error: "error",
  streaming: "judging",
  done: "done",
  offline: "offline",
};

const PHASE_PROGRESS: Record<string, number> = {
  waiting: 0,
  started: 0.1,
  building_prompt: 0.25,
  llm_call: 0.4,
  retry: 0.35,
  parsing_result: 0.55,
  sub_agent_pass_1: 0.6,
  sub_agent_pass_2: 0.7,
  sub_agent_pass_3: 0.8,
  judgment_call: 0.9,
  applying_hard_gates: 0.95,
  complete: 1,
  error: 1,
  streaming: 0.5,
  done: 1,
  offline: 1,
};

export default function AgentColumn({
  meta,
  state,
  lastPhase,
}: {
  meta: AgentMeta;
  state: AgentState;
  lastPhase?: string;
}) {
  const colRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const fillRef = useRef<HTMLDivElement>(null);
  const scoreRef = useRef<HTMLSpanElement>(null);
  const phaseRef = useRef<HTMLSpanElement>(null);

  const progress = PHASE_PROGRESS[lastPhase || state.phase] ?? 0;

  useEffect(() => {
    if (fillRef.current) {
      animate(fillRef.current, {
        scaleX: [fillRef.current.style.transform ? parseFloat(fillRef.current.style.transform.replace("scaleX(", "").replace(")", "")) : 0, progress],
        duration: 400,
        ease: "outCubic",
      });
    }
  }, [progress]);

  useEffect(() => {
    if (state.phase === "done" && state.score !== undefined && scoreRef.current) {
      const obj = { value: 0 };
      animate(obj, {
        value: [0, state.score],
        duration: 800,
        ease: "outCubic",
        onUpdate: () => {
          if (scoreRef.current) {
            scoreRef.current.textContent = String(Math.round(obj.value));
          }
        },
      });
    }
  }, [state.phase, state.score]);

  useEffect(() => {
    if (state.phase === "streaming" && lastPhase && phaseRef.current) {
      animate(phaseRef.current, {
        opacity: [0, 1],
        translateY: [4, 0],
        duration: 300,
        ease: "outCubic",
      });
    }
  }, [lastPhase, state.phase]);

  useEffect(() => {
    const el = textRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [state.text]);

  const label = PHASE_LABEL[lastPhase || state.phase] || state.phase;

  return (
    <div className={`agent-col phase-${state.phase}`} data-agent={meta.id} ref={colRef}>
      <div className="agent-head">
        <span className={`status-dot ${state.phase}`} />
        <span className="agent-name">{meta.name}</span>
        <span className="agent-weight">{meta.weight}</span>
      </div>
      <p className="agent-role">{meta.role}</p>

      <div className="agent-track">
        <div className="agent-track-fill" ref={fillRef} style={{ transform: "scaleX(0)", transformOrigin: "left" }} />
      </div>

      <div className="agent-body" ref={textRef}>
        {state.phase === "waiting" && (
          <div className="skeleton" aria-label="waiting for agent stream">
            <div className="bone w80" />
            <div className="bone w95" />
            <div className="bone w60" />
          </div>
        )}
        {state.phase === "offline" && (
          <p className="agent-note">{state.note}</p>
        )}
        {state.text && <pre className="agent-text">{state.text}</pre>}
      </div>

      <div className="agent-foot">
        <span className="agent-phase-label" ref={phaseRef} key={lastPhase || state.phase}>
          {label}
        </span>
        {state.phase === "done" && state.score !== undefined && (
          <span className="agent-score" ref={scoreRef}>0</span>
        )}
      </div>
    </div>
  );
}
