import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FinancesCard } from "./FinancesCard";
import type { CareerOutcome } from "@/types/build";

/**
 * FinancesCard tests:
 *   - Residency-aware tuition display (feature-residency-aware-tuition).
 *   - ROI receipt + debt-vs-median indicator + P25/P75 salary band
 *     (refactor-prune-deprecated-build-flow — migrated from CareerDetail).
 */

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
    earnings_1yr_median: 45_000,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    net_price_annual: 8_500,
    cost_of_attendance_annual: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: "Public",
    tuition_in_state: 10_000,
    tuition_out_of_state: 25_000,
    is_out_of_state: false,
    room_board_on_campus: null,
    roi_cost_basis: null,
    financed_dte: null,
    stats: { ern: null, roi: null, res: null, grw: null, hmn: null },
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

describe("FinancesCard — residency-aware tuition", () => {
  it("private school shows single tuition row", () => {
    render(
      <FinancesCard
        career={makeCareer({
          institution_control: "Private nonprofit",
          tuition_in_state: 35_000,
          tuition_out_of_state: 35_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByText("Tuition (4 yr)")).toBeInTheDocument();
    expect(screen.queryByText("In-state tuition (4 yr)")).not.toBeInTheDocument();
    expect(screen.queryByText("Out-of-state tuition (4 yr)")).not.toBeInTheDocument();
  });

  it("private for-profit also shows single tuition row", () => {
    render(
      <FinancesCard
        career={makeCareer({ institution_control: "Private for-profit" })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByText("Tuition (4 yr)")).toBeInTheDocument();
    expect(screen.queryByText("In-state tuition (4 yr)")).not.toBeInTheDocument();
  });

  it("public school shows both tuition rows", () => {
    render(
      <FinancesCard
        career={makeCareer({ institution_control: "Public" })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByText("In-state tuition (4 yr)")).toBeInTheDocument();
    expect(screen.getByText("Out-of-state tuition (4 yr)")).toBeInTheDocument();
    expect(screen.queryByText("Tuition (4 yr)")).not.toBeInTheDocument();
  });

  it("highlights in-state row when isInState is true", () => {
    render(
      <FinancesCard
        career={makeCareer({ institution_control: "Public" })}
        loanPct={1.0}
        isInState={true}
      />,
    );

    const yoursMarker = screen.getByText(/← yours/);
    expect(yoursMarker).toBeInTheDocument();

    const inStateLabel = screen.getByText("In-state tuition (4 yr)");
    const inStateRow = inStateLabel.closest("div.flex");
    expect(inStateRow).not.toBeNull();
    expect(inStateRow!.textContent).toContain("← yours");
  });

  it("highlights out-of-state row when isInState is false", () => {
    render(
      <FinancesCard
        career={makeCareer({ institution_control: "Public" })}
        loanPct={1.0}
        isInState={false}
      />,
    );

    const yoursMarker = screen.getByText(/← yours/);
    expect(yoursMarker).toBeInTheDocument();

    const outStateLabel = screen.getByText("Out-of-state tuition (4 yr)");
    const outStateRow = outStateLabel.closest("div.flex");
    expect(outStateRow).not.toBeNull();
    expect(outStateRow!.textContent).toContain("← yours");
  });

  it("no highlight when state unknown (isInState is null)", () => {
    render(
      <FinancesCard
        career={makeCareer({ institution_control: "Public" })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByText("In-state tuition (4 yr)")).toBeInTheDocument();
    expect(screen.getByText("Out-of-state tuition (4 yr)")).toBeInTheDocument();
    expect(screen.queryByText(/← yours/)).not.toBeInTheDocument();
  });

  it("renders tuition values multiplied by 4", () => {
    render(
      <FinancesCard
        career={makeCareer({
          institution_control: "Public",
          tuition_in_state: 10_000,
          tuition_out_of_state: 25_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByText("$40,000")).toBeInTheDocument();
    expect(screen.getByText("$100,000")).toBeInTheDocument();
  });

  it("renders dash when tuition is null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          institution_control: "Public",
          tuition_in_state: null,
          tuition_out_of_state: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });
});

describe("FinancesCard — P25/P75 salary band (migrated from CareerDetail)", () => {
  it("renders P25 and P75 subtitle when both bounds are non-null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: 38_000,
          earnings_1yr_p75: 78_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(
      screen.getByText("25th: $38,000 · 75th: $78,000"),
    ).toBeInTheDocument();
  });

  it("omits P25/P75 subtitle when either bound is null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: 38_000,
          earnings_1yr_p75: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.queryByText(/25th: /)).not.toBeInTheDocument();
  });

  // Symmetric edge case: original test only covered p75=null. Make sure
  // the gating predicate is "both must be set", not "p75 must be set".
  it("omits P25/P75 subtitle when p25 is null and p75 is set", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: null,
          earnings_1yr_p75: 78_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.queryByText(/25th: /)).not.toBeInTheDocument();
    expect(screen.queryByText(/75th: /)).not.toBeInTheDocument();
  });

  it("omits P25/P75 subtitle when both bounds are null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          earnings_1yr_p25: null,
          earnings_1yr_p75: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.queryByText(/25th: /)).not.toBeInTheDocument();
  });
});

describe("FinancesCard — DebtVsMedianIndicator (migrated from CareerDetail)", () => {
  it("shows caution variant when modeled debt > 1.2× median", () => {
    render(
      <FinancesCard
        career={makeCareer({
          modeled_total_debt: 30_000,
          debt_median_reference: 20_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByTestId("debt-indicator-caution")).toBeInTheDocument();
    expect(screen.queryByTestId("debt-indicator-thrive")).not.toBeInTheDocument();
  });

  it("shows thrive variant when modeled debt < 0.8× median", () => {
    render(
      <FinancesCard
        career={makeCareer({
          modeled_total_debt: 10_000,
          debt_median_reference: 20_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByTestId("debt-indicator-thrive")).toBeInTheDocument();
    expect(screen.queryByTestId("debt-indicator-caution")).not.toBeInTheDocument();
  });

  it("renders nothing when modeled debt is in the neutral band", () => {
    render(
      <FinancesCard
        career={makeCareer({
          modeled_total_debt: 20_000,
          debt_median_reference: 20_000,
        })}
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
        career={makeCareer({
          modeled_total_debt: null,
          debt_median_reference: 20_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.queryByTestId("debt-indicator-caution")).not.toBeInTheDocument();
    expect(screen.queryByTestId("debt-indicator-thrive")).not.toBeInTheDocument();
  });

  it("renders nothing when median is null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          modeled_total_debt: 30_000,
          debt_median_reference: null,
          debt_median: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.queryByTestId("debt-indicator-caution")).not.toBeInTheDocument();
    expect(screen.queryByTestId("debt-indicator-thrive")).not.toBeInTheDocument();
  });

  it("falls back to debt_median when debt_median_reference is null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          modeled_total_debt: 30_000,
          debt_median_reference: null,
          debt_median: 20_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    expect(screen.getByTestId("debt-indicator-caution")).toBeInTheDocument();
  });
});

describe("FinancesCard — ROI receipt (migrated from CareerDetail)", () => {
  it("renders cost-basis ROI receipt when roi_cost_basis is cost_of_attendance", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "cost_of_attendance",
          net_price_annual: 8_500,
          cost_of_attendance_annual: 32_000,
          earnings_1yr_median: 45_000,
          debt_to_earnings_annual: 0.42,
          modeled_total_debt: 18_000,
          stats: { ern: null, roi: 8, res: null, grw: null, hmn: null },
        })}
        loanPct={0.5}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));

    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt).toBeInTheDocument();
    expect(receipt.textContent).toContain("Net price per year: $8,500");
    expect(receipt.textContent).toContain("Cost of attendance per year: $32,000");
    expect(receipt.textContent).toContain("4-year cost of attendance: $34,000");
    expect(receipt.textContent).toContain("ROI DTE (cost ÷ earnings): 0.42");
    expect(receipt.textContent).toContain("→ ROI 8/10");
    expect(receipt.textContent).toContain("Loan coverage: 50%");
    expect(receipt.textContent).toContain("modeled debt $18,000");
    expect(receipt.textContent).toContain("(Field of Study + Institution Level)");
  });

  it("renders debt-median fallback receipt when cost-of-attendance unavailable", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "debt_median",
          net_price_annual: null,
          cost_of_attendance_annual: null,
          debt_median_reference: 22_000,
          earnings_1yr_median: 45_000,
          debt_to_earnings_annual: 0.49,
          stats: { ern: null, roi: 7, res: null, grw: null, hmn: null },
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));

    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt.textContent).toContain("Cost basis: median graduate debt $22,000");
    expect(receipt.textContent).toContain("(Field of Study)");
    expect(receipt.textContent).not.toContain("Net price per year");
  });

  it("renders unavailable cost basis when neither path applies", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "none",
          net_price_annual: null,
          debt_median_reference: null,
          debt_median: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    expect(screen.getByTestId("roi-receipt").textContent).toContain(
      "Cost basis: unavailable",
    );
  });

  // Legacy backend-response guard: roi_cost_basis was added later. Older
  // builds may not carry it at all. The receipt should fall through to
  // the "unavailable" branch gracefully when the field is undefined
  // (not just explicitly null).
  it("renders unavailable cost basis when roi_cost_basis is undefined (legacy response)", () => {
    const career = makeCareer({
      net_price_annual: null,
      debt_median_reference: null,
      debt_median: null,
    });
    // Force-delete the property so it's `undefined`, not `null`.
    delete (career as { roi_cost_basis?: unknown }).roi_cost_basis;

    render(<FinancesCard career={career} loanPct={1.0} isInState={null} />);

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    expect(screen.getByTestId("roi-receipt").textContent).toContain(
      "Cost basis: unavailable",
    );
  });

  // The receipt's net-price branch is gated on `net_price_annual > 0`,
  // not just `!== null`. A 0 net price (rare but possible at full-aid
  // institutions) must NOT render the cost-of-attendance branch — it
  // would compute "$0 × 4 = $0" which is misleading.
  it("treats net_price_annual of 0 as missing for the cost-of-attendance branch", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "cost_of_attendance",
          net_price_annual: 0,
          cost_of_attendance_annual: null,
          debt_median_reference: null,
          debt_median: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    const receipt = screen.getByTestId("roi-receipt");
    // Falls through to "unavailable" because the four-year cost is null.
    expect(receipt.textContent).toContain("Cost basis: unavailable");
    expect(receipt.textContent).not.toContain("4-year cost of attendance: $0");
  });

  // The cost-of-attendance branch hides the cost_of_attendance_annual
  // line if that field is null even when the branch fires (because
  // net_price_annual was the trigger).
  it("hides the cost-of-attendance line when only net_price_annual is set", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "cost_of_attendance",
          net_price_annual: 12_000,
          cost_of_attendance_annual: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt.textContent).toContain("Net price per year: $12,000");
    expect(receipt.textContent).toContain("4-year cost of attendance: $48,000");
    expect(receipt.textContent).not.toContain("Cost of attendance per year:");
  });

  // The receipt conditionally renders room/board, in-state tuition, and
  // out-of-state tuition lines. None of these had explicit coverage —
  // a regression that drops the conditional would silently degrade the
  // receipt without breaking any test.
  it("renders room_board_on_campus inside the receipt when set", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "cost_of_attendance",
          net_price_annual: 8_500,
          cost_of_attendance_annual: 32_000,
          room_board_on_campus: 14_500,
          tuition_in_state: 10_000,
          tuition_out_of_state: 25_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt.textContent).toContain("Room & board (on campus): $14,500");
    expect(receipt.textContent).toContain("In-state tuition: $10,000");
    expect(receipt.textContent).toContain("Out-of-state tuition: $25,000");
  });

  it("omits room/board and tuition lines from the receipt when they are null", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "cost_of_attendance",
          net_price_annual: 8_500,
          cost_of_attendance_annual: 32_000,
          room_board_on_campus: null,
          tuition_in_state: null,
          tuition_out_of_state: null,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt.textContent).not.toContain("Room & board");
    expect(receipt.textContent).not.toContain("In-state tuition:");
    expect(receipt.textContent).not.toContain("Out-of-state tuition:");
  });

  // financed_dte gets its own receipt line gated on non-null AND
  // non-undefined. Default fixture is `null` (no line). Verify the line
  // appears when set, and verify the toFixed(2) formatting.
  it("renders financed_dte line in the receipt when set, with two-decimal formatting", () => {
    render(
      <FinancesCard
        career={makeCareer({
          financed_dte: 0.567,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    expect(screen.getByTestId("roi-receipt").textContent).toContain(
      "Financed DTE (loans boss input): 0.57",
    );
  });

  // When cost_of_attendance branch fires AND median debt is also known,
  // the receipt renders an extra "Median debt of graduates" line. Verify
  // the conditional fires for that combo.
  it("appends median-debt line when cost-of-attendance branch fires with median data", () => {
    render(
      <FinancesCard
        career={makeCareer({
          roi_cost_basis: "cost_of_attendance",
          net_price_annual: 8_500,
          cost_of_attendance_annual: 32_000,
          debt_median_reference: 22_000,
        })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    expect(screen.getByTestId("roi-receipt").textContent).toContain(
      "Median debt of graduates from this program: $22,000",
    );
  });

  // Loan coverage rendering: Math.round(loanPct * 100). Boundary cases:
  //   loanPct === 0     → "0%"  (still renders the line because modeled is set)
  //   loanPct === 0.001 → "0%"  (rounds down — verify it doesn't render "0.1%")
  //   loanPct === 0.5   → "50%"
  //   loanPct === 1     → "100%"
  it("renders loan coverage 0% when loanPct is 0", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: 18_000 })}
        loanPct={0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    expect(screen.getByTestId("roi-receipt").textContent).toContain(
      "Loan coverage: 0%",
    );
  });

  it("rounds loan coverage to integer percent (0.001 → 0%)", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: 18_000 })}
        loanPct={0.001}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    const receipt = screen.getByTestId("roi-receipt");
    expect(receipt.textContent).toContain("Loan coverage: 0%");
    // Make sure we don't accidentally render an unrounded "0.1%".
    expect(receipt.textContent).not.toContain("0.1%");
  });

  it("renders loan coverage 100% when loanPct is 1", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: 18_000 })}
        loanPct={1.0}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    expect(screen.getByTestId("roi-receipt").textContent).toContain(
      "Loan coverage: 100%",
    );
  });

  // Loan coverage line is gated on modeled_total_debt being non-null —
  // when modeled debt is null, the line should not render at all
  // (because there's no debt to attribute to coverage).
  it("omits loan coverage line entirely when modeled_total_debt is null", () => {
    render(
      <FinancesCard
        career={makeCareer({ modeled_total_debt: null })}
        loanPct={0.5}
        isInState={null}
      />,
    );

    fireEvent.click(screen.getByLabelText("View data source for ROI"));
    expect(screen.getByTestId("roi-receipt").textContent).not.toContain(
      "Loan coverage:",
    );
  });

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
