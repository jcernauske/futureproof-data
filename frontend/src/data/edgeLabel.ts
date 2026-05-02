/**
 * T1.1 — Edge label selection.
 *
 * Picks the most striking delta to surface as a small pill on each
 * edge in the /future tree. Priority chain:
 *
 *   1. Education tier delta (non-zero)        → "+Master's"
 *   2. Pay delta (|Δ| ≥ $10,000)              → "+$24k" / "−$12k"
 *   3. Relatedness fallback                   → "Close" if rank ≤ 5; "Stretch" if rank ≥ 11
 *   4. Otherwise null — no pill renders
 *
 * Experience tier deltas were removed from the priority chain in
 * favor of the dedicated experience-range slider in the filter rail
 * — it's a stronger control surface for "what tier of jobs do I
 * want to see" than per-edge "Mid+" pills cluttering the canvas.
 *
 * The label kind drives pill color: improvement (green) for steps
 * that take the student forward (deeper degree, more pay, closer
 * match) and neutral (muted) for everything else.
 *
 * Number formatting (k-rounded for pills, full $ for hover) matches
 * T1.3 mini-compare for visual cohesion across the screen.
 */

import type { TreeNode } from "@/types/tree";

export type EdgeLabelKind =
  | "education"
  | "experience"
  | "pay"
  | "relatedness_close"
  | "relatedness_stretch";

export interface EdgeLabel {
  text: string;
  kind: EdgeLabelKind;
  isPositive: boolean;
}

const PAY_THRESHOLD = 10_000;

// Education hierarchy — index = depth. Anything not listed lands at -1
// and is treated as unknown for delta purposes.
const EDU_RANK: ReadonlyArray<string> = [
  "No formal educational credential",
  "High school diploma or equivalent",
  "Some college, no degree",
  "Postsecondary nondegree award",
  "Associate's degree",
  "Bachelor's degree",
  "Master's degree",
  "Doctoral or professional degree",
];

const EDU_LABEL_KEY: Record<string, string> = {
  "Bachelor's degree": "future.edge.degree.bachelors",
  "Master's degree": "future.edge.degree.masters",
  "Doctoral or professional degree": "future.edge.degree.doctorate",
  "Associate's degree": "future.edge.degree.associates",
};

function eduIndex(level: string | null | undefined): number {
  if (!level) return -1;
  return EDU_RANK.indexOf(level);
}

/** Round to nearest $1k; magnitude ≥ $1m flips to "Xm" form. */
export function formatPayDelta(deltaWage: number): string {
  const sign = deltaWage > 0 ? "+" : "−";
  const abs = Math.abs(deltaWage);
  if (abs >= 1_000_000) {
    return `${sign}$${(abs / 1_000_000).toFixed(1)}m`;
  }
  const k = Math.round(abs / 1_000);
  return `${sign}$${k}k`;
}

/** Full $-figure for hover expansion. Always signed. */
export function formatPayFull(deltaWage: number): string {
  const sign = deltaWage > 0 ? "+" : "−";
  return `${sign}$${Math.abs(deltaWage).toLocaleString()}`;
}

/** Translate-or-return helper that swallows missing keys gracefully. */
type Translator = (key: string) => string;

/**
 * Pick the most striking delta to surface on an edge from `parent` to
 * `child`. Returns null when no delta clears the visibility threshold.
 */
