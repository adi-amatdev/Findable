"use client";

import { useRef } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";

const STEPS = [
  {
    label: "STEP 1",
    title: "Crawl & Fetch",
    description:
      "Two fetchers run in parallel: Firecrawl renders the page like a browser would, while direct HTTP captures the raw source. Together they pull robots.txt, sitemap.xml, and llms.txt.",
    icon: (
      <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="var(--gold-2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="24" cy="24" r="20" opacity="0.15" fill="var(--gold-2)" />
        <path d="M14 20 L24 14 L34 20 L34 34 L14 34Z" />
        <path d="M20 34 V26 H28 V34" />
        <circle cx="24" cy="21" r="2" fill="var(--gold-2)" stroke="none" />
      </svg>
    ),
    visualLabel: "rendered + raw",
    badgeIcons: ["🤖", "📄"],
  },
  {
    label: "STEP 2",
    title: "Extract SiteFacts",
    description:
      "Deterministic Python parses every signal - no LLM in the loop. JS dependency, schema.org types, meta tags, authorship, and link graphs are distilled into a reproducible SiteFacts object.",
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
    visualLabel: "signals only",
    badgeIcons: ["⚙️", "📊"],
  },
  {
    label: "STEP 3",
    title: "Four AI Judges",
    description:
      "Four specialized agents read the same SiteFacts in parallel, each arguing one dimension of AI-readiness: crawlability, content quality, structured data, and entity authority.",
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
    visualLabel: "parallel",
    badgeIcons: ["⚖️", "🧠"],
  },
  {
    label: "STEP 4",
    title: "Score & Report",
    description:
      "Agent verdicts are weighted into a 0-100 AI Readiness Score with hard gates on critical failures. You get prioritized findings, before/after visibility, and an exportable report.",
    icon: (
      <svg viewBox="0 0 48 48" width="48" height="48" fill="none" stroke="var(--gold-2)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="24" cy="24" r="20" opacity="0.15" fill="var(--gold-2)" />
        <path d="M24 12 A12 12 0 0 1 36 24" />
        <path d="M24 12 A12 12 0 0 0 12 24" strokeDasharray="4 3" />
        <circle cx="24" cy="24" r="7" />
        <text x="24" y="27" textAnchor="middle" fontSize="9" fill="var(--gold-2)" stroke="none" fontFamily="Playfair Display, serif" fontWeight="700">87</text>
      </svg>
    ),
    visualLabel: "0–100",
    badgeIcons: ["📋", "🎯"],
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

const badgeVariants = {
  hidden: { opacity: 0, scale: 0.6 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    transition: { delay: 0.3 + i * 0.1, type: "spring" as const, stiffness: 200, damping: 14 },
  }),
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
        <span className="hiw-eyebrow">UNDER THE HOOD</span>
        <h2 className="hiw-title">How does it work?</h2>
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
                <div className="hiw-badges">
                  {step.badgeIcons.map((emoji, j) => (
                    <motion.span
                      className="hiw-badge"
                      key={j}
                      custom={j}
                      variants={badgeVariants}
                      initial="hidden"
                      animate={shouldAnimate ? "visible" : "visible"}
                    >
                      {emoji}
                    </motion.span>
                  ))}
                </div>
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
