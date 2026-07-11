// SSE client for per-agent streams.
// Connects to: {apiBase}/agent/stream/{agentId}
// which the main API (FastAPI) proxies to the agents-api.
//
// Wire format (OKF - see okf/components/streaming.md):
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
    // EventSource normally changes to CONNECTING and retries forever after a
    // failed HTTP/SSE connection. An audit cannot recover an unknown stream ID,
    // so settle this panel and let the report polling/fallback path complete.
    h.onOffline(
      es.readyState === EventSource.CLOSED
        ? "Agent stream closed unexpectedly."
        : "Agent stream connection failed.",
    );
    close();
  };

  function close() {
    if (!closed) {
      closed = true;
      es.close();
    }
  }
  return close;
}
