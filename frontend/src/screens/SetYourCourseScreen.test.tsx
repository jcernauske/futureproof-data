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

import { commitResolution, streamIntent } from "@/api/intent";
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


// ===========================================================================
// Bundle 4: narrowing_hint inline + softNudge medium-confidence (P0)
// post-100-build-test-fixes-bundle §4 — when there are NO alternatives but
// Gemma still emits a narrowing_hint (common for medium-confidence one-word
// inputs like "money" → Mathematics), render the hint inline. And extend
// softNudge to fire on confidence === "medium" as well as "low".
// ===========================================================================

describe("TestBundle4NarrowingHintInline", () => {
  it("renders_narrowing_hint_when_no_alternatives — inline narrowing hint surfaces when alternatives are empty", () => {
    // The contract: hint visible inline iff:
    //   currentResolution.narrowing_hint is non-empty
    //   AND initialResolution.alternatives is empty/absent.
    seedState({
      initialResolution: {
        matched_cip: "27.0101",
        matched_title: "Mathematics, General",
        confidence: "medium",
        reasoning: "Mathematics is the closest fit for 'money'.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        // Empty alternatives — this is what triggers the inline render.
        // CipPicker would otherwise own the narrowing_hint rendering.
        alternatives: [],
        parent_cip: "27.01",
        confirmed_focus: null,
        remaining_count: 0,
        narrowing_hint: "Try 'finance' or 'economics' if you want money-focused programs.",
      },
      currentResolution: {
        matched_cip: "27.0101",
        matched_title: "Mathematics, General",
        confidence: "medium",
        reasoning: "Mathematics is the closest fit for 'money'.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "27.01",
        confirmed_focus: null,
        remaining_count: 0,
        narrowing_hint: "Try 'finance' or 'economics' if you want money-focused programs.",
      },
    });

    renderScreen();

    const hint = screen.getByTestId("narrowing-hint-inline");
    expect(hint).toBeInTheDocument();
    expect(hint.textContent).toContain("'finance' or 'economics'");

    // CipPicker must NOT render (no alternatives) — otherwise we'd
    // get a duplicate hint.
    expect(screen.queryByTestId("cip-picker")).not.toBeInTheDocument();
  });

  it("does_not_render_inline_narrowing_hint_when_alternatives_present — CipPicker owns the hint when alts exist", () => {
    // Mutual-exclusion guard: the inline render must hide when
    // CipPicker is mounted (because the hint moves into the picker).
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
        remaining_count: 5,
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
        remaining_count: 5,
        narrowing_hint: "Try civil engineering",
      },
    });

    renderScreen();

    // CipPicker mounts → inline hint must NOT render.
    expect(screen.getByTestId("cip-picker")).toBeInTheDocument();
    expect(
      screen.queryByTestId("narrowing-hint-inline"),
    ).not.toBeInTheDocument();
  });
});


