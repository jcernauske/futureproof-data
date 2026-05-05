import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { MockedFunction } from "vitest";
import { CompareSchoolsPanel } from "./CompareSchoolsPanel";
import type {
  SchoolForCareerRow,
  SchoolsForCareerResponse,
} from "@/types/build";
import { fmtMoney } from "@/lib/format";

/**
 * CompareSchoolsPanel — leaderboard rendering, anchor handling, empty-state
 * escape hatch, and zero-pentagon contract per spec
 * `feature-compare-schools-for-career.md` §4 New Tests Required (P0/P1/P2).
 *
 * The panel is mode-aware (`by_soc` vs `by_cip_and_soc`) and renders a
 * CSS-grid table — never `<table>` — with two anchor paths: in-place when
 * the build is in the top-N, appended below a "Your school" divider when
 * it isn't. The API is mocked so we control the response shape per test.
 */

vi.mock("@/api/careers", () => ({
  fetchSchoolsBySoc: vi.fn(),
  fetchSchoolsByCipAndSoc: vi.fn(),
}));

import { fetchSchoolsBySoc, fetchSchoolsByCipAndSoc } from "@/api/careers";
const mockFetchBySoc = fetchSchoolsBySoc as MockedFunction<
  typeof fetchSchoolsBySoc
>;
const mockFetchByCipAndSoc = fetchSchoolsByCipAndSoc as MockedFunction<
  typeof fetchSchoolsByCipAndSoc
>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeRow(overrides: Partial<SchoolForCareerRow> = {}): SchoolForCareerRow {
  return {
    rank: 1,
    unitid: 110001,
    institution_name: "Top Tech",
    institution_control: "Public",
    state_abbr: "CA",
    cipcode: "11.0701",
    program_name: "Computer Science",
    soc_code: "15-1252",
    occupation_title: "Software Developers",
    stat_ern: 9,
    stat_roi: 9,
    earnings_1yr_median: 120000,
    net_price_annual: 20000,
    cost_of_attendance_annual: 30000,
    tuition_in_state: 9000,
    tuition_out_of_state: 21000,
    published_cost_4yr: 120000,
    stat_roi_in_state: 9,
    roi_residency_adjusted: false,
    overall_confidence: "high",
    confidence_tier_program: "high",
    match_quality: "full",
    is_anchor: false,
    ...overrides,
  };
}

function makeResponse(
  overrides: Partial<SchoolsForCareerResponse> = {},
): SchoolsForCareerResponse {
  return {
    mode: "by_soc",
    soc_code: "15-1252",
    occupation_title: "Software Developers",
    cipcode: null,
    program_name: null,
    rows: [makeRow()],
    anchor_in_top_n: false,
    total_qualifying_programs: 1,
    anchor_estimated_rank: null,
    confidence_filter_applied: "medium",
    state_filter_applied: null,
    min_program_confidence_applied: "low",
    generated_at: new Date().toISOString(),
    ...overrides,
  };
}

beforeEach(() => {
  mockFetchBySoc.mockReset();
  mockFetchByCipAndSoc.mockReset();
});

// ===========================================================================
// P0 — title + chip per mode
// ===========================================================================

