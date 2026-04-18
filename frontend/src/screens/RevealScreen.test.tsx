import { render, waitFor, act, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { RevealScreen } from "./RevealScreen";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { CareerOutcome } from "@/types/build";

/**
 * RevealScreen tests
 *
 * Focus: the two landmines flagged by code review —
 *   1. Nav guard on missing session state must set session-expired hint
 *      and redirect to /career-pick without kicking off any API calls.
 *   2. The initial build-trigger useEffect has empty deps. If the component
 *      unmounts mid-flight, the in-flight createBuild promise must NOT
 *      fire setBuild/setIsBuilding against an unmounted tree. Regression
 *      here produces a "Can't perform a React state update on unmounted
 *      component" console warning.
 */

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockCreateBuild = vi.fn();
vi.mock("@/api/build", () => ({
  createBuild: (...args: unknown[]) => mockCreateBuild(...args),
}));

function makeCareer(soc = "15-1252"): CareerOutcome {
  return {
    unitid: 110635,
    institution_name: "UC Berkeley",
    cipcode: "11.0701",
    program_name: "CS",
    soc_code: soc,
    occupation_title: "Software Developer",
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
    stats: { ern: 8, roi: 7, res: 4, grw: 9, hmn: 5 },
    bosses: { ai: 6, loans: 3, market: 2, burnout: 5, ceiling: 3 },
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
  };
}

function seedReady() {
  useBuildInputStore.setState({
    phase: "sliders",
    school: { unitid: 110635, name: "UC Berkeley", institutionControl: "Public", netPriceAnnual: null, costOfAttendanceAnnual: null },
    programs: [],
    major: {
      cipCode: "11.0701",
      cipTitle: "Computer Science",
      rawText: "Computer Science",
      careersPreview: [],
      substitutionApplied: false,
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
    hasSeenStatTutorial: true, // skip tutorial side-effect
  });
  useProfileStore.setState({
    profileName: "dancing happy bear 🐻",
    animalEmoji: "🐻",
    animalName: "bear",
  });
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockCreateBuild.mockReset();
  sessionStorage.clear();
  // Fresh fake timers — this screen schedules multiple setTimeouts.
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("RevealScreen — nav guard", () => {
  it("redirects to /career-pick and sets session-expired hint when selectedCareer is missing", async () => {
    seedReady();
    // Null out the piece of state that would trigger the guard.
    useBuildStore.setState({ selectedCareer: null });

    render(
      <MemoryRouter>
        <RevealScreen />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/career-pick", { replace: true });
    });
    expect(sessionStorage.getItem("fp-nav-hint")).toBe("session-expired");
    // Guard runs before runBuild — no build request should fire.
    expect(mockCreateBuild).not.toHaveBeenCalled();
  });
});

describe("RevealScreen — unmount race safety", () => {
  it("does NOT fire setState on unmounted component after in-flight build resolves", async () => {
    seedReady();

    // Hold createBuild in pending state until we release it.
    let resolveBuild!: (value: unknown) => void;
    mockCreateBuild.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveBuild = resolve;
        }),
    );

    // React logs the "can't perform state update on unmounted" warning via
    // console.error. Spy so we can assert it never fires.
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { unmount } = render(
      <MemoryRouter>
        <RevealScreen />
      </MemoryRouter>,
    );

    // Wait for the fetch to have kicked off.
    await waitFor(() => {
      expect(mockCreateBuild).toHaveBeenCalledTimes(1);
    });

    // Unmount mid-flight.
    unmount();

    // Now resolve the promise AFTER unmount. Without the `cancelled` ref
    // guard, setBuild/setIsBuilding would fire on an unmounted tree and
    // React would log a warning.
    await act(async () => {
      resolveBuild({
        build_id: "late-arrival",
        created_at: "2026-04-15T00:00:00Z",
        school_name: "UC Berkeley",
        unitid: 110635,
        major_text: "Computer Science",
        cipcode: "11.0701",
        program_name: "CS",
        effort: "balanced",
        loan_pct: 0.5,
        career: makeCareer(),
        gauntlet: { fights: [], wins: 0, losses: 0, draws: 0, unknown: 0, verdict: "" },
        branches: [],
        skill_recs: [],
        guidance: "",
        skills_crafted: [],
        skill_pool: [],
        next_steps: "",
      });
      // Drain microtasks AND the 2s minDisplayTime + 400ms revealTimer.
      await vi.advanceTimersByTimeAsync(3000);
    });

    // The minDisplayTime Promise.all gate would normally also call setBuild.
    // With the cancelledRef guard, neither setBuild nor setIsBuilding should
    // run. The store's build should remain null (we never set it).
    expect(useBuildStore.getState().build).toBeNull();

    // Crucial: no unmount warnings should have been logged.
    const unmountWarnings = errSpy.mock.calls.filter((args) =>
      args.some(
        (a) =>
          typeof a === "string" &&
          (a.includes("unmounted component") ||
            a.includes("not wrapped in act") ||
            a.includes("Can't perform a React state update")),
      ),
    );
    expect(unmountWarnings).toEqual([]);

    errSpy.mockRestore();
  });
});

describe("RevealScreen — grid layout", () => {
  it("pentagon wraps in col-span-7 and stat cards in col-span-5 at desktop", async () => {
    seedReady();
    // Seed a complete build so the screen renders the reveal content.
    useBuildStore.setState({
      build: {
        build_id: "b-1",
        created_at: "2026-04-17T00:00:00Z",
        school_name: "UC Berkeley",
        unitid: 110635,
        major_text: "CS",
        cipcode: "11.0701",
        program_name: "CS",
        effort: "balanced",
        loan_pct: 0.5,
        career: makeCareer(),
        gauntlet: { fights: [], wins: 0, losses: 0, draws: 0, unknown: 0, verdict: "" },
        branches: [],
        skill_recs: [],
        guidance: "",
        skills_crafted: [],
        skill_pool: [],
        next_steps: "",
        profile_name: "",
      },
      hasSeenStatTutorial: true,
    });

    render(
      <MemoryRouter>
        <RevealScreen />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Software Developer")).toBeInTheDocument();
    });

    // Pentagon wrapper carries col-span-12 on mobile + desktop:col-span-7.
    const pentagonCell = screen.getByText("Software Developer").closest("div")
      ?.parentElement
      ?.querySelector("[class*='desktop:col-span-7']");
    expect(pentagonCell).not.toBeNull();

    // Stat cards wrapper carries desktop:col-span-5.
    const statCardsCell = document.querySelector("[class*='desktop:col-span-5']");
    expect(statCardsCell).not.toBeNull();
    expect(statCardsCell!.className).toContain("col-span-12");
  });
});
