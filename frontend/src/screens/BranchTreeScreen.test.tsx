import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { BranchTreeScreen } from "./BranchTreeScreen";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { TreeResponse } from "@/types/tree";
import type { Build } from "@/types/build";

/**
 * BranchTreeScreen.test.tsx
 *
 * Tests the screen-level orchestration:
 * - Navigation guard: redirects to /reveal if no build in store
 * - Loading state: shows emoji + "Mapping your branches..."
 * - Tree state: renders BranchTreeSVG after API success
 * - Fallback state: renders TreeFallback when tree has no children
 * - Error state: shows error message with Retry + Continue buttons
 * - Retry navigates to /branches
 * - Continue navigates to /save
 * - CTA buttons navigate correctly
 *
 * NOTE: We use real timers here (not fakeTimers). The fetchTree function
 * has a minDisplayMs=1500 delay using Date.now + setTimeout. Fighting
 * fake timers with async promise chains and Date.now is fragile. Instead,
 * we let the mock resolve instantly and the minDisplay setTimeout fire
 * naturally, using waitFor to poll for state transitions.
 * The 1500ms wait is acceptable because waitFor's default timeout is 1000ms,
 * so we increase it where needed.
 */

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockGetTree = vi.fn();
vi.mock("@/api/tree", () => ({
  getTree: (...args: unknown[]) => mockGetTree(...args),
}));

// Minimal Build fixture
function makeBuild(overrides: Partial<Build> = {}): Build {
  return {
    build_id: "build-test-123",
    created_at: "2026-01-15T12:00:00Z",
    school_name: "State University",
    unitid: 123456,
    major_text: "Finance",
    cipcode: "52.0801",
    program_name: "Finance, General",
    effort: "balanced",
    loan_pct: 0.5,
    career: {
      unitid: 123456,
      institution_name: "State University",
      cipcode: "52.0801",
      program_name: "Finance, General",
      soc_code: "13-2051",
      occupation_title: "Financial Analyst",
      soc_major_group_name: "Business and Financial Operations",
      median_annual_wage: 95570,
      earnings_1yr_median: 45000,
      earnings_1yr_p25: 35000,
      earnings_1yr_p75: 55000,
      debt_median: 25000,
      debt_to_earnings_annual: 0.56,
      education_level_name: "Bachelor's degree",
      growth_category: "Faster than average",
      net_price_annual: null,
      cost_of_attendance_annual: null,
      modeled_total_debt: null,
      debt_median_reference: null,
      institution_control: null,
      tuition_in_state: null,
      tuition_out_of_state: null,
      room_board_on_campus: null,
      stats: { ern: 72, roi: 68, res: 45, grw: 61, hmn: 38 },
      bosses: { ai: 45, loans: 20, market: 30, burnout: 60, ceiling: 40 },
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
      wins: 3,
      losses: 1,
      draws: 1,
      unknown: 0,
      verdict: "Strong",
    },
    branches: [],
    skill_recs: [],
    guidance: "Test guidance",
    skills_crafted: [],
    skill_pool: [],
    next_steps: "",
    ...overrides,
  } as Build;
}

function makeTreeResponse(childCount = 2): TreeResponse {
  const children = Array.from({ length: childCount }, (_, i) => ({
    soc_code: `11-300${i}`,
    title: `Career ${i}`,
    level: 1,
    ern: 80 + i,
    roi: 70 + i,
    res: 40 + i,
    grw: 50 + i,
    hmn: 45 + i,
    median_wage: 100000 + i * 10000,
    education: "Bachelor's degree",
    boss_ai: "win" as const,
    boss_loans: "win" as const,
    boss_market: "draw" as const,
    boss_burnout: "lose" as const,
    boss_ceiling: "draw" as const,
    children: [],
  }));

  return {
    tree: {
      soc_code: "13-2051",
      title: "Financial Analyst",
      level: 0,
      ern: 72,
      roi: 68,
      res: 45,
      grw: 61,
      hmn: 38,
      median_wage: 95570,
      education: "Bachelor's degree",
      boss_ai: "draw",
      boss_loans: "win",
      boss_market: "win",
      boss_burnout: "lose",
      boss_ceiling: "draw",
      children,
    },
    stats: {
      total_nodes: childCount + 1,
      max_depth_reached: 1,
      mcp_calls: childCount,
      dead_ends: 0,
      wall_clock_ms: 1500,
    },
  };
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <BranchTreeScreen />
    </MemoryRouter>,
  );
}

// The minDisplayMs in BranchTreeScreen is 1500ms. Our mocks resolve instantly,
// so we need to wait up to ~1600ms for the state transition. Use this timeout.
const SETTLE_TIMEOUT = 3000;

beforeEach(() => {
  mockNavigate.mockReset();
  mockGetTree.mockReset();
  useBuildStore.setState({ build: makeBuild() });
  useProfileStore.setState({ animalEmoji: "\uD83D\uDC3B", animalName: "bear", profileName: "bold bear" });
});

afterEach(() => {
  useBuildStore.setState({ build: null });
  useProfileStore.setState({ animalEmoji: null, animalName: null, profileName: null });
});

