"use client";

import { useRef } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";

const STEPS = [
  {
    label: "DELIVERABLE 1",
    title: "Access map",
    description:
      "See which AI crawlers can reach your pages, where robots.txt blocks them, and whether JavaScript hides the content they need to read.",
    icon: (
      <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="var(--gold-2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="24" cy="24" r="20" opacity="0.15" fill="var(--gold-2)" />
        <path d="M14 20 L24 14 L34 20 L34 34 L14 34Z" />
        <path d="M20 34 V26 H28 V34" />
        <circle cx="24" cy="21" r="2" fill="var(--gold-2)" stroke="none" />
      </svg>
    ),
    visualLabel: "crawler access",
  },
  {
    label: "DELIVERABLE 2",
    title: "Evidence-led signals",
    description:
      "Inspect the signals behind every recommendation: structured data, metadata, authorship, internal links, and the rendered-versus-raw content gap.",
    icon: (
      <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="var(--gold-2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="24" cy="24" r="20" opacity="0.15" fill="var(--gold-2)" />
        <rect x="14" y="12" width="20" height="24" rx="2" />
        <line x1="18" y1="18" x2="30" y2="18" />
        <line x1="18" y1="23" x2="26" y2="23" />
        <line x1="18" y1="28" x2="28" y2="28" />
        <line x1="18" y1="33" x2="22" y2="33" />
      </svg>
    ),
    visualLabel: "source evidence",
  },
  {
    label: "DELIVERABLE 3",
    title: "Readiness breakdown",
    description:
      "Compare crawlability, content quality, structured data, and entity authority in one clear score breakdown instead of a single opaque grade.",
    icon: (
      <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="var(--gold-2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="24" cy="24" r="20" opacity="0.15" fill="var(--gold-2)" />
        <circle cx="16" cy="18" r="5" />
        <circle cx="32" cy="18" r="5" />
        <circle cx="16" cy="32" r="5" />
        <circle cx="32" cy="32" r="5" />
        <line x1="21" y1="18" x2="27" y2="18" opacity="0.4" />
        <line x1="16" y1="23" x2="16" y2="27" opacity="0.4" />
        <line x1="32" y1="23" x2="32" y2="27" opacity="0.4" />
        <line x1="21" y1="32" x2="27" y2="32" opacity="0.4" />
      </svg>
    ),
    visualLabel: "four dimensions",
  },
  {
    label: "DELIVERABLE 4",
    title: "Prioritized fixes",
    description:
      "Leave with ranked actions, expected visibility impact, and a shareable report that turns technical gaps into a practical next step.",
    icon: (
      <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="var(--gold-2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="24" cy="24" r="20" opacity="0.15" fill="var(--gold-2)" />
        <path d="M24 12 A12 12 0 0 1 36 24" />
        <path d="M24 12 A12 12 0 0 0 12 24" strokeDasharray="4 3" />
        <circle cx="24" cy="24" r="7" />
        <text x="24" y="27" textAnchor="middle" fontSize="9" fill="var(--gold-2)" stroke="none" fontFamily="Playfair Display, serif" fontWeight="700">87</text>
      </svg>
    ),
    visualLabel: "action plan",
  },
];

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.15 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 24, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 120, damping: 18 },
  },
};

export default function HowItWorks() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: true, amount: 0.2 });
  const prefersReducedMotion = useReducedMotion();

  const shouldAnimate = isInView && !prefersReducedMotion;

  return (
    <div className="hiw-section" ref={sectionRef}>
      <motion.div
        className="hiw-header"
        initial={{ opacity: 0, y: 16 }}
        animate={shouldAnimate ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] }}
      >
        <span className="hiw-eyebrow">WHAT YOU GET</span>
        <h2 className="hiw-title">A report you can act on</h2>
      </motion.div>

      <motion.div
        className="hiw-grid"
        variants={containerVariants}
        initial="hidden"
        animate={shouldAnimate ? "visible" : "visible"}
      >
        {STEPS.map((step, i) => (
          <motion.div className="hiw-col" key={step.label} variants={itemVariants}>
            <motion.div
              className="hiw-card"
              variants={cardVariants}
              whileHover={prefersReducedMotion ? undefined : { y: -4, boxShadow: "0 8px 32px rgba(0,0,0,0.3), 0 0 24px rgba(201,168,76,0.08)" }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
            >
              <div className="hiw-card-inner">
                <div className="hiw-icon-wrap">
                  {step.icon}
                </div>
                <div className="hiw-visual-label">{step.visualLabel}</div>
              </div>
            </motion.div>

            <motion.span className="hiw-step-label" variants={itemVariants}>
              {step.label}
            </motion.span>
            <motion.h3 className="hiw-step-title" variants={itemVariants}>
              {step.title}
            </motion.h3>
            <motion.p className="hiw-step-desc" variants={itemVariants}>
              {step.description}
            </motion.p>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}
