/**
 * Boss-outcome ("SURVIVES") filter for the /future tree.
 *
 * Trimmed to the three boss outcomes that carry real signal in the
 * tree payload (per @fp-data-reviewer 2026-05-01):
 *
 *   "boss_ai"       → boss_ai
 *   "boss_market"   → boss_market
 *   "boss_burnout"  → boss_burnout
 *
 * `boss_loans` and `boss_ceiling` were dropped because real data
 * resolves them to "unknown" for ~100% of non-root nodes — every
 * activated chip would hide every branch (worse UX than no chip).
 *
 * Semantics — match `educationFilter.ts` / `statFilter.ts`:
 *   - Within boss filters: AND. All selected bosses must "survive".
 *   - Across to other categories: AND.
 *   - Survival = outcome ∈ {"win", "draw"}. "unknown" intentionally
 *     fails — we don't claim survival we can't compute.
 */

import type { TreeNode } from "@/types/tree";

export type BossFilter = "boss_ai" | "boss_market" | "boss_burnout";

/**
 * Inspect the (unfiltered) tree and return the set of SURVIVES
 * filters that would match at least one branch or endpoint. Skips
 * chips for bosses whose outcome is "unknown" or "lose" everywhere
 * (the chip would just nuke the whole tree). Excludes the root.
 */
export function availableBossFilters(tree: TreeNode): Set<BossFilter> {
  const out = new Set<BossFilter>();
  const walk = (node: TreeNode, depth: number) => {
    if (depth > 0) {
      for (const f of ["boss_ai", "boss_market", "boss_burnout"] as const) {
        if (!out.has(f) && nodePassesBossFilter(node, f)) out.add(f);
      }
    }
    for (const child of node.children) walk(child, depth + 1);
  };
  walk(tree, 0);
  return out;
}

const SURVIVES = new Set<string>(["win", "draw"]);

export function nodePassesBossFilter(
  node: TreeNode,
  filter: BossFilter,
): boolean {
  const outcome = node[filter];
  return outcome != null && SURVIVES.has(outcome);
}

export function nodePassesAllBossFilters(
  node: TreeNode,
  filters: ReadonlySet<BossFilter>,
): boolean {
  if (filters.size === 0) return true;
  for (const f of filters) {
    if (!nodePassesBossFilter(node, f)) return false;
  }
  return true;
}

/**
 * Recursive — applies the filter to L1 AND L2. Mirrors education /
 * stat filter semantics so a kept L1 with mismatching L2s prunes
 * those L2s rather than rendering them as visible exceptions.
 *
 *   - Root is always preserved (the anchor career; not subject to
 *     the filter — it IS the reference).
 *   - L1 branches kept iff they pass ALL active filters.
 *   - L2 endpoints kept iff they pass too.
 *   - L1 with zero passing L2s is retained (it itself satisfies).
 *   - When no filters are active the tree is returned unchanged.
 */
export function filterTreeByBoss(
  tree: TreeNode,
  filters: ReadonlySet<BossFilter>,
): TreeNode {
  if (filters.size === 0) return tree;
  const keptL1 = tree.children
    .filter((branch) => nodePassesAllBossFilters(branch, filters))
    .map((branch) => ({
      ...branch,
      children: branch.children.filter((leaf) =>
        nodePassesAllBossFilters(leaf, filters),
      ),
    }));
  return {
    ...tree,
    children: keptL1,
  };
}
