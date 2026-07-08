---
type: Service
title: PDF Export
description: Playwright prints the Next.js dashboard HTML to PDF, producing a portable report from the same layout used in the browser.
tags: [pdf, playwright, report]
timestamp: 2026-07-08T00:00:00Z
---

# PDF Export

Served at `GET /api/audit/{id}/report.pdf` from the [API layer](/components/api.md).

Playwright headlessly loads and prints the [Frontend](/components/frontend.md) dashboard for the given audit ID. Because it prints the live dashboard HTML, no separate PDF template is needed — one layout, two surfaces.

The [AuditReport](/data/audit-report.md) data must be finalized and cached before this endpoint is called; the [Frontend](/components/frontend.md) fetches it client-side for the PDF render.
