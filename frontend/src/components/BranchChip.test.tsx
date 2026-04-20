import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BranchChip } from "./BranchChip";
import type { CareerBranch } from "@/types/build";

/**
 * BranchChip tests (P2)
 *
 * Covers the two behaviors the spec calls out:
 *   - Non-zero stat deltas are rendered; zero deltas are suppressed.
 *   - Rationale (`unlock` field) renders when present, omitted when absent.
 *
 * Stat-delta formatting rule: magnitude == abs(trunc(value)), capped at 3,
 * rendered as "+"/"-" repeated `magnitude` times. Zero => pill suppressed.
 */

function baseBranch(overrides: Partial<CareerBranch> = {}): CareerBranch {
  return {
    from_soc: "13-2051",
    to_soc: "13-2052",
    to_title: "Portfolio Manager",
    delta_ern: 0,
    delta_roi: 0,
    delta_res: 0,
    delta_grw: 0,
    delta_hmn: 0,
    unlock: null,
    relatedness: 0.8,
    experience_years: null,
    experience_tier: null,
    experience_delta: null,
    related_education_level: null,
    ...overrides,
  };
}

describe("BranchChip", () => {
  it("renders non-zero stat deltas only (zero deltas suppressed)", () => {
    render(
      <BranchChip
        branch={baseBranch({
          delta_ern: 3,
          delta_roi: 0,
          delta_res: -1,
          delta_grw: 0,
          delta_hmn: 2,
        })}
      />,
    );

    // Present deltas:
    expect(screen.getByText(/ERN \+\+\+/)).toBeInTheDocument();
    expect(screen.getByText(/RES -/)).toBeInTheDocument();
    expect(screen.getByText(/HMN \+\+/)).toBeInTheDocument();

    // Suppressed (0 values):
    expect(screen.queryByText(/ROI/)).not.toBeInTheDocument();
    expect(screen.queryByText(/GRW/)).not.toBeInTheDocument();
  });

  it("suppresses pills when delta is null or undefined", () => {
    // The CareerBranch type allows `number | null`. Null must behave like 0.
    render(
      <BranchChip
        branch={baseBranch({
          delta_ern: null,
          delta_roi: null,
          delta_res: null,
          delta_grw: null,
          delta_hmn: null,
        })}
      />,
    );

    expect(screen.queryByText(/ERN/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ROI/)).not.toBeInTheDocument();
    expect(screen.queryByText(/RES/)).not.toBeInTheDocument();
    expect(screen.queryByText(/GRW/)).not.toBeInTheDocument();
    expect(screen.queryByText(/HMN/)).not.toBeInTheDocument();
  });

  it("caps delta magnitude at 3 (a delta of 5 still renders as '+++')", () => {
    render(
      <BranchChip
        branch={baseBranch({
          delta_ern: 5,
        })}
      />,
    );
    expect(screen.getByText(/ERN \+\+\+/)).toBeInTheDocument();
    // No "+++++" or other longer sequence leaked through.
    expect(screen.queryByText(/ERN \++\+\+\+\+/)).not.toBeInTheDocument();
  });

  it("renders rationale (unlock) when present", () => {
    render(
      <BranchChip
        branch={baseBranch({
          unlock: "Typical after 4-5 years of analyst work",
        })}
      />,
    );
    expect(
      screen.getByText(/Typical after 4-5 years of analyst work/),
    ).toBeInTheDocument();
  });

  it("omits rationale paragraph when unlock is null", () => {
    const { container } = render(<BranchChip branch={baseBranch()} />);

    // The component's rationale is rendered as a <p className="... italic ...">.
    // When unlock is null the <p> is not rendered at all — assert no <p> under
    // the chip article (the title is an <h3>, the pills row is a <div>).
    const article = container.querySelector("article");
    expect(article).not.toBeNull();
    const paragraphs = article!.querySelectorAll("p");
    expect(paragraphs.length).toBe(0);
  });

  it("renders branch title as the heading text", () => {
    render(<BranchChip branch={baseBranch({ to_title: "CFO" })} />);
    expect(
      screen.getByRole("heading", { level: 3, name: "CFO" }),
    ).toBeInTheDocument();
  });
});
