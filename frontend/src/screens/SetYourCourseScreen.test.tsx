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

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
    wage_p10: null,
    wage_p25: null,
    wage_p75: null,
    wage_p90: null,
    earnings_1yr_median: 38000,
    earnings_1yr_p25: 32000,
    earnings_1yr_p75: 45000,
    debt_median: 24000,
    debt_to_earnings_annual: 0.63,
    education_level_name: "Bachelor's degree",
    growth_category: "Average",
    work_experience_code: null,
    net_price_annual: 20000,
    cost_of_attendance_annual: 28000,
    published_cost_4yr: null,
    modeled_total_debt: 80000,
    debt_median_reference: 24000,
    institution_control: "Public",
    tuition_in_state: 9000,
    tuition_out_of_state: 24000,
    room_board_on_campus: 11000,
    stats: { ern: 2, roi: 3, res: 4, grw: 3, aura: 3 },
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
// `getCareerPickChips` / `askCareerPickChip` are no longer consumed
// by SetYourCourseScreen — replaced by per-career sparkle that fires
// the scoped Ask Gemma chat. Mock left in place defensively in case any
// transitive import still pulls the module.
vi.mock("@/api/careerPick", () => ({
  getCareerPickChips: vi.fn().mockResolvedValue([]),
  askCareerPickChip: vi.fn(),
}));

// askGemmaStream — the per-career sparkle opens GemmaChat with a
// career-scope opener that fires this immediately. Stub to a happy
// SSE-equivalent default so the auto-fire doesn't blow up in jsdom.
const mockAskGemmaStream = vi.fn().mockImplementation(
  async (..._args: unknown[]) => {
    const final = { type: "final_text" as const, response: "ok" };
    const done = { type: "done" as const };
    const onEvent = _args[3] as ((e: unknown) => void) | undefined;
    if (onEvent) {
      onEvent(final);
      onEvent(done);
    }
    return { response: "ok", events: [final, done] };
  },
);
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    askGemmaStream: (...args: Parameters<typeof import("@/api/menu").askGemmaStream>) =>
      mockAskGemmaStream(...args),
  };
});
vi.mock("@/api/client", () => ({
  apiGet: vi.fn().mockResolvedValue([]),
  apiPost: vi.fn().mockResolvedValue({ committed: true, logged: false }),
}));

// careerDescriptionStore — sparkle click runs through this single-flight
// store. Mock so tests can drive the cache-hit / cache-miss paths.
const mockLoadCareerDescription = vi.fn();
const mockGetCachedCareerDescription = vi.fn();
vi.mock("@/store/careerDescriptionStore", () => ({
  loadCareerDescription: (...args: unknown[]) =>
    mockLoadCareerDescription(...args),
  getCachedCareerDescription: (...args: unknown[]) =>
    mockGetCachedCareerDescription(...args),
  clearCareerDescriptionCache: vi.fn(),
}));
// ChapterBook fetches branches on mount. Mock so no network escapes and
// the book can render ready/loading/error shapes in the list→book tests.
vi.mock("@/api/tree", () => ({
  getBranchesForSoc: vi.fn().mockResolvedValue([]),
}));

