/**
 * SaveWrappedScreen.test.tsx
 *
 * Tests the Screen 9 orchestrator:
 * - Navigation guard: redirects to /reveal when build is null
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
});

// --- Tests --------------------------------------------------------------

describe("SaveWrappedScreen", () => {
  // --- Navigation guard ---

  it("redirects to /reveal when build is null", () => {
    useBuildStore.setState({ build: null });
    renderScreen();
    expect(mockNavigate).toHaveBeenCalledWith("/reveal", { replace: true });
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

    expect(screen.getByTestId("region-save-confirm")).toBeInTheDocument();
    expect(
      screen.getByText(/bold bear.*Indiana University.*Financial Analyst/),
    ).toBeInTheDocument();
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

    expect(
      screen.getByText(/Anonymous.*Indiana University.*Financial Analyst/),
    ).toBeInTheDocument();
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