describe("CompareSchoolsPanel — title + chip per mode", () => {
  it("renders_correct_title_chip_per_mode (by_soc)", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        mode: "by_soc",
        occupation_title: "Software Developers",
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    // Title contains the occupation_title.
    expect(
      screen.getByRole("heading", { level: 2 }),
    ).toHaveTextContent(/Software Developers/);
    // Mode chip carries the by_soc label.
    const chip = screen.getByTestId("chip-leaderboard-mode");
    expect(chip).toHaveTextContent(/BY CAREER/);
    expect(chip).not.toHaveTextContent(/BY MAJOR/);
  });

  it("renders_correct_title_chip_per_mode (by_cip_and_soc)", async () => {
    mockFetchByCipAndSoc.mockResolvedValueOnce(
      makeResponse({
        mode: "by_cip_and_soc",
        cipcode: "11.0701",
        program_name: "Computer Science",
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_cip_and_soc"
        enclosure="inline"
        socCode="15-1252"
        cipcode="11.0701"
        occupationTitle="Software Developers"
        programName="Computer Science"
        defaultExpanded
      />,
    );

    await waitFor(() => expect(mockFetchByCipAndSoc).toHaveBeenCalled());

    // Title interpolates BOTH program_name and occupation_title.
    const heading = screen.getByRole("heading", { level: 2 });
    expect(heading).toHaveTextContent(/Computer Science/);
    expect(heading).toHaveTextContent(/Software Developers/);

    // Mode chip is durable in the title and reads BY MAJOR + CAREER.
    const chip = screen.getByTestId("chip-leaderboard-mode");
    expect(chip).toHaveTextContent(/BY MAJOR \+ CAREER/);
  });
});

// ===========================================================================
// P0 — anchor row rendering
// ===========================================================================

describe("CompareSchoolsPanel — anchor row rendering", () => {
  it("renders_anchor_row_when_anchor_present (in-place)", async () => {
    const anchorRow = makeRow({
      rank: 2,
      unitid: 110002,
      institution_name: "Anchor U",
      cipcode: "11.0701",
      is_anchor: true,
    });
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [makeRow(), anchorRow, makeRow({ rank: 3, unitid: 110003 })],
        anchor_in_top_n: true,
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        anchor={{ unitid: 110002, cipcode: "11.0701" }}
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    const anchorEl = await screen.findByTestId("row-anchor-110002-11.0701");
    expect(anchorEl).toBeInTheDocument();
    expect(anchorEl).toHaveAttribute("data-anchor", "true");

    // Non-anchor rows do NOT carry the anchor data attribute. Scope to
    // the desktop grid — the card-stack renders the same rows in jsdom
    // and would double-count.
    const grid = screen.getByTestId("compare-grid");
    const allRows = within(grid).getAllByRole("row");
    const anchored = allRows.filter(
      (r) => r.getAttribute("data-anchor") === "true",
    );
    expect(anchored).toHaveLength(1);
  });

  it("renders_appended_anchor_row_when_below_top_n (with divider)", async () => {
    const top = [
      makeRow({ rank: 1, unitid: 110001 }),
      makeRow({ rank: 2, unitid: 110002, institution_name: "Two" }),
      makeRow({ rank: 3, unitid: 110003, institution_name: "Three" }),
    ];
    const appendedAnchor = makeRow({
      rank: 7,
      unitid: 110007,
      institution_name: "My School",
      cipcode: "11.0701",
      is_anchor: true,
    });

    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [...top, appendedAnchor],
        anchor_in_top_n: false,
        total_qualifying_programs: 11,
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        anchor={{ unitid: 110007, cipcode: "11.0701" }}
        open
      />,
    );

    const appended = await screen.findByTestId("row-anchor-110007-11.0701");
    // Carries its absolute rank (7), not a synthesized 4.
    expect(appended).toHaveTextContent("7");
    expect(appended).toHaveTextContent(/My School/);

    // The "Your school" dashed divider appears above the appended row
    // (rendered in both the grid and the card-stack — getAll covers both).
    expect(screen.getAllByText(/Your school/i).length).toBeGreaterThan(0);
  });

  it("renders_synthetic_anchor_row_from_estimated_rank_when_anchor_absent_from_universe", async () => {
    // Backend returns a top-N with NO is_anchor row, but supplies
    // anchor_estimated_rank because the caller passed anchor stats.
    // The panel should splice in a synthetic row from the anchor prop's
    // build data + render the "estimated" callout copy.
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({ rank: 1, unitid: 110001, institution_name: "Top School" }),
          makeRow({ rank: 2, unitid: 110002, institution_name: "Two" }),
        ],
        anchor_in_top_n: false,
        total_qualifying_programs: 962,
        anchor_estimated_rank: 31,
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="13-1161"
        occupationTitle="Market research analysts and marketing specialists"
        anchor={{
          unitid: 151351,
          cipcode: "52.01",
          statErn: 8,
          statRoi: 7,
          institutionName: "Indiana University-Bloomington",
          institutionControl: "Public",
          programName: "Marketing/Marketing Management",
          stateAbbr: "IN",
          earnings1yrMedian: 42675,
          netPriceAnnual: 15342,
        }}
        open
      />,
    );

    // Synthetic row appears with the build's unitid + cipcode.
    const synthetic = await screen.findByTestId("row-anchor-151351-52.01");
    expect(synthetic).toHaveTextContent(/Indiana University-Bloomington/);
    expect(synthetic).toHaveTextContent("31");
    // Stats from the build, not from any backend row.
    expect(synthetic).toHaveTextContent(/8/); // stat_ern
    expect(synthetic).toHaveTextContent(/7/); // stat_roi
    // Estimated pill is visible on the row.
    expect(within(synthetic).getByTestId("estimated-pill")).toHaveTextContent(
      /Estimated/,
    );

    // The rank callout uses the estimated copy and the total from the
    // backend's filtered universe.
    const callout = screen.getByTestId("anchor-rank-callout");
    expect(callout).toHaveAttribute("data-estimated", "true");
    expect(callout).toHaveTextContent(/962/);
    expect(callout).toHaveTextContent(/estimated/i);

    // Divider is rendered above the appended synthetic row. Match
    // exactly so the estimatedNote (which also contains "Your school")
    // doesn't double-match. Card-stack renders the same divider, so
    // assert at least one match rather than exactly one.
    expect(screen.getAllByText("Your school").length).toBeGreaterThan(0);
  });

  it("does_not_render_synthetic_row_when_anchor_stats_missing", async () => {
    // Backend returned an estimated rank but the panel has no anchor
    // stats to build the row from — degrade to "no anchor shown".
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [makeRow({ rank: 1, unitid: 110001 })],
        anchor_in_top_n: false,
        total_qualifying_programs: 500,
        anchor_estimated_rank: 47,
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        anchor={{ unitid: 151351, cipcode: "52.01" }}
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    expect(screen.queryByTestId("anchor-rank-callout")).toBeNull();
    expect(screen.queryByText(/Your school/i)).toBeNull();
    expect(screen.queryByTestId("estimated-pill")).toBeNull();
  });

  it("renders_clean_when_no_anchor", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({ rank: 1, unitid: 110001 }),
          makeRow({ rank: 2, unitid: 110002, institution_name: "Two" }),
        ],
        anchor_in_top_n: false,
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    // No row carries the anchor data attribute.
    await waitFor(() => {
      const anchored = screen
        .getAllByRole("row")
        .filter((r) => r.getAttribute("data-anchor") === "true");
      expect(anchored).toHaveLength(0);
    });
    // No "Your school" divider.
    expect(screen.queryByText(/Your school/i)).toBeNull();
    // No fallback notice.
    expect(screen.queryByText(/Showing all programs/i)).toBeNull();
  });
});

