/**
 * Experience tier range filter for the /future tree.
 *
 * Discrete 4-step scale: entry < early < mid < senior. The filter
 * is a [minIdx, maxIdx] window over those indices — only branches
 * whose `experience_tier` falls inside the window are kept. Branches
 * with NULL experience_tier are NEVER filtered (treated as "unknown
 * — keep visible") so we don't hide nodes whose ETE coverage is
 * missing from O*NET.
 *
 * Path-permissive recursion mirrors educationFilter / statFilter:
 * an L1 is kept if it passes OR any of its L2 children passes. The
 * L1 acts as a transit stepping stone to a matching destination.
 */

import type { TreeNode } from "@/types/tree";

export const EXPERIENCE_TIERS = ["entry", "early", "mid", "senior"] as const;
export type ExperienceTier = (typeof EXPERIENCE_TIERS)[number];

/** Tuple of tier indices, both inclusive. Default = full range = no filter. */
export type ExperienceRange = readonly [number, number];

export const EXPERIENCE_RANGE_FULL: ExperienceRange = [
  0,
  EXPERIENCE_TIERS.length - 1,
] as const;

export function isFullRange(range: ExperienceRange): boolean {
  return range[0] === 0 && range[1] === EXPERIENCE_TIERS.length - 1;
}

function tierIndex(tier: string | null | undefined): number | null {
  if (!tier) return null;
  const idx = (EXPERIENCE_TIERS as readonly string[]).indexOf(tier.toLowerCase());
  return idx === -1 ? null : idx;
}

export function nodePassesExperienceRange(
  node: TreeNode,
  range: ExperienceRange,
): boolean {
  const idx = tierIndex(node.experience_tier);
  if (idx == null) return true; // unknown tier never gates
  return idx >= range[0] && idx <= range[1];
}

/**
 * Path-permissive recursion. L1 kept iff it passes OR any L2 child
 * passes. L2 kept iff it passes. Identity tree returned when the
 * range is the full domain (no-op fast path).
 */
export function filterTreeByExperience(
  tree: TreeNode,
  range: ExperienceRange,
): TreeNode {
  if (isFullRange(range)) return tree;
  const keptL1: TreeNode[] = [];
  for (const branch of tree.children) {
    const keptL2 = branch.children.filter((leaf) =>
      nodePassesExperienceRange(leaf, range),
    );
    const branchPasses = nodePassesExperienceRange(branch, range);
    if (!branchPasses && keptL2.length === 0) continue;
    keptL1.push({ ...branch, children: keptL2 });
  }
  return { ...tree, children: keptL1 };
}
