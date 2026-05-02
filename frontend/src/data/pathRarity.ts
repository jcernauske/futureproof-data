/**
 * Path-rarity tiering — derives a single "how unusual is this trajectory"
 * label from the cumulative relatedness ranks along a path of TreeNodes.
 *
 * **Honest framing**: this is a SKILL-OVERLAP estimate, not real
 * transition frequency. We're using O*NET `best_index` (1 = closest
 * skill match, 20 = stretch ceiling) as the only path-shape signal we
 * have today. A "Long shot" path means "the cumulative skill distance
 * is large" — it does NOT mean "no one has ever done this." Real
 * frequency data would need a Census ACS PUMS / BLS Job-to-Job Flows
 * ingest (separate spec).
 *
 * Tiering rule: take the WORST hop along the path. The chain is only
 * as plausible as its weakest link.
 *
 *   max rank ≤ 5   → "direct"     (don't badge — absence is the signal)
 *   max rank ≤ 10  → "adjacent"   (badge: muted)
 *   max rank ≤ 15  → "stretch"    (badge: caution)
 *   max rank > 15  → "longshot"   (badge: alert)
 *
 * Null relatedness on any hop is skipped (treated as "we don't know").
 * If every hop is null we return null and no badge renders.
 */

import type { TreeNode } from "@/types/tree";

export type PathRarity = "direct" | "adjacent" | "stretch" | "longshot";

export interface PathRarityResult {
  tier: PathRarity;
  /** Worst (highest) relatedness rank across the non-root hops. */
  maxRank: number;
  /** Number of non-root hops counted. */
  hopCount: number;
}

/**
 * @param path TreeNode chain from root → ... → selected. Root is
 *   skipped (it has no parent and no relatedness rank). Returns null
 *   when the path has no non-root hops with known relatedness.
 */
export function computePathRarity(path: TreeNode[]): PathRarityResult | null {
  if (path.length < 2) return null;
  let maxRank = -Infinity;
  let hopCount = 0;
  for (let i = 1; i < path.length; i++) {
    const rank = path[i]!.relatedness;
    if (rank == null) continue;
    if (rank > maxRank) maxRank = rank;
    hopCount += 1;
  }
  if (hopCount === 0) return null;
  let tier: PathRarity;
  if (maxRank <= 5) tier = "direct";
  else if (maxRank <= 10) tier = "adjacent";
  else if (maxRank <= 15) tier = "stretch";
  else tier = "longshot";
  return { tier, maxRank, hopCount };
}