// ===========================================================================
// P0 — empty state with drop-confidence escape
// ===========================================================================

describe("CompareSchoolsPanel — empty state with drop-confidence escape", () => {
  it("renders_empty_state_with_drop_confidence_escape", async () => {
    // First call: empty under default medium filter.
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [],
        total_qualifying_programs: 0,
      }),
    );
    // Second call (after Show all click): rows with low filter.
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [makeRow({ overall_confidence: "low" })],
        total_qualifying_programs: 1,
        confidence_filter_applied: "low",
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="17-2199"
        occupationTitle="Engineers, All Other"
        open
      />,
    );

    // Empty state renders.
    const empty = await screen.findByTestId("empty-compare-schools");
    expect(empty).toBeInTheDocument();
    const showAllBtn = within(empty).getByRole("button", {
      name: /show all programs/i,
    });

    // Click triggers a re-fetch with min_confidence='low'.
    fireEvent.click(showAllBtn);

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalledTimes(2));
    const secondCallArgs = mockFetchBySoc.mock.calls[1]!;
    expect(secondCallArgs[0]).toBe("17-2199");
    // Second positional arg is the opts object.
    expect(secondCallArgs[1]).toMatchObject({ minConfidence: "low" });
  });
});

// ===========================================================================
// P0 — zero pentagons (locks Decision #2)
// ===========================================================================

