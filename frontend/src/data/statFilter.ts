/**
 * Stat-improvement filters for the /future tree.
 *
 * Each filter gates a branch on whether it strictly improves a
 * specific axis vs the root career:
 *
 *   "earnings"      → branch.median_wage > root.median_wage
 *   "ai_resilient"  → branch.res         > root.res         (RES = AI resistance)
 *   "growth"        → branch.grw         > root.grw         (GRW = BLS growth outlook)
 *
 * Semantics:
 *   - Within stat filters: AND. All selected stats must strictly
 *     improve. "Higher earnings AND faster growth" returns only paths
 *     that improve both.
 *   - Across category filters (vs educationFilter): also AND. A
 *     branch must satisfy education AND stat filters together.
 *
 * Null safety: if either side of a comparison is null the filter
 * returns false for that node — we can't claim improvement we don't
 * have data for. ERN is intentionally not a filter axis because the
 * absolute ERN stat is null on L1/L2 (program-specific).
 */

import type { TreeNode } from "@/types/tree";

export type StatFilter = "earnings" | "ai_resilient" | "growth";

/**
 * Inspect the (unfiltered) tree and return the set of IMPROVES
 * filters where at least one non-root branch beats the root on that
 * stat. Hides chips that would always render zero results — e.g. a
 * tree where no branch out-earns the root drops the "Higher pay"
 * chip from the rail.
 */
export function availableStatFilters(tree: TreeNode): Set<StatFilter> {
  const out = new Set<StatFilter>();
  const walk = (node: TreeNode, depth: number) => {
    if (depth > 0) {
      for (const f of ["earnings", "ai_resilient", "growth"] as const) {
        if (!out.has(f) && nodePassesStatFilter(node, tree, f)) out.add(f);
      }
    }
    for (const child of node.children) walk(child, depth + 1);
  };
  walk(tree, 0);
  return out;
}

function strictlyGreater(a: number | null, b: number | null): boolean {
  return a != null && b != null && a > b;
}

export function nodePassesStatFilter(
  node: TreeNode,
  root: TreeNode,
  filter: StatFilter,
): boolean {
  switch (filter) {
    case "earnings":
      return strictlyGreater(node.median_wage, root.median_wage);
    case "ai_resilient":
      return strictlyGreater(node.res, root.res);
    case "growth":
      return strictlyGreater(node.grw, root.grw);
  }
}

export function nodePassesAllStatFilters(
  node: TreeNode,
  root: TreeNode,
  filters: ReadonlySet<StatFilter>,
): boolean {
  if (filters.size === 0) return true;
  for (const f of filters) {
    if (!nodePassesStatFilter(node, root, f)) return false;
  }
  return true;
}

/**
 * Return a copy of the tree with non-matching nodes removed.
 *
 * **Path-permissive recursion** — an L1 branch is kept when it
 * improves over the root OR when at least one of its L2 children does.
 * This treats a non-improving L1 as a transit "stepping stone" to a
 * matching destination (e.g. Public Relations Specialists $67k ↦
 * Chief Executives $206k under a "Higher earnings" filter — the L1
 * isn't itself an improvement but the L2 absolutely is). Aligns the
 * filter with the tour-chip ranking, which scans all visible nodes.
 *
 * Specifics:
 *   - Root is always preserved (the comparison reference, not subject
 *     to the filter).
 *   - L1 branches kept iff they pass ALL active stat filters OR any
 *     L2 child passes.
 *   - L2 endpoints kept iff they themselves pass — the original
 *     honesty guarantee. Caught case: Sales Managers $138k passing
 *     while its Customer Service Rep $42k child rendered as a kid.
 *   - L1s with no L2 children are kept iff they themselves pass.
 *   - When no filters are active the tree is returned unchanged.
 */
export function filterTreeByStats(
  tree: TreeNode,
  filters: ReadonlySet<StatFilter>,
): TreeNode {
  if (filters.size === 0) return tree;
  const keptL1: TreeNode[] = [];
  for (const branch of tree.children) {
    const keptL2 = branch.children.filter((leaf) =>
      nodePassesAllStatFilters(leaf, tree, filters),
    );
    const branchPasses = nodePassesAllStatFilters(branch, tree, filters);
    if (!branchPasses && keptL2.length === 0) continue;
    keptL1.push({ ...branch, children: keptL2 });
  }
  return {
    ...tree,
    children: keptL1,
  };
}
