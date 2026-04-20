/**
 * Chapter Book — bucketing.
 *
 * Pure function. No I/O. Spec: docs/specs/feature-chapter-book.md §4
 * Service Changes (Bucketing Rules) + §2 Decisions #10, #11, #12, #14,
 * #15, #16.
 *
 * Takes the parent career + a list of branches, returns 2–4 chapters.
 */
import type { CareerBranch, CareerOutcome } from "@/types/build";
import type { StatKey } from "@/data/statExplanations";
import type { Chapter, ChapterTier } from "./types";
import { chapterCopy } from "./chapterCopy";

const GRAD_DEGREE_EDU = /^Master|^Doctoral/i;
const GRAD_DEGREE_UNLOCK = /Master|Doctor/i;

const TIER_ORDER: readonly ChapterTier[] = ["entry", "early", "mid", "senior"];
type NonAnchorTier = "early" | "mid" | "senior";
const NON_ANCHOR_TIERS: readonly NonAnchorTier[] = ["early", "mid", "senior"];

// Per-tier label composition. The terminating-ceiling case at the `early`
// tier composes `"1+ yr"` by stripping the upper bound from `"Years 1–4"`,
// per §3.6 — see composeTerminatingCeilingLabel below.
const DEFAULT_YEARS_LABEL: Record<ChapterTier, string> = {
  entry: chapterCopy.years.entry,
  early: chapterCopy.years.early,
  mid: chapterCopy.years.mid,
  senior: chapterCopy.years.senior,
};

// Chapter slot numbers are fixed by tier position.
const CHAPTER_NUMBER: Record<ChapterTier, 1 | 2 | 3 | 4> = {
  entry: 1,
  early: 2,
  mid: 3,
  senior: 4,
};

const TIER_LOWER_BOUND_YEARS: Record<ChapterTier, number> = {
  entry: 0,
  early: 1,
  mid: 4,
  senior: 8,
};

function requiresGradDegree(branch: CareerBranch): boolean {
  if (
    branch.related_education_level !== null &&
    GRAD_DEGREE_EDU.test(branch.related_education_level)
  ) {
    return true;
  }
  if (
    branch.related_education_level === null &&
    branch.unlock !== null &&
    GRAD_DEGREE_UNLOCK.test(branch.unlock)
  ) {
    return true;
  }
  return false;
}

function parentRequiresGradDegree(career: CareerOutcome): boolean {
  const edu = career.education_level_name;
  return edu !== null && GRAD_DEGREE_EDU.test(edu);
}

function branchDeltas(branch: CareerBranch): Partial<Record<StatKey, number>> {
  const entries: Array<[StatKey, number | null]> = [
    ["ern", branch.delta_ern],
    ["roi", branch.delta_roi],
    ["res", branch.delta_res],
    ["grw", branch.delta_grw],
    ["hmn", branch.delta_hmn],
  ];
  const out: Partial<Record<StatKey, number>> = {};
  for (const [key, value] of entries) {
    // Strip zeros and nulls — §3.4: delta pill row never renders "+0".
    if (value !== null && value !== 0) {
      out[key] = value;
    }
  }
  return out;
}

function parentStatsSnapshot(
  career: CareerOutcome,
): Partial<Record<StatKey, number>> {
  const out: Partial<Record<StatKey, number>> = {};
  const stats = career.stats;
  if (stats.ern !== null) out.ern = stats.ern;
  if (stats.roi !== null) out.roi = stats.roi;
  if (stats.res !== null) out.res = stats.res;
  if (stats.grw !== null) out.grw = stats.grw;
  if (stats.hmn !== null) out.hmn = stats.hmn;
  return out;
}

/**
 * Compose the years label for a terminating ceiling (Rule 6). The label
 * becomes "everything beyond the prior tier's lower bound," since a
 * labeled range like "Years 1–4" would contradict the "arc levels off"
 * title. Example: a ceiling firing at `early` reads "1+ yr".
 */
function composeTerminatingCeilingLabel(tier: ChapterTier): string {
  const bound = TIER_LOWER_BOUND_YEARS[tier];
  const unit = bound === 1 ? "yr" : "yrs";
  return `${bound}+ ${unit}`;
}

function pickRepresentative(
  branches: readonly CareerBranch[],
  tier: ChapterTier,
): CareerBranch | undefined {
  const pool = branches.filter((b) => b.experience_tier === tier);
  if (pool.length === 0) return undefined;
  // Sort by relatedness desc; tie-break by to_soc lexicographic asc
  // per §2 Decision #11. Treat null relatedness as -Infinity so a
  // missing score never outranks a real one.
  const sorted = [...pool].sort((a, b) => {
    const rA = a.relatedness ?? Number.NEGATIVE_INFINITY;
    const rB = b.relatedness ?? Number.NEGATIVE_INFINITY;
    if (rB !== rA) return rB - rA;
    return a.to_soc < b.to_soc ? -1 : a.to_soc > b.to_soc ? 1 : 0;
  });
  return sorted[0];
}

