import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SelectedNodeCard, treeNodeToCareerOutcome } from "./SelectedNodeCard";
import type { Build } from "@/types/build";
import type { TreeNode } from "@/types/tree";

function makeBuild(): Build {
  return {
    build_id: "b-test",
    created_at: "2026-04-30T12:00:00Z",
    school_name: "State U",
    unitid: 999,
    major_text: "Finance",
    cipcode: "52.0801",
    program_name: "Finance, General",
    effort: "balanced",
    loan_pct: 0.5,
    career: {
      unitid: 999,
      institution_name: "State U",
      cipcode: "52.0801",
      program_name: "Finance, General",
      soc_code: "13-2051",
      occupation_title: "Financial Analyst",
      soc_major_group_name: "Business",
      median_annual_wage: 95570,
      earnings_1yr_median: 45000,
      earnings_1yr_p25: 35000,
      earnings_1yr_p75: 55000,
      debt_median: 25000,
      debt_to_earnings_annual: 0.56,
      education_level_name: "Bachelor's degree",
      growth_category: "Faster than average",
      net_price_annual: null,
      cost_of_attendance_annual: null,
      modeled_total_debt: null,
      debt_median_reference: null,
      institution_control: null,
      tuition_in_state: null,
      tuition_out_of_state: null,
      is_out_of_state: false,
      room_board_on_campus: null,
      stats: { ern: 7, roi: 6, res: 5, grw: 6, hmn: 4 },
      bosses: { ai: 4, loans: 3, market: 5, burnout: 6, ceiling: 4 },
      top_5_activities: [],
      top_human_activities: [],
      burnout_drivers: [],
      stats_available_count: 5,
      overall_confidence: "high",
      match_quality: null,
      substitution_applied: false,
      reported_cipcode: null,
      substituted_cipcode: null,
      data_caveat: null,
      loan_pct: 0.5,
    },
    gauntlet: { fights: [], wins: 0, losses: 0, draws: 0, unknown: 0, verdict: "" },
    branches: [],
    skill_recs: [],
    guidance: "",
    skills_crafted: [],
    skill_pool: [],
    next_steps: "",
  } as Build;
}

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    soc_code: "11-3031",
    title: "Financial Manager",
    level: 1,
    ern: null,
    roi: 7,
    res: 6,
    grw: 8,
    hmn: 5,
    median_wage: 140000,
    education: "Bachelor's degree",
    boss_ai: null,
    boss_loans: null,
    boss_market: null,
    boss_burnout: null,
    boss_ceiling: null,
    children: [],
    ...overrides,
  };
}

describe("treeNodeToCareerOutcome", () => {
  it("maps the four CareerCard-read fields verbatim", () => {
    const node = makeNode();
    const out = treeNodeToCareerOutcome(node, makeBuild());
    expect(out.soc_code).toBe("11-3031");
    expect(out.occupation_title).toBe("Financial Manager");
    expect(out.median_annual_wage).toBe(140000);
    expect(out.stats).toEqual({
      ern: null,
      roi: 7,
      res: 6,
      grw: 8,
      hmn: 5,
    });
  });

  it("preserves null ERN on L1/L2 nodes (program-specific data)", () => {
    const node = makeNode({ ern: null });
    const out = treeNodeToCareerOutcome(node, makeBuild());
    expect(out.stats.ern).toBeNull();
  });

  it("uses the node's education label for education_level_name", () => {
    const node = makeNode({ education: "Master's degree" });
    const out = treeNodeToCareerOutcome(node, makeBuild());
    expect(out.education_level_name).toBe("Master's degree");
  });
});

describe("SelectedNodeCard", () => {
  it("renders with data-soc matching the node SOC", () => {
    render(
      <SelectedNodeCard node={makeNode()} build={makeBuild()} picked={true} />,
    );
    const card = screen.getByTestId("selected-node-card");
    expect(card.getAttribute("data-soc")).toBe("11-3031");
  });

  it("renders the occupation title", () => {
    render(
      <SelectedNodeCard node={makeNode()} build={makeBuild()} picked={false} />,
    );
    expect(screen.getByText("Financial Manager")).toBeInTheDocument();
  });

  it("renders the wage formatted as dollars", () => {
    render(
      <SelectedNodeCard node={makeNode()} build={makeBuild()} picked={false} />,
    );
    expect(screen.getByText(/\$140,000\/yr median/)).toBeInTheDocument();
  });

  it("renders the education label", () => {
    render(
      <SelectedNodeCard
        node={makeNode({ education: "Master's degree" })}
        build={makeBuild()}
        picked={false}
      />,
    );
    expect(screen.getByText("Master's degree")).toBeInTheDocument();
  });

  it("does not render an ERN bar when ern is null (hideNullStats)", () => {
    render(
      <SelectedNodeCard
        node={makeNode({ ern: null })}
        build={makeBuild()}
        picked={false}
      />,
    );
    // The bar's stat label is "ERN" — should be absent.
    expect(screen.queryByText("ERN")).toBeNull();
    // But ROI / RES / GRW / HMN should still render.
    expect(screen.getByText("ROI")).toBeInTheDocument();
    expect(screen.getByText("RES")).toBeInTheDocument();
    expect(screen.getByText("GRW")).toBeInTheDocument();
    expect(screen.getByText("HMN")).toBeInTheDocument();
  });

  it("renders ERN when the node carries a value (root case)", () => {
    render(
      <SelectedNodeCard
        node={makeNode({ ern: 7 })}
        build={makeBuild()}
        picked={false}
      />,
    );
    expect(screen.getByText("ERN")).toBeInTheDocument();
  });
});