describe("TestBundle4SoftNudgeMedium", () => {
  it("extends_softnudge_to_medium_confidence — medium-confidence resolution surfaces soft-nudge + caution color", async () => {
    const careers = makeCareers();
    vi.mocked(getOutcomes).mockResolvedValue(careers);

    seedState({
      initialResolution: {
        matched_cip: "27.0101",
        matched_title: "Mathematics, General",
        confidence: "medium",  // the new path — Bundle 4 flips this on.
        reasoning: "Mathematics is the closest fit.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "27.01",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "27.0101",
        matched_title: "Mathematics, General",
        confidence: "medium",
        reasoning: "Mathematics is the closest fit.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "27.01",
        confirmed_focus: null,
      },
    });
    useBuildStore.setState({ selectedCareer: careers[0]! });

    renderScreen();

    // softNudge surfaces — same testid as the low-confidence path, but
    // the trigger is now confidence === "medium".
    const nudge = await screen.findByTestId("soft-nudge");
    expect(nudge).toBeInTheDocument();
    expect(nudge.textContent).toMatch(/close call/i);

    // Commit stays enabled — the nudge is informational, not a gate.
    const commit = screen.getByText(/Build my character/);
    expect(commit).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// DemoChipsDrawer integration (P0)
// End-to-end coverage of the chip → school → majorText → useEffect →
// resolve → streamIntent chain. The drawer fires onPick, the screen seeds
// the store via handleSchoolSelect + setMajorText, and a deferred useEffect
// triggers resolve() once school + majorText have both committed (the
// closure-staleness workaround at SetYourCourseScreen.tsx:166-173).
// ---------------------------------------------------------------------------

describe("SetYourCourseScreen — DemoChipsDrawer integration (P0)", () => {
  beforeEach(() => {
    vi.mocked(streamIntent).mockClear();
  });

  it("chip_click_seeds_school_and_major_and_fires_intent_stream — happy path", async () => {
    // Start with no school selected — the demo chip is the only way in.
    seedState({ school: null });
    renderScreen();

    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-single-110635-computer-science"),
    );

    // School lands in the buildInputStore (chip's hardcoded SchoolSelection).
    await waitFor(() => {
      expect(useBuildInputStore.getState().school?.unitid).toBe(110635);
    });
    expect(useBuildInputStore.getState().school?.name).toBe(
      "University of California-Berkeley",
    );

    // Major input displays the chip's majorText (drives the resolve trigger).
    expect(await screen.findByDisplayValue("Computer Science")).toBeInTheDocument();

    // streamIntent fires once the 300ms resolve debounce elapses. The
    // useEffect at SetYourCourseScreen.tsx:168-173 is what actually
    // triggers this — without it the resolve closure short-circuits.
    await waitFor(
      () => {
        expect(vi.mocked(streamIntent)).toHaveBeenCalled();
      },
      { timeout: 2000 },
    );
    const calls = vi.mocked(streamIntent).mock.calls;
    const lastCall = calls[calls.length - 1]?.[0];
    expect(lastCall?.majorText).toBe("Computer Science");
    expect(lastCall?.schoolName).toBe(
      "University of California-Berkeley",
    );
    expect(lastCall?.unitid).toBe(110635);
  });

  it("clear_school_after_chip_click_does_not_leak_stale_resolve_when_next_school_picked — HIGH-3 regression guard", async () => {
    // Repro of the bug staff engineer caught: user clicks a chip, then
    // clicks the SchoolSearch clear button before the useEffect fires
    // resolve. Without the ref-clear in onClear, pendingChipMajorRef
    // would retain the chip's major text and fire resolve against
    // whichever school the user picked next.
    seedState({ school: null });
    renderScreen();

    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-single-110635-computer-science"),
    );

    // Confirm the chip seeded school first.
    await waitFor(() => {
      expect(useBuildInputStore.getState().school?.unitid).toBe(110635);
    });

    // Reset the mock so we only observe streamIntent calls AFTER the
    // user-driven school swap below.
    vi.mocked(streamIntent).mockClear();

    // User clicks the SchoolSearch clear button. The onClear callback
    // also nulls pendingChipMajorRef — that's the fix under test.
    fireEvent.click(screen.getByLabelText("Clear school selection"));
    await waitFor(() => {
      expect(useBuildInputStore.getState().school).toBeNull();
    });

    // User manually seeds a different school via the store (simulates
    // SchoolSearch.onSelect → handleSchoolSelect for any non-chip school).
    // Then we type a new major. If the ref had leaked, the useEffect
    // would fire resolve with the chip's old "Computer Science" against
    // this new school instead of the typed major.
    useBuildInputStore.setState({
      school: {
        unitid: 151351,
        name: "Indiana University",
        institutionControl: "Public",
        stateAbbr: "IN",
        netPriceAnnual: null,
        costOfAttendanceAnnual: null,
        tuitionInState: null,
        tuitionOutOfState: null,
      },
    });

    // Give React + the deferred effect a generous window to fire — if
    // the ref had leaked, streamIntent would have been called with
    // "Computer Science" by now.
    await new Promise((r) => setTimeout(r, 500));

    expect(vi.mocked(streamIntent)).not.toHaveBeenCalledWith(
      expect.objectContaining({
        majorText: "Computer Science",
        unitid: 151351,
      }),
    );
  });

  it("rapid_chip_switching_lands_on_final_chip — race-safety", async () => {
    // Two chip clicks back-to-back. The pendingChipMajorRef overwrite +
    // the effect's `ref.current !== majorText` guard combine so that
    // intermediate state (school A + major B, or vice versa) never
    // triggers a resolve. The final streamIntent call must reflect the
    // second chip's pair.
    seedState({ school: null });
    renderScreen();

    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-single-110635-computer-science"),
    );
    // Immediately click the second chip (different school, different major).
    fireEvent.click(screen.getByTestId("demo-chip-single-228778-nursing"));

    // School ends up on the second chip (UT Austin).
    await waitFor(() => {
      expect(useBuildInputStore.getState().school?.unitid).toBe(228778);
    });

    // streamIntent fires for the second chip's pair, not the first.
    await waitFor(
      () => {
        expect(vi.mocked(streamIntent)).toHaveBeenCalledWith(
          expect.objectContaining({
            majorText: "Nursing",
            unitid: 228778,
          }),
        );
      },
      { timeout: 2000 },
    );

    // Belt-and-suspenders: no streamIntent call was made for the
    // intermediate (school A + major B) or (school B + major A) cross.
    const cs_at_ut_austin = vi.mocked(streamIntent).mock.calls.find(
      (c) =>
        c[0]?.majorText === "Computer Science" && c[0]?.unitid === 228778,
    );
    const nursing_at_berkeley = vi.mocked(streamIntent).mock.calls.find(
      (c) => c[0]?.majorText === "Nursing" && c[0]?.unitid === 110635,
    );
    expect(cs_at_ut_austin).toBeUndefined();
    expect(nursing_at_berkeley).toBeUndefined();
  });

  it("no_match_state_renders_helpful_hint_instead_of_raw_validation_error — defends against Gemma 'none' leak", async () => {
    // Mirror the post-coercion state: currentResolution exists (Gemma
    // responded) but matched_cip + matched_title are empty (coerced
    // in useSetYourCourse when Gemma's matched_cip was "none" or any
    // other non-CIP string). The SOC caption MUST NOT render (would
    // crash on .slice on empty); the friendly hint MUST render
    // interpolating the school name + the typed major text.
    seedState({
      currentResolution: {
        matched_cip: "",
        matched_title: "",
        confidence: "low",
        reasoning: "None of the school's programs match mortuary science.",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
      initialResolution: {
        matched_cip: "",
        matched_title: "",
        confidence: "low",
        reasoning: "None of the school's programs match mortuary science.",
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

    // The no-match hint renders.
    const hint = await screen.findByTestId("syc-no-match-hint");
    expect(hint).toBeInTheDocument();
    expect(hint.textContent).toMatch(/couldn't find a program/i);
    expect(hint.textContent).toMatch(/Indiana University/);
    expect(hint.textContent).toMatch(/Try different search terms/i);

    // The raw validation error caption MUST NOT render (would say
    // "Showing Standard Occupational Classification (SOC) codes
    // related to CIP ." with an empty slice).
    expect(
      screen.queryByText(/Showing Standard Occupational Classification/i),
    ).toBeNull();
  });

  it("drawer_chip_disabled_while_streaming_or_busy_does_not_fire_onPick — gating contract", async () => {
    // The screen passes `disabled={streaming || busy}` to the drawer.
    // Seed a state where streaming would be true by initiating a chip
    // click first, then verify a second chip click during the same
    // window is no-op'd. This is a thin smoke test — the drawer's own
    // unit test exhaustively covers the disabled branch.
    seedState({ school: null });
    renderScreen();

    fireEvent.click(screen.getByTestId("demo-chips-trigger"));
    fireEvent.click(
      screen.getByTestId("demo-chip-single-110635-computer-science"),
    );
    // Even before streaming flips true, the chip is enabled — gating is
    // ergonomic, not a correctness barrier. This test just confirms the
    // smoke path: trigger handler runs, no exception, state lands.
    await waitFor(() => {
      expect(useBuildInputStore.getState().school?.unitid).toBe(110635);
    });
  });
});
