"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";

interface Orb {
  el: HTMLDivElement;
  x: number;
  y: number;
  size: number;
}

export default function LivingBackground() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    const orbs: Orb[] = [];

    // Compose 8 orbs in a golden halo around the hero
    const configs = [
      { x: 50, y: 30, size: 280, color: "rgba(201, 168, 76, 0.08)" },
      { x: 35, y: 40, size: 200, color: "rgba(180, 120, 60, 0.06)" },
      { x: 65, y: 35, size: 220, color: "rgba(210, 180, 100, 0.07)" },
      { x: 50, y: 55, size: 160, color: "rgba(160, 100, 50, 0.05)" },
      { x: 25, y: 60, size: 140, color: "rgba(200, 160, 80, 0.04)" },
      { x: 75, y: 50, size: 180, color: "rgba(220, 190, 120, 0.05)" },
      { x: 50, y: 20, size: 120, color: "rgba(180, 140, 70, 0.06)" },
      { x: 45, y: 70, size: 100, color: "rgba(150, 90, 40, 0.04)" },
    ];

    configs.forEach((cfg) => {
      const el = document.createElement("div");
      el.className = "living-orb";
      el.style.cssText = `
        width:${cfg.size}px; height:${cfg.size}px;
        left:${cfg.x}%; top:${cfg.y}%;
        background:radial-gradient(circle at 35% 35%, ${cfg.color}, transparent 70%);
        filter:blur(${40 + Math.random() * 30}px);
      `;
      container.appendChild(el);

      const orb: Orb = { el, x: cfg.x, y: cfg.y, size: cfg.size };
      orbs.push(orb);

      const dur = 14000 + Math.random() * 10000;
      const xDrift = 8 + Math.random() * 14;
      const yDrift = 5 + Math.random() * 10;

      animate(el, {
        translateX: [0, xDrift, -xDrift * 0.6, xDrift * 0.3, 0],
        translateY: [0, -yDrift, yDrift * 0.5, -yDrift * 0.3, 0],
        scale: [1, 1.08, 0.94, 1.03, 1],
        opacity: [0.6, 0.9, 0.5, 0.8, 0.6],
        duration: dur,
        loop: true,
        ease: "inOutSine",
      });
    });

    return () => {
      orbs.forEach((o) => o.el.remove());
    };
  }, []);

  return <div ref={ref} className="living-bg" aria-hidden="true" />;
}
