"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";

interface Orb {
  el: HTMLDivElement;
}

export default function LivingBackground() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    const orbs: Orb[] = [];

    // Original small golden particles
    const particleConfigs = [
      { x: 50, y: 30, size: 280, color: "rgba(201, 168, 76, 0.08)" },
      { x: 35, y: 40, size: 200, color: "rgba(180, 120, 60, 0.06)" },
      { x: 65, y: 35, size: 220, color: "rgba(210, 180, 100, 0.07)" },
      { x: 50, y: 55, size: 160, color: "rgba(160, 100, 50, 0.05)" },
      { x: 25, y: 60, size: 140, color: "rgba(200, 160, 80, 0.04)" },
      { x: 75, y: 50, size: 180, color: "rgba(220, 190, 120, 0.05)" },
      { x: 50, y: 20, size: 120, color: "rgba(180, 140, 70, 0.06)" },
      { x: 45, y: 70, size: 100, color: "rgba(150, 90, 40, 0.04)" },
    ];

    particleConfigs.forEach((cfg) => {
      const el = document.createElement("div");
      el.className = "living-orb";
      el.style.cssText = `
        width:${cfg.size}px; height:${cfg.size}px;
        left:${cfg.x}%; top:${cfg.y}%;
        background:radial-gradient(circle at 35% 35%, ${cfg.color}, transparent 70%);
        filter:blur(${40 + Math.random() * 30}px);
      `;
      container.appendChild(el);
      orbs.push({ el });

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

    // Nebula blobs — large soft gradient clouds
    const nebulaConfigs = [
      { x: 20, y: 10, size: 500, color: "rgba(201, 168, 76, 0.15)", blur: 80, dx: 15, dy: 10, dur: 18000 },
      { x: 80, y: 8, size: 480, color: "rgba(201, 168, 76, 0.12)", blur: 90, dx: -12, dy: 8, dur: 22000 },
      { x: 50, y: 15, size: 550, color: "rgba(212, 175, 55, 0.10)", blur: 100, dx: 10, dy: -6, dur: 25000 },
      { x: 8, y: 35, size: 420, color: "rgba(180, 120, 60, 0.12)", blur: 70, dx: 16, dy: 8, dur: 20000 },
      { x: 90, y: 25, size: 400, color: "rgba(201, 168, 76, 0.13)", blur: 75, dx: -14, dy: 10, dur: 19000 },
      { x: 45, y: 3, size: 600, color: "rgba(212, 175, 55, 0.08)", blur: 110, dx: 8, dy: 5, dur: 28000 },
    ];

    nebulaConfigs.forEach((cfg) => {
      const el = document.createElement("div");
      el.className = "living-orb";
      el.style.cssText = `
        width:${cfg.size}px; height:${cfg.size}px;
        left:${cfg.x}%; top:${cfg.y}%;
        background:radial-gradient(circle, ${cfg.color}, transparent 70%);
        filter:blur(${cfg.blur}px);
        opacity:0;
      `;
      container.appendChild(el);
      orbs.push({ el });

      animate(el, {
        opacity: [0, 1],
        duration: 2500,
        delay: Math.random() * 600,
        ease: "outQuad",
      });

      animate(el, {
        translateX: [0, cfg.dx, -cfg.dx * 0.7, cfg.dx * 0.4, 0],
        translateY: [0, -cfg.dy, cfg.dy * 0.6, -cfg.dy * 0.3, 0],
        scale: [1, 1.06, 0.94, 1.03, 1],
        duration: cfg.dur,
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
