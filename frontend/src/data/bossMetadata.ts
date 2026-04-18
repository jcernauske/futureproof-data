import type { BossId } from "@/types/build";

interface BossMetadata {
  id: BossId;
  label: string;
  emoji: string;
  subtitle: string;
  colorToken: string;
  glowToken: string;
  bgWash: string;
}

export const BOSS_ORDER: BossId[] = ["ai", "loans", "market", "burnout", "ceiling"];

export const BOSS_METADATA: Record<BossId, BossMetadata> = {
  ai: {
    id: "ai",
    label: "Fight AI",
    emoji: "\u{1F916}",
    subtitle: "How safe is this career from automation?",
    colorToken: "text-boss-ai",
    glowToken: "shadow-glow-insight",
    bgWash: "rgba(184, 169, 232, 0.08)",
  },
  loans: {
    id: "loans",
    label: "Fight Student Loans",
    emoji: "\u{1F4B0}",
    subtitle: "Can your earnings handle the debt?",
    colorToken: "text-boss-loans",
    glowToken: "shadow-glow-alert",
    bgWash: "rgba(244, 169, 126, 0.08)",
  },
  market: {
    id: "market",
    label: "Fight the Market",
    emoji: "\u{1F4C8}",
    subtitle: "Is this field growing or shrinking?",
    colorToken: "text-boss-market",
    glowToken: "shadow-glow-info",
    bgWash: "rgba(123, 184, 224, 0.08)",
  },
  burnout: {
    id: "burnout",
    label: "Fight Burnout",
    emoji: "\u{1F525}",
    subtitle: "How sustainable is this work long-term?",
    colorToken: "text-boss-burnout",
    glowToken: "shadow-glow-empathy",
    bgWash: "rgba(232, 139, 169, 0.08)",
  },
  ceiling: {
    id: "ceiling",
    label: "Fight the Ceiling",
    emoji: "\u{1F4CA}",
    subtitle: "How high can your earnings go?",
    colorToken: "text-boss-ceiling",
    glowToken: "shadow-glow-info",
    bgWash: "rgba(196, 191, 176, 0.08)",
  },
};

export const RESULT_COLORS = {
  win: "accent-thrive",
  lose: "accent-alert",
  draw: "accent-caution",
  unknown: "accent-info",
} as const;

export const VERDICT_COLORS: Record<string, string> = {
  DOMINANT: "text-accent-thrive",
  SOLID: "text-accent-thrive",
  MIXED: "text-accent-caution",
  VULNERABLE: "text-accent-alert",
};

export function getVerdictColor(verdict: string): string {
  const firstWord = verdict.split(" ")[0]?.toUpperCase() ?? "";
  return VERDICT_COLORS[firstWord] ?? "text-text-secondary";
}
