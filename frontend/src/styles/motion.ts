/**
 * Brightpath Design System — Motion Tokens
 * Framer Motion spring configurations and animation presets.
 *
 * CSS can't do spring physics, so these live in JS.
 * Import into any component: import { springs, transitions, stagger } from "@/styles/motion";
 */

import type { Variants } from "framer-motion";

// ============================================================
// SPRING CONFIGURATIONS
// ============================================================

export const springs = {
  /** Playful pop, noticeable overshoot. Character reveals, boss entrance, stat counters. */
  bouncy: { type: "spring" as const, stiffness: 300, damping: 20 },

  /** Confident settle, gentle overshoot. Page transitions, card entrances, panel expansions. */
  smooth: { type: "spring" as const, stiffness: 200, damping: 25 },

  /** Slow and graceful, minimal overshoot. Background shifts, ambient glows, branch tree initial render. */
  gentle: { type: "spring" as const, stiffness: 150, damping: 30 },

  /** Quick and responsive, slight bounce. Button press, toggle, slider thumb, micro-interactions. */
  snappy: { type: "spring" as const, stiffness: 400, damping: 25 },
} as const;

// ============================================================
// STAGGER DELAYS
// ============================================================

export const stagger = {
  /** 50ms — stat bars, skill badges, rapid lists. */
  fast: 0.05,

  /** 80ms — card grids, branch nodes, standard lists. */
  normal: 0.08,

  /** 100ms — branch tree tiers, boss fight sequence, cinematic reveals. */
  slow: 0.1,
} as const;

// ============================================================
// COMMON TRANSITIONS
// ============================================================

export const transitions = {
  /** Standard element entrance: slide up + fade in with smooth spring. */
  fadeInUp: {
    initial: { opacity: 0, y: 24 },
    animate: { opacity: 1, y: 0 },
    transition: springs.smooth,
  },

  /** Scale reveal: for bears, pentagons, boss monsters. Bouncy spring. */
  scaleIn: {
    initial: { opacity: 0, scale: 0.8 },
    animate: { opacity: 1, scale: 1 },
    transition: springs.bouncy,
  },

  /** Gentle fade: for background shifts, ambient changes. */
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.3, ease: "easeOut" },
  },

  /** Quick press feedback for buttons. */
  press: {
    whileTap: { scale: 0.97 },
    transition: springs.snappy,
  },
} as const;

// ============================================================
// REUSABLE VARIANTS
// ============================================================

/** Container that staggers its children. */
export const staggerContainer = (delayChildren: number = 0, staggerAmount: number = stagger.normal): Variants => ({
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      delayChildren,
      staggerChildren: staggerAmount,
    },
  },
});

/** Individual child item that fades up. Use with staggerContainer. */
export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: springs.smooth,
  },
};

/** Scale-in child. Use with staggerContainer for grid reveals. */
export const scaleItem: Variants = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: springs.bouncy,
  },
};

// ============================================================
// SCREEN-SPECIFIC PRESETS
// ============================================================

/** Stage 2 Reveal: bear evolution sequence. */
export const stage2Reveal = {
  /** Glow pulse before the bear appears. */
  glowPulse: {
    animate: { opacity: [0, 0.3, 0.15] },
    transition: { duration: 0.8, ease: "easeInOut" },
  },

  /** Bear scales up with bounce. */
  bearReveal: {
    initial: { opacity: 0, scale: 0.85 },
    animate: { opacity: 1, scale: 1 },
    transition: { ...springs.bouncy, delay: 0.5 },
  },

  /** Pentagon draws from center. */
  pentagonDraw: {
    initial: { scale: 0, opacity: 0 },
    animate: { scale: 1, opacity: 1 },
    transition: { ...springs.smooth, delay: 1.0 },
  },

  /** Career title types in. */
  titleReveal: {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { ...springs.smooth, delay: 1.4 },
  },
} as const;

/** Boss fight entrance sequence. */
export const bossFight = {
  /** Vignette darkening. */
  vignette: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    transition: { duration: 0.3 },
  },

  /** Boss bounces in from above. */
  bossEntrance: {
    initial: { opacity: 0, y: -60, scale: 0.8 },
    animate: { opacity: 1, y: 0, scale: 1 },
    transition: springs.bouncy,
  },

  /** Win: green burst. */
  winBurst: {
    animate: { scale: [1, 1.15, 1], opacity: [1, 0.8, 1] },
    transition: { duration: 0.4, ease: "easeOut" },
  },

  /** Lose: screen shake. */
  loseShake: {
    animate: { x: [0, -3, 3, -3, 3, 0] },
    transition: { duration: 0.3 },
  },
} as const;

/** Branch tree reveal timing. */
export const branchTree = {
  /** Total reveal duration in seconds. */
  totalDuration: 3.5,

  /** Root node glow starts. */
  glowStart: 0,

  /** Branch lines begin drawing. */
  linesStart: 0.3,

  /** Branch label nodes pop in. */
  labelsStart: 0.8,

  /** Career progression nodes appear. */
  careerStart: 1.5,

  /** Endpoint silhouettes fade in. */
  endpointsStart: 2.2,

  /** Particles begin drifting. */
  particlesStart: 3.0,

  /** Per-tier line draw duration. */
  lineDrawDuration: 0.5,

  /** Stagger between branch label nodes. */
  labelStagger: 0.1,

  /** Endpoint glow pulse duration. */
  endpointPulseDuration: 0.15,
} as const;
