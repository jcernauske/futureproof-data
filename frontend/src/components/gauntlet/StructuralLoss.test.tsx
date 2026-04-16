import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StructuralLoss } from "./StructuralLoss";

/**
 * StructuralLoss tests
 *
 * This component renders when the student's skill pool is exhausted for a boss
 * fight but the result is still a loss. It's the product's most honest moment:
 * "the gap is structural, not a skill-tree problem."
 *
 * We test: correct messaging renders, the continue button fires the callback,
 * accessibility attributes, and boss-specific identification.
 */

describe("StructuralLoss", () => {
  it("renders the structural loss message", () => {
    render(<StructuralLoss bossId="burnout" onContinue={vi.fn()} />);

    expect(
      screen.getByText(/every available skill for this fight has been equipped/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/the gap isn't a skill-tree problem/i),
    ).toBeInTheDocument();
  });

  it("renders the follow-up reassurance text", () => {
    render(<StructuralLoss bossId="ai" onContinue={vi.fn()} />);

    expect(
      screen.getByText(/your next steps checklist will address this/i),
    ).toBeInTheDocument();
  });

  it("calls onContinue when the continue button is clicked", () => {
    const onContinue = vi.fn();
    render(<StructuralLoss bossId="loans" onContinue={onContinue} />);

    const button = screen.getByRole("button", { name: /continue/i });
    fireEvent.click(button);

    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it("has role=alert for screen reader announcement", () => {
    render(<StructuralLoss bossId="market" onContinue={vi.fn()} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("includes boss-specific id for DOM targeting", () => {
    const { container } = render(
      <StructuralLoss bossId="ceiling" onContinue={vi.fn()} />,
    );

    const region = container.querySelector("#region-structural-loss-ceiling");
    expect(region).toBeInTheDocument();
  });

  it("has accessible label describing the situation", () => {
    render(<StructuralLoss bossId="ai" onContinue={vi.fn()} />);

    expect(
      screen.getByLabelText(/structural loss.*all skills exhausted/i),
    ).toBeInTheDocument();
  });
});