describe("BranchTreeScreen", () => {
  // --- Navigation guard ---

  it("redirects to /reveal when build is null", () => {
    useBuildStore.setState({ build: null });
    renderScreen();

    expect(mockNavigate).toHaveBeenCalledWith("/reveal", { replace: true });
  });

  it("does NOT redirect when build is present", () => {
    mockGetTree.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(mockNavigate).not.toHaveBeenCalledWith("/reveal", { replace: true });
  });

  // --- Loading state ---

  it("shows loading state initially with bouncing emoji and text", () => {
    mockGetTree.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(screen.getByText("Mapping your branches...")).toBeInTheDocument();
    expect(screen.getByText(/Tracing career paths/)).toBeInTheDocument();
  });

  it("shows the animal emoji from profile store during loading", () => {
    useProfileStore.setState({ animalEmoji: "\uD83E\uDD8A" });
    mockGetTree.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(screen.getByText("\uD83E\uDD8A")).toBeInTheDocument();
  });

  it("falls back to bear emoji when animalEmoji is null", () => {
    useProfileStore.setState({ animalEmoji: null });
    mockGetTree.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(screen.getByText("\uD83D\uDC3B")).toBeInTheDocument();
  });

  // --- Tree state (successful load) ---

  it("transitions from loading to tree after API resolves", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    renderScreen();

    // Initially shows loading
    expect(screen.getByText("Mapping your branches...")).toBeInTheDocument();

    // Wait for the minDisplayMs (1500ms) to pass and state transition
    await waitFor(
      () => {
        expect(screen.getByTestId("region-branch-tree")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );
  });

  it("renders Save & Share CTA button in tree state", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByTestId("btn-save-share")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );
  });

  it("Save & Share button navigates to /save", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByTestId("btn-save-share")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );

    fireEvent.click(screen.getByTestId("btn-save-share"));
    expect(mockNavigate).toHaveBeenCalledWith("/save");
  });

  // --- Fallback state (empty tree) ---

  it("shows fallback when tree has zero children", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(0));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByTestId("region-fallback")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );
  });

  it("fallback shows career title in message", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(0));
    renderScreen();

    await waitFor(
      () => {
        // The career title appears in both the SVG and the fallback message.
        // Assert on the specific fallback paragraph text.
        expect(
          screen.getByText(/We're mapping career branches for Financial Analyst/),
        ).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );
  });

  it("fallback still shows Save & Share button", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(0));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByTestId("btn-save-share")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );
  });

  // --- Error state ---

  it("shows error state when API rejects", async () => {
    mockGetTree.mockRejectedValue(new Error("Network timeout"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText(/Couldn't load the branch tree/)).toBeInTheDocument();
    });
  });

  it("shows generic error message regardless of error type", async () => {
    mockGetTree.mockRejectedValue(new Error("Server returned 503"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Failed to load tree")).toBeInTheDocument();
    });
  });

  it("error state has Try Again and Continue buttons", async () => {
    mockGetTree.mockRejectedValue(new Error("fail"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Try Again")).toBeInTheDocument();
      expect(screen.getByText(/Continue/)).toBeInTheDocument();
    });
  });

  it("Continue button in error state navigates to /save", async () => {
    mockGetTree.mockRejectedValue(new Error("fail"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText(/Continue/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Continue/));
    expect(mockNavigate).toHaveBeenCalledWith("/save");
  });

  it("Try Again triggers a re-fetch", async () => {
    mockGetTree.mockRejectedValue(new Error("fail"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Try Again")).toBeInTheDocument();
    });

    // Clicking Try Again re-triggers the fetch via retryCount
    mockGetTree.mockResolvedValue(makeTreeResponse());
    fireEvent.click(screen.getByText("Try Again"));

    await waitFor(() => {
      expect(mockGetTree).toHaveBeenCalledTimes(2);
    });
  });

  // --- API call ---

  it("calls getTree with the build_id from the store", () => {
    mockGetTree.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(mockGetTree).toHaveBeenCalledWith("build-test-123");
  });

  it("does not call getTree when build is null", () => {
    useBuildStore.setState({ build: null });
    renderScreen();

    expect(mockGetTree).not.toHaveBeenCalled();
  });

  // --- Navigation buttons in tree state ---

  it("Back to Gauntlet navigates to /gauntlet", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByText("Back to Gauntlet")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );

    fireEvent.click(screen.getByText("Back to Gauntlet"));
    expect(mockNavigate).toHaveBeenCalledWith("/gauntlet");
  });

  it("Back to My Build navigates to /reveal", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByText("Back to My Build")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );

    fireEvent.click(screen.getByText("Back to My Build"));
    expect(mockNavigate).toHaveBeenCalledWith("/reveal");
  });

  it("wraps content in PageContainer grid with tree col-span-8 and sidebar col-span-4 at desktop", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByTestId("page-container")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );

    // Tree cell carries desktop:col-span-8 on mobile-default col-span-12.
    const treeCell = document.querySelector("[class*='desktop:col-span-8']");
    expect(treeCell).not.toBeNull();
    expect(treeCell!.className).toContain("col-span-12");

    // Sidebar cell carries desktop:col-span-4 and is hidden on mobile.
    const sidebarCell = document.querySelector(
      "[class*='desktop:col-span-4']",
    );
    expect(sidebarCell).not.toBeNull();
    expect(sidebarCell!.className).toContain("hidden");
    expect(sidebarCell!.className).toContain("desktop:block");
  });
});
