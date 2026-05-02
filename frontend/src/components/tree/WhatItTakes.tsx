import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { useT } from "@/i18n/useT";
import type { TreeNode } from "@/types/tree";

/**
 * T2.3 — Three-bullet "What it takes:" block on the SelectedNodeCard.
 * Renders only on a non-root active selection. Replaces the existing
 * single-line educationLabel in that case (root anchor keeps the
 * single line).
 *
 * Bullet rules:
 *   - Education: shown when both sides are known and non-equal
 *   - Experience: shown when both tiers are known and non-equal
 *   - Top stat shift: max |Δ| across res/grw/hmn (skips wage/roi —
 *     those duplicate the mini-compare strip)
 *
 * Glyph color rule per spec: `↑` always thrive — investment framing,
 * not delta framing. The mini-compare strip carries delta temperature.
 */

interface WhatItTakesProps {
  selected: TreeNode;
  root: TreeNode;
}

const TIER_LABEL_KEY: Record<string, string> = {
  entry: "future.edge.tier.entry",
  early: "future.edge.tier.early",
  mid: "future.edge.tier.mid",
  senior: "future.edge.tier.senior",
};

const EDU_LABEL_KEY: Record<string, string> = {
  "Bachelor's degree": "future.edge.degree.bachelors",
  "Master's degree": "future.edge.degree.masters",
  "Doctoral or professional degree": "future.edge.degree.doctorate",
  "Associate's degree": "future.edge.degree.associates",
};

interface Bullet {
  key: string;
  /** Inline label like "Education:" — rendered weight 600, text-secondary. */
  labelText: string;
  /** Inline value like "Bachelor's → Master's" — rendered weight 400, text-primary. */
  valueText: string;
}

/**
 * Split a localized template "Label: value" into the two parts the
 * spec wants styled separately. Splits on the first ": " — every
 * locale (en/es/ar) carries the colon separator, so this is robust
 * across translations.
 */
function splitLabelValue(combined: string): { labelText: string; valueText: string } {
  const sep = ": ";
  const idx = combined.indexOf(sep);
  if (idx === -1) {
    return { labelText: "", valueText: combined };
  }
  return {
    labelText: combined.slice(0, idx + 1),
    valueText: combined.slice(idx + sep.length),
  };
}

function pickTopStat(
  selected: TreeNode,
  root: TreeNode,
  t: (key: string) => string,
): Bullet | null {
  type Stat = { key: "res" | "grw" | "hmn"; labelKey: string };
  const candidates: Stat[] = [
    { key: "res", labelKey: "future.stat.aiResilient" },
    { key: "grw", labelKey: "future.stat.growth" },
    { key: "hmn", labelKey: "future.stat.humanWork" },
  ];
  let best: { stat: Stat; delta: number } | null = null;
  for (const stat of candidates) {
    const a = selected[stat.key];
    const b = root[stat.key];
    if (a == null || b == null) continue;
    const delta = a - b;
    if (Math.abs(delta) < 1) continue;
    if (best == null || Math.abs(delta) > Math.abs(best.delta)) {
      best = { stat, delta };
    }
  }
  if (best == null) return null;
  const sign = best.delta > 0 ? "+" : "−";
  const value = `${sign}${Math.abs(best.delta)}`;
  const combined = t("future.whatItTakes.topStat")
    .replace("{statName}", t(best.stat.labelKey))
    .replace("{delta}", value);
  return { key: "top-stat", ...splitLabelValue(combined) };
}

function buildBullets(
  selected: TreeNode,
  root: TreeNode,
  t: (key: string) => string,
): Bullet[] {
  const bullets: Bullet[] = [];

  // Education bullet
  if (
    selected.education &&
    root.education &&
    selected.education !== root.education
  ) {
    const fromKey = EDU_LABEL_KEY[root.education];
    const toKey = EDU_LABEL_KEY[selected.education];
    if (fromKey && toKey) {
      const combined = t("future.whatItTakes.education")
        .replace("{from}", t(fromKey))
        .replace("{to}", t(toKey));
      bullets.push({ key: "edu", ...splitLabelValue(combined) });
    }
  }

  // Experience bullet (rendered only when both tiers and a positive
  // year delta are known — investment framing, no negative deltas).
  if (
    selected.experience_tier &&
    root.experience_tier &&
    selected.experience_tier !== root.experience_tier
  ) {
    const fromKey = TIER_LABEL_KEY[root.experience_tier.toLowerCase()];
    const toKey = TIER_LABEL_KEY[selected.experience_tier.toLowerCase()];
    if (fromKey && toKey) {
      const yearsDelta =
        selected.experience_years != null && root.experience_years != null
          ? selected.experience_years - root.experience_years
          : null;
      if (yearsDelta == null || yearsDelta > 0) {
        const combined = t("future.whatItTakes.experience")
          .replace("{fromTier}", t(fromKey))
          .replace("{toTier}", t(toKey))
          .replace(
            "{years}",
            yearsDelta != null ? Math.round(yearsDelta).toString() : "?",
          );
        bullets.push({ key: "exp", ...splitLabelValue(combined) });
      }
    }
  }

  const top = pickTopStat(selected, root, t);
  if (top) bullets.push(top);

  return bullets;
}

export function WhatItTakes({ selected, root }: WhatItTakesProps) {
  const t = useT();
  const reducedMotion = useReducedMotion() ?? false;

  if (selected.soc_code === root.soc_code) return null;
  const bullets = buildBullets(selected, root, t);
  if (bullets.length === 0) return null;

  return (
    <section
      data-testid="what-it-takes"
      className="mt-4 mb-4"
    >
      <motion.h4
        className="font-body text-small font-bold text-text-primary mb-2"
        initial={reducedMotion ? false : { opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={reducedMotion ? { duration: 0 } : springs.smooth}
      >
        {t("future.whatItTakes.title")}
      </motion.h4>
      <ul className="flex flex-col gap-2">
        {bullets.map((bullet, i) => (
          <motion.li
            key={bullet.key}
            data-testid={`what-it-takes-${bullet.key}`}
            className="flex flex-row items-baseline gap-2"
            initial={reducedMotion ? false : { opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={
              reducedMotion ? { duration: 0 } : { ...springs.snappy, delay: 0.06 * i }
            }
          >
            <span
              aria-hidden="true"
              className="font-data text-[13px] font-bold text-accent-thrive"
            >
              ↑
            </span>
            {bullet.labelText && (
              <span className="font-body text-small font-semibold text-text-secondary">
                {bullet.labelText}
              </span>
            )}
            <span className="font-body text-small text-text-primary">
              {bullet.valueText}
            </span>
          </motion.li>
        ))}
      </ul>
    </section>
  );
}
