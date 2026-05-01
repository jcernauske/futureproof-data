import { CareerCard } from "@/components/CareerCard";
import type { Build, CareerOutcome } from "@/types/build";
import type { TreeNode } from "@/types/tree";

interface SelectedNodeCardProps {
  /** Tree node to render — root, L1, or L2. */
  node: TreeNode;
  /** Build the tree was rooted on, used as fallback for root-level fields. */
  build: Build;
  /**
   * True when this card reflects an active user selection (vs. the
   * default root anchor). /future passes `selectedNodeId !== null`.
   */
  picked: boolean;
}

/**
 * /future card surface — shows the SOC card for whichever node the
 * user has anchored the chat to (or root by default).
 *
 * Reuses CareerCard (the same component /set-your-course renders for
 * career picks) by adapting TreeNode → CareerOutcome. The synthesized
 * CareerOutcome populates the four fields CareerCard actually reads
 * (soc_code, occupation_title, median_annual_wage, stats) and stubs
 * the rest with build-level or null defaults — pure type plumbing.
 *
 * ERN is null on L1 and L2 nodes by design (program-specific data
 * only exists at the root); CareerCard's hideNullStats prop drops the
 * empty bar instead of rendering "—".
 */
function treeNodeToCareerOutcome(
  node: TreeNode,
  build: Build,
): CareerOutcome {
  const career = build.career;
  return {
    // The four fields CareerCard actually reads.
    soc_code: node.soc_code,
    occupation_title: node.title,
    median_annual_wage: node.median_wage,
    stats: {
      ern: node.ern,
      roi: node.roi,
      res: node.res,
      grw: node.grw,
      hmn: node.hmn,
    },
    // Build-level fields — kept as-is so any future CareerCard
    // additions that read them don't crash. None are visible today.
    unitid: career.unitid,
    institution_name: career.institution_name,
    cipcode: career.cipcode,
    program_name: career.program_name,
    soc_major_group_name: career.soc_major_group_name,
    earnings_1yr_median: null,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: node.education,
    growth_category: null,
    net_price_annual: null,
    cost_of_attendance_annual: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    is_out_of_state: false,
    room_board_on_campus: null,
    bosses: {
      ai: null,
      loans: null,
      market: null,
      burnout: null,
      ceiling: null,
    },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: null,
    overall_confidence: null,
    match_quality: null,
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    loan_pct: build.loan_pct,
  };
}

export function SelectedNodeCard({
  node,
  build,
  picked,
}: SelectedNodeCardProps) {
  const career = treeNodeToCareerOutcome(node, build);
  return (
    <div data-testid="selected-node-card" data-soc={node.soc_code}>
      <CareerCard
        career={career}
        picked={picked}
        onSelect={() => {}}
        educationLabel={node.education}
        hideNullStats
      />
    </div>
  );
}

export { treeNodeToCareerOutcome };
