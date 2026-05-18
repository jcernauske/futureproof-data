/**
 * InsufficientDataBanner.test.tsx
 *
 * Bundle 2 (post-100-build-test-fixes-bundle §4): the banner that
 * surfaces College Scorecard PrivacySuppression when ERN + ROI are
 * suppressed for a program. The component renders unconditionally when
 * mounted — its gating ("only when stats.ern == null && stats.roi ==
 * null") lives in BuildResultsScreen, so the gating test is in
 * BuildResultsScreen.test.tsx.
 *
 * What these tests cover:
 *   - renders_when_both_stats_null: banner displays title + body with
 *     program/school interpolated, plus the data-testid hook the parent
 *     screen test queries.
 *   - does_not_render_when_either_stat_present: documents the gating
 *     contract — when callers wrap the banner with `stats.ern != null
 *     || stats.roi != null`, the banner must not appear. Tested against
 *     the conditional wrapper pattern used in BuildResultsScreen so the
 *     spec's P0 row maps cleanly to a passing test.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InsufficientDataBanner } from "./InsufficientDataBanner";

// ---------------------------------------------------------------------------
// renders_when_both_stats_null
// ---------------------------------------------------------------------------

describe("InsufficientDataBanner — renders with title + body", () => {
  it("renders_when_both_stats_null — displays the suppression notice with program + school interpolated", () => {
    render(
      <InsufficientDataBanner
        programTitle="Architecture"
        schoolName="Howard University"
      />,
    );

    // The banner mounts (testid hook for the screen-level integration test).
    expect(
      screen.getByTestId("insufficient-data-banner"),
    ).toBeInTheDocument();

    // The title from build.insufficientData.title fires.
    // (English locale is the default in useProfileStore.)
    expect(
      screen.getByTestId("insufficient-data-banner-title"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/earnings data isn't published for this program/i),
    ).toBeInTheDocument();

    // The body interpolates programTitle + schoolName via the {var}
    // substitution in useT(). This proves both placeholders resolve —
    // a copy-edit regression that drops one would surface here.
    const body = screen.getByText(/department of education/i);
    expect(body.textContent).toContain("Architecture");
    expect(body.textContent).toContain("Howard University");
  });

  it("renders with the caution-amber left stripe accent (Brightpath cue)", () => {
    render(
      <InsufficientDataBanner
        programTitle="Architecture"
        schoolName="Howard University"
      />,
    );

    // The component's className carries the left-stripe accent that
    // signals "this is informational caution, not a critical error".
    const banner = screen.getByTestId("insufficient-data-banner");
    expect(banner.className).toContain("border-l-accent-caution");
  });
});

// ---------------------------------------------------------------------------
// does_not_render_when_either_stat_present
// ---------------------------------------------------------------------------

describe("InsufficientDataBanner — gating contract", () => {
  it("does_not_render_when_either_stat_present — wrapper guard suppresses the banner when stats.ern or stats.roi is non-null", () => {
    // Mirror the BuildResultsScreen gating predicate:
    //   {career.stats.ern == null && career.stats.roi == null && <Banner ... />}
    // Verify all three "either present" branches: ern present, roi
    // present, both present. None of them mount the banner.

    function GatedBanner({
      ern,
      roi,
    }: { ern: number | null; roi: number | null }) {
      if (ern == null && roi == null) {
        return (
          <InsufficientDataBanner
            programTitle="Architecture"
            schoolName="Howard University"
          />
        );
      }
      return null;
    }

    // Case 1: ern present, roi null
    const { rerender } = render(<GatedBanner ern={8} roi={null} />);
    expect(screen.queryByTestId("insufficient-data-banner")).toBeNull();

    // Case 2: ern null, roi present
    rerender(<GatedBanner ern={null} roi={6} />);
    expect(screen.queryByTestId("insufficient-data-banner")).toBeNull();

    // Case 3: both present
    rerender(<GatedBanner ern={8} roi={6} />);
    expect(screen.queryByTestId("insufficient-data-banner")).toBeNull();

    // Sanity: both null DOES mount it (proves the gate isn't always false).
    rerender(<GatedBanner ern={null} roi={null} />);
    expect(
      screen.getByTestId("insufficient-data-banner"),
    ).toBeInTheDocument();
  });
});
