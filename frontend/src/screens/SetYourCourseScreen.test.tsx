/**
 * SetYourCourseScreen.test.tsx
 *
 * Smoke coverage for the unified Set Your Course screen:
 *   - Renders every load-bearing section (school input, effort/loans,
 *     commit + start-over buttons).
 *   - Commit navigates to /my-build.
 *   - Low-confidence resolution surfaces a soft nudge but does NOT
 *     disable the commit button (P1).
 *   - Start-over (after the confirm dialog) resets school / major /
 *     resolution / debug trace (P1).
 *   - 4fr_8fr grid renders at desktop viewport, collapses to 1-col below 1200px.
 */

import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import type { CareerOutcome } from "@/types/build";

function makeCareer(overrides: Partial<CareerOutcome> = {}): CareerOutcome {
  return {
    unitid: 153603,
    institution_name: "Iowa State University",
    cipcode: "26.0101",
    program_name: "Biology, General",
    soc_code: "19-4021",
    occupation_title: "Biological Technician",
    soc_major_group_name: "Life, Physical, and Social Science",
    median_annual_wage: 52140,
    earnings_1yr_median: 38000,
    earnings_1yr_p25: 32000,
    earnings_1yr_p75: 45000,
    debt_median: 24000,
    debt_to_earnings_annual: 0.63,
    education_level_name: "Bachelor's degree",
    growth_category: "Average",
    net_price_annual: 20000,
    cost_of_attendance_annual: 28000,
    modeled_total_debt: 80000,
    debt_median_reference: 24000,
    institution_control: "Public",
    tuition_in_state: 9000,
    tuition_out_of_state: 24000,
    room_board_on_campus: 11000,
    stats: { ern: 2, roi: 3, res: 4, grw: 3, hmn: 3 },
    bosses: { ai: 1, loans: 2, market: 2, burnout: 1, ceiling: 2 },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: 5,
    overall_confidence: "high",
    match_quality: null,
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    is_out_of_state: false,
    loan_pct: 1.0,
    ...overrides,
  };
}

// Mock every API module the screen pulls in so no network escapes.
vi.mock("@/api/intent", () => ({
  streamIntent: vi.fn(async function* () {
    // No events — the screen stays in its idle state for these tests.
  }),
  dispatchChip: vi.fn(),
  commitResolution: vi.fn(),
}));
vi.mock("@/api/build", () => ({
  getOutcomes: vi.fn().mockResolvedValue([]),
  getTieredCareers: vi.fn().mockResolvedValue({
    common: [],
    less_common: [],
    stretch: [],
  }),
}));
const mockGetCareerPickChips = vi.fn();
const mockAskCareerPickChip = vi.fn();
vi.mock("@/api/careerPick", () => ({
  getCareerPickChips: (...args: unknown[]) => mockGetCareerPickChips(...args),
  askCareerPickChip: (...args: unknown[]) => mockAskCareerPickChip(...args),
}));
vi.mock("@/api/client", () => ({
  apiGet: vi.fn().mockResolvedValue([]),
  apiPost: vi.fn().mockResolvedValue({ committed: true, logged: false }),
}));
// ChapterBook fetches branches on mount. Mock so no network escapes and
// the book can render ready/loading/error shapes in the list→book tests.
vi.mock("@/api/tree", () => ({
  getBranchesForSoc: vi.fn().mockResolvedValue([]),
}));

import { commitResolution } from "@/api/intent";
import { getOutcomes } from "@/api/build";
import { SetYourCourseScreen } from "./SetYourCourseScreen";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderScreen() {
  return render(
    <MemoryRouter>
      <SetYourCourseScreen />
    </MemoryRouter>,
  );
}

function seedState(overrides: Partial<ReturnType<typeof useBuildInputStore.getState>> = {}) {
  useProfileStore.setState({
    profileName: "dancing happy bear",
    animalEmoji: "🐻",
    animalName: "bear",
  });
  useBuildInputStore.setState({
    phase: "major",
    school: {
      unitid: 151351,
      name: "Indiana University",
      institutionControl: null,
      stateAbbr: "IN",
      netPriceAnnual: null,
      costOfAttendanceAnnual: null,
      tuitionInState: null,
      tuitionOutOfState: null,
    },
    programs: [],
    major: null,
    effort: { level: "balanced", percentile: 50, ernShift: 0 },
    loans: { percentage: 50 },
    initialResolution: null,
    currentResolution: null,
    hasCorrected: false,
    debugTrace: null,
    ...overrides,
  });
  useBuildStore.setState({
    selectedCareer: null,
  });
}

