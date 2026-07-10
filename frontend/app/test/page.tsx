"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";

export default function TestPage() {
  const bgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = bgRef.current;
    if (!container) return;

    const els: HTMLDivElement[] = [];

    const configs = [
      { x: 20, y: 15, size: 400, color: "rgba(212, 175, 55, 0.3)", blur: 80, dx: 20, dy: 12, dur: 12000 },
      { x: 75, y: 20, size: 350, color: "rgba(201, 168, 76, 0.25)", blur: 90, dx: -15, dy: 10, dur: 15000 },
      { x: 50, y: 50, size: 500, color: "rgba(184, 134, 11, 0.2)", blur: 100, dx: 12, dy: -8, dur: 18000 },
      { x: 10, y: 70, size: 300, color: "rgba(212, 175, 55, 0.22)", blur: 70, dx: 18, dy: -10, dur: 14000 },
      { x: 85, y: 65, size: 320, color: "rgba(201, 168, 76, 0.18)", blur: 75, dx: -16, dy: 8, dur: 16000 },
    ];

    configs.forEach((cfg) => {
      const el = document.createElement("div");
      el.style.cssText = `
        position: absolute;
        width: ${cfg.size}px;
        height: ${cfg.size}px;
        left: ${cfg.x}%;
        top: ${cfg.y}%;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        background: radial-gradient(circle, ${cfg.color}, transparent 70%);
        filter: blur(${cfg.blur}px);
        opacity: 0;
        will-change: transform, opacity;
        pointer-events: none;
      `;
      container.appendChild(el);
      els.push(el);

      animate(el, {
        opacity: [0, 1],
        duration: 2000,
        delay: Math.random() * 500,
        ease: "outQuad",
      });

      animate(el, {
        translateX: [0, cfg.dx, -cfg.dx * 0.7, cfg.dx * 0.4, 0],
        translateY: [0, -cfg.dy, cfg.dy * 0.6, -cfg.dy * 0.3, 0],
        scale: [1, 1.1, 0.92, 1.05, 1],
        duration: cfg.dur,
        loop: true,
        ease: "inOutSine",
      });
    });

    return () => els.forEach((el) => el.remove());
  }, []);

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      background: "#0c0806",
      overflow: "hidden",
    }}>
      <div ref={bgRef} style={{
        position: "absolute",
        inset: 0,
      }} />
      <div style={{
        position: "relative",
        zIndex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        color: "#e8dccc",
        fontFamily: "Inter, sans-serif",
        textAlign: "center",
        padding: "20px",
      }}>
        <h1 style={{ fontSize: "48px", margin: "0 0 12px" }}>Nebula Test</h1>
        <p style={{ fontSize: "18px", opacity: 0.6 }}>If you see soft gold clouds drifting, it works.</p>
      </div>
    </div>
  );
}
