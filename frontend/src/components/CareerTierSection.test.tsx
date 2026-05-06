import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CareerTierSection } from "./CareerTierSection";
import type { CareerOutcome } from "@/types/build";

function makeCareer(soc: string, title: string): CareerOutcome {
  return {
    unitid: 1,
    institution_name: "U",
    cipcode: "11.0701",
    program_name: "CS",
    soc_code: soc,
    occupation_title: title,
    soc_major_group_name: null,
    median_annual_wage: 90000,
    earnings_1yr_median: null,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    net_price_annual: null,
    cost_of_attendance_annual: null,
    published_cost_4yr: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    room_board_on_campus: null,
    stats: { ern: 7, roi: 6, res: 5, grw: 6, aura: 5 },
    bosses: { ai: 5, loans: 3, market: 3, burnout: 4, ceiling: 4 },
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
    is_out_of_state: false,
    loan_pct: 0.5,
  };
}

describe("CareerTierSection", () => {
  const careers = [
    makeCareer("15-1252", "Software Developer"),
    makeCareer("15-2051", "Data Scientist"),
  ];

  it("renders careers with tier heading and count", () => {
    render(
      <CareerTierSection
        id="section-tier-common"
        label="Common"
        description="Most common paths"
        accent="common"
        careers={careers}
        pickedSoc={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("Common")).toBeInTheDocument();
    expect(screen.getByText("2 paths")).toBeInTheDocument();
    expect(screen.getByText("Software Developer")).toBeInTheDocument();
    expect(screen.getByText("Data Scientist")).toBeInTheDocument();
  });

  it("renders null when careers array is empty (no dead sections)", () => {
    const { container } = render(
      <CareerTierSection
        id="section-tier-common"
        label="Common"
        description="Most common paths"
        accent="common"
        careers={[]}
        pickedSoc={null}
        onSelect={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("calls onSelect when a career card is clicked", () => {
    const onSelect = vi.fn();
    render(
      <CareerTierSection
        id="section-tier-common"
        label="Common"
        description="Most common paths"
        accent="common"
        careers={careers}
        pickedSoc={null}
        onSelect={onSelect}
      />,
    );
    // CareerCard is a `<div role="button">` (so it can nest a real
    // sparkle <button> for Ask Gemma without violating button-in-button
    // semantics) — match by role, not tag.
    screen
      .getByText("Software Developer")
      .closest("[role=\"button\"]")!
      .dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onSelect).toHaveBeenCalledWith(careers[0]);
  });
});
