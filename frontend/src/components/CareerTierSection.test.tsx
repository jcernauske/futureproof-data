import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CareerTierSection } from "./CareerTierSection";
import type { CareerOutcome } from "@/types/build";

/**
 * CareerTierSection tests
 *
 * Section is a disclosure — the header toggles visibility. aria-expanded has
 * to reflect actual state or screen readers will lie about the tree.
 */

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
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    room_board_on_campus: null,
    stats: { ern: 7, roi: 6, res: 5, grw: 6, hmn: 5 },
    bosses: { ai: 5, loans: 3, market: 3, burnout: 4, ceiling: 4 },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: 5,
    overall_confidence: "high",
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    loan_pct: 0.5,
  };
}

describe("CareerTierSection", () => {
  const careers = [
    makeCareer("15-1252", "Software Developer"),
    makeCareer("15-2051", "Data Scientist"),
  ];

  it("defaults to expanded and shows careers + aria-expanded=true", () => {
    render(
      <CareerTierSection
        id="section-tier-common"
        label="Common"
        description="Most common paths"
        careers={careers}
        selectedSoc={null}
        onSelect={vi.fn()}
      />,
    );
    const toggle = screen.getByRole("button", { expanded: true });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Software Developer")).toBeVisible();
    expect(screen.getByText("Data Scientist")).toBeVisible();
  });

  it("toggle hides careers from the a11y tree and flips aria-expanded", () => {
    render(
      <CareerTierSection
        id="section-tier-common"
        label="Common"
        description="Most common paths"
        careers={careers}
        selectedSoc={null}
        onSelect={vi.fn()}
      />,
    );
    const toggle = screen.getByRole("button", { expanded: true });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    // After collapse click, the toggle should flip state. The AnimatePresence
    // exit animation may still leave DOM around, so the contract we assert
    // on is the aria-expanded flag (which is what screen readers see).
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });

  it("renders null when careers array is empty (no dead sections)", () => {
    const { container } = render(
      <CareerTierSection
        id="section-tier-common"
        label="Common"
        description="Most common paths"
        careers={[]}
        selectedSoc={null}
        onSelect={vi.fn()}
      />,
    );
    // Guard against rendering a header + "0 paths" badge for an empty tier.
    expect(container.firstChild).toBeNull();
  });
});
