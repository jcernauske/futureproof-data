/**
 * BuildResultsScreen.test.tsx
 *
 * Comprehensive tests for the single-page build results view.
 *
 * What's tested:
 *   P0: Loading state, full render, nav guard redirect, reroll flow
 *   P1: Verdict recalculation, hero identity, all 5 boss bands,
 *        save button navigation, path card data, stat info popover
 *   P2: Error state with retry, victory bar cell types
 *
 * Key decisions:
 *   - Mock `createBuild` and `rerollFight` at the API module level
 *   - Set Zustand store state directly (same pattern as RevealScreen.test.tsx)
 *   - Mock `useHorizonPick` to return a deterministic pick for CampusHeroBanner
 *   - IntersectionObserver is already stubbed in test-setup.ts
 */

import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { Build, BossFightResult, CareerOutcome } from "@/types/build";

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockCreateBuild = vi.fn();
vi.mock("@/api/build", () => ({
  createBuild: (...args: unknown[]) => mockCreateBuild(...args),
}));

const mockRerollFight = vi.fn();
vi.mock("@/api/gauntlet", () => ({
  rerollFight: (...args: unknown[]) => mockRerollFight(...args),
}));

// CampusHeroBanner calls useHorizonPick which relies on sessionStorage
// bag-walk and crypto. Mock the hook to return a deterministic pick.
vi.mock("@/hooks/useHorizonPick", () => ({
  useHorizonPick: () => ({
    index: 0,
    basename: "test-campus-0",
    caption: "Test campus caption",
  }),
  useHorizonAt: (index: number) => ({
    index,
    basename: `test-campus-${index}`,
    caption: "Test campus caption",
  }),
}));

// Lazy import so module-level mocks are installed first.
import { BuildResultsScreen } from "./BuildResultsScreen";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeCareer(overrides: Partial<CareerOutcome> = {}): CareerOutcome {
  return {
    unitid: 110635,
    institution_name: "UC Berkeley",
    cipcode: "11.0701",
    program_name: "Computer Science",
    soc_code: "15-1252",
    occupation_title: "Software Developers",
    soc_major_group_name: null,
    median_annual_wage: 127260,
    earnings_1yr_median: null,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    net_price_annual: null,
    cost_of_attendance_annual: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    room_board_on_campus: null,
    stats: { ern: 8, roi: 6, res: 7, grw: 9, hmn: 5 },
    bosses: { ai: 7, loans: 4, market: 9, burnout: 5, ceiling: 8 },
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
    loan_pct: 0.5,
    ...overrides,
  };
}

function makeFight(overrides: Partial<BossFightResult> = {}): BossFightResult {
  return {
    boss: "ai",
    label: "Fight AI",
    result: "win",
    raw_score: 7,
    threshold_win: 6,
    threshold_draw: 4,
    reason: "test",
    narrative: "AI narrative",
    rerolled: false,
    reroll_count: 0,
    original_result: null,
    original_raw_score: null,
    applied_skill_titles: [],
    ...overrides,
  };
}

