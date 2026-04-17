import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { CareerDetail } from "./CareerDetail";
import type { CareerOutcome } from "@/types/build";

/**
 * CareerDetail — ROI receipt + debt-vs-median indicator tests
 *
 * The roi-formula-cost-of-attendance spec adds two visible affordances to the
 * ROI panel: a richer "?" receipt with the full cost breakdown, and a subtle
 * caution/thrive indicator comparing the student's modeled debt to the program
 * median. The thresholds are 1.2x (caution) and 0.8x (thrive). These tests pin
 * those bands so a refactor that loses the comparison would fail loudly.
 */

function makeCareer(overrides: Partial<CareerOutcome> = {}): CareerOutcome {
  return {
    unitid: 110635,
    institution_name: "Indiana State University",
    cipcode: "11.0701",
    program_name: "Computer Science",
    soc_code: "15-1252",
    occupation_title: "Software Developer",
    soc_major_group_name: null,
    median_annual_wage: 90000,
    earnings_1yr_median: 48000,
    earnings_1yr_p25: 38000,
    earnings_1yr_p75: 60000,
    debt_median: 28400,
    debt_to_earnings_annual: 0.89,
    education_level_name: "Bachelor's degree",
    growth_category: "Faster than average",
    net_price_annual: 14200,
    cost_of_attendance_annual: 22800,
    modeled_total_debt: 28400,
    debt_median_reference: 28400,
    institution_control: "Public",
    tuition_in_state: 9500,
    tuition_out_of_state: 21000,
    room_board_on_campus: 11000,
    stats: { ern: 7, roi: 7, res: 5, grw: 8, hmn: 5 },
    bosses: { ai: 5, loans: 5, market: 3, burnout: 4, ceiling: 4 },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: 5,
    overall_confidence: "high",
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    loan_pct: 0.75,
    ...overrides,
  };
}

describe("CareerDetail — debt-vs-median indicator", () => {
  it("shows caution indicator when modeled_total_debt > debt_median_reference * 1.2", () => {
    // 50,000 > 28,400 * 1.2 (=34,080) → caution
    render(
      <CareerDetail
        career={makeCareer({
          modeled_total_debt: 50000,
          debt_median_reference: 28400,
        })}
        loanPct={0.75}
      />,
    );
    const caution = screen.getByTestId("debt-indicator-caution");
    expect(caution).toBeInTheDocument();
    expect(caution).toHaveTextContent(/significantly above the program median/i);
    expect(screen.queryByTestId("debt-indicator-thrive")).toBeNull();
  });

  it("shows thrive indicator when modeled_total_debt < debt_median_reference * 0.8", () => {
    // 15,000 < 28,400 * 0.8 (=22,720) → thrive
    render(
      <CareerDetail
        career={makeCareer({
          modeled_total_debt: 15000,
          debt_median_reference: 28400,
        })}
        loanPct={0.25}
      />,
    );
    const thrive = screen.getByTestId("debt-indicator-thrive");
    expect(thrive).toBeInTheDocument();
    expect(thrive).toHaveTextContent(/well below the program median/i);
    expect(screen.queryByTestId("debt-indicator-caution")).toBeNull();
  });

  it("renders no indicator when modeled debt is within 0.8x–1.2x of median", () => {
    // 28,400 == median → ratio 1.0, neither side fires.
    render(
      <CareerDetail
        career={makeCareer({
          modeled_total_debt: 28400,
          debt_median_reference: 28400,
        })}
        loanPct={1.0}
      />,
    );
    expect(screen.queryByTestId("debt-indicator-caution")).toBeNull();
    expect(screen.queryByTestId("debt-indicator-thrive")).toBeNull();
  });

  it("renders no indicator when modeled_total_debt is missing", () => {
    render(
      <CareerDetail
        career={makeCareer({
          modeled_total_debt: null,
          debt_median_reference: 28400,
        })}
        loanPct={0.5}
      />,
    );
    expect(screen.queryByTestId("debt-indicator-caution")).toBeNull();
    expect(screen.queryByTestId("debt-indicator-thrive")).toBeNull();
  });

  it("falls back to debt_median when debt_median_reference is missing", () => {
    // debt_median_reference null but debt_median present — indicator should still
    // compute against debt_median so older builds keep the visual signal.
    render(
      <CareerDetail
        career={makeCareer({
          modeled_total_debt: 50000,
          debt_median_reference: null,
          debt_median: 28400,
        })}
        loanPct={0.9}
      />,
    );
    expect(screen.getByTestId("debt-indicator-caution")).toBeInTheDocument();
  });
});

describe("CareerDetail — ROI receipt", () => {
  it("renders the cost-of-attendance breakdown when roi_cost_basis is cost_of_attendance", () => {
    render(
      <CareerDetail
        career={makeCareer({
          net_price_annual: 14200,
          cost_of_attendance_annual: 22800,
          modeled_total_debt: 42600,
          institution_control: "Public",
          roi_cost_basis: "cost_of_attendance",
          financed_dte: 42600 / 48000,
        })}
        loanPct={0.75}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /View data source for ROI/i }),
    );

    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt).toHaveTextContent("Net price per year");
    expect(receipt).toHaveTextContent("$14,200");
    expect(receipt).toHaveTextContent("$22,800"); // cost of attendance
    expect(receipt).toHaveTextContent("$56,800"); // 14_200 × 4
    expect(receipt).toHaveTextContent("4-year cost of attendance");
    expect(receipt).toHaveTextContent("ROI DTE");
    expect(receipt).toHaveTextContent("Loan coverage: 75%");
    expect(receipt).toHaveTextContent("$42,600"); // modeled debt
    expect(receipt).toHaveTextContent("Financed DTE");
    expect(receipt).toHaveTextContent("Public");
    expect(receipt).toHaveTextContent(/College Scorecard.*Institution Level/i);
  });

  it("renders the debt_median approximation copy when roi_cost_basis is debt_median", () => {
    render(
      <CareerDetail
        career={makeCareer({
          net_price_annual: null,
          cost_of_attendance_annual: null,
          modeled_total_debt: 19500,
          debt_median: 19500,
          debt_median_reference: 19500,
          roi_cost_basis: "debt_median",
          financed_dte: 19500 / 48000,
        })}
        loanPct={1.0}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /View data source for ROI/i }),
    );

    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt).toHaveTextContent(/median graduate debt/i);
    expect(receipt).toHaveTextContent(/approximation/i);
    expect(receipt).toHaveTextContent("$19,500");
    expect(receipt).toHaveTextContent(/Sources:\s*College Scorecard\s*\(Field of Study\)/i);
    // Institution-level attribution must NOT appear on the fallback path.
    expect(receipt.textContent).not.toMatch(/Institution Level/i);
  });
});
