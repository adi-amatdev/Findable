---
type: Service
title: PDF Export
status: implemented
description: Backend endpoint generates a verbose, self-contained PDF using fpdf2 (no system deps, Latin-1 safe) and streams it directly to the browser on click.
tags: [pdf, fpdf2, report, api]
timestamp: 2026-07-09T00:00:00Z
---

# PDF Export

Served at `GET /api/audit/{audit_id}/pdf` from the [API layer](/components/api.md).

## Implementation

Built with `fpdf2>=2.7` — pure Python, no Playwright, no headless browser, no system dependencies. Implemented in `app/pdf.py` (`build_pdf(raw: dict) -> bytes`).

The endpoint (`app/api/routes.py`):
1. Fetches the AuditReport from mock state (if `MOCK_STREAM=true`) or from agents-api
2. Calls `build_pdf()` which normalises the report and renders a PDF
3. Returns a `StreamingResponse(application/pdf)` with `Content-Disposition: attachment`

The frontend calls this endpoint directly when `auditId` is available:
```ts
a.href = `${API_BASE}/api/audit/${auditId}/pdf`;
a.download = `findable-${hostname}.pdf`;
a.click();
```
Falls back to `window.print()` for fallback reports (no `auditId`).

## PDF content

| Section | Content |
|---|---|
| Title block | URL, generation date |
| Score | Large colour-coded score (green ≥80 / amber 50–79 / red <50) + one-line verdict |
| Executive Summary | LLM-generated summary paragraph |
| Category Scores | Table: agent name, weight, score (colour-coded) |
| Visibility Analysis | Table: platform, before %, after %, multiplier; avg improvement line |
| Findings | All findings verbose: title, severity badge, effort, impact, detail, recommendation, evidence, reference URL |

## Latin-1 safety

Helvetica (fpdf2 core font) is Latin-1 only. All strings pass through `_s(text)` before being written:
- Replaces em/en dashes, curly quotes, bullets, arrows, ellipsis, non-breaking spaces
- Falls back to `encode("latin-1", errors="replace")` for any remaining characters

## Normaliser

`_normalise(raw)` handles both report shapes:
- **Mock/flat**: `ai_readiness_score` at top level
- **Real/nested**: `pages[0].ai_readiness_score` + `pages[0].category_scores`
