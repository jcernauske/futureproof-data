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
 * Return a copy of the tree with non-matching L1 branches removed.
 *   - Root is always preserved (anchor career, not subject to filter).
 *   - L1 branches are kept iff they match any active filter.
 *   - L2 children come along with their L1 parent — when the L1 is
 *     kept they are kept, when the L1 is dropped they are dropped.
 *   - When no filters are active the tree is returned unchanged.
 */
export function filterTreeByEducation(
  tree: TreeNode,
  filters: ReadonlySet<EducationFilter>,
): TreeNode {
  if (filters.size === 0) return tree;
  const keptChildren = tree.children.filter((branch) =>
    nodeMatchesAny(branch, filters),
  );
  return {
    ...tree,
    children: keptChildren,
  };
}