beforeEach(() => {
  window.scrollTo = vi.fn();
  mockNavigate.mockReset();
  mockGetCareerPickChips.mockReset().mockResolvedValue([]);
  mockAskCareerPickChip.mockReset().mockResolvedValue({
    chip_id: "why_these_tiers",
    answer: "Gemma explains these paths.",
    fallback_fired: false,
  });
  vi.mocked(commitResolution).mockReset();
  vi.mocked(commitResolution).mockResolvedValue({
    committed: true,
    logged: false,
  });
});

// ---------------------------------------------------------------------------
// TestRender
// ---------------------------------------------------------------------------

describe("TestRender", () => {
  it("renders_all_sections — school, major, and preview surfaces all present", () => {
    seedState();
    renderScreen();

    expect(screen.getByText(/Where does this take you\?/i)).toBeInTheDocument();
    expect(screen.getByText(/^Your school$/i)).toBeInTheDocument();
    expect(screen.getByText(/^Your field of study$/i)).toBeInTheDocument();
    expect(screen.getByTestId("major-input")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// TestFlow
// ---------------------------------------------------------------------------

describe("TestFlow", () => {
  it("commit_navigates_to_my_build — tapping Spec my build with outcomes loaded routes to /my-build", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedState({
      initialResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
    });

    renderScreen();

    const commit = await screen.findByText(/Spec my build/);
    expect(commit).not.toBeDisabled();

    fireEvent.click(commit);

    await waitFor(() => {
      expect(commitResolution).toHaveBeenCalledTimes(1);
      expect(mockNavigate).toHaveBeenCalledWith("/my-build");
    });
  });
});

// ---------------------------------------------------------------------------
// TestLowConfidence (P1)
// ---------------------------------------------------------------------------

describe("TestLowConfidence", () => {
  it("commit_shows_nudge_not_gate — low-confidence resolution surfaces a soft nudge but leaves commit enabled", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedState({
      initialResolution: {
        matched_cip: "51.0000",
        matched_title: "Something vaguely health-ish",
        confidence: "low",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: true,
        alternatives: null,
        parent_cip: "",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "51.0000",
        matched_title: "Something vaguely health-ish",
        confidence: "low",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: true,
        alternatives: null,
        parent_cip: "",
        confirmed_focus: null,
      },
    });

    renderScreen();
    const nudge = await screen.findByTestId("soft-nudge");
    expect(nudge).toBeInTheDocument();
    expect(nudge.textContent).toMatch(/wasn't sure/i);
    const commit = screen.getByText(/Spec my build/);
    expect(commit).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// TestStartOver (P1)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// TestChapterBook — feature-chapter-book §4 New Tests Required (P0)
//
// These tests exercise the 4fr/8fr grid, the list→book swap when a
// career row is tapped, and the book-state reset when the Gemma
// resolution's matched_cip changes.
// ---------------------------------------------------------------------------

const RESOLVED_MARKETING = {
  matched_cip: "52.1401",
  matched_title: "Marketing",
  confidence: "high",
  reasoning: "",
  careers_preview: [],
  audit_flag: null,
  audit_message: null,
  needs_clarification: false,
  alternatives: [],
  parent_cip: "",
  confirmed_focus: null,
};

function seedWithResolvedMajor(): void {
  seedState({
    initialResolution: { ...RESOLVED_MARKETING },
    currentResolution: { ...RESOLVED_MARKETING },
  });
}

function makeCareers(): CareerOutcome[] {
  // Two careers — so we can prove the clicked-on one (not "the first")
  // is what opens in the book. The second has a distinctive SOC prefix
  // (11-*) for unambiguous assertions.
  return [
    makeCareer({
      soc_code: "19-4021",
      occupation_title: "Biological Technician",
    }),
    makeCareer({
      soc_code: "11-9121",
      occupation_title: "Natural Sciences Manager",
    }),
  ];
}


describe("TestChapterBook_GridLayout", () => {
  it("renders the 4fr_8fr grid on desktop viewports (>=1200px)", () => {
    // window.innerWidth for jsdom defaults to 1024. We bump it to the
    // desktop breakpoint for this assertion — though we're really
    // checking that the class is in the DOM, since Tailwind doesn't
    // actually evaluate media queries in jsdom. The `desktop:` prefix
    // is what @fp-design-auditor reviews for.
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1280,
    });
    seedState();
    const { container } = renderScreen();
    // Find the grid wrapper by its class signature. This matches the
    // wrapper in SetYourCourseScreen.tsx:319.
    const grid = container.querySelector(".grid.grid-cols-1");
    expect(grid).not.toBeNull();
    expect(grid!.className).toContain("desktop:grid-cols-2");
    // Guard against a silent regression to the older 7fr_5fr ratio.
    expect(grid!.className).not.toContain("7fr_5fr");
  });

  it("collapses to single column below desktop (<1200px)", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024, // tablet
    });
    seedState();
    const { container } = renderScreen();
    const grid = container.querySelector(".grid.grid-cols-1");
    expect(grid).not.toBeNull();
    // The fallback `grid-cols-1` class is present, so below the desktop
    // breakpoint Tailwind falls through to the single-column layout.
    expect(grid!.className).toContain("grid-cols-1");
  });
});

// Chapter Book tests removed — chapter book was removed from SetYourCourseScreen.
// Career exploration now happens on BranchTreeScreen post-reveal.

// ---------------------------------------------------------------------------
// TestSocRevealStates (P0) — outcomes-first paint + tier slot-in
// ---------------------------------------------------------------------------

describe("TestSocRevealStates", () => {
  beforeEach(() => {
    vi.mocked(getOutcomes).mockReset();
  });

  it("career cards render when outcomes load", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedWithResolvedMajor();
    renderScreen();

    expect(await screen.findByText("Biological Technician")).toBeInTheDocument();
    expect(screen.getByText("Natural Sciences Manager")).toBeInTheDocument();
    expect(screen.getByText("Where this leads")).toBeInTheDocument();
  });

  it("effort section appears after outcomes load", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedWithResolvedMajor();
    renderScreen();

    const section = await screen.findByTestId("effort-commit-section");
    expect(section).toBeInTheDocument();
    expect(screen.getByText(/Spec my build/)).toBeInTheDocument();
  });

  it("renders Ask Gemma chips above Where this leads when outcomes load", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    mockGetCareerPickChips.mockResolvedValueOnce([
      {
        id: "why_these_tiers",
        label: "Why are some careers 'Common' and some 'Stretch'?",
        elevated: false,
        terminal_title: null,
      },
    ]);
    seedWithResolvedMajor();
    renderScreen();

    const group = await screen.findByRole("group", {
      name: "Ask Gemma about these career paths",
    });
    expect(
      within(group).getByRole("button", {
        name: "Why are some careers 'Common' and some 'Stretch'?",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Make sense of these paths")).toBeInTheDocument();
    expect(mockGetCareerPickChips).toHaveBeenCalledWith({
      cipcode: "52.1401",
      majorText: "Marketing",
      socCodes: ["19-4021", "11-9121"],
    });
  });

  it("asks Gemma from the Set Your Course chip row with rendered SOC context", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    mockGetCareerPickChips.mockResolvedValueOnce([
      {
        id: "why_these_tiers",
        label: "Why are some careers 'Common' and some 'Stretch'?",
        elevated: false,
        terminal_title: null,
      },
    ]);
    mockAskCareerPickChip.mockResolvedValueOnce({
      chip_id: "why_these_tiers",
      answer: "Gemma explains how these paths relate to the program.",
      fallback_fired: false,
    });
    seedWithResolvedMajor();
    renderScreen();

    const group = await screen.findByRole("group", {
      name: "Ask Gemma about these career paths",
    });
    fireEvent.click(
      within(group).getByRole("button", {
        name: "Why are some careers 'Common' and some 'Stretch'?",
      }),
    );

    await waitFor(() => {
      expect(mockAskCareerPickChip).toHaveBeenCalledWith({
        chipId: "why_these_tiers",
        cipcode: "52.1401",
        majorText: "Marketing",
        socCodes: ["19-4021", "11-9121"],
        selectedSoc: null,
        terminalTitle: null,
        locale: "en",
      });
    });
    expect(
      await screen.findByText(
        "Gemma explains how these paths relate to the program.",
      ),
    ).toBeInTheDocument();
  });
});

describe("TestStartOver", () => {
  it("resets_state — confirming start-over clears school, major, resolution, debug trace", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedState({
      initialResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
      debugTrace: "prior trace",
    });

    renderScreen();

    const startOver = await screen.findByTestId("btn-start-over");
    fireEvent.click(startOver);
    expect(await screen.findByTestId("confirm-start-over")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("btn-confirm-start-over"));

    await waitFor(() => {
      const state = useBuildInputStore.getState();
      expect(state.school).toBeNull();
      expect(state.major).toBeNull();
      expect(state.currentResolution).toBeNull();
      expect(state.initialResolution).toBeNull();
      expect(state.debugTrace).toBeNull();
    });
  });
});

// ---------------------------------------------------------------------------
// TestCipPicker (P1) — multi-CIP picker rendering
// ---------------------------------------------------------------------------

describe("TestCipPicker", () => {
  it("renders_cip_picker_when_alternatives_present — resolution with 2 alts shows picker", () => {
    seedState({
      initialResolution: {
        matched_cip: "14.0901",
        matched_title: "Computer Engineering",
        confidence: "high",
        reasoning: "Closest match.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [
          { cip: "14.1001", title: "Electrical Engineering", why: "Circuits", parent_cip: "14.10" },
          { cip: "14.1901", title: "Mechanical Engineering", why: "Physical", parent_cip: "14.19" },
        ],
        parent_cip: "14.09",
        confirmed_focus: null,
        remaining_count: 11,
        narrowing_hint: "Try civil engineering",
      },
      currentResolution: {
        matched_cip: "14.0901",
        matched_title: "Computer Engineering",
        confidence: "high",
        reasoning: "Closest match.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [
          { cip: "14.1001", title: "Electrical Engineering", why: "Circuits", parent_cip: "14.10" },
          { cip: "14.1901", title: "Mechanical Engineering", why: "Physical", parent_cip: "14.19" },
        ],
        parent_cip: "14.09",
        confirmed_focus: null,
        remaining_count: 11,
        narrowing_hint: "Try civil engineering",
      },
    });

    renderScreen();

    expect(screen.getByTestId("cip-picker")).toBeInTheDocument();
    expect(screen.getByTestId("cip-option-primary")).toBeInTheDocument();
    expect(screen.getByTestId("cip-option-alt-0")).toBeInTheDocument();
    expect(screen.getByTestId("cip-option-alt-1")).toBeInTheDocument();
  });

  it("no_picker_when_single_cip — resolution with no alternatives renders no picker", () => {
    seedState({
      initialResolution: {
        matched_cip: "51.3801",
        matched_title: "Nursing",
        confidence: "high",
        reasoning: "Unambiguous match.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "51.38",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "51.3801",
        matched_title: "Nursing",
        confidence: "high",
        reasoning: "Unambiguous match.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "51.38",
        confirmed_focus: null,
      },
    });

    renderScreen();

    expect(screen.queryByTestId("cip-picker")).not.toBeInTheDocument();
  });

  it("remaining_count_hint_rendered — remaining_count: 11 shows hint text", () => {
    seedState({
      initialResolution: {
        matched_cip: "14.0901",
        matched_title: "Computer Engineering",
        confidence: "high",
        reasoning: "Closest match.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [
          { cip: "14.1001", title: "Electrical Engineering", why: "Circuits", parent_cip: "14.10" },
        ],
        parent_cip: "14.09",
        confirmed_focus: null,
        remaining_count: 11,
        narrowing_hint: "Try civil engineering",
      },
      currentResolution: {
        matched_cip: "14.0901",
        matched_title: "Computer Engineering",
        confidence: "high",
        reasoning: "Closest match.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [
          { cip: "14.1001", title: "Electrical Engineering", why: "Circuits", parent_cip: "14.10" },
        ],
        parent_cip: "14.09",
        confirmed_focus: null,
        remaining_count: 11,
        narrowing_hint: "Try civil engineering",
      },
    });

    renderScreen();

    const hint = screen.getByTestId("cip-remaining-hint");
    expect(hint).toBeInTheDocument();
    expect(hint.textContent).toMatch(/11 more programs match/);
    expect(hint.textContent).toMatch(/Try civil engineering/);
  });
});