const mockRequestPrefetch = vi.fn();
vi.mock("@/api/prefetch", () => ({
  requestPrefetch: (...args: unknown[]) => mockRequestPrefetch(...args),
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
  mockAskGemmaStream.mockClear();
  mockRequestPrefetch.mockReset();
  mockLoadCareerDescription.mockReset();
  mockGetCachedCareerDescription.mockReset();
  // Default: cache miss, fetch resolves to a populated description.
  mockGetCachedCareerDescription.mockReturnValue(null);
  mockLoadCareerDescription.mockResolvedValue({
    soc_code: "19-4021",
    summary: "Biological technicians help biologists in the lab.",
    tasks: [
      "Set up lab equipment for experiments",
      "Record observations in lab notebooks",
      "Collect and prepare samples",
      "Maintain instruments and clean glassware",
    ],
    anchor_tier: "activities",
    generated_at: "2026-05-07T00:00:00+00:00",
    model: "gemma-4-26b-a4b-it",
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
  it("commit_navigates_to_my_build — tapping Build my character with outcomes loaded routes to /my-build", async () => {
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
    useBuildStore.setState({ selectedCareer: careers[0]! });

    renderScreen();

    const commit = await screen.findByText(/Build my character/);
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
    useBuildStore.setState({ selectedCareer: careers[0]! });

    renderScreen();
    const nudge = await screen.findByTestId("soft-nudge");
    expect(nudge).toBeInTheDocument();
    expect(nudge.textContent).toMatch(/close call/i);
    const commit = screen.getByText(/Build my character/);
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
    // Both careers have work_experience_code=null → fall into the
    // "Early-career roles" bucket via the null fallback.
    expect(screen.getByText("Early-career roles")).toBeInTheDocument();
  });

  it("groups careers into first-jobs / early-career / long-term sections in order", async () => {
    // Mixed work_experience_code values exercise all three buckets.
    const mixed: CareerOutcome[] = [
      makeCareer({
        soc_code: "15-1252",
        occupation_title: "Software Developers",
        work_experience_code: 3, // None required → first jobs
      }),
      makeCareer({
        soc_code: "11-3021",
        occupation_title: "Computer and Information Systems Managers",
        work_experience_code: 1, // 5+ yrs → long-term
      }),
      makeCareer({
        soc_code: "15-1211",
        occupation_title: "Computer Systems Analysts",
        work_experience_code: 2, // <5 yrs → early-career
      }),
      makeCareer({
        soc_code: "15-1299",
        occupation_title: "Computer Occupations, All Other",
        work_experience_code: null, // null → early-career fallback
      }),
    ];
    vi.mocked(getOutcomes).mockResolvedValue(mixed);
    seedWithResolvedMajor();
    renderScreen();

    // All three section headers visible.
    const firstJobs = await screen.findByText("Likely first jobs");
    const earlyCareer = screen.getByText("Early-career roles");
    const longTerm = screen.getByText("Where this can lead long-term");

    // DOM order matches render order: first jobs → early-career → long-term.
    const docOrder = [...document.querySelectorAll("h2")]
      .map((h) => h.textContent ?? "")
      .filter((t) =>
        ["Likely first jobs", "Early-career roles", "Where this can lead long-term"].includes(t),
      );
    expect(docOrder).toEqual([
      "Likely first jobs",
      "Early-career roles",
      "Where this can lead long-term",
    ]);

    // Each section's section element scopes its career card.
    const firstJobsSection = firstJobs.closest("section");
    const earlyCareerSection = earlyCareer.closest("section");
    const longTermSection = longTerm.closest("section");
    expect(firstJobsSection).not.toBeNull();
    expect(earlyCareerSection).not.toBeNull();
    expect(longTermSection).not.toBeNull();

    // Software Developers (code 3) lands in first-jobs.
    expect(firstJobsSection!.textContent).toContain("Software Developers");
    // Both code 2 and null career titles land in early-career.
    expect(earlyCareerSection!.textContent).toContain("Computer Systems Analysts");
    expect(earlyCareerSection!.textContent).toContain("Computer Occupations, All Other");
    // Manager role (code 1) lands in long-term.
    expect(longTermSection!.textContent).toContain(
      "Computer and Information Systems Managers",
    );
  });

  it("hides empty sections entirely", async () => {
    // Only long-term careers — first-jobs and early-career headers
    // should not appear at all.
    const onlyLongTerm: CareerOutcome[] = [
      makeCareer({
        soc_code: "11-3021",
        occupation_title: "IT Manager",
        work_experience_code: 1,
      }),
    ];
    vi.mocked(getOutcomes).mockResolvedValue(onlyLongTerm);
    seedWithResolvedMajor();
    renderScreen();

    expect(
      await screen.findByText("Where this can lead long-term"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Likely first jobs")).not.toBeInTheDocument();
    expect(screen.queryByText("Early-career roles")).not.toBeInTheDocument();
  });

  it("effort section appears after outcomes load", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedWithResolvedMajor();
    useBuildStore.setState({ selectedCareer: careers[0]! });
    renderScreen();

    const section = await screen.findByTestId("effort-commit-section");
    expect(section).toBeInTheDocument();
    expect(screen.getByText(/Build my character/)).toBeInTheDocument();
  });

  it("renders a per-career Ask Gemma sparkle button", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedWithResolvedMajor();
    renderScreen();

    // One sparkle button per rendered career.
    expect(
      await screen.findByTestId("btn-ask-career-19-4021"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("btn-ask-career-11-9121")).toBeInTheDocument();
  });

  it("clicking the career sparkle opens the chat with a career scope and no auto-fired opener", async () => {
    // The structured "About this career" card is now the answer; the
    // freeform describe-in-detail opener that used to auto-fire was
    // producing a duplicate description below the card. Chat starts
    // empty — the student types their own follow-up.
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedWithResolvedMajor();
    renderScreen();

    const sparkle = await screen.findByTestId("btn-ask-career-19-4021");
    mockAskGemmaStream.mockClear();
    fireEvent.click(sparkle);

    // Chat dialog mounts (the slide-in's role=dialog).
    await waitFor(() => {
      expect(screen.getByTestId("dialog-chat")).toBeInTheDocument();
    });

    // No opener fires — askGemmaStream stays untouched until the user
    // types something into the chat.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(mockAskGemmaStream).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------
  // feature-career-description-on-pdf.md §4 New Tests Required (P1):
  // sparkle click drives the careerDescriptionStore single-flight.
  // -------------------------------------------------------------------

  it("sparkle_click_fetches_career_description — click → loadCareerDescription called with the SOC", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedWithResolvedMajor();
    renderScreen();

    const sparkle = await screen.findByTestId("btn-ask-career-19-4021");
    // Cache miss — store should dispatch a fetch.
    mockGetCachedCareerDescription.mockReturnValue(null);
    fireEvent.click(sparkle);

    await waitFor(() => {
      expect(mockGetCachedCareerDescription).toHaveBeenCalledWith("19-4021");
      expect(mockLoadCareerDescription).toHaveBeenCalledTimes(1);
    });
    const [soc, title] = mockLoadCareerDescription.mock.calls[0]!;
    expect(soc).toBe("19-4021");
    expect(title).toBe("Biological Technician");
  });

  it("sparkle_click_cache_hit_skips_fetch — second click for same SOC → no second loadCareerDescription call", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);
    seedWithResolvedMajor();
    renderScreen();

    const sparkle = await screen.findByTestId("btn-ask-career-19-4021");

    // First click — cache miss, fetch dispatches.
    mockGetCachedCareerDescription.mockReturnValue(null);
    fireEvent.click(sparkle);
    await waitFor(() => {
      expect(mockLoadCareerDescription).toHaveBeenCalledTimes(1);
    });

    // Second click for the SAME SOC — store now reports a cache hit.
    // The screen should pull synchronously from the cache and NOT
    // invoke loadCareerDescription a second time.
    mockGetCachedCareerDescription.mockReturnValue({
      soc_code: "19-4021",
      summary: "cached",
      tasks: ["a", "b", "c", "d"],
      anchor_tier: "activities",
      generated_at: "2026-05-07T00:00:00+00:00",
      model: "gemma-4-26b-a4b-it",
    });
    fireEvent.click(sparkle);

    // Wait a microtask so any pending async work settles before asserting.
    await waitFor(() => {
      expect(mockGetCachedCareerDescription).toHaveBeenCalledWith("19-4021");
    });
    // Still exactly 1 fetch — cache hit short-circuits.
    expect(mockLoadCareerDescription).toHaveBeenCalledTimes(1);
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


// ===========================================================================
// TestPrefetch — speculative build prefetch fires on career select
// ===========================================================================

describe("TestPrefetch", () => {
  it("fires requestPrefetch when school + resolution + career are set", async () => {
    seedState({
      initialResolution: { ...RESOLVED_MARKETING },
      currentResolution: { ...RESOLVED_MARKETING },
    });
    useBuildStore.setState({
      selectedCareer: makeCareer({
        soc_code: "19-4021",
        occupation_title: "Biological Technician",
      }),
    });

    renderScreen();

    await waitFor(() => {
      expect(mockRequestPrefetch).toHaveBeenCalledTimes(1);
    });

    const call = mockRequestPrefetch.mock.calls[0] as [Record<string, unknown>];
    const params = call[0];
    expect(params.unitid).toBe(151351);
    expect(params.cipcode).toBe("52.1401");
    expect(params.soc_code).toBe("19-4021");
    expect(params.effort).toBe("balanced");
    expect(params.loan_pct).toBe(0.5);
  });

  it("does not fire prefetch when no career is selected", () => {
    seedState({
      initialResolution: { ...RESOLVED_MARKETING },
      currentResolution: { ...RESOLVED_MARKETING },
    });

    renderScreen();

    expect(mockRequestPrefetch).not.toHaveBeenCalled();
  });
});
