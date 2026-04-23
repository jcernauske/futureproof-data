import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FinancesCard } from "./FinancesCard";

/**
 * FinancesCard tests — residency-aware tuition display.
 *
 * Feature: docs/specs/feature-residency-aware-tuition.md
 *
 * Private schools show a single "Tuition (4 yr)" row.
 * Public schools show both in-state and out-of-state rows,
 * with the applicable one highlighted when the student's
 * home state is known.
 */

const BASE_PROPS = {
  startingSalary: 45_000,
  medianSalary: 65_000,
  tuitionInState: 10_000,
  tuitionOutOfState: 25_000,
  loanPct: 1.0,
  isInState: null as boolean | null,
  institutionControl: "Public" as string | null,
};

describe("FinancesCard", () => {
  it("private school shows single tuition row", () => {
    render(
      <FinancesCard
        {...BASE_PROPS}
        institutionControl="Private nonprofit"
        tuitionInState={35_000}
        tuitionOutOfState={35_000}
      />
    );

    // Should show "Tuition (4 yr)" — not "In-state" or "Out-of-state".
    expect(screen.getByText("Tuition (4 yr)")).toBeInTheDocument();
    expect(
      screen.queryByText("In-state tuition (4 yr)")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Out-of-state tuition (4 yr)")
    ).not.toBeInTheDocument();
  });

  it("private for-profit also shows single tuition row", () => {
    // "Private" prefix check — both "Private nonprofit" and
    // "Private for-profit" should behave identically.
    render(
      <FinancesCard
        {...BASE_PROPS}
        institutionControl="Private for-profit"
      />
    );

    expect(screen.getByText("Tuition (4 yr)")).toBeInTheDocument();
    expect(
      screen.queryByText("In-state tuition (4 yr)")
    ).not.toBeInTheDocument();
  });

  it("public school shows both tuition rows", () => {
    render(
      <FinancesCard {...BASE_PROPS} institutionControl="Public" />
    );

    expect(
      screen.getByText("In-state tuition (4 yr)")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Out-of-state tuition (4 yr)")
    ).toBeInTheDocument();
    // Should NOT show the private-style single row.
    expect(screen.queryByText("Tuition (4 yr)")).not.toBeInTheDocument();
  });

  it("highlights in-state row when isInState is true", () => {
    render(
      <FinancesCard
        {...BASE_PROPS}
        institutionControl="Public"
        isInState={true}
      />
    );

    // The highlighted row gets a "yours" indicator.
    const yoursMarker = screen.getByText(/← yours/);
    expect(yoursMarker).toBeInTheDocument();

    // The "yours" marker should be adjacent to "In-state tuition".
    // Find the parent row container that holds the in-state label.
    const inStateLabel = screen.getByText("In-state tuition (4 yr)");
    const inStateRow = inStateLabel.closest("div.flex");
    expect(inStateRow).not.toBeNull();

    // Verify the "yours" marker is inside the in-state row.
    expect(inStateRow!.textContent).toContain("← yours");
  });

  it("highlights out-of-state row when isInState is false", () => {
    render(
      <FinancesCard
        {...BASE_PROPS}
        institutionControl="Public"
        isInState={false}
      />
    );

    const yoursMarker = screen.getByText(/← yours/);
    expect(yoursMarker).toBeInTheDocument();

    // The "yours" marker should be adjacent to "Out-of-state tuition".
    const outStateLabel = screen.getByText("Out-of-state tuition (4 yr)");
    const outStateRow = outStateLabel.closest("div.flex");
    expect(outStateRow).not.toBeNull();
    expect(outStateRow!.textContent).toContain("← yours");
  });

  it("no highlight when state unknown (isInState is null)", () => {
    render(
      <FinancesCard
        {...BASE_PROPS}
        institutionControl="Public"
        isInState={null}
      />
    );

    // Both rows should be visible but neither should have "yours".
    expect(
      screen.getByText("In-state tuition (4 yr)")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Out-of-state tuition (4 yr)")
    ).toBeInTheDocument();
    expect(screen.queryByText(/← yours/)).not.toBeInTheDocument();
  });

  it("renders tuition values multiplied by 4", () => {
    render(
      <FinancesCard
        {...BASE_PROPS}
        institutionControl="Public"
        tuitionInState={10_000}
        tuitionOutOfState={25_000}
      />
    );

    // 10,000 * 4 = 40,000; 25,000 * 4 = 100,000
    expect(screen.getByText("$40,000")).toBeInTheDocument();
    expect(screen.getByText("$100,000")).toBeInTheDocument();
  });

  it("renders dash when tuition is null", () => {
    render(
      <FinancesCard
        {...BASE_PROPS}
        institutionControl="Public"
        tuitionInState={null}
        tuitionOutOfState={null}
      />
    );

    // Null values should display as "—"
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });
});
