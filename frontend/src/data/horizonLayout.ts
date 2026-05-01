/**
 * Pure-function lane assignment for the /branch-tree horizon map.
 *
 * Bucketing rule: destination SOC major group → product taxonomy bucket.
 * The older education-delta helpers are kept for legacy callers/tests, but
 * branch map grouping is SOC-taxonomy-driven.
 *
 * Within-lane sort (D#5): relatednessTier ASC (Primary-Short → Primary-Long
 * → Supplemental), then `relatedness` ASC as tiebreak (most-related first,
 * since `relatedness` is `best_index` where 1 = most related — D#17).
 *
 * relatednessTier (D#17) is derived from `relatedness` here on the frontend;
 * the API surfaces only the integer rank. Mirrors src/silver/onet_transformer.py:68-74.
 *
 * Lane cap (D#6): 6 chips. Overflow surfaces as "+N more" via `totalBeforeCap`.
 *
 * "Hide supplemental" filter (D#7): drops branches where the derived tier is
 * "Supplemental" before bucketing.
 */

import type { CareerBranch } from "@/types/build";

export type RollupKey =
  | "business"
  | "technical"
  | "arts"
  | "education"
  | "care"
  | "service"
  | "trades";

export type LaneId = RollupKey;
export type RelatednessTier = "Primary-Short" | "Primary-Long" | "Supplemental";

export interface BucketedLane {
  id: LaneId;
  branches: CareerBranch[];
  totalBeforeCap: number;
}

export type BucketedLanes = Record<LaneId, BucketedLane>;

const EDU_RANK: Record<string, number> = {
  "High school diploma or equivalent": 0,
  "No formal educational credential": 1,
  "Postsecondary nondegree award": 1,
  "Some college, no degree": 1,
  "Associate's degree": 2,
  "Bachelor's degree": 3,
  "Master's degree": 4,
  "Doctoral or professional degree": 5,
};

const RELATEDNESS_TIER_ORDER: Record<RelatednessTier, number> = {
  "Primary-Short": 0,
  "Primary-Long": 1,
  "Supplemental": 2,
};

const LANE_CAP = 6;
const PRIMARY_SHORT_MAX = 5;
const PRIMARY_LONG_MAX = 10;

export const SOC_ROLLUP_ORDER: readonly LaneId[] = [
  "business",
  "technical",
  "arts",
  "education",
  "care",
  "service",
  "trades",
] as const;

const EMPTY_BUCKETS = (): Record<LaneId, CareerBranch[]> => ({
  business: [],
  technical: [],
  arts: [],
  education: [],
  care: [],
  service: [],
  trades: [],
});

export function eduRank(educationLevelName: string | null | undefined): number | null {
  if (educationLevelName == null) return null;
  return EDU_RANK[educationLevelName] ?? null;
}

export function relatednessTier(
  relatedness: number | null | undefined,
): RelatednessTier | null {
  if (relatedness == null) return null;
  if (relatedness <= PRIMARY_SHORT_MAX) return "Primary-Short";
  if (relatedness <= PRIMARY_LONG_MAX) return "Primary-Long";
  return "Supplemental";
}

export function sortBranchesInLane(branches: CareerBranch[]): CareerBranch[] {
  return [...branches].sort((a, b) => {
    const ta = RELATEDNESS_TIER_ORDER[relatednessTier(a.relatedness) ?? "Supplemental"];
    const tb = RELATEDNESS_TIER_ORDER[relatednessTier(b.relatedness) ?? "Supplemental"];
    if (ta !== tb) return ta - tb;
    // `relatedness` is best_index (1 = most related), so ASC = most-related first.
    const ra = a.relatedness ?? Infinity;
    const rb = b.relatedness ?? Infinity;
    return ra - rb;
  });
}

export function bucketBranches(
  branches: CareerBranch[],
  _buildEdu: string | null | undefined,
  hideSupplemental: boolean,
  options: { laneCap?: number } = {},
): BucketedLanes {
  const cap = options.laneCap ?? LANE_CAP;
  const filtered = hideSupplemental
    ? branches.filter((b) => relatednessTier(b.relatedness) !== "Supplemental")
    : branches;
  const byLane = EMPTY_BUCKETS();
  for (const branch of filtered) {
    const lane = socRollup(branch.to_soc);
    if (lane !== null) byLane[lane].push(branch);
  }
  const out = SOC_ROLLUP_ORDER.reduce((acc, id) => {
    acc[id] = { id, branches: [], totalBeforeCap: 0 };
    return acc;
  }, {} as BucketedLanes);
  for (const laneId of SOC_ROLLUP_ORDER) {
    const sorted = sortBranchesInLane(byLane[laneId]);
    out[laneId] = {
      id: laneId,
      branches: sorted.slice(0, cap),
      totalBeforeCap: sorted.length,
    };
  }
  return out;
}

