// SSE client for per-agent streams.
// Connects to: {apiBase}/agent/stream/{agentId}
// which the main API (FastAPI) proxies to the agents-api.
//
// Wire format (OKF — see okf/components/streaming.md):
//   event: agent_status
//   data: {"agent_id":"<uuid>","agent":"<name>","phase":"<phase>","detail":"...","score":null,"ts":...}
//
// Phase "complete" -> stream done. "error" -> stream failed.

export interface StreamHandlers {
  onPhase: (
    agentName: string,
    phase: string,
    detail: string | null,
    score: number | null,
  ) => void;
  onDone: () => void;
  onOffline: (message: string) => void;
}

export function openAgentStream(
  apiBase: string,
  agentId: string,
  h: StreamHandlers,
): () => void {
  let closed = false;
  const url = `${apiBase}/agent/stream/${agentId}`;
  const es = new EventSource(url);

  es.addEventListener("agent_status", (ev) => {
    if (closed) return;
    try {
      const event = JSON.parse(ev.data);
      if (event && typeof event === "object" && "phase" in event) {
        if (event.phase === "complete") {
          h.onPhase(event.agent, event.phase, event.detail ?? null, event.score ?? null);
          h.onDone();
          close();
        } else if (event.phase === "error") {
          h.onPhase(event.agent, event.phase, event.detail ?? null, null);
          h.onDone();
          close();
        } else {
          h.onPhase(event.agent, event.phase, event.detail ?? null, null);
        }
      }
    } catch {
      /* ignore malformed JSON */
    }
  });

  es.onerror = () => {
    if (closed) return;
    if (es.readyState === EventSource.CLOSED) {
      h.onOffline("Agent stream is not live yet.");
      close();
    }
  };

  function close() {
    if (!closed) {
      closed = true;
      es.close();
    }
  }
  return close;
}
