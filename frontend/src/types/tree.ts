/**
 * TypeScript types for the career branch tree API.
 * Matches the backend TreeNode model from career_tree.py.
 */

export interface TreeNode {
  soc_code: string;
  title: string;
  level: number;
  ern: number | null;
  roi: number | null;
  res: number | null;
  grw: number | null;
  hmn: number | null;
  median_wage: number | null;
  education: string | null;
  experience_years: number | null;
  experience_tier: string | null;
  /**
   * O*NET career_branches.best_index — relatedness rank where
   * 1 = closest match, 20 = stretch ceiling. Null on the root and
   * on any node whose source row lacked best_index.
   */
  relatedness: number | null;
  boss_ai: string | null;
  boss_loans: string | null;
  boss_market: string | null;
  boss_burnout: string | null;
  boss_ceiling: string | null;
  children: TreeNode[];
}

export interface TreeStats {
  total_nodes: number;
  max_depth_reached: number;
  mcp_calls: number;
  dead_ends: number;
  wall_clock_ms: number;
}

export interface TreeResponse {
  tree: TreeNode;
  stats: TreeStats;
}
