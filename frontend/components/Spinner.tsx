"use client";

import { useEffect, useRef } from "react";
import { animate, svg } from "animejs";

export default function Spinner() {
  const pathRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    if (!pathRef.current) return;
    const [drawable] = svg.createDrawable(pathRef.current);
    animate(drawable, {
      draw: ["0 0", "0 1", "1 1", "1 0", "0 0"],
      duration: 2000,
      loop: true,
      ease: "inOutQuad",
    });
  }, []);

  return (
    <svg className="svg-spinner" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        ref={pathRef}
        d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"
        stroke="var(--accent)"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