function makeAnchor(career: CareerOutcome): Chapter {
  return {
    number: 1,
    years_label: DEFAULT_YEARS_LABEL.entry,
    tier: "entry",
    kind: "anchor",
    title: career.occupation_title,
    soc: career.soc_code,
    what_changes: chapterCopy.anchor.what_changes,
    unlock: null,
    related_education_level: career.education_level_name,
    requires_grad_degree: parentRequiresGradDegree(career),
    deltas: {},
    stats_snapshot: parentStatsSnapshot(career),
  };
}

function makeRole(branch: CareerBranch, tier: ChapterTier): Chapter {
  const gradGated = requiresGradDegree(branch);
  return {
    number: CHAPTER_NUMBER[tier],
    years_label: DEFAULT_YEARS_LABEL[tier],
    tier,
    kind: gradGated ? "locked" : "role",
    title: branch.to_title,
    soc: branch.to_soc,
    // Branches carry what-changes in `unlock` only as a gate phrase, not
    // as narrative. §3 delegates narrative copy to the visionary/copywriter
    // — for now, role chapters use an empty string so the implementer sees
    // it's a known follow-up. The UI shows the role header + delta pills
    // even when what_changes is empty.
    what_changes: "",
    unlock: branch.unlock,
    related_education_level: branch.related_education_level,
    requires_grad_degree: gradGated,
    deltas: branchDeltas(branch),
  };
}

function makeTerminatingCeiling(tier: ChapterTier): Chapter {
  return {
    number: CHAPTER_NUMBER[tier],
    years_label: composeTerminatingCeilingLabel(tier),
    tier,
    kind: "ceiling",
    title: chapterCopy.ceiling.title,
    soc: null,
    what_changes: chapterCopy.ceiling.what_changes,
    unlock: null,
    related_education_level: null,
    requires_grad_degree: false,
    deltas: {},
  };
}

function makeBridgeCeiling(tier: ChapterTier): Chapter {
  return {
    number: CHAPTER_NUMBER[tier],
    years_label: DEFAULT_YEARS_LABEL[tier],
    tier,
    kind: "ceiling",
    title: chapterCopy.ceiling.title,
    soc: null,
    what_changes: chapterCopy.ceiling.what_changes,
    unlock: null,
    related_education_level: null,
    requires_grad_degree: false,
    deltas: {},
  };
}

export function bucketBranches(
  career: CareerOutcome,
  branches: readonly CareerBranch[],
): Chapter[] {
  // Rule 2: drop branches with null experience_tier (not rendered,
  // not counted).
  // Rule 3: drop self-referencing branches (Decision #15).
  const filtered = branches.filter(
    (b) =>
      b.experience_tier !== null &&
      TIER_ORDER.includes(b.experience_tier as ChapterTier) &&
      b.to_soc !== career.soc_code,
  );

  // Resolve per-tier representatives. undefined entries mean "no branch
  // in this tier" and will trigger ceiling synthesis.
  const reps: Record<NonAnchorTier, CareerBranch | undefined> = {
    early: pickRepresentative(filtered, "early"),
    mid: pickRepresentative(filtered, "mid"),
    senior: pickRepresentative(filtered, "senior"),
  };

  // Find the last non-anchor tier that still has a representative; all
  // tiers beyond it will be ceiling-terminating (Rule 6), and any empty
  // tier at or before it will be a ceiling-bridge (Rule 7).
  let lastFilledIndex = -1;
  for (let i = NON_ANCHOR_TIERS.length - 1; i >= 0; i -= 1) {
    const tier = NON_ANCHOR_TIERS[i] as NonAnchorTier;
    if (reps[tier] !== undefined) {
      lastFilledIndex = i;
      break;
    }
  }

  const chapters: Chapter[] = [makeAnchor(career)];

  if (lastFilledIndex === -1) {
    // Every non-anchor tier is empty — emit exactly one terminating
    // ceiling at the `early` tier (the first tier after anchor) and
    // stop. This is the minimum 2-chapter book per §3.6 empty state.
    chapters.push(makeTerminatingCeiling("early"));
    return chapters;
  }

  for (let i = 0; i < NON_ANCHOR_TIERS.length; i += 1) {
    const tier = NON_ANCHOR_TIERS[i] as NonAnchorTier;
    const rep = reps[tier];
    if (rep !== undefined) {
      chapters.push(makeRole(rep, tier));
      continue;
    }
    if (i < lastFilledIndex) {
      // Bridge ceiling (Rule 7) — a gap in the middle of the arc.
      chapters.push(makeBridgeCeiling(tier));
      continue;
    }
    // Terminating ceiling (Rule 6) — everything past this point is
    // absent; emit one ceiling and stop.
    chapters.push(makeTerminatingCeiling(tier));
    break;
  }

  return chapters;
}
