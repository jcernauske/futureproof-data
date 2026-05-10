import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FinancesCard } from "./FinancesCard";
import type { CareerOutcome } from "@/types/build";

function makeCareer(overrides: Partial<CareerOutcome> = {}): CareerOutcome {
  return {
    unitid: 1,
    institution_name: "Test U",
    cipcode: "00.0000",
    program_name: "Test Program",
    soc_code: "00-0000",
    occupation_title: "Test Occupation",
    soc_major_group_name: null,
    median_annual_wage: 65_000,
    wage_p10: null,
    wage_p25: null,
    wage_p75: null,
    wage_p90: null,
    earnings_1yr_median: 45_000,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    work_experience_code: null,
    net_price_annual: 8_500,
    cost_of_attendance_annual: null,
    published_cost_4yr: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: "Public",
    tuition_in_state: 10_000,
    tuition_out_of_state: 25_000,
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

describe("FinancesCard — residency-aware cost display", () => {
  it("renders published cost row when published_cost_4yr is set", () => {
    render(
      <FinancesCard
        career={makeCareer({ published_cost_4yr: 140_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("Published cost (4 yr)")).toBeInTheDocument();
    expect(screen.getByText("$140,000")).toBeInTheDocument();
  });

  it("omits published cost row when published_cost_4yr is null", () => {
    render(
      <FinancesCard
        career={makeCareer({ published_cost_4yr: null })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByText("Published cost (4 yr)")).not.toBeInTheDocument();
  });

  it("shows out-of-state label when isInState is false", () => {
    render(
      <FinancesCard
        career={makeCareer({ published_cost_4yr: 140_000 })}
        loanPct={1.0}
        isInState={false}
      />,
    );
    expect(screen.getByText("← out-of-state applied")).toBeInTheDocument();
  });

  it("no out-of-state label when isInState is true", () => {
    render(
      <FinancesCard
        career={makeCareer({ published_cost_4yr: 140_000 })}
        loanPct={1.0}
        isInState={true}
      />,
    );
    expect(screen.queryByText("← out-of-state applied")).not.toBeInTheDocument();
  });

  it("renders avg net price row when net_price_annual > 0", () => {
    render(
      <FinancesCard
        career={makeCareer({ net_price_annual: 10_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("Avg. net price (4 yr)")).toBeInTheDocument();
    expect(screen.getByText("$40,000")).toBeInTheDocument();
  });

  it("omits avg net price row when net_price_annual is null", () => {
    render(
      <FinancesCard
        career={makeCareer({ net_price_annual: null })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByText("Avg. net price (4 yr)")).not.toBeInTheDocument();
  });

  it("omits avg net price row when net_price_annual is 0", () => {
    render(
      <FinancesCard
        career={makeCareer({ net_price_annual: 0 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByText("Avg. net price (4 yr)")).not.toBeInTheDocument();
  });
});

describe("FinancesCard — Year-1 peer band", () => {
  it("renders the peer band visualization when p25 and p75 are set", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: 38_000,
          earnings_1yr_p75: 78_000,
          earnings_1yr_median: 60_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByTestId("year1-salary-bar")).toBeInTheDocument();
    expect(screen.getByText("Peer band · Year-1 (this field)")).toBeInTheDocument();
    // SalaryBar uses formatSalaryShort ($XXK) — verify peer p25/p75 render.
    expect(screen.getByText("$38K")).toBeInTheDocument();
    expect(screen.getByText("$78K")).toBeInTheDocument();
    // Program median pill ($60K) — inside the peer band, no callout.
    expect(screen.getByText("$60K")).toBeInTheDocument();
    expect(screen.queryByText(/Standout earnings/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Earnings caution/)).not.toBeInTheDocument();
  });

  it("flags Standout earnings when program median exceeds peer p75", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: 38_000,
          earnings_1yr_p75: 50_000,
          earnings_1yr_median: 63_371, // IU/Marketing real-world case
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText(/Standout earnings/)).toBeInTheDocument();
    expect(
      screen.getByText(/beats the peer-program 75th percentile/),
    ).toBeInTheDocument();
  });

  it("flags Earnings caution when program median sits below peer p25", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: 50_000,
          earnings_1yr_p75: 80_000,
          earnings_1yr_median: 35_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText(/Earnings caution/)).toBeInTheDocument();
    expect(
      screen.getByText(/sits below the peer-program 25th percentile/),
    ).toBeInTheDocument();
  });

  it("falls back to mid-career wage when program median is null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: 38_000,
          earnings_1yr_p75: 78_000,
          earnings_1yr_median: null,
          median_annual_wage: 92_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    // Pill shows the career-wage fallback in $K shorthand.
    expect(screen.getByText("$92K")).toBeInTheDocument();
    expect(
      screen.getByText(/career wage reference because program median earnings are unavailable/),
    ).toBeInTheDocument();
  });

  it("omits the peer band entirely when no salary signal exists", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_median: null,
          earnings_1yr_p25: null,
          earnings_1yr_p75: null,
          median_annual_wage: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByTestId("year1-salary-bar")).not.toBeInTheDocument();
    expect(screen.queryByText(/Peer band/)).not.toBeInTheDocument();
  });
});

describe("FinancesCard — Career salary range (OEWS, long-term: code 1)", () => {
  // Long-term careers (work_experience_code=1) display the typical
  // p25–p75 range under the "Career salary range" label.
  it("renders career salary range row when wage_p25 and wage_p75 are set", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p25: 98_000,
          wage_p75: 168_000,
          occupation_title: "Software Developers",
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("Career salary range")).toBeInTheDocument();
    expect(screen.getByText("$98,000 – $168,000")).toBeInTheDocument();
    // The subtitle is the occupation title — confirms scoping is per-career.
    expect(screen.getByText("Software Developers")).toBeInTheDocument();
  });

  it("omits career salary range row when wage_p25 is null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p25: null,
          wage_p75: 168_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByText("Career salary range")).not.toBeInTheDocument();
  });

  it("omits career salary range row when wage_p75 is null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p25: 98_000,
          wage_p75: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByText("Career salary range")).not.toBeInTheDocument();
  });

  it("omits career salary range row when both wage_p25 and wage_p75 are null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p25: null,
          wage_p75: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByText("Career salary range")).not.toBeInTheDocument();
  });

  it("renders career salary range alongside the Year-1 peer band (they are different concepts)", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 1,
          wage_p25: 98_000,
          wage_p75: 168_000,
          earnings_1yr_p25: 60_000,
          earnings_1yr_p75: 90_000,
          occupation_title: "Software Developers",
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    // OEWS career-level row uses the comma-formatted range.
    expect(screen.getByText("Career salary range")).toBeInTheDocument();
    expect(screen.getByText("$98,000 – $168,000")).toBeInTheDocument();
    // Year-1 row is now the peer band visualization with its own label set.
    expect(screen.getByText("Peer band · Year-1 (this field)")).toBeInTheDocument();
    expect(screen.getByTestId("year1-salary-bar")).toBeInTheDocument();
    // Peer band labels render at $K shorthand inside the bar.
    expect(screen.getByText("$60K")).toBeInTheDocument();
    expect(screen.getByText("$90K")).toBeInTheDocument();
  });
});