/**
 * Pick the dominant stat-delta from a CareerBranch — the largest abs(delta)
 * across ern/grw/hmn/res. Returns null when all four are null/zero.
 *
 * Note: roi is intentionally excluded from the chip badge per §1 success
 * criteria (stays "ern/grw/hmn/res only" since roi is a derived ratio
 * that conflates the cost axis with the earnings axis).
 */
export interface DominantDelta {
  stat: "ern" | "grw" | "hmn" | "res";
  value: number;
}

export function dominantStatDelta(branch: CareerBranch): DominantDelta | null {
  const candidates: DominantDelta[] = [];
  if (branch.delta_ern != null) candidates.push({ stat: "ern", value: branch.delta_ern });
  if (branch.delta_grw != null) candidates.push({ stat: "grw", value: branch.delta_grw });
  if (branch.delta_hmn != null) candidates.push({ stat: "hmn", value: branch.delta_hmn });
  if (branch.delta_res != null) candidates.push({ stat: "res", value: branch.delta_res });
  if (candidates.length === 0) return null;
  let best = candidates[0]!;
  for (const c of candidates.slice(1)) {
    if (Math.abs(c.value) > Math.abs(best.value)) best = c;
  }
  if (best.value === 0) return null;
  return best;
}

/**
 * Truncate a chip title to ≤ maxLen with ellipsis. Conservative on word
 * boundaries — only cuts mid-word when the last word itself is too long.
 */
export function truncateTitle(title: string, maxLen = 32): string {
  if (title.length <= maxLen) return title;
  const sliced = title.slice(0, maxLen - 1);
  const lastSpace = sliced.lastIndexOf(" ");
  if (lastSpace > maxLen / 2) {
    return `${sliced.slice(0, lastSpace)}…`;
  }
  return `${sliced}…`;
}

/**
 * Roll up a SOC code's major group (first 2 digits) to a 7-bucket
 * categorization for the chip badge: Business / Technical / Arts &
 * Creativity / Education & Community / Care / Service / Trades.
 *
 * Source taxonomy: `src/silver/bls_ooh_transformer.py:36-59`
 * (BLS 2018 SOC structure, 22 major groups).
 *
 * Bucket assignments:
 *   - Business: 11 Mgmt, 13 Business/Finance, 23 Legal, 41 Sales, 43 Office Admin
 *   - Technical: 15 Computer/Math, 17 Architecture/Engineering, 19 Sciences
 *   - Arts & Creativity: 27 Arts/Design/Entertainment/Sports/Media
 *   - Education & Community: 21 Community Service, 25 Education/Library
 *   - Care: 29 Healthcare Practitioners, 31 Healthcare Support, 33 Protective
 *   - Service: 35 Food, 37 Cleaning, 39 Personal Care
 *   - Trades: 45 Farming, 47 Construction, 49 Maintenance, 51 Production, 53 Transportation
 *
 * Returns null when soc is null/undefined or the major group is unknown
 * (defensive — covers future SOC revisions or malformed codes).
 */
const SOC_ROLLUP: Record<string, RollupKey> = {
  "11": "business",
  "13": "business",
  "23": "business",
  "41": "business",
  "43": "business",
  "15": "technical",
  "17": "technical",
  "19": "technical",
  "27": "arts",
  "21": "education",
  "25": "education",
  "29": "care",
  "31": "care",
  "33": "care",
  "35": "service",
  "37": "service",
  "39": "service",
  "45": "trades",
  "47": "trades",
  "49": "trades",
  "51": "trades",
  "53": "trades",
};

export function socRollup(soc: string | null | undefined): RollupKey | null {
  if (!soc) return null;
  const majorGroup = soc.slice(0, 2);
  return SOC_ROLLUP[majorGroup] ?? null;
}