function makeBuild(overrides: Partial<Build> = {}): Build {
  return {
    build_id: "test-build-1",
    created_at: "2026-04-21T00:00:00Z",
    school_name: "UC Berkeley",
    unitid: 110635,
    major_text: "Computer Science",
    cipcode: "11.0701",
    program_name: "Computer Science",
    effort: "balanced",
    loan_pct: 0.5,
    career: makeCareer(),
    gauntlet: {
      fights: [
        makeFight({ boss: "ai", result: "win", raw_score: 7, narrative: "AI narrative" }),
        makeFight({ boss: "loans", label: "Fight Loans", result: "lose", raw_score: 4, narrative: "Loans narrative" }),
        makeFight({ boss: "market", label: "Fight Market", result: "win", raw_score: 9, narrative: "Market narrative" }),
        makeFight({ boss: "burnout", label: "Fight Burnout", result: "draw", raw_score: 5, narrative: "Burnout narrative" }),
        makeFight({ boss: "ceiling", label: "Fight Ceiling", result: "win", raw_score: 8, narrative: "Ceiling narrative" }),
      ],
      wins: 3,
      losses: 1,
      draws: 1,
      unknown: 0,
      verdict: "SOLID BUILD",
    },
    branches: [],
    skill_recs: [],
    guidance: "UC Berkeley has strong alignment between Computer Science and Software Development careers.",
    skills_crafted: [],
    skill_pool: [
      {
        id: "sk1",
        title: "Part-time Work",
        rationale: "test",
        targets: ["loans"],
        delta_ern: 1,
        delta_roi: 2,
        delta_res: 0,
        delta_grw: 0,
        delta_hmn: 0,
        delta_burnout_raw: 0,
        delta_ceiling_raw: 0,
      },
    ],
    next_steps: "",
    profile_name: "dancing happy bear",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// State seeding
// ---------------------------------------------------------------------------

function seedReady() {
  useBuildInputStore.setState({
    phase: "sliders",
    school: {
      unitid: 110635,
      name: "UC Berkeley",
      institutionControl: "Public",
      stateAbbr: "CA",
      netPriceAnnual: null,
      costOfAttendanceAnnual: null,
      tuitionInState: null,
      tuitionOutOfState: null,
    },
    programs: [],
    major: {
      cipCode: "11.0701",
      cipTitle: "Computer Science",
      rawText: "Computer Science",
      careersPreview: [],
      substitutionApplied: false,
      parentCip: "",
    },
    effort: { level: "balanced", percentile: 50, ernShift: 0 },
    loans: { percentage: 50 },
  });
  useBuildStore.setState({
    tieredCareers: null,
    selectedCareer: makeCareer(),
    isBuilding: false,
    buildingStage: 0,
    build: null,
    hasSeenStatTutorial: true,
  });
  useProfileStore.setState({
    profileName: "dancing happy bear",
    animalEmoji: "\u{1F43B}",
    animalName: "bear",
  });
}

function seedWithBuild(buildOverrides: Partial<Build> = {}) {
  seedReady();
  const build = makeBuild(buildOverrides);
  useBuildStore.setState({ build, isBuilding: false });
}

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={["/my-build"]}>
      <BuildResultsScreen />
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

beforeEach(() => {
  mockNavigate.mockReset();
  mockCreateBuild.mockReset();
  mockRerollFight.mockReset();
  sessionStorage.clear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

// ===========================================================================
// P0 Tests
// ===========================================================================

describe("BuildResultsScreen -- loading state (P0)", () => {
  it("renders_loading_state -- shows loading indicator while POST /build is in flight", async () => {
    seedReady();

    // Hold createBuild as a pending promise so loading state stays visible.
    let resolveBuild!: (value: Build) => void;
    mockCreateBuild.mockImplementation(
      () => new Promise((resolve) => { resolveBuild = resolve; }),
    );

    renderScreen();

    // The loading text is rendered while the build is in flight.
    await waitFor(() => {
      expect(screen.getByText(/Gemma is analyzing your build/)).toBeInTheDocument();
    });

    // The animal emoji is used as a loading avatar.
    expect(screen.getByText("\u{1F43B}")).toBeInTheDocument();

    // The build content is NOT yet visible.
    expect(screen.queryByText("Software Developers")).toBeNull();
    expect(screen.queryByText("Save This Build")).toBeNull();

    // createBuild was called.
    expect(mockCreateBuild).toHaveBeenCalledTimes(1);

    // Clean up: resolve the promise so async work settles.
    await act(async () => {
      resolveBuild(makeBuild());
      await vi.advanceTimersByTimeAsync(2000);
    });
  });
});

describe("BuildResultsScreen -- full render (P0)", () => {
  it("renders_full_build_results -- all sections render when build is loaded", () => {
    seedWithBuild();
    renderScreen();

    // Hero identity: profile name
    expect(screen.getByText("dancing happy bear")).toBeInTheDocument();

    // Hero identity: subtitle with school and program
    expect(screen.getByText(/Studying Computer Science at UC Berkeley/)).toBeInTheDocument();

    // Path card: program name, CIP code, career, SOC code
    expect(screen.getByText("Computer Science")).toBeInTheDocument();
    expect(screen.getByText(/CIP 11\.0701/)).toBeInTheDocument();
    expect(screen.getByText("Software Developers")).toBeInTheDocument();
    expect(screen.getByText(/SOC 15-1252/)).toBeInTheDocument();

    // Institution card: school name
    // The InstitutionCard renders the school name plus "About the School".
    expect(screen.getByText("About the School")).toBeInTheDocument();
    // School name appears in InstitutionCard (22px heading).
    const schoolHeadings = screen.getAllByText("UC Berkeley");
    expect(schoolHeadings.length).toBeGreaterThanOrEqual(1);

    // Pentagon chart section header.
    expect(screen.getByText("Build Stats")).toBeInTheDocument();

    // Gauntlet section header.
    expect(screen.getByText("The Gauntlet")).toBeInTheDocument();
    expect(screen.getByText("5 fights. Your stats vs. real-world threats.")).toBeInTheDocument();

    // All 5 boss bands are rendered (each has a role="region" with boss name).
    const bossBands = screen.getAllByRole("region");
    const bossLabels = bossBands
      .map((el) => el.getAttribute("aria-label"))
      .filter(Boolean);
    expect(bossLabels).toContain("AI: VICTORY");
    expect(bossLabels).toContain("Student Loans: DEFEATED");
    expect(bossLabels).toContain("The Market: VICTORY");
    expect(bossLabels).toContain("Burnout: STANDOFF");
    expect(bossLabels).toContain("The Ceiling: VICTORY");

    // Verdict badge: "CAREER READINESS" label is present.
    expect(screen.getByText("CAREER READINESS")).toBeInTheDocument();

    // Save button.
    expect(screen.getByText("Save This Build")).toBeInTheDocument();
  });
});

describe("BuildResultsScreen -- nav guard (P0)", () => {
  it("nav_guard_redirects_when_no_session -- redirects when school is missing", () => {
    seedReady();
    useBuildInputStore.setState({ school: null });

    renderScreen();

    expect(mockNavigate).toHaveBeenCalledWith("/set-your-course", { replace: true });
    expect(sessionStorage.getItem("fp-nav-hint")).toBe("session-expired");
    expect(mockCreateBuild).not.toHaveBeenCalled();
  });

  it("nav_guard_redirects_when_major_is_missing", () => {
    seedReady();
    useBuildInputStore.setState({ major: null });

    renderScreen();

    expect(mockNavigate).toHaveBeenCalledWith("/set-your-course", { replace: true });
    expect(sessionStorage.getItem("fp-nav-hint")).toBe("session-expired");
  });

  it("nav_guard_redirects_when_selectedCareer_is_missing", () => {
    seedReady();
    useBuildStore.setState({ selectedCareer: null });

    renderScreen();

    expect(mockNavigate).toHaveBeenCalledWith("/set-your-course", { replace: true });
    expect(sessionStorage.getItem("fp-nav-hint")).toBe("session-expired");
  });
});

describe("BuildResultsScreen -- reroll (P0)", () => {
  it("reroll_updates_fight_result -- selecting skill and rescoring updates the fight", async () => {
    // Set up a build where the loans boss is a loss with an available skill.
    seedWithBuild();

    renderScreen();

    // Find the Loans boss band. It should show "DEFEATED" since result is "lose".
    const loansBand = screen.getByRole("region", { name: /Student Loans: DEFEATED/ });
    expect(loansBand).toBeInTheDocument();

    // The skill pool has a "Part-time Work" skill that targets "loans".
    // The BossBand component renders a skill-selection UI for non-win results.
    // Look for the skill title inside the boss band.
    const skillButton = screen.getByText("Part-time Work");
    expect(skillButton).toBeInTheDocument();

    // Mock the rerollFight to return a win.
    const updatedFight: BossFightResult = makeFight({
      boss: "loans",
      label: "Fight Loans",
      result: "win",
      raw_score: 8,
      narrative: "Rescored loans narrative",
      rerolled: true,
      reroll_count: 1,
      original_result: "lose",
      original_raw_score: 4,
    });
    mockRerollFight.mockResolvedValue(updatedFight);

    // Click the skill to select it.
    fireEvent.click(skillButton);

    // Find and click the rematch button. BossBand renders a button for rematching.
    const rematchButton = screen.getByText(/Rematch/i);
    fireEvent.click(rematchButton);

    // Wait for the reroll to complete and the UI to update.
    await waitFor(() => {
      expect(mockRerollFight).toHaveBeenCalledWith("test-build-1", "loans", ["sk1"]);
    });

    // The fight result should update. The boss band re-renders with
    // the updated result via the parent's handleRerollComplete callback.
    await waitFor(() => {
      expect(screen.getByRole("region", { name: /Student Loans: VICTORY/ })).toBeInTheDocument();
    });
  });
});

// ===========================================================================
// P1 Tests
// ===========================================================================

describe("BuildResultsScreen -- verdict after reroll (P1)", () => {
  it("verdict_updates_after_reroll -- verdict recalculates with rescored wins", async () => {
    seedWithBuild();
    renderScreen();

    // Initial state: 3 wins (raw), 1 loss, 1 draw -> "SOLID BUILD" (3+ wins).
    // The VerdictBadge contains "CAREER READINESS" and a tally with "of 5 victories".
    // Find the tally element by searching for "of 5 victories" text content.
    const findTally = () => {
      const el = screen.getByText(/of 5 victories/);
      return el.textContent ?? "";
    };
    expect(findTally()).toContain("3");
    expect(findTally()).toContain("of 5 victories");

    // Now mock a reroll that turns the loss into a win.
    const updatedFight: BossFightResult = makeFight({
      boss: "loans",
      label: "Fight Loans",
      result: "win",
      raw_score: 8,
      narrative: "Rescored loans narrative",
      rerolled: true,
      reroll_count: 1,
      original_result: "lose",
      original_raw_score: 4,
    });
    mockRerollFight.mockResolvedValue(updatedFight);

    // Click skill, then rematch.
    fireEvent.click(screen.getByText("Part-time Work"));
    fireEvent.click(screen.getByText(/Rematch/i));

    // After reroll, 3 raw wins + 1 equipped win = 4 total.
    await waitFor(() => {
      const tally = findTally();
      expect(tally).toContain("4");
      expect(tally).toContain("of 5 victories");
    });

    // The equipped win breakdown should appear: "3 decisive + 1 skill-assisted".
    await waitFor(() => {
      const tally = findTally();
      expect(tally).toContain("3 decisive");
      expect(tally).toContain("skill-assisted");
    });
  });
});

describe("BuildResultsScreen -- hero identity (P1)", () => {
  it("hero_identity_renders_with_emoji_bg -- avatar shows with emoji, name, and subtitle", () => {
    seedWithBuild();
    renderScreen();

    // The animal emoji appears in multiple places (hero identity + boss band
    // VS overlays). Verify at least one is present, then check the hero
    // identity specifically.
    const emojis = screen.getAllByText("\u{1F43B}");
    expect(emojis.length).toBeGreaterThanOrEqual(1);

    // The hero identity avatar has an 80px emoji.
    const heroEmoji = emojis.find(
      (el) => el.style.fontSize === "80px",
    );
    expect(heroEmoji).toBeDefined();

    // The profile name is rendered.
    expect(screen.getByText("dancing happy bear")).toBeInTheDocument();

    // The subtitle shows the program and school.
    expect(screen.getByText(/Studying Computer Science at UC Berkeley/)).toBeInTheDocument();
  });
});

describe("BuildResultsScreen -- boss bands (P1)", () => {
  it("all_five_boss_bands_render -- all 5 boss bands render with correct data", () => {
    seedWithBuild();
    renderScreen();

    // Each boss band is a role="region" with aria-label containing the boss
    // short name and result word.
    const expectedLabels = [
      "AI: VICTORY",
      "Student Loans: DEFEATED",
      "The Market: VICTORY",
      "Burnout: STANDOFF",
      "The Ceiling: VICTORY",
    ];

    for (const label of expectedLabels) {
      expect(screen.getByRole("region", { name: label })).toBeInTheDocument();
    }

    // Each band has data-boss and data-result attributes.
    const bossBands = screen.getAllByRole("region").filter(
      (el) => el.dataset.boss !== undefined,
    );
    expect(bossBands.length).toBe(5);

    const bossIds = bossBands.map((el) => el.dataset.boss);
    expect(bossIds).toEqual(["ai", "loans", "market", "burnout", "ceiling"]);

    const results = bossBands.map((el) => el.dataset.result);
    expect(results).toEqual(["win", "lose", "win", "draw", "win"]);
  });
});

describe("BuildResultsScreen -- save button (P1)", () => {
  it("save_button_navigates_to_save -- clicking Save This Build navigates to /save", () => {
    seedWithBuild();
    renderScreen();

    const saveButton = screen.getByText("Save This Build");
    fireEvent.click(saveButton);

    expect(mockNavigate).toHaveBeenCalledWith("/save");
  });

  it("branch_tree_link_navigates -- clicking branch tree link navigates to /branches", () => {
    seedWithBuild();
    renderScreen();

    const branchLink = screen.getByText(/Want to explore career branches/);
    fireEvent.click(branchLink);

    expect(mockNavigate).toHaveBeenCalledWith("/branches");
  });
});

describe("BuildResultsScreen -- path card data (P1)", () => {
  it("path_card_shows_cip_soc_wage -- path card displays program, CIP, career, SOC, and wage", () => {
    seedWithBuild();
    renderScreen();

    // Program name appears in path card.
    expect(screen.getByText("Your Path")).toBeInTheDocument();
    // CIP code.
    expect(screen.getByText(/CIP 11\.0701/)).toBeInTheDocument();
    // Career name.
    expect(screen.getByText("Software Developers")).toBeInTheDocument();
    // SOC code.
    expect(screen.getByText(/SOC 15-1252/)).toBeInTheDocument();
    // Median salary in Finances card, formatted as "$127,260 / yr".
    expect(screen.getByText("$127,260 / yr")).toBeInTheDocument();
  });

  it("finances_card_shows_dash_when_wage_null", () => {
    seedWithBuild({ career: makeCareer({ median_annual_wage: null }) });
    renderScreen();

    expect(screen.getByText("Finances")).toBeInTheDocument();
    // FinancesCard renders "—" for null values
    const dashes = screen.getAllByText(/— \/ yr/);
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });
});

describe("BuildResultsScreen -- stat info popover (P1)", () => {
  it("stat_info_popover_opens_closes -- ? button opens popover, clicking again closes", async () => {
    seedWithBuild();
    const { container } = renderScreen();

    // Find the "What is Earning Power?" button.
    const infoButton = screen.getByRole("button", { name: /What is Earning Power/ });
    expect(infoButton).toBeInTheDocument();
    expect(infoButton.getAttribute("aria-expanded")).toBe("false");

    // Click to open.
    fireEvent.click(infoButton);

    // The popover opens with id="info-ern".
    const popover = container.querySelector("#info-ern");
    expect(popover).not.toBeNull();
    // The popover should contain the stat definition source text.
    expect(screen.getByText(/Source: College Scorecard/)).toBeInTheDocument();
    expect(infoButton.getAttribute("aria-expanded")).toBe("true");

    // Click the same button again to close.
    fireEvent.click(infoButton);

    // The popover should be gone.
    expect(container.querySelector("#info-ern")).toBeNull();
    expect(infoButton.getAttribute("aria-expanded")).toBe("false");
  });
});

// ===========================================================================
// P2 Tests
// ===========================================================================

describe("BuildResultsScreen -- error state (P2)", () => {
  it("error_state_shows_retry -- error shows message and retry button", async () => {
    seedReady();

    // createBuild rejects immediately.
    mockCreateBuild.mockRejectedValue(new Error("Network timeout"));

    renderScreen();

    // Wait for the error to appear.
    await waitFor(() => {
      expect(screen.getByText("Network timeout")).toBeInTheDocument();
    });

    // "Try Again" and "Go Back" buttons should be present.
    expect(screen.getByText("Try Again")).toBeInTheDocument();
    expect(screen.getByText("Go Back")).toBeInTheDocument();

    // Click "Try Again" triggers a new build attempt.
    mockCreateBuild.mockReset();
    let resolveBuild!: (value: Build) => void;
    mockCreateBuild.mockImplementation(
      () => new Promise((resolve) => { resolveBuild = resolve; }),
    );

    fireEvent.click(screen.getByText("Try Again"));

    await waitFor(() => {
      expect(mockCreateBuild).toHaveBeenCalledTimes(1);
    });

    // Clean up.
    await act(async () => {
      resolveBuild(makeBuild());
      await vi.advanceTimersByTimeAsync(2000);
    });
  });

  it("error_go_back_navigates -- clicking Go Back navigates to /set-your-course", async () => {
    seedReady();
    mockCreateBuild.mockRejectedValue(new Error("Server error"));

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Go Back")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Go Back"));

    expect(mockNavigate).toHaveBeenCalledWith("/set-your-course");
  });
});

describe("BuildResultsScreen -- victory bar (P2)", () => {
  it("victory_bar_shows_correct_cell_types -- 5 cells with correct classes for 3W/1L/1D", () => {
    seedWithBuild();
    const { container } = renderScreen();

    // The VictoryBar renders cells with classNames: "raw", "equipped",
    // "draw-cell", "loss". For 3 raw wins, 0 equipped, 1 draw, 1 loss:
    const rawCells = container.querySelectorAll(".raw");
    const drawCells = container.querySelectorAll(".draw-cell");
    const lossCells = container.querySelectorAll(".loss");

    expect(rawCells.length).toBe(3);
    expect(drawCells.length).toBe(1);
    expect(lossCells.length).toBe(1);
  });

  it("victory_bar_shows_equipped_cells_after_reroll", async () => {
    seedWithBuild();

    // Mock reroll turning the loss into a win.
    const updatedFight: BossFightResult = makeFight({
      boss: "loans",
      label: "Fight Loans",
      result: "win",
      raw_score: 8,
      narrative: "Rescored",
      rerolled: true,
      reroll_count: 1,
      original_result: "lose",
      original_raw_score: 4,
    });
    mockRerollFight.mockResolvedValue(updatedFight);

    const { container } = renderScreen();

    // Trigger the reroll.
    fireEvent.click(screen.getByText("Part-time Work"));
    fireEvent.click(screen.getByText(/Rematch/i));

    // After reroll: 3 raw + 1 equipped + 1 draw = 5 cells.
    await waitFor(() => {
      const equipped = container.querySelectorAll(".equipped");
      expect(equipped.length).toBe(1);
    });

    const rawCells = container.querySelectorAll(".raw");
    expect(rawCells.length).toBe(3);
  });
});

// ===========================================================================
// Edge cases
// ===========================================================================

describe("BuildResultsScreen -- unmount race safety", () => {
  it("does NOT fire setState after unmount when createBuild resolves late", async () => {
    seedReady();

    let resolveBuild!: (value: Build) => void;
    mockCreateBuild.mockImplementation(
      () => new Promise((resolve) => { resolveBuild = resolve; }),
    );

    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { unmount } = renderScreen();

    await waitFor(() => {
      expect(mockCreateBuild).toHaveBeenCalledTimes(1);
    });

    // Unmount mid-flight.
    unmount();

    // Resolve after unmount. The cancelledRef guard should prevent
    // setBuild/setIsBuilding from firing.
    await act(async () => {
      resolveBuild(makeBuild());
      await vi.advanceTimersByTimeAsync(2000);
    });

    // Build should remain null -- the cancelled guard prevented the write.
    expect(useBuildStore.getState().build).toBeNull();

    // No "unmounted component" warnings.
    const unmountWarnings = errSpy.mock.calls.filter((args) =>
      args.some(
        (a) =>
          typeof a === "string" &&
          (a.includes("unmounted component") ||
            a.includes("Can't perform a React state update")),
      ),
    );
    expect(unmountWarnings).toEqual([]);

    errSpy.mockRestore();
  });
});

describe("BuildResultsScreen -- stat legend", () => {
  it("renders all 5 stat rows with abbreviations, names, and scores", () => {
    seedWithBuild();
    renderScreen();

    // The stat legend renders names for all 5 stats. Names are unique in the
    // stat legend so we can query them directly. Abbreviations may appear in
    // multiple places (PathCard stat bars), so use getAllByText.
    const expectedStats = [
      { abbr: "ERN", name: "Earning Power" },
      { abbr: "ROI", name: "Return on Investment" },
      { abbr: "RES", name: "AI Resilience" },
      { abbr: "GRW", name: "Growth Outlook" },
      { abbr: "HMN", name: "Human Edge" },
    ];

    for (const stat of expectedStats) {
      // Abbreviation may appear in both legend and PathCard stat bars.
      const abbrs = screen.getAllByText(stat.abbr);
      expect(abbrs.length).toBeGreaterThanOrEqual(1);
      // Name is unique to the stat legend.
      expect(screen.getByText(stat.name)).toBeInTheDocument();
    }

    // Verify each stat has a "/10" suffix rendered next to its score.
    const tenSuffixes = screen.getAllByText("/10");
    expect(tenSuffixes.length).toBe(5);
  });
});

describe("BuildResultsScreen -- institution card", () => {
  it("renders Gemma guidance narrative", () => {
    seedWithBuild();
    renderScreen();

    expect(
      screen.getByText(/UC Berkeley has strong alignment/),
    ).toBeInTheDocument();

    // The "Written by Gemma" attribution is present.
    expect(screen.getByText(/Written by Gemma/)).toBeInTheDocument();
  });
});

describe("BuildResultsScreen -- createBuild is called with correct params", () => {
  it("passes all expected arguments from store state to createBuild", async () => {
    seedReady();

    let resolveBuild!: (value: Build) => void;
    mockCreateBuild.mockImplementation(
      () => new Promise((resolve) => { resolveBuild = resolve; }),
    );

    renderScreen();

    await waitFor(() => {
      expect(mockCreateBuild).toHaveBeenCalledTimes(1);
    });

    // Verify the arguments passed to createBuild match what the component
    // extracts from the stores.
    expect(mockCreateBuild).toHaveBeenCalledWith(
      "dancing happy bear",    // profileName
      "UC Berkeley",           // school.name
      110635,                  // school.unitid
      "11.0701",               // major.cipCode (lookupCip = parentCip || cipCode)
      "Computer Science",      // major.cipTitle
      "Computer Science",      // major.rawText
      "balanced",              // effort.level
      0.5,                     // loans.percentage / 100
      "15-1252",               // selectedCareer.soc_code
      "Software Developers",   // selectedCareer.occupation_title
      "Computer Science",      // major.rawText (studentMajor)
      undefined,               // studentCip (undefined when no parentCip)
      undefined,               // homeState (null → undefined)
      "CA",                    // schoolState from mock school
      "🐻",                    // animalEmoji
    );

    // Clean up.
    await act(async () => {
      resolveBuild(makeBuild());
      await vi.advanceTimersByTimeAsync(2000);
    });
  });

  it("passes parentCip as lookupCip and cipCode as studentCip when parentCip is set", async () => {
    seedReady();
    useBuildInputStore.setState({
      major: {
        cipCode: "11.0701",
        cipTitle: "Computer Science",
        rawText: "Computer Science",
        careersPreview: [],
        substitutionApplied: false,
        parentCip: "11.07",
      },
    });

    let resolveBuild!: (value: Build) => void;
    mockCreateBuild.mockImplementation(
      () => new Promise((resolve) => { resolveBuild = resolve; }),
    );

    renderScreen();

    await waitFor(() => {
      expect(mockCreateBuild).toHaveBeenCalledTimes(1);
    });

    // When parentCip is set, lookupCip = parentCip ("11.07") and
    // studentCip = cipCode ("11.0701").
    expect(mockCreateBuild).toHaveBeenCalledWith(
      expect.anything(),
      expect.anything(),
      expect.anything(),
      "11.07",                 // lookupCip = parentCip
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.anything(),
      expect.anything(),
      "11.0701",               // studentCip = cipCode
      undefined,               // homeState
      "CA",                    // schoolState from mock school
      "🐻",                    // animalEmoji
    );

    await act(async () => {
      resolveBuild(makeBuild());
      await vi.advanceTimersByTimeAsync(2000);
    });
  });
});

describe("BuildResultsScreen -- skips build when already loaded", () => {
  it("does not call createBuild when build is already in the store", () => {
    seedWithBuild();
    renderScreen();

    // When the build is already present in the store on mount, the component
    // should NOT call createBuild. The useEffect checks `!build && !isBuilding`.
    expect(mockCreateBuild).not.toHaveBeenCalled();
  });
});
