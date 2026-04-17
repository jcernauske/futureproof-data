import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EffortLoansPanel } from "./EffortLoansPanel";
import type { EffortSelection, LoanSelection } from "@/types/buildInput";

/**
 * EffortLoansPanel — cost-of-attendance context tests
 *
 * The loan slider has two display modes driven by `netPriceAnnual`:
 *   1. Institution-level cost is known (number > 0) → render the cost line and
 *      a live "At {pct}%: ${modeled} in loans" line that recomputes as the
 *      slider moves.
 *   2. Cost is null/undefined/0 → render no extra lines, leaving the legacy
 *      "scales debt-to-earnings to N%" copy alone. The slider must still work.
 *
 * These tests pin the contract because the cost lines are the entire point of
 * the roi-formula-cost-of-attendance spec for this screen — silently dropping
 * them would defeat the transparency moment the spec asks for.
 */

const baseEffort: EffortSelection = {
  level: "balanced",
  percentile: 50,
  ernShift: 0,
};

function renderPanel(overrides: Partial<{
  loans: LoanSelection;
  netPriceAnnual: number | null;
}> = {}) {
  const onLoanChange = vi.fn();
  const result = render(
    <EffortLoansPanel
      effort={baseEffort}
      loans={overrides.loans ?? { percentage: 50 }}
      onEffortChange={vi.fn()}
      onLoanChange={onLoanChange}
      profileName="bold swift fox"
      onSubmit={vi.fn()}
      submitting={false}
      netPriceAnnual={overrides.netPriceAnnual ?? null}
    />,
  );
  return { ...result, onLoanChange };
}

describe("EffortLoansPanel — loan slider cost context", () => {
  it("renders cost-of-attendance line and modeled-debt line when netPriceAnnual is provided", () => {
    renderPanel({ netPriceAnnual: 14200, loans: { percentage: 75 } });

    const ctx = screen.getByTestId("loan-slider-cost-context");
    // The annual × 4 = total framing line. We assert the formatted dollars
    // rather than the exact wording so a copy tweak doesn't snap this test.
    expect(ctx).toHaveTextContent("$14,200");
    expect(ctx).toHaveTextContent("$56,800"); // 14,200 * 4

    // 14,200 * 4 * 0.75 = 42,600
    expect(ctx).toHaveTextContent("At 75%");
    expect(ctx).toHaveTextContent("$42,600");
  });

  it("recomputes modeled debt when slider value changes", () => {
    const { rerender } = render(
      <EffortLoansPanel
        effort={baseEffort}
        loans={{ percentage: 25 }}
        onEffortChange={vi.fn()}
        onLoanChange={vi.fn()}
        profileName="bold swift fox"
        onSubmit={vi.fn()}
        submitting={false}
        netPriceAnnual={10000}
      />,
    );
    // 10,000 * 4 * 0.25 = 10,000
    expect(screen.getByTestId("loan-slider-cost-context")).toHaveTextContent(
      "$10,000",
    );
    expect(screen.getByTestId("loan-slider-cost-context")).toHaveTextContent(
      "At 25%",
    );

    rerender(
      <EffortLoansPanel
        effort={baseEffort}
        loans={{ percentage: 100 }}
        onEffortChange={vi.fn()}
        onLoanChange={vi.fn()}
        profileName="bold swift fox"
        onSubmit={vi.fn()}
        submitting={false}
        netPriceAnnual={10000}
      />,
    );
    // 10,000 * 4 * 1.0 = 40,000
    expect(screen.getByTestId("loan-slider-cost-context")).toHaveTextContent(
      "$40,000",
    );
    expect(screen.getByTestId("loan-slider-cost-context")).toHaveTextContent(
      "At 100%",
    );
  });

  it("falls back gracefully when netPriceAnnual is null — no cost context line, slider still functional", () => {
    const { onLoanChange } = renderPanel({
      netPriceAnnual: null,
      loans: { percentage: 50 },
    });

    expect(screen.queryByTestId("loan-slider-cost-context")).toBeNull();
    // Copy now describes the Loans Boss impact (ROI is cost-based and
    // loan_pct-agnostic). The slider impact label must still render.
    expect(
      screen.getByText(/financing 50% of 4-year cost/i),
    ).toBeInTheDocument();

    // Slider still invokes the handler — keyboard arrow advances one stop.
    const slider = screen.getByRole("slider", { name: /loan percentage/i });
    fireEvent.keyDown(slider, { key: "ArrowRight" });
    expect(onLoanChange).toHaveBeenCalledTimes(1);
  });

  it("falls back gracefully when netPriceAnnual is omitted entirely", () => {
    render(
      <EffortLoansPanel
        effort={baseEffort}
        loans={{ percentage: 50 }}
        onEffortChange={vi.fn()}
        onLoanChange={vi.fn()}
        profileName="bold swift fox"
        onSubmit={vi.fn()}
        submitting={false}
      />,
    );
    expect(screen.queryByTestId("loan-slider-cost-context")).toBeNull();
  });

  it("does not render cost context when netPriceAnnual is 0 (treat as missing data)", () => {
    renderPanel({ netPriceAnnual: 0, loans: { percentage: 50 } });
    expect(screen.queryByTestId("loan-slider-cost-context")).toBeNull();
  });
});
