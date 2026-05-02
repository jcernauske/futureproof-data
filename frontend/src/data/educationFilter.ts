/**
 * Education-level filters for the /future tree.
 *
 * The data source is the BLS "education_level_name" field (carried on
 * each TreeNode as `education`). BLS lumps PhDs, MDs, JDs, DDS, etc.
 * into a single "Doctoral or professional degree" bucket — there is
 * no clean way to split PhD from professional school with this data.
 * The three filter buckets below match the data verbatim:
 *
 *   "bachelors"  → Bachelor's degree and below (sub-degree included)
 *   "masters"    → Master's degree
 *   "doctoral"   → Doctoral or professional degree (PhD + MD + JD + …)
 *
 * Filters are multi-select and OR'd together. When zero filters are
 * active the tree is unfiltered (default state). The root is always
 * preserved — the student's anchor career is not subject to the
 * filter.
 */

import type { TreeNode } from "@/types/tree";

export type EducationFilter = "bachelors" | "masters" | "doctoral";

/**
 * Inspect the (unfiltered) tree and return the set of education
 * filters that would match at least one branch or endpoint. Used by
 * the desktop filter rail to skip rendering chips that wouldn't do
 * anything — saves vertical real estate when the source tree lacks
 * coverage for a given degree level.
 */
export function availableEducationFilters(
  tree: import("@/types/tree").TreeNode,
): Set<EducationFilter> {
  const out = new Set<EducationFilter>();
  const walk = (node: import("@/types/tree").TreeNode, depth: number) => {
    if (depth > 0) {
      // Root is excluded — it's the reference, not a filter target.
      for (const f of ["bachelors", "masters", "doctoral"] as const) {
        if (!out.has(f) && nodeMatchesFilter(node, f)) out.add(f);
      }
    }
    for (const child of node.children) walk(child, depth + 1);
  };
  walk(tree, 0);
  return out;
}

const BACHELORS_OR_BELOW: ReadonlySet<string> = new Set([
  "Bachelor's degree",
  "Associate's degree",
  "Postsecondary nondegree award",
  "Some college, no degree",
  "High school diploma or equivalent",
  "No formal educational credential",
]);

export function nodeMatchesFilter(
  node: TreeNode,
  filter: EducationFilter,
): boolean {
  const edu = node.education;
  if (!edu) return false;
  switch (filter) {
    case "bachelors":
      return BACHELORS_OR_BELOW.has(edu);
    case "masters":
      return edu === "Master's degree";
    case "doctoral":
      return edu === "Doctoral or professional degree";
  }
}

export function nodeMatchesAny(
  node: TreeNode,
  filters: ReadonlySet<EducationFilter>,
): boolean {
  if (filters.size === 0) return true;
  for (const f of filters) {
    if (nodeMatchesFilter(node, f)) return true;
  }
  return false;
}

/**
 * Return a copy of the tree with non-matching nodes removed.
 *
 * **Path-permissive recursion** — a branch is kept either when it
 * matches the filter directly OR when at least one of its L2 children
 * matches. This treats the L1 as a transit "stepping stone" to a
 * matching destination so a Master's-level L2 isn't pruned just
 * because the only route to it is through a Bachelor's-level L1. The
 * tour-chip ranking already considers all visible nodes, so this
 * keeps the filter and the tour aligned.
 *
 * Specifics:
 *   - Root is always preserved (anchor career, not subject to filter).
 *   - L1 branches kept iff they match the filter OR any of their
 *     L2 children match.
 *   - L2 endpoints kept iff they themselves match — mismatched L2s
 *     under a matched L1 are still pruned (the original honesty
 *     guarantee: don't render Bachelor's-only L2s under a "Master's
 *     required" filter).
 *   - L1s with no L2 children are kept iff they themselves match.
 *   - When no filters are active the tree is returned unchanged.
 */
export function filterTreeByEducation(
  tree: TreeNode,
  filters: ReadonlySet<EducationFilter>,
): TreeNode {
  if (filters.size === 0) return tree;
  const keptL1: TreeNode[] = [];
  for (const branch of tree.children) {
    const keptL2 = branch.children.filter((leaf) =>
      nodeMatchesAny(leaf, filters),
    );
    const branchMatches = nodeMatchesAny(branch, filters);
    if (!branchMatches && keptL2.length === 0) continue;
    keptL1.push({ ...branch, children: keptL2 });
  }
  return {
    ...tree,
    children: keptL1,
  };
}