export function pickEdgeLabel(
  parent: TreeNode,
  child: TreeNode,
  t: Translator,
): EdgeLabel | null {
  // 1. Education delta — only meaningful when both sides are known.
  const parentEduIdx = eduIndex(parent.education);
  const childEduIdx = eduIndex(child.education);
  if (
    parentEduIdx !== -1 &&
    childEduIdx !== -1 &&
    parentEduIdx !== childEduIdx
  ) {
    const childEduKey = EDU_LABEL_KEY[child.education!];
    if (childEduKey) {
      const sign = childEduIdx > parentEduIdx ? "+" : "−";
      return {
        text: `${sign}${t(childEduKey)}`,
        kind: "education",
        isPositive: childEduIdx > parentEduIdx,
      };
    }
  }

  // 2. Pay delta — only render when |Δ| crosses the visibility threshold.
  if (parent.median_wage != null && child.median_wage != null) {
    const delta = child.median_wage - parent.median_wage;
    if (Math.abs(delta) >= PAY_THRESHOLD) {
      return {
        text: formatPayDelta(delta),
        kind: "pay",
        isPositive: delta > 0,
      };
    }
  }

  // 3. Relatedness fallback — only when the tier is informative.
  const rank = child.relatedness;
  if (rank != null) {
    if (rank <= 5) {
      return {
        text: t("future.edge.related.close"),
        kind: "relatedness_close",
        isPositive: true,
      };
    }
    if (rank >= 11) {
      return {
        text: t("future.edge.related.stretch"),
        kind: "relatedness_stretch",
        isPositive: false,
      };
    }
  }

  return null;
}

interface HoverContextEducation {
  kind: "education";
  /** i18n key when parent education is in the label map; null when we
   * fall back to the raw BLS string (BLS names are English-only). */
  fromKey: string | null;
  /** Raw label text for the from-side. Either resolved from i18n or
   * the raw BLS education string. */
  fromText: string;
  toKey: string;
  toText: string;
}
interface HoverContextExperience {
  kind: "experience";
  fromTierKey: string;
  toTierKey: string;
  yearsDelta: number | null;
}
interface HoverContextPay {
  kind: "pay";
  fromWage: number;
  toWage: number;
  delta: number;
}
interface HoverContextRelated {
  kind: "relatedness_close" | "relatedness_stretch";
  rank: number;
  total: number;
  label: string;
}

export type EdgeLabelHoverContext =
  | HoverContextEducation
  | HoverContextExperience
  | HoverContextPay
  | HoverContextRelated
  | null;

/**
 * Compute the hover-expansion context for the same parent/child pair.
 * Mirrors `pickEdgeLabel`'s priority chain so the hover detail
 * matches the pill text. Returns null when no pill would render.
 */
export function pickEdgeHover(
  parent: TreeNode,
  child: TreeNode,
): EdgeLabelHoverContext {
  const parentEduIdx = eduIndex(parent.education);
  const childEduIdx = eduIndex(child.education);
  // Match pickEdgeLabel's permissiveness — only require the CHILD to
  // be in EDU_LABEL_KEY (since that's what produces the pill text).
  // Parent falls back to the raw BLS string when missing from the
  // label map, so the hover expansion still has a "from → to" arrow
  // instead of returning null and collapsing the pill.
  if (
    parentEduIdx !== -1 &&
    childEduIdx !== -1 &&
    parentEduIdx !== childEduIdx &&
    parent.education &&
    child.education &&
    EDU_LABEL_KEY[child.education]
  ) {
    const fromKey = EDU_LABEL_KEY[parent.education] ?? null;
    return {
      kind: "education",
      fromKey,
      fromText: parent.education,
      toKey: EDU_LABEL_KEY[child.education]!,
      toText: child.education,
    };
  }

  if (parent.median_wage != null && child.median_wage != null) {
    const delta = child.median_wage - parent.median_wage;
    if (Math.abs(delta) >= PAY_THRESHOLD) {
      return {
        kind: "pay",
        fromWage: parent.median_wage,
        toWage: child.median_wage,
        delta,
      };
    }
  }

  const rank = child.relatedness;
  if (rank != null && (rank <= 5 || rank >= 11)) {
    return {
      kind: rank <= 5 ? "relatedness_close" : "relatedness_stretch",
      rank,
      total: 20,
      label: rank <= 5 ? "future.edge.related.close" : "future.edge.related.stretch",
    };
  }

  return null;
}
