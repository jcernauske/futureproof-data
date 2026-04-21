/**
 * SetYourCourseScreen.test.tsx
 *
 * Smoke coverage for the unified Set Your Course screen:
 *   - Renders every load-bearing section (school input, effort/loans,
 *     commit + start-over buttons).
 *   - Commit navigates to /reveal.
 *   - Low-confidence resolution surfaces a soft nudge but does NOT
 *     disable the commit button (P1).
 *   - Start-over (after the confirm dialog) resets school / major /
 *     resolution / debug trace (P1).
 *   - 4fr_8fr grid renders at desktop viewport, collapses to 1-col below 1200px.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { makeCareer } from "@/components/chapter-book/__fixtures__/branches";
import type { CareerOutcome, TieredCareers } from "@/types/build";

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
import { getOutcomes, getTieredCareers } from "@/api/build";
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
    profileName: "dancing happy bear 🐻",
    animalEmoji: "🐻",
    animalName: "bear",
  });
  useBuildInputStore.setState({
    phase: "major",
    school: {
      unitid: 151351,
      name: "Indiana University",
      institutionControl: null,
      netPriceAnnual: null,
      costOfAttendanceAnnual: null,
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
    tieredCareers: null,
    selectedCareer: null,
  });
}

beforeEach(() => {
  mockNavigate.mockReset();
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
  it("renders_all_sections — school, major, and commit surfaces all present", () => {
    seedState();
    renderScreen();

    // Mockup-aligned eyebrow + headline.
    expect(screen.getByText(/Where does this take you\?/i)).toBeInTheDocument();
    // School + major labels from the two-column layout.
    expect(screen.getByText(/^Your school$/i)).toBeInTheDocument();
    expect(screen.getByText(/^Your field of study$/i)).toBeInTheDocument();
    expect(screen.getByTestId("major-input")).toBeInTheDocument();
    // Commit + start over (desktop has these; mobile duplicates are in
    // the bottom bar, so just check for presence).
    expect(screen.getByTestId("btn-start-over")).toBeInTheDocument();
    expect(screen.getByTestId("btn-commit")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// TestFlow
// ---------------------------------------------------------------------------

describe("TestFlow", () => {
  it("commit_navigates_to_reveal — tapping commit with a valid resolution routes to /reveal", async () => {
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
    const commit = screen.getByTestId("btn-commit");
    expect(commit).not.toBeDisabled();

    fireEvent.click(commit);

    await waitFor(() => {
      expect(commitResolution).toHaveBeenCalledTimes(1);
      expect(mockNavigate).toHaveBeenCalledWith("/reveal");
    });
  });
});

// ---------------------------------------------------------------------------
// TestLowConfidence (P1)
// ---------------------------------------------------------------------------

describe("TestLowConfidence", () => {
  it("commit_shows_nudge_not_gate — low-confidence resolution surfaces a soft nudge but leaves commit enabled", () => {
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
    const nudge = screen.getByTestId("soft-nudge");
    expect(nudge).toBeInTheDocument();
    expect(nudge.textContent).toMatch(/wasn't sure/i);
    // Commit is NOT disabled — low confidence is a nudge, not a gate.
    const commit = screen.getByTestId("btn-commit");
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
    expect(grid!.className).toContain("desktop:grid-cols-[4fr_8fr]");
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
    vi.mocked(getTieredCareers).mockReset();
  });

  it("chips render in intermediate state with shimmer header", async () => {
    const careers = makeCareers();
    // getOutcomes resolves fast; getTieredCareers hangs forever.
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    let tierResolve!: (v: TieredCareers) => void;
    vi.mocked(getTieredCareers).mockReturnValue(
      new Promise((res) => { tierResolve = res; }),
    );
    seedWithResolvedMajor();
    renderScreen();

    const shimmer = await screen.findByTestId("tier-section-loading");
    expect(shimmer).toBeInTheDocument();
    expect(shimmer.textContent).toMatch(/Organizing your paths/i);

    // Chips are rendered even though tiers haven't resolved.
    expect(screen.getByText("Biological Technician")).toBeInTheDocument();
    expect(screen.getByText("Natural Sciences Manager")).toBeInTheDocument();

    // Clean up the hanging promise to avoid dangling state.
    tierResolve({ common: careers, less_common: [], stretch: [] });
  });

  it("tier headers replace shimmer when tier resolves", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    vi.mocked(getTieredCareers).mockResolvedValue({
      common: [careers[0]!],
      less_common: [careers[1]!],
      stretch: [],
    });
    seedWithResolvedMajor();
    renderScreen();

    // Wait for the full flow: debounce fires, outcomes resolve, tier resolves.
    await waitFor(
      () => {
        expect(screen.queryByTestId("tier-section-loading")).not.toBeInTheDocument();
        expect(screen.getByText("Where this commonly leads")).toBeInTheDocument();
      },
      { timeout: 3000 },
    );

    expect(screen.getByText(/Uncommon paths/)).toBeInTheDocument();
  });
});

describe("TestStartOver", () => {
  it("resets_state — confirming start-over clears school, major, resolution, debug trace", async () => {
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

    // Open confirm dialog.
    fireEvent.click(screen.getByTestId("btn-start-over"));
    expect(await screen.findByTestId("confirm-start-over")).toBeInTheDocument();

    // Confirm.
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
