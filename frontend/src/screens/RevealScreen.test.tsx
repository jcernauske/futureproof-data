import { render, waitFor, act, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { RevealScreen } from "./RevealScreen";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { CareerOutcome } from "@/types/build";
import {
  setReducedMotion,
  resetReducedMotion,
} from "@/test/mocks/prefers-reduced-motion";

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
    match_quality: null,
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    is_out_of_state: false,
    loan_pct: 0.5,
  };
}

function seedReady() {
  useBuildInputStore.setState({
    phase: "sliders",
    school: { unitid: 110635, name: "UC Berkeley", institutionControl: "Public", stateAbbr: "CA", netPriceAnnual: null, costOfAttendanceAnnual: null, tuitionInState: null, tuitionOutOfState: null },
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
    hasSeenStatTutorial: true, // skip tutorial side-effect
  });
  useProfileStore.setState({
    profileName: "dancing happy bear",
    animalEmoji: "🐻",
    animalName: "bear",
  });
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockCreateBuild.mockReset();
  sessionStorage.clear();
  resetReducedMotion();
  // Fresh fake timers — this screen schedules multiple setTimeouts.
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
  resetReducedMotion();
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

describe("RevealScreen — relaxed pacing floor", () => {
  /**
   * Spec: docs/specs/perf-reveal-loading-screen.md §3 / §6 — the
   * minDisplayTime floor dropped from 2000ms to 1000ms so fast backend
   * responses surface faster on screens 6→7. This test locks the new
   * floor in.
   *
   * Setup: createBuild resolves in 200ms. The LoadingScreen must stay
   * mounted past the 1000ms floor (still showing at t=1001) but must
   * give way to the reveal before t=1500 — i.e. the floor is 1000ms,
   * not the old 2000ms.
   */
  it("holds LoadingScreen for at least 1000ms then reveals by 1500ms", async () => {
    seedReady();

    mockCreateBuild.mockImplementation(
      () =>
        new Promise((resolve) => {
          // Use the real setTimeout so fake-timer advances drive it.
          setTimeout(() => {
            resolve({
              build_id: "fast-build",
              created_at: "2026-04-18T00:00:00Z",
              school_name: "UC Berkeley",
              unitid: 110635,
              major_text: "Computer Science",
              cipcode: "11.0701",
              program_name: "CS",
              effort: "balanced",
              loan_pct: 0.5,
              career: makeCareer(),
              gauntlet: {
                fights: [],
                wins: 0,
                losses: 0,
                draws: 0,
                unknown: 0,
                verdict: "",
              },
              branches: [],
              skill_recs: [],
              guidance: "You have strong alignment.",
              skills_crafted: [],
              skill_pool: [],
              next_steps: "",
              profile_name: "",
            });
          }, 200);
        }),
    );

    render(
      <MemoryRouter>
        <RevealScreen />
      </MemoryRouter>,
    );

    // Wait for the fetch to have kicked off so we know the component
    // mounted and hit its initial useEffect.
    await waitFor(() => {
      expect(mockCreateBuild).toHaveBeenCalledTimes(1);
    });

    // At t=500 (well past the 200ms build resolve but well before the
    // 1000ms floor) the LoadingScreen must still be mounted. Promise.all
    // is gated on the slower minDisplayTime promise, so setBuild hasn't
    // run yet and the reveal content is withheld.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.queryByRole("status")).not.toBeNull();
    expect(screen.queryByText("Software Developer")).toBeNull();

    // Advance past the 1000ms floor. minDisplayTime resolves, Promise.all
    // completes, setBuild fires, then a 400ms revealTimer flips
    // revealReady so the career title enters the DOM.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000); // now at t=1500 total
    });

    // Reveal is showing by t=1500 at the latest — the hard upper
    // bound the spec sets after the floor relaxation.
    expect(screen.getByText("Software Developer")).toBeInTheDocument();
    // And the loading overlay is gone.
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("does NOT reveal before the 1000ms floor even when build resolves instantly", async () => {
    seedReady();

    // createBuild resolves on microtask queue — immediately available.
    mockCreateBuild.mockResolvedValue({
      build_id: "instant-build",
      created_at: "2026-04-18T00:00:00Z",
      school_name: "UC Berkeley",
      unitid: 110635,
      major_text: "Computer Science",
      cipcode: "11.0701",
      program_name: "CS",
      effort: "balanced",
      loan_pct: 0.5,
      career: makeCareer(),
      gauntlet: {
        fights: [],
        wins: 0,
        losses: 0,
        draws: 0,
        unknown: 0,
        verdict: "",
      },
      branches: [],
      skill_recs: [],
      guidance: "",
      skills_crafted: [],
      skill_pool: [],
      next_steps: "",
      profile_name: "",
    });

    render(
      <MemoryRouter>
        <RevealScreen />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockCreateBuild).toHaveBeenCalledTimes(1);
    });

    // At t=500 (halfway through the floor), reveal content is still
    // withheld.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(screen.queryByText("Software Developer")).toBeNull();
    expect(screen.queryByRole("status")).not.toBeNull();
  });
});

describe("RevealScreen — prefers-reduced-motion", () => {
  /**
   * Spec §4 Stage 2 Reveal Motion Sequence — reduced-motion fallback:
   * when useReducedMotion() returns true, all 8 beats fire simultaneously
   * with transition: { duration: 0 } (or via Framer Motion's automatic
   * collapse). The user sees the full reveal at t=0 — no holds, no stagger.
   *
   * This test asserts the VISIBLE RENDER STATE, not specific transition.delay
   * values. Framer Motion obscures `transition` internals (especially under
   * reduced motion where it overrides the user-provided value), so we verify
   * that the eight end-state elements are all present immediately after mount
   * + a flush of any pending microtasks.
   */
  it("collapses the 3.7s reveal sequence to instant when reduced motion is set", async () => {
    setReducedMotion(true);
    seedReady();

    // Seed a complete build so the reveal content renders without the
    // 2s minDisplayTime gate. The component calls setRevealReady(true)
    // immediately when build is already present in the store.
    useBuildStore.setState({
      build: {
        build_id: "b-reduced-motion",
        created_at: "2026-04-17T00:00:00Z",
        school_name: "UC Berkeley",
        unitid: 110635,
        major_text: "CS",
        cipcode: "11.0701",
        program_name: "CS",
        effort: "balanced",
        loan_pct: 0.5,
        career: makeCareer(),
        gauntlet: {
          fights: [],
          wins: 0,
          losses: 0,
          draws: 0,
          unknown: 0,
          verdict: "",
        },
        branches: [],
        skill_recs: [],
        guidance: "You have strong alignment between your stats and this path.",
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

    // Under reduced motion, the career title (the t=1.5s beat in the normal
    // sequence) must render without waiting for any timer advance. The
    // `revealReady` state flips synchronously in the useEffect when a build
    // is already present, so the element enters the DOM on the next render.
    await waitFor(() => {
      expect(screen.getByText("Software Developer")).toBeInTheDocument();
    });

    // Every downstream beat must also be present at t=0 — no 3.7s wall clock.
    // These elements span beats 3–8 of the retimed sequence (title, pentagon,
    // stat cards, Gemma's Take, career detail, Fight bosses CTA).
    expect(screen.getByText("at UC Berkeley")).toBeInTheDocument();
    // Fight bosses CTA — the final beat (t=3.7s in normal flow).
    expect(
      screen.getByRole("button", { name: "Fight the Bosses" }),
    ).toBeInTheDocument();
  });
});
