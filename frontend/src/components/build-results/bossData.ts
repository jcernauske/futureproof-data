import type { BossId } from "@/types/build";

export interface BossMeta {
  id: BossId;
  emoji: string;
  /** English fallback. Prefer `shortNameKey` + `t(...)` for display. */
  shortName: string;
  /** i18n key for the localized short name. */
  shortNameKey: string;
  subtitle: string;
  subtitleKey: string;
  color: string;
  gradient: string;
}

export const BOSS_META: Record<BossId, BossMeta> = {
  ai: {
    id: "ai",
    emoji: "\u{1F916}",
    shortName: "AI",
    shortNameKey: "build.boss.ai.shortName",
    subtitle: "How safe is this career from automation?",
    subtitleKey: "build.boss.ai.subtitle",
    color: "var(--color-boss-ai)",
    gradient: "linear-gradient(135deg, rgba(184,169,232,0.30) 0%, rgba(184,169,232,0.12) 100%)",
  },
  loans: {
    id: "loans",
    emoji: "\u{1F4B8}",
    shortName: "Student Loans",
    shortNameKey: "build.boss.loans.shortName",
    subtitle: "Can your earnings handle the debt?",
    subtitleKey: "build.boss.loans.subtitle",
    color: "var(--color-boss-loans)",
    gradient: "linear-gradient(135deg, rgba(244,169,126,0.30) 0%, rgba(244,169,126,0.12) 100%)",
  },
  market: {
    id: "market",
    emoji: "\u{1F4C8}",
    shortName: "The Market",
    shortNameKey: "build.boss.market.shortName",
    subtitle: "Is this field growing or shrinking?",
    subtitleKey: "build.boss.market.subtitle",
    color: "var(--color-boss-market)",
    gradient: "linear-gradient(135deg, rgba(123,184,224,0.30) 0%, rgba(123,184,224,0.12) 100%)",
  },
  burnout: {
    id: "burnout",
    emoji: "\u{1F525}",
    shortName: "Burnout",
    shortNameKey: "build.boss.burnout.shortName",
    subtitle: "How sustainable is this work long-term?",
    subtitleKey: "build.boss.burnout.subtitle",
    color: "var(--color-boss-burnout)",
    gradient: "linear-gradient(135deg, rgba(232,139,169,0.30) 0%, rgba(232,139,169,0.12) 100%)",
  },
  ceiling: {
    id: "ceiling",
    emoji: "\u{1F4CA}",
    shortName: "The Ceiling",
    shortNameKey: "build.boss.ceiling.shortName",
    subtitle: "How high can your earnings go?",
    subtitleKey: "build.boss.ceiling.subtitle",
    color: "var(--color-boss-ceiling)",
    gradient: "linear-gradient(135deg, rgba(196,191,176,0.30) 0%, rgba(196,191,176,0.12) 100%)",
  },
};

export const EMOJI_BG: Record<string, string> = {
  "\u{1F43B}": "var(--color-accent-caution)",   // Bear
  "\u{1F430}": "var(--color-accent-insight)",    // Bunny
  "\u{1F422}": "var(--color-accent-info)",       // Turtle
  "\u{1F43F}\u{FE0F}": "var(--color-accent-thrive)",  // Chipmunk
  "\u{1F98A}": "var(--color-accent-insight)",    // Fox
  "\u{1F989}": "var(--color-accent-caution)",    // Owl
  "\u{1F427}": "var(--color-accent-info)",       // Penguin
  "\u{1F431}": "var(--color-accent-alert)",      // Cat
};

export const STAT_COLORS: Record<string, { text: string; bg: string }> = {
  ern: { text: "var(--color-stat-ern)", bg: "rgba(242,212,119,0.15)" },
  roi: { text: "var(--color-stat-roi)", bg: "rgba(125,212,163,0.15)" },
  res: { text: "var(--color-stat-res)", bg: "rgba(184,169,232,0.15)" },
  grw: { text: "var(--color-stat-grw)", bg: "rgba(123,184,224,0.15)" },
  aura: { text: "var(--color-stat-aura)", bg: "rgba(232,184,107,0.15)" },
  brn: { text: "var(--color-boss-burnout)", bg: "rgba(232,139,169,0.15)" },
  ceil: { text: "var(--color-boss-ceiling)", bg: "rgba(196,191,176,0.15)" },
};

export const STAT_INFO: Record<string, { title: string; definition: string; source: string }> = {
  ern: {
    title: "Earning Power",
    definition: "Measures how your expected salary compares to graduates from similar programs nationally, based on median earnings 1 and 4 years after graduation.",
    source: "College Scorecard",
  },
  roi: {
    title: "Return on Investment",
    definition: "A 15-year payback multiplier. Projects cumulative earnings over a typical 15-year repayment window (starting salary grown at flat 3% annually) and divides by the program's 4-year published cost. Higher = better. Financing-agnostic — the loan slider doesn't move it.",
    source: "College Scorecard",
  },
  res: {
    title: "AI Resilience",
    definition: "How well your career holds up against AI. Blends two signals: how much the work still needs people, and how poorly automation actually does it today.",
    source: "Karpathy AI Exposure + Anthropic Economic Index + O*NET task profiles",
  },
  grw: {
    title: "Growth Potential",
    definition: "Projects how fast this occupation is expected to add jobs over the next decade, relative to the national average across all occupations.",
    source: "BLS Occupational Outlook Handbook",
  },
  aura: {
    title: "Brand Gravity",
    definition: "How much weight your school's name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don't have it yet.",
    source: "IPEDS Finance + EADA athletics",
  },
};

export const RESULT_COLORS = {
  win: { border: "rgba(125,212,163,0.18)", glow: "rgba(125,212,163,0.10)" },
  lose: { border: "rgba(244,169,126,0.20)", glow: "rgba(244,169,126,0.10)" },
  draw: { border: "rgba(242,212,119,0.18)", glow: "rgba(242,212,119,0.10)" },
  unknown: { border: "rgba(255,255,255,0.06)", glow: "transparent" },
};

export const VERDICT_TIERS = [
  { min: 5, word: "DOMINANT BUILD", wordKey: "build.verdictDominant", subtitle: "Unstoppable", subtitleKey: "build.verdictSubDominant", accentClass: "text-accent-thrive", border: "rgba(125,212,163,0.3)", glow: "0 0 20px rgba(125,212,163,0.15)" },
  { min: 3, word: "SOLID BUILD", wordKey: "build.verdictSolid", subtitle: "Strong across the board", subtitleKey: "build.verdictSubSolid", accentClass: "text-accent-thrive", border: "rgba(125,212,163,0.25)", glow: "0 0 16px rgba(125,212,163,0.10)" },
  { min: 2, word: "MIXED BUILD", wordKey: "build.verdictMixed", subtitle: "Real strengths, real challenges", subtitleKey: "build.verdictSubMixed", accentClass: "text-accent-caution", border: "rgba(242,212,119,0.25)", glow: "0 0 16px rgba(242,212,119,0.10)" },
  { min: 0, word: "VULNERABLE BUILD", wordKey: "build.verdictVulnerable", subtitle: "Eyes open", subtitleKey: "build.verdictSubVulnerable", accentClass: "text-accent-alert", border: "rgba(244,169,126,0.25)", glow: "0 0 16px rgba(244,169,126,0.10)" },
] as const;