describe("CompareSchoolsPanel — pentagon-free contract", () => {
  it("does_not_render_pentagon_charts", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({ rank: 1, unitid: 110001 }),
          makeRow({ rank: 2, unitid: 110002, institution_name: "Two" }),
          makeRow({ rank: 3, unitid: 110003, institution_name: "Three" }),
        ],
      }),
    );

    const { container } = render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    // No pentagon test ids leak through.
    expect(screen.queryAllByTestId(/pentagon/i)).toHaveLength(0);
    // No SVG with the pentagon polygon path either — defensive guard
    // against a future refactor that drops the testid.
    const polygons = container.querySelectorAll("polygon");
    // A pentagon chart renders one or more <polygon> shapes; the
    // leaderboard surface should render exactly zero.
    expect(polygons).toHaveLength(0);
  });
});

// ===========================================================================
// P1 — money formatted via existing helper
// ===========================================================================

describe("CompareSchoolsPanel — money formatting", () => {
  it("formats_money_via_existing_helper", async () => {
    const earnings = 87654;
    const cost4yr = 123456;
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({
            rank: 1,
            unitid: 110001,
            earnings_1yr_median: earnings,
            published_cost_4yr: cost4yr,
          }),
        ],
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    // The same helper used elsewhere in the app is the source of truth.
    expect(fmtMoney(earnings)).toBe("$87,654");
    expect(fmtMoney(cost4yr)).toBe("$123,456");

    // Both values appear in the rendered DOM in this exact format.
    // The grid AND the card-stack render the row in jsdom (Tailwind
    // doesn't evaluate media queries), so each value appears twice.
    expect(screen.getAllByText(fmtMoney(earnings)).length).toBeGreaterThan(0);
    expect(screen.getAllByText(fmtMoney(cost4yr)).length).toBeGreaterThan(0);
  });

  it("formats_null_money_as_em_dash_via_helper", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({
            rank: 1,
            unitid: 110001,
            earnings_1yr_median: null,
            net_price_annual: null,
          }),
        ],
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());
    // fmtMoney(null) === "—". There may be other em-dashes in the
    // skeleton, but at minimum the cells render the same glyph.
    expect(fmtMoney(null)).toBe("—");
    // Confirm at least one — appears for null money.
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });
});

// ===========================================================================
// P2 — narrow viewport responsive collapse
// ===========================================================================

