"use client";

import { useEffect, useRef, useState } from "react";
import { animate } from "animejs";

export default function ReportBar({
  filename,
  markdown,
}: {
  filename: string;
  markdown: string;
}) {
  const [open, setOpen] = useState(false);
  const chipRef = useRef<HTMLButtonElement>(null);
  const paneRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chipRef.current) {
      animate(chipRef.current, {
        translateY: [24, 0],
        opacity: [0, 1],
        scale: [0.92, 1],
        duration: 650,
        ease: "spring(1, 80, 12, 0)",
      });
    }
  }, []);

  useEffect(() => {
    if (paneRef.current) {
      animate(paneRef.current, {
        translateX: open ? ["100%", "0%"] : ["0%", "100%"],
        duration: 480,
        ease: "cubicBezier(0.22, 1, 0.36, 1)",
      });
    }
  }, [open]);

  function downloadMarkdown() {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function downloadPdf() {
    document.body.classList.add("printing-report");
    window.print();
    document.body.classList.remove("printing-report");
  }

  const sizeKb = Math.max(1, Math.round(markdown.length / 1024));

  return (
    <>
      <button ref={chipRef} className="report-chip" onClick={() => setOpen(true)}>
        <span className="chip-icon">▤</span>
        <span className="chip-meta">
          <span className="chip-name">{filename}</span>
          <span className="chip-sub">audit report · {sizeKb} KB · click to view</span>
        </span>
        <span className="chip-open">open ↗</span>
      </button>

      {open && (
        <div className="pane-backdrop" onClick={() => setOpen(false)}>
          <div
            className="report-pane"
            ref={paneRef}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pane-head">
              <span className="chip-name">{filename}</span>
              <span className="pane-actions">
                <button className="ghost" onClick={downloadMarkdown}>↓ .md</button>
                <button className="ghost" onClick={downloadPdf}>↓ PDF</button>
                <button className="ghost" onClick={() => setOpen(false)}>✕</button>
              </span>
            </div>
            <div className="pane-body" id="report-print-area">
              <pre className="report-md">{markdown}</pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
