// SSE client for the (future) per-agent stream:
//   GET {API_BASE}/agent/stream/{agent_id}
//
// Event contract (tolerant by design — the backend lands later):
//   - plain text data            -> treated as a token chunk
//   - {"type":"token","text"}    -> token chunk
//   - {"type":"status", ...}     -> lifecycle ("started" | "finished")
//   - {"type":"result", ...}     -> final AgentResult JSON (okf/data/agent-result.md)
//   - {"type":"done"}            -> stream complete
// Connection errors surface as `offline` so the UI can say so honestly.

export interface StreamHandlers {
  onToken: (text: string) => void;
  onResult?: (result: unknown) => void;
  onDone: () => void;
  onOffline: (message: string) => void;
}

export function openAgentStream(
  apiBase: string,
  agentId: string,
  h: StreamHandlers
): () => void {
  let closed = false;
  const url = `${apiBase}/agent/stream/${agentId}`;
  const es = new EventSource(url);

  es.onmessage = (ev) => {
    if (closed) return;
    const data = ev.data ?? "";
    try {
      const msg = JSON.parse(data);
      if (msg && typeof msg === "object" && "type" in msg) {
        if (msg.type === "token" && typeof msg.text === "string") h.onToken(msg.text);
        else if (msg.type === "result") h.onResult?.(msg);
        else if (msg.type === "done") {
          h.onDone();
          close();
        }
        return;
      }
    } catch {
      /* not JSON — fall through to plain token */
    }
    if (data) h.onToken(data);
  };

  es.onerror = () => {
    if (closed) return;
    // EventSource fires error both for "endpoint missing" and transient drops.
    // readyState CLOSED means it gave up — report offline instead of spinning.
    if (es.readyState === EventSource.CLOSED) {
      h.onOffline("Agent stream is not live yet — the backend endpoint ships soon.");
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
