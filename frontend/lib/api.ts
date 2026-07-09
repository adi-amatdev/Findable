// Backend client. Points at the Findable FastAPI app.

import type { AuditReport, AuditStartResponse, SiteFacts } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export async function getSiteFacts(
  url: string,
  refresh = false,
  signal?: AbortSignal
): Promise<SiteFacts> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/sitefacts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, refresh }),
      signal,
    });
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}. Is it running?`);
  }

  if (!res.ok) {
    let msg = `Request failed (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      const detail = body?.detail;
      if (typeof detail === "string") msg = detail;
      else if (detail?.error) msg = detail.error;
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, msg);
  }

  return res.json();
}

export async function postAuditStart(
  url: string,
  signal?: AbortSignal
): Promise<AuditStartResponse> {
  const res = await fetch(`${API_BASE}/api/audit/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    signal,
  });
  if (!res.ok) {
    let msg = `Failed to start audit (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      if (body?.detail) msg = body.detail;
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json();
}

export async function getAuditResult(
  auditId: string,
  signal?: AbortSignal
): Promise<AuditReport> {
  const res = await fetch(`${API_BASE}/api/audit/${auditId}`, { signal });
  if (!res.ok) {
    throw new ApiError(res.status, `Failed to get audit result (HTTP ${res.status})`);
  }
  return res.json();
}