describe("FinancesCard — Career starting range (OEWS, entry-accessible)", () => {
  // Entry-accessible careers (work_experience_code 2, 3, or null) flip
  // to p10–p25 with the "Career starting range" label so a year-one
  // student sees what entrants actually earn — not incumbents.
  it("entry-accessible (code 3) renders p10–p25 with Career starting range label", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 3,
          wage_p10: 45_000,
          wage_p25: 62_000,
          wage_p75: 110_000,
          occupation_title: "Web Developers",
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("Career starting range")).toBeInTheDocument();
    expect(screen.getByText("$45,000 – $62,000")).toBeInTheDocument();
    expect(screen.getByText("Web Developers")).toBeInTheDocument();
    // Long-term label must NOT appear when starting range is shown.
    expect(screen.queryByText("Career salary range")).not.toBeInTheDocument();
  });

  it("entry-accessible (code 2) renders p10–p25 with Career starting range label", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 2,
          wage_p10: 50_000,
          wage_p25: 70_000,
          wage_p75: 120_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("Career starting range")).toBeInTheDocument();
    expect(screen.getByText("$50,000 – $70,000")).toBeInTheDocument();
  });

  it("null work_experience_code is treated as entry-accessible", () => {
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: null,
          wage_p10: 40_000,
          wage_p25: 58_000,
          wage_p75: 105_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("Career starting range")).toBeInTheDocument();
    expect(screen.getByText("$40,000 – $58,000")).toBeInTheDocument();
    expect(screen.queryByText("Career salary range")).not.toBeInTheDocument();
  });

  it("entry-accessible but wage_p10 null omits the row entirely", () => {
    // No fall-through to typical range — that would frame incumbent
    // percentiles as a starting figure.
    render(
      <FinancesCard
        career={makeCareer({
          work_experience_code: 3,
          wage_p10: null,
          wage_p25: 62_000,
          wage_p75: 110_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByText("Career starting range")).not.toBeInTheDocument();
    expect(screen.queryByText("Career salary range")).not.toBeInTheDocument();
  });
});

describe("FinancesCard — DebtVsMedianIndicator", () => {
  it("shows caution variant when modeled debt > 1.2x median", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: 30_000, debt_median_reference: 20_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByTestId("debt-indicator-caution")).toBeInTheDocument();
  });

  it("shows thrive variant when modeled debt < 0.8x median", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: 10_000, debt_median_reference: 20_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByTestId("debt-indicator-thrive")).toBeInTheDocument();
  });

  it("renders nothing when modeled debt is in neutral band", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: 20_000, debt_median_reference: 20_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByTestId("debt-indicator-caution")).not.toBeInTheDocument();
    expect(screen.queryByTestId("debt-indicator-thrive")).not.toBeInTheDocument();
  });

  it("renders nothing when modeled debt is null", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: null, debt_median_reference: 20_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.queryByTestId("debt-indicator-caution")).not.toBeInTheDocument();
  });

  it("falls back to debt_median when debt_median_reference is null", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: 30_000, debt_median_reference: null, debt_median: 20_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByTestId("debt-indicator-caution")).toBeInTheDocument();
  });
});

describe("FinancesCard — ROI label", () => {
  it("ROI label reflects DTE thresholds", () => {
    const { rerender } = render(
      <FinancesCard
        career={makeCareer({ debt_to_earnings_annual: 0.4 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("ROI: Strong ROI")).toBeInTheDocument();

    rerender(
      <FinancesCard
        career={makeCareer({ debt_to_earnings_annual: 0.8 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("ROI: Moderate ROI")).toBeInTheDocument();

    rerender(
      <FinancesCard
        career={makeCareer({ debt_to_earnings_annual: 1.5 })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("ROI: Challenging ROI")).toBeInTheDocument();

    rerender(
      <FinancesCard
        career={makeCareer({ debt_to_earnings_annual: null })}
        loanPct={1.0}
        isInState={null}
      />,
    );
    expect(screen.getByText("ROI: Insufficient data")).toBeInTheDocument();
  });
});
