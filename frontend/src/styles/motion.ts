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

  /** Slide-overs, rail expand/collapse, sheet detents — confident landings,
   *  no overshoot. Sits between smooth (200/25) and snappy (400/25). */
  cozy: { type: "spring" as const, stiffness: 240, damping: 28 },
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

/** Ambient "float" loop for character emojis (reveal screen, loading screen). */
export const ambient = {
  /** Character emoji float — slow vertical bob. */
  emojiFloat: {
    animate: { y: [0, -6, 0] as number[] },
    transition: { duration: 4, ease: "easeInOut" as const, repeat: Infinity, delay: 1.5 },
  },

  /** Loading screen emoji float — slightly faster, no delay. */
  emojiFloatLoading: {
    animate: { y: [0, -8, 0] as number[] },
    transition: { duration: 3, ease: "easeInOut" as const, repeat: Infinity },
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

// ============================================================
// SHEET DETENTS (CareerLineageSheet)
// ============================================================

/**
 * Detent heights as fractions of the viewport.
 * Desktop + tablet use the standard values; mobile uses larger
 * compacts so the chip row + title row stay legible on small viewports.
 */
export const sheetDetent = {
  compact: { desktop: 0.33, tablet: 0.33, mobile: 0.45 },
  medium: { desktop: 0.5, tablet: 0.5, mobile: 0.6 },
  large: { desktop: 0.85, tablet: 0.85, mobile: 0.88 },
} as const;

/**
 * Snap spring used by CareerLineageSheet when dragging ends and the
 * sheet resolves to a detent. Tuned for "confident thunk" — fast enough
 * to feel deliberate, damped enough to not overshoot an iOS-style sheet.
 */
export const sheetSnap = {
  type: "spring" as const,
  stiffness: 420,
  damping: 42,
  mass: 0.9,
  restDelta: 0.5,
} as const;

/**
 * Drag elasticity — resistance past the compact/large limits.
 * 0.12 means the sheet follows the finger at 12% of the overshoot.
 * Below 0.1 feels walled-off; above 0.2 feels loose.
 */
export const sheetDragElastic = 0.12;

/**
 * Velocity threshold that promotes a drag-end to the next detent
 * even if the student didn't cross the midpoint. Units: px/s (Framer
 * Motion pan velocity). ±600 ≈ a moderate flick.
 */
export const sheetFlingVelocity = 600;

// ============================================================
// CHIP ROW + RESPONSE CARD (CareerLineageSheet)
// ============================================================

/**
 * Response card expand/collapse. Uses a custom spring for the height
 * animation so it has real physics; opacity cross-fades on a tween so
 * the entering answer doesn't fight the spring.
 */
export const chipResponseExpand = {
  initial: { opacity: 0, height: 0 },
  animate: { opacity: 1, height: "auto" },
  exit: { opacity: 0, height: 0 },
  transition: {
    opacity: { duration: 0.22, ease: "easeOut" as const },
    height: { type: "spring" as const, stiffness: 260, damping: 30 },
  },
} as const;

/**
 * Elevated-chip ambient pulse. The chip's shadow opacity breathes on a
 * 2.4s cycle. Gated at the consumer on ``useReducedMotion()``.
 */
export const elevatedChipPulse = {
  animate: {
    boxShadow: [
      "0 0 14px rgba(244, 169, 126, 0.22)",
      "0 0 22px rgba(244, 169, 126, 0.38)",
      "0 0 14px rgba(244, 169, 126, 0.22)",
    ] as string[],
  },
  transition: {
    duration: 2.4,
    ease: "easeInOut" as const,
    repeat: Infinity,
  },
} as const;

/**
 * Optional idle ambient pulse on the drag handle pill. Opacity breathe
 * on a 2.2s cycle. Gated at the consumer on ``useReducedMotion()``.
 */
export const handlePulse = {
  animate: { opacity: [0.4, 0.65, 0.4] as number[] },
  transition: {
    duration: 2.2,
    ease: "easeInOut" as const,
    repeat: Infinity,
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

/**
 * Branch tree node highlight pulse — fires when Gemma names a branch in
 * chat. Attentional, not celebratory; the metaphor is a soft pulse like
 * a nav reveal, not a victory burst. ~600ms total: bloom (0→0.42s) +
 * settle (0.42→1.0s). Color is ``accent-info`` so the flash reads as
 * "Gemma pointing" — same identity as the chat send button.
 *
 * Reduced motion: consumer must gate on ``useReducedMotion()`` and
 * substitute an 80ms opacity blink (no scale, no glow).
 */
export const branchFlash = {
  animate: {
    scale: [1, 1.06, 1] as number[],
    boxShadow: [
      "0 0 0 rgba(123, 184, 224, 0)",
      "0 0 24px rgba(123, 184, 224, 0.55)",
      "0 0 0 rgba(123, 184, 224, 0)",
    ] as string[],
  },
  transition: {
    duration: 0.6,
    times: [0, 0.42, 1] as number[],
    ease: "easeInOut" as const,
  },
} as const;

/** Stagger between multi-match highlights (one Gemma response naming several branches). */
export const branchFlashStagger = 0.2;