describe("CompareSchoolsPanel — narrow viewport collapses columns (P2)", () => {
  // Per §3.D: at <768px ("tablet" Tailwind breakpoint) the desktop CSS-grid
  // table hides and a card-stack takes over. Tailwind doesn't evaluate
  // media queries in jsdom, so these assertions check the *responsive
  // class wiring* — that the right elements get `hidden tablet:grid` /
  // `tablet:hidden` — plus that the card-stack DOM is actually rendered
  // with one card per row. The grid path is exercised by every other
  // test in this file via the same fixtures, so by symmetry the card
  // path is the only new surface to pin here.

  it("narrow_viewport_collapses_columns — grid and card-stack co-render with correct responsive classes", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({ rank: 1, unitid: 110001, institution_name: "Top Tech" }),
          makeRow({ rank: 2, unitid: 110002, institution_name: "Second Place" }),
          makeRow({ rank: 3, unitid: 110003, institution_name: "Bronze U" }),
        ],
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    // Desktop grid is wired with `hidden tablet:grid` so it only renders
    // at the tablet breakpoint and above.
    const grid = await screen.findByTestId("compare-grid");
    expect(grid.className).toContain("hidden");
    expect(grid.className).toContain("tablet:grid");

    // Card-stack is wired with `tablet:hidden` so it only renders below
    // the tablet breakpoint.
    const cardStack = screen.getByTestId("compare-card-stack");
    expect(cardStack.className).toContain("tablet:hidden");

    // Both render the same data (jsdom ignores media queries, so both
    // are present in the DOM).
    expect(within(cardStack).getByText("Top Tech")).toBeInTheDocument();
    expect(within(cardStack).getByText("Second Place")).toBeInTheDocument();
    expect(within(cardStack).getByText("Bronze U")).toBeInTheDocument();
  });

  it("card_renders_rank_school_state_ern_roi_earnings_cost4yr — every data point preserved", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({
            rank: 1,
            unitid: 110001,
            institution_name: "Top Tech",
            program_name: "Computer Science",
            state_abbr: "CA",
            stat_ern: 9,
            stat_roi: 8,
            earnings_1yr_median: 120000,
            published_cost_4yr: 234567,
          }),
        ],
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    const cardStack = await screen.findByTestId("compare-card-stack");
    // Rank, school name, program subtitle, state, ERN, ROI, earnings, cost (4 yr).
    expect(within(cardStack).getByText("1")).toBeInTheDocument();
    expect(within(cardStack).getByText("Top Tech")).toBeInTheDocument();
    expect(within(cardStack).getByText("Computer Science")).toBeInTheDocument();
    expect(within(cardStack).getByText("CA")).toBeInTheDocument();
    expect(within(cardStack).getByText("9")).toBeInTheDocument(); // ERN
    expect(within(cardStack).getByText("8")).toBeInTheDocument(); // ROI
    expect(within(cardStack).getByText(fmtMoney(120000))).toBeInTheDocument();
    expect(within(cardStack).getByText(fmtMoney(234567))).toBeInTheDocument();
  });

  it("card_renders_anchor_variant_with_thrive_left_border", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({
            rank: 7,
            unitid: 999999,
            institution_name: "Your School",
            is_anchor: true,
          }),
          makeRow({ rank: 1, unitid: 110001, institution_name: "Other School" }),
        ],
        anchor_in_top_n: true,
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        anchor={{ unitid: 999999, cipcode: "11.0701" }}
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    // Anchor card has the thrive-tinted bg + 3px left border tokens.
    const anchorCard = await screen.findByTestId("card-anchor-999999-11.0701");
    expect(anchorCard.className).toContain("border-l-accent-thrive");
    expect(anchorCard.className).toContain("bg-accent-thrive/[0.06]");
    // Anchor cards do NOT show the "Build here" CTA (already there).
    expect(
      within(anchorCard).queryByTestId(/btn-card-build-at-/),
    ).not.toBeInTheDocument();
  });

  it("card_stack_renders_appended_anchor_divider_when_anchor_outside_top_n", async () => {
    mockFetchBySoc.mockResolvedValueOnce(
      makeResponse({
        rows: [
          makeRow({ rank: 1, unitid: 110001, institution_name: "Top" }),
          makeRow({ rank: 2, unitid: 110002, institution_name: "Two" }),
          makeRow({
            rank: 47,
            unitid: 999999,
            institution_name: "Your School",
            is_anchor: true,
          }),
        ],
        anchor_in_top_n: false,
      }),
    );

    render(
      <CompareSchoolsPanel
        mode="by_soc"
        enclosure="sheet"
        socCode="15-1252"
        occupationTitle="Software Developers"
        anchor={{ unitid: 999999, cipcode: "11.0701" }}
        open
      />,
    );

    await waitFor(() => expect(mockFetchBySoc).toHaveBeenCalled());

    const cardStack = await screen.findByTestId("compare-card-stack");
    // The "Your school" divider text appears in BOTH the grid and the
    // card-stack (jsdom renders both branches). Assert it's present
    // inside the card-stack DOM specifically.
    const dividerInCardStack = within(cardStack).getAllByText(/your school/i);
    expect(dividerInCardStack.length).toBeGreaterThan(0);
  });
});
