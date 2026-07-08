"use client";

import { useEffect, useRef, useState } from "react";
import anime from "animejs";

// The Claude-style artifact chip: the finished report collapses into a
// file bar; clicking it opens a split pane with the report + download actions.

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

  // Chip lands with a soft drop-in.
  useEffect(() => {
    if (chipRef.current) {
      anime({
        targets: chipRef.current,
        translateY: [24, 0],
        opacity: [0, 1],
        scale: [0.92, 1],
        duration: 650,
        easing: "spring(1, 80, 12, 0)",
      });
    }
  }, []);

  // Split pane slides open / closed.
  useEffect(() => {
    if (paneRef.current) {
      anime({
        targets: paneRef.current,
        translateX: open ? ["100%", "0%"] : ["0%", "100%"],
        duration: 480,
        easing: "cubicBezier(0.22, 1, 0.36, 1)",
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

  // PDF via the browser's print pipeline: print styles isolate the report pane.
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
