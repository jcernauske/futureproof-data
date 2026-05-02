/**
 * T1.2 — Tour chip ranking functions.
 *
 * Each tour returns the top-N React Flow node IDs to flash via
 * BranchHighlightDriver. Rankings run against the *current* tree
 * (post-filter). Tour chips don't reshape the tree — they highlight
 * the top picks for a question.
 *
 * Node ID conventions mirror `treeFlowLayout.ts`:
 *   L1 career:   `career-${soc}-${branchIdx}`
 *   L2 endpoint: `endpoint-${soc}-${branchIdx}-${epIdx}`
 * The root is never a flash target — tours surface where the student
 * could go, not where they are.
 */

import type { TreeNode } from "@/types/tree";

export type TourId =
  | "highest_ceiling"
  | "ai_resilient"
  | "fastest_to_mid"
  | "biggest_pay_jump";

interface FlatNode {
  id: string;
  node: TreeNode;
}

const TIER_RANK: Record<string, number> = {
  entry: 0,
  early: 1,
  mid: 2,
  senior: 3,
};

function flattenForTour(tree: TreeNode): FlatNode[] {
  const out: FlatNode[] = [];
  tree.children.forEach((branch, branchIdx) => {
    out.push({ id: `career-${branch.soc_code}-${branchIdx}`, node: branch });
    branch.children.forEach((ep, epIdx) => {
      out.push({
        id: `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`,
        node: ep,
      });
    });
  });
  return out;
}

function topByDesc<T>(
  items: T[],
  key: (t: T) => number | null,
  topN: number,
): T[] {
  return items
    .filter((t) => key(t) != null)
    .sort((a, b) => (key(b)! - key(a)!))
    .slice(0, topN);
}

export function rankNodesForTour(
  tour: TourId,
  tree: TreeNode,
  topN: number = 3,
): string[] {
  const flat = flattenForTour(tree);
  if (flat.length === 0) return [];

  switch (tour) {
    case "highest_ceiling": {
      return topByDesc(flat, (f) => f.node.median_wage, topN).map((f) => f.id);
    }
    case "ai_resilient": {
      // Sort by res desc, tiebreak by median_wage desc.
      return flat
        .filter((f) => f.node.res != null)
        .sort((a, b) => {
          const dr = (b.node.res ?? 0) - (a.node.res ?? 0);
          if (dr !== 0) return dr;
          return (b.node.median_wage ?? 0) - (a.node.median_wage ?? 0);
        })
        .slice(0, topN)
        .map((f) => f.id);
    }
    case "fastest_to_mid": {
      // Sort by experience tier asc (entry < early < mid < senior),
      // tiebreak by relatedness asc (closest first). Skip rows with
      // no tier info — the tour is only meaningful when we know.
      return flat
        .filter((f) => f.node.experience_tier != null)
        .sort((a, b) => {
          const ta = TIER_RANK[a.node.experience_tier!.toLowerCase()] ?? 99;
          const tb = TIER_RANK[b.node.experience_tier!.toLowerCase()] ?? 99;
          if (ta !== tb) return ta - tb;
          const ra = a.node.relatedness ?? 99;
          const rb = b.node.relatedness ?? 99;
          return ra - rb;
        })
        .slice(0, topN)
        .map((f) => f.id);
    }
    case "biggest_pay_jump": {
      const rootWage = tree.median_wage ?? 0;
      return topByDesc(
        flat,
        (f) => (f.node.median_wage != null ? f.node.median_wage - rootWage : null),
        topN,
      ).map((f) => f.id);
    }
  }
}

export const TOUR_LABEL_KEYS: Record<TourId, string> = {
  highest_ceiling: "future.tour.highestCeiling",
  ai_resilient: "future.tour.aiResilient",
  fastest_to_mid: "future.tour.fastestToMid",
  biggest_pay_jump: "future.tour.biggestPayJump",
};
