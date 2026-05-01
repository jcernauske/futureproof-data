/**
 * SaveWrappedScreen.test.tsx
 *
 * Tests the Screen 9 orchestrator:
 * - Navigation guard: redirects to /my-build when build is null
 * - Save-confirmation phase renders the build summary
 * - Transition to the story viewer after render + getWrapped resolve
 * - Error phase on render rejection
 * - Done action navigates to /branches
 *
 * The API is stubbed at module level so Playwright never runs and we
 * fully control the timeline.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SaveWrappedScreen } from "./SaveWrappedScreen";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { Build } from "@/types/build";
import type { StoredBag } from "@/hooks/useHorizonPick";
import { __resetInMemoryBagsForTesting } from "@/hooks/useHorizonPick";

// --- Mocks --------------------------------------------------------------

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockRenderWrapped = vi.fn();
const mockGetWrapped = vi.fn();
vi.mock("@/api/wrapped", () => ({
  renderWrapped: (...args: unknown[]) => mockRenderWrapped(...args),
  getWrapped: (...args: unknown[]) => mockGetWrapped(...args),
}));

// --- Fixtures -----------------------------------------------------------

function makeBuild(overrides: Partial<Build> = {}): Build {
  return {
    build_id: "iu-b-marketing-001",
    created_at: "2026-04-15T12:00:00Z",
    school_name: "Indiana University",
    unitid: 151351,
    major_text: "Marketing",
    cipcode: "52.14",
    program_name: "Marketing",
    effort: "balanced",
    loan_pct: 1.0,
    career: {
      unitid: 151351,
      institution_name: "Indiana University",
      cipcode: "52.14",
      program_name: "Marketing",
      soc_code: "13-2051",
      occupation_title: "Financial Analyst",
      stats: { ern: 8, roi: 9, res: 4, grw: 6, hmn: 6 },
      bosses: { ai: 7, loans: null, market: 7, burnout: 6, ceiling: null },
      median_annual_wage: 66490,
      earnings_1yr_median: 45000,
      earnings_1yr_p25: null,
      earnings_1yr_p75: null,
      debt_median: 25000,
      debt_to_earnings_annual: 0.56,
      education_level_name: "Bachelor's degree",
      growth_category: "Average",
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
      loan_pct: 1.0,
    },
    gauntlet: {
      fights: [],
      wins: 3,
      losses: 1,
      draws: 1,
      unknown: 0,
      verdict: "SOLID",
    },
    branches: [],
    skill_recs: [],
    guidance: "",
    skills_crafted: [],
    skill_pool: [],
    next_steps: "",
    profile_name: "bold bear",
    ...overrides,
  } as Build;
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <SaveWrappedScreen />
    </MemoryRouter>,
  );
}

// --- Setup --------------------------------------------------------------

beforeEach(() => {
  mockNavigate.mockReset();
  mockRenderWrapped.mockReset();
  mockGetWrapped.mockReset();
  // Wipe horizon bag state so cursor-stability assertions aren't polluted
  // by leftovers from prior tests.
  if (typeof window !== "undefined" && window.sessionStorage) {
    window.sessionStorage.clear();
  }
  __resetInMemoryBagsForTesting();
  useBuildStore.setState({ build: makeBuild() });
  useProfileStore.setState({
    profileName: "bold bear",
    animalEmoji: "\uD83D\uDC3B",
    animalName: "bear",
  });
});

afterEach(() => {
  useBuildStore.setState({ build: null });
  useProfileStore.setState({
    profileName: null,
    animalEmoji: null,
    animalName: null,
  });
  __resetInMemoryBagsForTesting();
});

// --- Tests --------------------------------------------------------------

describe("SaveWrappedScreen", () => {
  // --- Navigation guard ---

  it("redirects to /my-build when build is null", () => {
    useBuildStore.setState({ build: null });
    renderScreen();
    expect(mockNavigate).toHaveBeenCalledWith("/my-build", { replace: true });
  });

  it("does not fire render when no build is present", () => {
    useBuildStore.setState({ build: null });
    renderScreen();
    expect(mockRenderWrapped).not.toHaveBeenCalled();
  });

  // --- Save confirmation phase ---

  it("shows save confirmation with profile + school + career", () => {
    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();

    const region = screen.getByTestId("region-save-confirm");
    expect(region).toBeInTheDocument();
    // Profile name now lives inside its own <bdi> for bidi isolation,
    // so it's a separate text node from "· Indiana University ·". Match
    // the full textContent of the line instead of a single text node.
    expect(region.textContent).toMatch(
      /bold bear.*Indiana University.*Financial Analyst/,
    );
  });

  it("save confirmation region has the correct aria-label", () => {
    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();
    expect(screen.getByTestId("region-save-confirm")).toHaveAttribute(
      "aria-label",
      "Build saved successfully",
    );
  });

  it("shows the W/D/L tally from the gauntlet", () => {
    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();
    expect(screen.getByText(/3W.*1D.*1L/)).toBeInTheDocument();
  });

  it("kicks off renderWrapped immediately on mount", () => {
    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();
    expect(mockRenderWrapped).toHaveBeenCalledWith("iu-b-marketing-001");
  });

  it("falls back to ✦ emoji when profile has no animalEmoji", () => {
    useProfileStore.setState({ animalEmoji: null });
    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(screen.getByText("✦")).toBeInTheDocument();
  });

  it("falls back to 'Anonymous' when profileName is empty", () => {
    useProfileStore.setState({ profileName: "" });
    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();

    const region = screen.getByTestId("region-save-confirm");
    expect(region.textContent).toMatch(
      /Anonymous.*Indiana University.*Financial Analyst/,
    );
  });

  // --- Transition to viewer ---

  it("transitions to viewer after render + getWrapped resolve", async () => {
    mockRenderWrapped.mockResolvedValue({ status: "ok", frame_count: 6 });
    mockGetWrapped.mockResolvedValue({
      frames: Array.from({ length: 6 }, (_, i) => ({
        index: i,
        url: `data:image/svg+xml;base64,frame-${i}`,
      })),
    });
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByTestId("region-wrapped-viewer")).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    expect(screen.getByText("1 / 6")).toBeInTheDocument();
  });

  it("calls getWrapped after renderWrapped resolves", async () => {
    mockRenderWrapped.mockResolvedValue({ status: "ok", frame_count: 6 });
    mockGetWrapped.mockResolvedValue({ frames: [] });
    renderScreen();

    await waitFor(
      () => {
        expect(mockGetWrapped).toHaveBeenCalledWith("iu-b-marketing-001");
      },
      { timeout: 4000 },
    );
  });

  // --- Error phase ---

  it("shows error message when render rejects", async () => {
    mockRenderWrapped.mockRejectedValue(
      new Error("playwright is not installed"),
    );
    renderScreen();

    await waitFor(
      () => {
        expect(
          screen.getByText(/Your wrapped didn't develop/i),
        ).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    expect(
      screen.getByText("playwright is not installed"),
    ).toBeInTheDocument();
  });

  it("shows error when getWrapped rejects", async () => {
    mockRenderWrapped.mockResolvedValue({ status: "ok", frame_count: 6 });
    mockGetWrapped.mockRejectedValue(new Error("connection refused"));
    renderScreen();

    await waitFor(
      () => {
        expect(
          screen.getByText(/Your wrapped didn't develop/i),
        ).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
  });

  it("error phase exposes 'Try again' and 'Skip to menu' actions", async () => {
    mockRenderWrapped.mockRejectedValue(new Error("fail"));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByText("Try again")).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    expect(screen.getByText("Skip to menu")).toBeInTheDocument();
  });

  it("'Skip to menu' navigates to /branches", async () => {
    mockRenderWrapped.mockRejectedValue(new Error("fail"));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByText("Skip to menu")).toBeInTheDocument();
      },
      { timeout: 4000 },
    );

    fireEvent.click(screen.getByText("Skip to menu"));
    expect(mockNavigate).toHaveBeenCalledWith("/branches");
  });

  it("handles a non-Error thrown value without crashing", async () => {
    /* Saboteur: what if renderWrapped throws something that isn't an
     * Error instance? The screen must still transition to the error
     * phase with a sane fallback message — "Failed to render wrapped"
     * per the screen's non-Error branch. */
    mockRenderWrapped.mockRejectedValue("weird string error");
    renderScreen();

    await waitFor(
      () => {
        expect(
          screen.getByText(/Your wrapped didn't develop/i),
        ).toBeInTheDocument();
      },
      { timeout: 4000 },
    );
    // The non-Error branch surfaces "Failed to render wrapped"
    expect(
      screen.getByText(/Failed to render wrapped/),
    ).toBeInTheDocument();
  });

  // --- Horizon silhouette / horizonIndex commit (feature-horizon-footer §4) ---

  it("sets build.horizonIndex on first mount when absent", async () => {
    /* Locked-at-commit contract: the first time SaveWrappedScreen mounts
     * with build.horizonIndex === undefined, the desktop bag is drawn and
     * the index is persisted onto the build via setBuild. No pre-existing
     * value should ever be drawn — the value is locked from this point on.
     */
    // Belt-and-suspenders: clear any leftover bag state.
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.clear();
    }
    expect(useBuildStore.getState().build?.horizonIndex).toBeUndefined();

    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();

    await waitFor(() => {
      const idx = useBuildStore.getState().build?.horizonIndex;
      expect(idx).not.toBeUndefined();
    });

    const idx = useBuildStore.getState().build?.horizonIndex;
    expect(typeof idx).toBe("number");
    expect(idx!).toBeGreaterThanOrEqual(0);
    expect(idx!).toBeLessThan(48); // HORIZON_POOL_SIZE
  });

  it("preserves build.horizonIndex on subsequent mounts (locked-at-commit)", async () => {
    /* Once horizonIndex is set, future mounts MUST NOT overwrite it —
     * not even when index 0 was the locked value. The implementer used
     * `=== undefined` (not `!build.horizonIndex`); this test is the
     * regression guard against someone "simplifying" that to a falsy
     * check, which would silently re-roll for the 1/48 of builds with
     * index 0.
     */
    useBuildStore.setState({ build: makeBuild({ horizonIndex: 0 }) });

    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();

    // Give the effect a chance to run.
    await act(async () => {
      await new Promise((r) => setTimeout(r, 30));
    });

    expect(useBuildStore.getState().build?.horizonIndex).toBe(0);
  });

  it("preserves a non-zero horizonIndex on remount", async () => {
    useBuildStore.setState({ build: makeBuild({ horizonIndex: 17 }) });

    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    renderScreen();
    await act(async () => {
      await new Promise((r) => setTimeout(r, 30));
    });

    expect(useBuildStore.getState().build?.horizonIndex).toBe(17);
  });

  it("does NOT advance the desktop bag on remount when horizonIndex is already set (Major #2 regression)", async () => {
    /* Code review Major #2: previously SaveWrappedScreen called
     * `useHorizonPick("desktop")` unconditionally, whose mount-time effect
     * draws + persists every time. Result: every save-screen view burned a
     * desktop bag entry — even when horizonIndex was already locked — and
     * polluted the landing footer's shared bag walk.
     *
     * Fix: lazy-draw via `drawAndPersist`, gated by
     * `horizonIndex === undefined`. When the index is already set, we make
     * zero touches to the bag.
     *
     * This test seeds the desktop bag, locks an index on the build, mounts
     * the save screen, and asserts the storage cursor did not move.
     */
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.clear();
    }

    // Seed a known desktop bag so we can detect any cursor advance.
    const seededBag: StoredBag = {
      order: Array.from({ length: 48 }, (_, i) => i),
      cursor: 7,
      lastShown: 6,
    };
    window.sessionStorage.setItem(
      "fp.horizon.bag.v1.desktop",
      JSON.stringify(seededBag),
    );

    // Build already has horizonIndex set — the screen must NOT touch the bag.
    useBuildStore.setState({ build: makeBuild({ horizonIndex: 23 }) });

    mockRenderWrapped.mockReturnValue(new Promise(() => {}));
    mockGetWrapped.mockReturnValue(new Promise(() => {}));

    // First mount with horizonIndex set.
    const { unmount: unmountA } = renderScreen();
    await act(async () => {
      await new Promise((r) => setTimeout(r, 30));
    });
    unmountA();

    // Second mount, same locked horizonIndex.
    const { unmount: unmountB } = renderScreen();
    await act(async () => {
      await new Promise((r) => setTimeout(r, 30));
    });
    unmountB();

    // Third mount for paranoid measure.
    renderScreen();
    await act(async () => {
      await new Promise((r) => setTimeout(r, 30));
    });

    // The bag's cursor MUST be exactly where we left it. If anyone wires the
    // hook back in unconditionally, this jumps to 8/9/10 and the test fails.
    const raw = window.sessionStorage.getItem("fp.horizon.bag.v1.desktop");
    expect(raw).not.toBeNull();
    const after = JSON.parse(raw!) as StoredBag;
    expect(after.cursor).toBe(7);
    expect(after.lastShown).toBe(6);

    // And the build's horizonIndex is still the locked value.
    expect(useBuildStore.getState().build?.horizonIndex).toBe(23);
  });

  it("silhouette mounts behind share card (z-index check)", async () => {
    /* Layering contract: the silhouette overlay must sit at z-0 while the
     * WrappedViewer card sits at z-10 above. If anyone reorders the JSX
     * or strips the z-index utility, the silhouette would either occlude
     * the card or stack visually wrong.
     */
    useBuildStore.setState({ build: makeBuild({ horizonIndex: 5 }) });
    mockRenderWrapped.mockResolvedValue({ status: "ok", frame_count: 6 });
    mockGetWrapped.mockResolvedValue({
      frames: Array.from({ length: 6 }, (_, i) => ({
        index: i,
        url: `data:image/svg+xml;base64,frame-${i}`,
      })),
    });

    const { container } = renderScreen();

    // Wait for the viewer phase (silhouette is only mounted there).
    await waitFor(
      () => {
        expect(screen.getByTestId("region-wrapped-viewer")).toBeInTheDocument();
      },
      { timeout: 4000 },
    );

    const silhouette = container.querySelector("#horizon-silhouette");
    expect(silhouette).not.toBeNull();

    // Walk up to find the wrapper that carries the z-0 utility.
    const silhouetteWrap = silhouette!.closest(".z-0");
    expect(silhouetteWrap).not.toBeNull();

    // The viewer should be wrapped in a sibling at z-10.
    const viewer = screen.getByTestId("region-wrapped-viewer");
    const viewerWrap = viewer.closest(".z-10");
    expect(viewerWrap).not.toBeNull();
  });

  it("does not render the silhouette during the save-confirmation phase", async () => {
    /* Layering boundary: the silhouette is gated by both the viewer
     * phase AND `build.horizonIndex !== undefined`. During the save
     * phase (the first 1.5s) the viewer JSX block isn't mounted at all,
     * so the silhouette must be absent — it must not leak into the
     * SaveConfirmation card.
     */
    useBuildStore.setState({ build: makeBuild({ horizonIndex: 5 }) });
    mockRenderWrapped.mockReturnValue(new Promise(() => {})); // hang
    mockGetWrapped.mockReturnValue(new Promise(() => {}));
    const { container } = renderScreen();

    expect(screen.getByTestId("region-save-confirm")).toBeInTheDocument();
    expect(container.querySelector("#horizon-silhouette")).toBeNull();
  });

  // --- Cancellation on unmount ---

  it("unmounting mid-render does not trigger a phase transition", async () => {
    /* If the cleanup `cancelled` flag is broken, an unmounted
     * component can fire setPhase → React warning. We assert that
     * after unmount, navigate isn't called (the only externally
     * observable side-effect).
     */
    let resolveRender: (v: unknown) => void = () => {};
    mockRenderWrapped.mockReturnValue(
      new Promise((r) => {
        resolveRender = r;
      }),
    );
    mockGetWrapped.mockResolvedValue({ frames: [] });

    const { unmount } = renderScreen();
    unmount();

    // Resolve the stalled render AFTER unmount — must not navigate
    await act(async () => {
      resolveRender({ status: "ok", frame_count: 6 });
      await new Promise((r) => setTimeout(r, 50));
    });

    // Navigate should only have been called if build was null — it wasn't
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
