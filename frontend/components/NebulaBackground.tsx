"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";

interface NebulaBackgroundProps {
  intensity?: number;
  className?: string;
}

export default function NebulaBackground({
  intensity = 1,
  className = "",
}: NebulaBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const cs = getComputedStyle(document.documentElement);
    const gold = cs.getPropertyValue("--gold-2").trim() || "#d4af37";
    const gold1 = cs.getPropertyValue("--gold-1").trim() || "#c9a84c";

    const hexToRgb = (hex: string) => {
      const h = hex.replace("#", "");
      return [
        parseInt(h.substring(0, 2), 16),
        parseInt(h.substring(2, 4), 16),
        parseInt(h.substring(4, 6), 16),
      ] as const;
    };

    const [gr, gg, gb] = hexToRgb(gold);
    const [g1r, g1g, g1b] = hexToRgb(gold1);

    const configs = [
      { x: 20, y: 10, size: 60, color: `rgba(${gr},${gg},${gb},0.25)`, blur: 70, driftX: 15, driftY: 10, dur: 18000 },
      { x: 80, y: 8, size: 55, color: `rgba(${g1r},${g1g},${g1b},0.22)`, blur: 80, driftX: -12, driftY: 8, dur: 22000 },
      { x: 50, y: 18, size: 50, color: `rgba(${gr},${gg},${gb},0.18)`, blur: 90, driftX: 10, driftY: -6, dur: 25000 },
      { x: 8, y: 40, size: 45, color: `rgba(${g1r},${g1g},${g1b},0.20)`, blur: 65, driftX: 16, driftY: 8, dur: 20000 },
      { x: 90, y: 30, size: 42, color: `rgba(${gr},${gg},${gb},0.22)`, blur: 75, driftX: -14, driftY: 10, dur: 19000 },
      { x: 50, y: 5, size: 70, color: `rgba(${gr},${gg},${gb},0.14)`, blur: 100, driftX: 8, driftY: 5, dur: 28000 },
    ];

    const els: HTMLDivElement[] = [];

    configs.forEach((cfg) => {
      const el = document.createElement("div");
      el.className = "nebula-blob";
      el.style.cssText = `
        position:absolute;
        width:${cfg.size}vw;
        height:${cfg.size}vw;
        left:${cfg.x}%;
        top:${cfg.y}%;
        transform:translate(-50%,-50%);
        border-radius:50%;
        background:radial-gradient(circle, ${cfg.color}, transparent 70%);
        filter:blur(${cfg.blur}px);
        opacity:0;
        will-change:transform,opacity;
        pointer-events:none;
      `;
      root.appendChild(el);
      els.push(el);

      animate(el, {
        opacity: [0, 1],
        duration: 2500,
        delay: Math.random() * 600,
        ease: "outQuad",
      });

      const dx = cfg.driftX;
      const dy = cfg.driftY;
      animate(el, {
        translateX: [0, dx, -dx * 0.7, dx * 0.4, 0],
        translateY: [0, -dy, dy * 0.6, -dy * 0.3, 0],
        scale: [1, 1.08, 0.93, 1.04, 1],
        duration: cfg.dur,
        loop: true,
        ease: "inOutSine",
      });
    });

    return () => {
      els.forEach((el) => el.remove());
    };
  }, [intensity]);

  return (
    <div
      ref={containerRef}
      className={`nebula-bg ${className}`}
      aria-hidden="true"
    />
  );
}
