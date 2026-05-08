import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CareerCard } from "./CareerCard";
import type { CareerOutcome } from "@/types/build";

function makeCareer(overrides: Partial<CareerOutcome> = {}): CareerOutcome {
  return {
    unitid: 1,
    institution_name: "Test U",
    cipcode: "11.0701",
    program_name: "CS",
    soc_code: "15-1252",
    occupation_title: "Software Developers",
    soc_major_group_name: null,
    median_annual_wage: 130_000,
    wage_p10: null,
    wage_p25: null,
    wage_p75: null,
    wage_p90: null,
    earnings_1yr_median: null,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    work_experience_code: null,
    net_price_annual: null,
    cost_of_attendance_annual: null,
    published_cost_4yr: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    is_out_of_state: false,
    room_board_on_campus: null,
    roi_cost_basis: null,
    financed_dte: null,
    stats: { ern: null, roi: null, res: null, grw: null, aura: null },
    bosses: { ai: null, loans: null, market: null, burnout: null, ceiling: null },
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
    loan_pct: 1.0,
    ...overrides,
  };
}

describe("CareerCard — salary range priority chain", () => {
  it("priority 1: OEWS p25–p75 wins for long-term careers (work_experience_code=1)", () => {
    render(
      <CareerCard
        career={makeCareer({
          // 5+ yrs required → typical range (p25–p75).
          work_experience_code: 1,
          wage_p25: 98_000,
          wage_p75: 168_000,
          // Scorecard data also present — must be ignored.
          earnings_1yr_p25: 60_000,
          earnings_1yr_p75: 90_000,
          earnings_1yr_median: 75_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/\$98,000\s+–\s+\$168,000/)).toBeInTheDocument();
    expect(screen.getByText("typical range")).toBeInTheDocument();
    // Scorecard fallback row must NOT render.
    expect(screen.queryByText(/\$60,000\s+–\s+\$90,000/)).not.toBeInTheDocument();
    expect(screen.queryByText("year one")).not.toBeInTheDocument();
  });

  it("priority 2: Scorecard p25–p75 wins when OEWS missing", () => {
    render(
      <CareerCard
        career={makeCareer({
          wage_p25: null,
          wage_p75: null,
          earnings_1yr_p25: 60_000,
          earnings_1yr_p75: 90_000,
          earnings_1yr_median: 75_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/\$60,000\s+–\s+\$90,000/)).toBeInTheDocument();
    expect(screen.getByText("year one")).toBeInTheDocument();
    expect(screen.queryByText("typical range")).not.toBeInTheDocument();
  });

  it("priority 3: Scorecard median when neither range available", () => {
    render(
      <CareerCard
        career={makeCareer({
          wage_p25: null,
          wage_p75: null,
          earnings_1yr_p25: null,
          earnings_1yr_p75: null,
          earnings_1yr_median: 75_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("$75,000")).toBeInTheDocument();
    expect(screen.getByText("year one")).toBeInTheDocument();
  });

  it("priority 4: omits salary row when nothing is available", () => {
    render(
      <CareerCard
        career={makeCareer({
          median_annual_wage: null,
          wage_p25: null,
          wage_p75: null,
          earnings_1yr_p25: null,
          earnings_1yr_p75: null,
          earnings_1yr_median: null,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.queryByText("typical range")).not.toBeInTheDocument();
    expect(screen.queryByText("year one")).not.toBeInTheDocument();
    expect(screen.queryByText("mid-career")).not.toBeInTheDocument();
  });

  it("renders mid-career row alongside the salary range when median_annual_wage is set", () => {
    render(
      <CareerCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p25: 98_000,
          wage_p75: 168_000,
          median_annual_wage: 130_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("$130,000")).toBeInTheDocument();
    expect(screen.getByText("mid-career")).toBeInTheDocument();
  });

  it("requires BOTH wage_p25 and wage_p75 for the OEWS typical-range row to appear", () => {
    // Only one of the OEWS bounds present → fall through to Scorecard.
    render(
      <CareerCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p25: 98_000,
          wage_p75: null,
          earnings_1yr_p25: 60_000,
          earnings_1yr_p75: 90_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.queryByText("typical range")).not.toBeInTheDocument();
    expect(screen.getByText(/\$60,000\s+–\s+\$90,000/)).toBeInTheDocument();
  });
});

describe("CareerCard — experience-aware OEWS branching", () => {
  // Entry-accessible careers (work_experience_code 2, 3, or null) show
  // the OEWS p10–p25 "starting range" instead of p25–p75 "typical range",
  // so a year-one student doesn't see currently-working incumbents'
  // mid-career percentiles framed as their first paycheck.
  it("entry-accessible (code 3, None required) renders p10–p25 starting range", () => {
    render(
      <CareerCard
        career={makeCareer({
          work_experience_code: 3,
          wage_p10: 45_000,
          wage_p25: 62_000,
          wage_p75: 110_000,
          wage_p90: 140_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/\$45,000\s+–\s+\$62,000/)).toBeInTheDocument();
    expect(screen.getByText("starting range")).toBeInTheDocument();
    expect(screen.queryByText("typical range")).not.toBeInTheDocument();
  });

  it("entry-accessible (code 2, <5 yrs) renders p10–p25 starting range", () => {
    render(
      <CareerCard
        career={makeCareer({
          work_experience_code: 2,
          wage_p10: 50_000,
          wage_p25: 70_000,
          wage_p75: 120_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/\$50,000\s+–\s+\$70,000/)).toBeInTheDocument();
    expect(screen.getByText("starting range")).toBeInTheDocument();
  });

  it("long-term (code 1, 5+ yrs) renders p25–p75 typical range", () => {
    // Regression: incumbent percentiles for a 5+ yr role still surface
    // as "typical" (mid-career) — not "starting".
    render(
      <CareerCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p10: 70_000,
          wage_p25: 98_000,
          wage_p75: 168_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/\$98,000\s+–\s+\$168,000/)).toBeInTheDocument();
    expect(screen.getByText("typical range")).toBeInTheDocument();
    expect(screen.queryByText("starting range")).not.toBeInTheDocument();
  });

  it("null work_experience_code is treated as early-career (p10–p25 starting)", () => {
    // Per project memory feedback_no_substitution_caveat we don't render
    // a "limited data" warning — null silently joins early-career so the
    // starting-range data still surfaces.
    render(
      <CareerCard
        career={makeCareer({
          work_experience_code: null,
          wage_p10: 40_000,
          wage_p25: 58_000,
          wage_p75: 105_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText(/\$40,000\s+–\s+\$58,000/)).toBeInTheDocument();
    expect(screen.getByText("starting range")).toBeInTheDocument();
  });

  it("entry-accessible but wage_p10 null falls through to Scorecard chain", () => {
    // OEWS starting branch needs both p10 and p25; without p10 it
    // shouldn't degrade to typical range (that would be misleading) —
    // it falls through to the Scorecard year-one fallback.
    render(
      <CareerCard
        career={makeCareer({
          work_experience_code: 3,
          wage_p10: null,
          wage_p25: 62_000,
          wage_p75: 110_000,
          earnings_1yr_p25: 35_000,
          earnings_1yr_p75: 55_000,
        })}
        picked={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.queryByText("starting range")).not.toBeInTheDocument();
    expect(screen.queryByText("typical range")).not.toBeInTheDocument();
    expect(screen.getByText(/\$35,000\s+–\s+\$55,000/)).toBeInTheDocument();
    expect(screen.getByText("year one")).toBeInTheDocument();
  });
});
