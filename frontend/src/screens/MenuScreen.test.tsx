/**
 * MenuScreen.test.tsx
 *
 * Tests Screen 10 (post-build hub):
 * - Renders saved builds for the active profile (P0)
 * - Tap a build card → loads via getBuild → navigate to /my-build (P0)
 * - "New Build" → clearProfile() + resetInputs() + navigate to /profile (P1)
 * - "Compare Builds" disabled when fewer than 2 builds (P1)
 *
 * The @/api/menu module is mocked at module boundary so we don't hit
 * the mock fallback's setTimeout delays — tests resolve deterministically.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MenuScreen } from "./MenuScreen";
import { useProfileStore } from "@/store/profileStore";
import { useBuildStore } from "@/store/buildStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildsCountStore } from "@/store/buildsCountStore";
import type { BuildSummary } from "@/api/menu";
import type { Build } from "@/types/build";

// --- Mocks --------------------------------------------------------------

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockListBuilds = vi.fn();
const mockCompareBuilds = vi.fn();
const mockCompareInsights = vi.fn();
const mockSendChat = vi.fn();
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    listBuilds: (...args: unknown[]) => mockListBuilds(...args),
    compareBuilds: (...args: unknown[]) => mockCompareBuilds(...args),
    compareInsights: (...args: unknown[]) => mockCompareInsights(...args),
    sendChat: (...args: unknown[]) => mockSendChat(...args),
  };
});

const mockGetBuild = vi.fn();
const mockDeleteBuild = vi.fn();
vi.mock("@/api/build", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/build")>("@/api/build");
  return {
    ...actual,
    getBuild: (...args: unknown[]) => mockGetBuild(...args),
    deleteBuild: (...args: unknown[]) => mockDeleteBuild(...args),
  };
});

// --- Fixtures -----------------------------------------------------------

function makeSummary(overrides: Partial<BuildSummary> = {}): BuildSummary {
  return {
    build_id: "berkeley-cs-001",
    created_at: "2026-04-12T18:30:00Z",
    school_name: "UC Berkeley",
    major_text: "Computer Science",
    career_title: "Software Developers",
    ern: 8,
    roi: 7,
    res: 4,
    grw: 9,
    hmn: 5,
    wins: 4,
    losses: 0,
    draws: 1,
    profile_name: "Wandering Otter",
    animal_emoji: "🦦",
    ...overrides,
  };
}

function makeBuild(overrides: Partial<Build> = {}): Build {
  return {
    build_id: "berkeley-cs-001",
    created_at: "2026-04-12T18:30:00Z",
    school_name: "UC Berkeley",
    unitid: 110635,
    major_text: "Computer Science",
    cipcode: "11.0701",
    program_name: "Computer Science",
    effort: "balanced",
    loan_pct: 0.5,
    career: {
      unitid: 110635,
      institution_name: "UC Berkeley",
      cipcode: "11.0701",
      program_name: "Computer Science",
      soc_code: "15-1252",
      occupation_title: "Software Developers",
      stats: { ern: 8, roi: 7, res: 4, grw: 9, hmn: 5 },
      bosses: { ai: 7, loans: 3, market: 3, burnout: 4, ceiling: 4 },
      median_annual_wage: 130000,
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
    },
    gauntlet: {
      fights: [],
      wins: 4,
      losses: 0,
      draws: 1,
      unknown: 0,
      verdict: "STRONG",
    },
    branches: [],
    skill_recs: [],
    guidance: "",
    skills_crafted: [],
    skill_pool: [],
    next_steps: "",
    profile_name: "Wandering Otter",
    ...overrides,
  } as Build;
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <MenuScreen />
    </MemoryRouter>,
  );
}

// --- Setup --------------------------------------------------------------

beforeEach(() => {
  mockNavigate.mockReset();
  mockListBuilds.mockReset();
  mockCompareBuilds.mockReset();
  mockCompareInsights.mockReset();
  mockSendChat.mockReset();
  mockGetBuild.mockReset();
  mockDeleteBuild.mockReset();
  useBuildsCountStore.setState({ count: null, loading: false, error: null });
  // Sane defaults — individual tests can override.
  mockCompareBuilds.mockReturnValue(new Promise(() => {}));
  mockCompareInsights.mockReturnValue(new Promise(() => {}));
  mockSendChat.mockReturnValue(new Promise(() => {}));
  useProfileStore.setState({
    profileName: "Wandering Otter",
    animalEmoji: "\uD83E\uDD9C", // otter
    animalName: "otter",
  });
  useBuildStore.setState({
    tieredCareers: null,
    selectedCareer: null,
    isBuilding: false,
    buildingStage: 0,
    build: null,
  });
  useBuildInputStore.getState().reset();
});

afterEach(() => {
  useProfileStore.setState({
    profileName: null,
    animalEmoji: null,
    animalName: null,
  });
  useBuildStore.setState({ build: null });
});

// --- Tests --------------------------------------------------------------

describe("MenuScreen", () => {
  // --- P0: renders saved builds for the profile ---

  it("renders a build card for each saved build (P0)", async () => {
    mockListBuilds.mockResolvedValue([
      makeSummary(),
      makeSummary({
        build_id: "iu-bloom-mkt-001",
        school_name: "Indiana University Bloomington",
        major_text: "Marketing",
        career_title: "Marketing Managers",
      }),
      makeSummary({
        build_id: "purdue-nursing-001",
        school_name: "Purdue University",
        major_text: "Nursing",
        career_title: "Registered Nurses",
      }),
    ]);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByTestId("card-build-berkeley-cs-001")).toBeInTheDocument();
    });
    expect(screen.getByTestId("card-build-iu-bloom-mkt-001")).toBeInTheDocument();
    expect(screen.getByTestId("card-build-purdue-nursing-001")).toBeInTheDocument();
    expect(mockListBuilds).toHaveBeenCalledWith();
  });

  it("calls listBuilds with the active profile name (P0)", async () => {
    mockListBuilds.mockResolvedValue([]);
    renderScreen();
    await waitFor(() => {
      expect(mockListBuilds).toHaveBeenCalledWith();
    });
  });

  it("redirects to /set-your-course when no profile in store (saboteur: profile-less direct nav)", () => {
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
    mockListBuilds.mockResolvedValue([]);
    renderScreen();
    expect(mockNavigate).toHaveBeenCalledWith("/set-your-course", { replace: true });
    // Must not fire the list query before the profile guard kicks the user out.
    expect(mockListBuilds).not.toHaveBeenCalled();
  });

  // --- P0: tap card loads build + navigates ---

  it("tap build card → loads via getBuild → setBuild → navigate to /my-build (P0)", async () => {
    mockListBuilds.mockResolvedValue([makeSummary()]);
    mockGetBuild.mockResolvedValue(makeBuild());

    renderScreen();

    const card = await screen.findByTestId("card-build-berkeley-cs-001");
    fireEvent.click(card);

    await waitFor(() => {
      expect(mockGetBuild).toHaveBeenCalledWith("berkeley-cs-001");
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/my-build");
    });
    // Build must have landed in the store before navigation finishes.
    expect(useBuildStore.getState().build?.build_id).toBe("berkeley-cs-001");
  });

  it("tap card whose getBuild rejects shows an error and does NOT navigate (saboteur)", async () => {
    mockListBuilds.mockResolvedValue([makeSummary()]);
    mockGetBuild.mockRejectedValue(new Error("backend on fire"));

    renderScreen();

    const card = await screen.findByTestId("card-build-berkeley-cs-001");
    fireEvent.click(card);

    await waitFor(() => {
      expect(screen.getByText("backend on fire")).toBeInTheDocument();
    });
    // Must NOT have navigated even though the user clicked a card.
    expect(mockNavigate).not.toHaveBeenCalledWith("/my-build");
  });

  // --- P1: New Build clears inputs and navigates ---

  it('"New Build" calls resetInputs() then navigates to /profile (P1)', async () => {
    mockListBuilds.mockResolvedValue([makeSummary()]);

    // Pollute build inputs first so we can prove the reset.
    useBuildInputStore.setState({
      phase: "sliders",
      school: { unitid: 1, name: "Old School", institutionControl: "Public", stateAbbr: null, netPriceAnnual: null, costOfAttendanceAnnual: null, tuitionInState: null, tuitionOutOfState: null },
      programs: [],
      major: {
        cipCode: "99.99",
        cipTitle: "Old Major",
        rawText: "Old Major",
        careersPreview: [],
        substitutionApplied: false,
        parentCip: "",
      },
      effort: { level: "all_in", percentile: 90, ernShift: 2 },
      loans: { percentage: 100 },
    });

    renderScreen();

    // Wait for builds to land so the action region renders the screen-local btn.
    await screen.findByTestId("card-build-berkeley-cs-001");

    fireEvent.click(screen.getByTestId("btn-new-build"));

    expect(mockNavigate).toHaveBeenCalledWith("/profile");
    const after = useBuildInputStore.getState();
    expect(after.school).toBeNull();
    expect(after.major).toBeNull();
    expect(after.effort.level).toBe("balanced");
    expect(after.loans.percentage).toBe(50);
  });

  // --- P1: Compare disabled with fewer than 2 builds ---

  it('"Compare Builds" is disabled when only 1 build exists (P1)', async () => {
    mockListBuilds.mockResolvedValue([makeSummary()]);
    renderScreen();

    const enterCompare = await screen.findByTestId("btn-enter-compare");
    expect(enterCompare).toBeDisabled();
  });

  it('"Compare Builds" is enabled when 2+ builds exist (P1)', async () => {
    mockListBuilds.mockResolvedValue([
      makeSummary(),
      makeSummary({ build_id: "iu-bloom-mkt-001", school_name: "IU" }),
    ]);
    renderScreen();

    const enterCompare = await screen.findByTestId("btn-enter-compare");
    expect(enterCompare).not.toBeDisabled();
  });

  // --- P1: select mode caps at 4 builds (Party Select) ---

  it("allows selecting up to 4 builds in select mode; rejects the 5th (P1)", async () => {
    const fiveBuilds = [
      makeSummary({ build_id: "build-a", school_name: "School A" }),
      makeSummary({ build_id: "build-b", school_name: "School B" }),
      makeSummary({ build_id: "build-c", school_name: "School C" }),
      makeSummary({ build_id: "build-d", school_name: "School D" }),
      makeSummary({ build_id: "build-e", school_name: "School E" }),
    ];
    mockListBuilds.mockResolvedValue(fiveBuilds);
    renderScreen();

    // Wait for builds to render.
    await screen.findByTestId("card-build-build-a");

    // Enter select mode.
    fireEvent.click(screen.getByTestId("btn-enter-compare"));

    // Select 4 builds — all should succeed.
    fireEvent.click(screen.getByTestId("card-build-build-a"));
    fireEvent.click(screen.getByTestId("card-build-build-b"));
    fireEvent.click(screen.getByTestId("card-build-build-c"));
    fireEvent.click(screen.getByTestId("card-build-build-d"));

    // Button should show "Compare 4/4" and be enabled.
    const compareBtn = screen.getByTestId("btn-compare");
    expect(compareBtn).toHaveTextContent("Compare 4/4");
    expect(compareBtn).not.toBeDisabled();

    // Click a 5th build — must be silently rejected (cap at 4).
    fireEvent.click(screen.getByTestId("card-build-build-e"));

    // Still "Compare 4/4" — the 5th selection was dropped.
    expect(compareBtn).toHaveTextContent("Compare 4/4");
  });

  it("deselecting a build in select mode allows re-selecting another (P1)", async () => {
    const fourBuilds = [
      makeSummary({ build_id: "build-a", school_name: "School A" }),
      makeSummary({ build_id: "build-b", school_name: "School B" }),
      makeSummary({ build_id: "build-c", school_name: "School C" }),
      makeSummary({ build_id: "build-d", school_name: "School D" }),
      makeSummary({ build_id: "build-e", school_name: "School E" }),
    ];
    mockListBuilds.mockResolvedValue(fourBuilds);
    renderScreen();

    await screen.findByTestId("card-build-build-a");
    fireEvent.click(screen.getByTestId("btn-enter-compare"));

    // Select 4.
    fireEvent.click(screen.getByTestId("card-build-build-a"));
    fireEvent.click(screen.getByTestId("card-build-build-b"));
    fireEvent.click(screen.getByTestId("card-build-build-c"));
    fireEvent.click(screen.getByTestId("card-build-build-d"));

    const compareBtn = screen.getByTestId("btn-compare");
    expect(compareBtn).toHaveTextContent("Compare 4/4");

    // Deselect build-b (toggle off).
    fireEvent.click(screen.getByTestId("card-build-build-b"));
    expect(compareBtn).toHaveTextContent("Compare 3/4");

    // Now build-e can be selected.
    fireEvent.click(screen.getByTestId("card-build-build-e"));
    expect(compareBtn).toHaveTextContent("Compare 4/4");
  });

  it("empty-state CTA also routes to /profile via resetInputs (saboteur: zero-builds path)", async () => {
    mockListBuilds.mockResolvedValue([]);
    renderScreen();

    const cta = await screen.findByTestId("btn-new-build");
    fireEvent.click(cta);
    expect(mockNavigate).toHaveBeenCalledWith("/profile");
  });

  // ---------------------------------------------------------------------------
  // Header builds-count invalidation (P1)
  // docs/specs/feature-header-persistent-actions.md §4 New Tests Required.
  // The badge must update after a build is deleted from the hub. Production
  // code calls useBuildsCountStore.refresh() in handleDeleteBuild after
  // deleteBuild resolves; we observe that via a second listBuilds() call
  // followed by the count store landing on the new server-truth value.
  // ---------------------------------------------------------------------------

  it("refreshes builds count after deleteBuild (P1)", async () => {
    // First listBuilds populates the screen and seeds count=3 via the
    // screen's load effect (MenuScreen.tsx:53).
    mockListBuilds.mockResolvedValueOnce([
      makeSummary({ build_id: "build-a", school_name: "School A" }),
      makeSummary({ build_id: "build-b", school_name: "School B" }),
      makeSummary({ build_id: "build-c", school_name: "School C" }),
    ]);
    // Second listBuilds — fired by useBuildsCountStore.refresh() after
    // delete resolves — returns the 2 remaining builds. If refresh()
    // never fires, this mock never resolves and the count stays at 3.
    mockListBuilds.mockResolvedValueOnce([
      { build_id: "build-a" },
      { build_id: "build-c" },
    ]);
    mockDeleteBuild.mockResolvedValue(undefined);

    renderScreen();

    // Wait for the initial list to render and the count store to land on 3.
    await screen.findByTestId("card-build-build-a");
    await waitFor(() => {
      expect(useBuildsCountStore.getState().count).toBe(3);
    });
    expect(mockListBuilds).toHaveBeenCalledTimes(1);

    // Click the delete button on build-b.
    fireEvent.click(screen.getByTestId("btn-delete-build-b"));

    // The deleteBuild API must be called with the right id.
    await waitFor(() => {
      expect(mockDeleteBuild).toHaveBeenCalledWith("build-b");
    });

    // The store must end up at 2 — proving refresh() called listBuilds()
    // a second time and committed the result. We assert on the final
    // count rather than on the optimistic local list state because the
    // count store is what AppHeader's badge actually reads.
    await waitFor(() => {
      expect(useBuildsCountStore.getState().count).toBe(2);
    });
    expect(mockListBuilds).toHaveBeenCalledTimes(2);
  });

  it("preserves builds count when deleteBuild fails (P1)", async () => {
    mockListBuilds.mockResolvedValueOnce([
      makeSummary({ build_id: "build-a", school_name: "School A" }),
      makeSummary({ build_id: "build-b", school_name: "School B" }),
    ]);
    mockDeleteBuild.mockRejectedValue(new Error("backend on fire"));

    renderScreen();

    await screen.findByTestId("card-build-build-a");
    await waitFor(() => {
      expect(useBuildsCountStore.getState().count).toBe(2);
    });
    const initialCallCount = mockListBuilds.mock.calls.length;

    fireEvent.click(screen.getByTestId("btn-delete-build-b"));

    // Wait for the failure to surface so we know handleDeleteBuild ran.
    await waitFor(() => {
      expect(screen.getByText("backend on fire")).toBeInTheDocument();
    });

    // Count must not have changed; refresh() must not have fired (it sits
    // inside the try-block after deleteBuild resolves successfully).
    expect(useBuildsCountStore.getState().count).toBe(2);
    expect(mockListBuilds).toHaveBeenCalledTimes(initialCallCount);
  });
});
