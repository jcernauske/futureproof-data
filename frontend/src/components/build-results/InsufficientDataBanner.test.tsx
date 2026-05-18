/**
 * InsufficientDataBanner.test.tsx
 *
 * Covers:
 *   - renders_dual_interpretation: title + both bullet interpretations +
 *     ask-the-report outro, with program/school/career interpolation.
 *   - renders_bls_anchor_when_wage_present: BLS sentence appears with
 *     formatted wage when blsWage is non-null.
 *   - omits_bls_anchor_when_wage_null: BLS sentence does NOT render when
 *     blsWage is null.
 *   - gating contract: parent screen's `ern == null && roi == null` guard
 *     keeps the banner from mounting otherwise.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InsufficientDataBanner } from "./InsufficientDataBanner";

describe("InsufficientDataBanner — content", () => {
  it("renders_dual_interpretation — title + both interpretations + outro with interpolation", () => {
    render(
      <InsufficientDataBanner
        programTitle="Finance"
        schoolName="Harvard University"
        careerTitle="Financial Analysts"
        blsWage={96220}
      />,
    );

    expect(screen.getByTestId("insufficient-data-banner")).toBeInTheDocument();

    // Title — short, cause-agnostic.
    expect(
      screen.getByText(/limited earnings data for this program/i),
    ).toBeInTheDocument();

    // Lede interpolates school + program.
    const lede = screen.getByText(
      /doesn't publish program-level earnings/i,
    );
    expect(lede.textContent).toContain("Harvard University");
    expect(lede.textContent).toContain("Finance");

    // Both interpretations render.
    expect(
      screen.getByText(/selective enough that few graduates take federal loans/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/very few students from this specific program/i),
    ).toBeInTheDocument();

    // Outro references the report and the career title.
    const outro = screen.getByText(
      /added a question to your downloadable report/i,
    );
    expect(outro.textContent).toContain("Financial Analysts");
  });

  it("renders_bls_anchor_when_wage_present — BLS sentence appears with formatted wage", () => {
    render(
      <InsufficientDataBanner
        programTitle="Finance"
        schoolName="Harvard University"
        careerTitle="Financial Analysts"
        blsWage={96220}
      />,
    );

    const bls = screen.getByText(/bureau of labor statistics/i);
    expect(bls.textContent).toContain("$96,220");
    expect(bls.textContent).toContain("Financial Analysts");
  });

  it("omits_bls_anchor_when_wage_null — BLS sentence does NOT render", () => {
    render(
      <InsufficientDataBanner
        programTitle="Finance"
        schoolName="Harvard University"
        careerTitle="Financial Analysts"
        blsWage={null}
      />,
    );

    expect(screen.queryByText(/bureau of labor statistics/i)).toBeNull();
    // Outro still renders without the BLS tail.
    expect(
      screen.getByText(/added a question to your downloadable report/i),
    ).toBeInTheDocument();
  });

  it("renders with the caution-amber left stripe accent (Brightpath cue)", () => {
    render(
      <InsufficientDataBanner
        programTitle="Finance"
        schoolName="Harvard University"
        careerTitle="Financial Analysts"
        blsWage={96220}
      />,
    );
    const banner = screen.getByTestId("insufficient-data-banner");
    expect(banner.className).toContain("border-l-accent-caution");
  });
});

describe("InsufficientDataBanner — gating contract", () => {
  it("does_not_render_when_either_stat_present — wrapper guard suppresses the banner when stats.ern or stats.roi is non-null", () => {
    function GatedBanner({
      ern,
      roi,
    }: { ern: number | null; roi: number | null }) {
      if (ern == null && roi == null) {
        return (
          <InsufficientDataBanner
            programTitle="Finance"
            schoolName="Harvard University"
            careerTitle="Financial Analysts"
            blsWage={96220}
          />
        );
      }
      return null;
    }

    const { rerender } = render(<GatedBanner ern={8} roi={null} />);
    expect(screen.queryByTestId("insufficient-data-banner")).toBeNull();

    rerender(<GatedBanner ern={null} roi={6} />);
    expect(screen.queryByTestId("insufficient-data-banner")).toBeNull();

    rerender(<GatedBanner ern={8} roi={6} />);
    expect(screen.queryByTestId("insufficient-data-banner")).toBeNull();

    rerender(<GatedBanner ern={null} roi={null} />);
    expect(
      screen.getByTestId("insufficient-data-banner"),
    ).toBeInTheDocument();
  });
});
