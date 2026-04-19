/**
 * MenuScreen.test.tsx
 *
 * Tests Screen 10 (post-build hub):
 * - Renders saved builds for the active profile (P0)
 * - Tap a build card → loads via getBuild → navigate to /reveal (P0)
 * - "New Build" → resetInputs() + navigate to /school (P1)
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
const mockSendChat = vi.fn();
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    listBuilds: (...args: unknown[]) => mockListBuilds(...args),
    compareBuilds: (...args: unknown[]) => mockCompareBuilds(...args),
    sendChat: (...args: unknown[]) => mockSendChat(...args),
  };
});

const mockGetBuild = vi.fn();
vi.mock("@/api/build", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/build")>("@/api/build");
  return {
    ...actual,
    getBuild: (...args: unknown[]) => mockGetBuild(...args),
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
  mockSendChat.mockReset();
  mockGetBuild.mockReset();
  // Sane defaults — individual tests can override.
  mockCompareBuilds.mockReturnValue(new Promise(() => {}));
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
    hasSeenStatTutorial: false,
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
    expect(mockListBuilds).toHaveBeenCalledWith("Wandering Otter");
  });

  it("calls listBuilds with the active profile name (P0)", async () => {
    mockListBuilds.mockResolvedValue([]);
    renderScreen();
    await waitFor(() => {
      expect(mockListBuilds).toHaveBeenCalledWith("Wandering Otter");
    });
  });

  it("redirects to /app when no profile in store (saboteur: profile-less direct nav)", () => {
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
    mockListBuilds.mockResolvedValue([]);
    renderScreen();
    expect(mockNavigate).toHaveBeenCalledWith("/app", { replace: true });
    // Must not fire the list query before the profile guard kicks the user out.
    expect(mockListBuilds).not.toHaveBeenCalled();
  });

  // --- P0: tap card loads build + navigates ---

  it("tap build card → loads via getBuild → setBuild → navigate to /reveal (P0)", async () => {
    mockListBuilds.mockResolvedValue([makeSummary()]);
    mockGetBuild.mockResolvedValue(makeBuild());

    renderScreen();

    const card = await screen.findByTestId("card-build-berkeley-cs-001");
    fireEvent.click(card);

    await waitFor(() => {
      expect(mockGetBuild).toHaveBeenCalledWith("berkeley-cs-001");
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/reveal");
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
    expect(mockNavigate).not.toHaveBeenCalledWith("/reveal");
  });

  // --- P1: New Build clears inputs and navigates ---

  it('"New Build" calls resetInputs() then navigates to /school (P1)', async () => {
    mockListBuilds.mockResolvedValue([makeSummary()]);

    // Pollute build inputs first so we can prove the reset.
    useBuildInputStore.setState({
      phase: "sliders",
      school: { unitid: 1, name: "Old School", institutionControl: "Public", netPriceAnnual: null, costOfAttendanceAnnual: null },
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

    expect(mockNavigate).toHaveBeenCalledWith("/school");
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

  it("empty-state CTA also routes to /school via resetInputs (saboteur: zero-builds path)", async () => {
    mockListBuilds.mockResolvedValue([]);
    renderScreen();

    const cta = await screen.findByTestId("btn-new-build");
    fireEvent.click(cta);
    expect(mockNavigate).toHaveBeenCalledWith("/school");
  });
});
