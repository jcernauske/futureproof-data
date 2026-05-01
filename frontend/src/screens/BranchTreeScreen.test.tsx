import { useState } from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { BranchTreeScreen } from "./BranchTreeScreen";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { TreeResponse } from "@/types/tree";
import type { Build, CareerBranch } from "@/types/build";

// Mock the Ask Gemma client at the module boundary. The embedded
// GemmaChat fires askGemma() on mount with the auto-opener; the screen
// tests need full control over the response shape and timing.
const mockAskGemma = vi.fn();
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    askGemma: (...args: unknown[]) => mockAskGemma(...args),
  };
});

// Replace BranchHorizonMap with a thin test double that exposes a real
// DOM button per chip so fireEvent.click drives onSelectNode through
// the screen's actual selection wiring. The double also renders the
// branch-flash className so the highlight test can find it.
//
// Chip id schema (Decision #14): `chip-${branch.to_soc}` — flat L1-only
// candidate set, no L0 root chip, no L2/L3 entries.
vi.mock("@/components/tree/BranchHorizonMap", () => ({
  BranchHorizonMap: ({
    branches,
    onSelectNode,
    selectedNodeId,
    highlightedNodeIds,
  }: {
    branches: { to_soc: string; to_title: string }[];
    onSelectNode: (id: string | null) => void;
    selectedNodeId: string | null;
    highlightedNodeIds?: ReadonlySet<string>;
  }) => {
    return (
      <div data-testid="region-branch-horizon">
        {branches.map((branch) => {
          const id = `chip-${branch.to_soc}`;
          return (
            <button
              key={id}
              type="button"
              data-testid={`chip-branch-${branch.to_soc}`}
              data-selected={selectedNodeId === id}
              className={highlightedNodeIds?.has(id) ? "branch-flash" : ""}
              onClick={() => onSelectNode(id)}
            >
              {branch.to_title}
            </button>
          );
        })}
      </div>
    );
  },
}));

/**
 * BranchTreeScreen.test.tsx
 *
 * Tests the screen-level orchestration:
 * - Navigation guard: redirects to /my-build if no build in store
 * - Loading state: shows emoji + "Mapping your branches..."
 * - Tree state: renders BranchTreeSVG after API success
 * - Fallback state: renders TreeFallback when tree has no children
 * - Error state: shows error message with Retry + Continue buttons
 * - Retry navigates to /branches
 * - Continue navigates to /save
 * - CTA buttons navigate correctly
 *
 * NOTE: Most tests use real timers because the embedded chat opener and
 * selection debounce use normal async React effects. Scope-binding tests
 * switch to fake timers locally where they need direct debounce control.
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

// Branch fixtures matching makeTreeResponse's children. Soc codes line up
// with `11-300${i}` so click-test selectors stay aligned across the two.
function makeBranches(count: number): CareerBranch[] {
  return Array.from({ length: count }, (_, i) => ({
    from_soc: "13-2051",
    to_soc: `11-300${i}`,
    to_title: `Career ${i}`,
    delta_ern: 5 + i,
    delta_roi: null,
    delta_res: null,
    delta_grw: null,
    delta_hmn: null,
    unlock: null,
    relatedness: i + 1,
    experience_years: null,
    experience_tier: null,
    experience_delta: null,
    related_education_level: "Bachelor's degree",
  }));
}

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
  mockAskGemma.mockReset();
  useBuildStore.setState({ build: makeBuild({ branches: makeBranches(3) }) });
  useProfileStore.setState({ animalEmoji: "\uD83D\uDC3B", animalName: "bear", profileName: "bold bear" });
});

afterEach(() => {
  useBuildStore.setState({ build: null });
  useProfileStore.setState({ animalEmoji: null, animalName: null, profileName: null });
});

describe("BranchTreeScreen", () => {
  // --- Navigation guard ---

  it("redirects to /my-build when build is null", () => {
    useBuildStore.setState({ build: null });
    renderScreen();

    expect(mockNavigate).toHaveBeenCalledWith("/my-build", { replace: true });
  });

  it("does NOT redirect when build is present", () => {
    mockGetTree.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(mockNavigate).not.toHaveBeenCalledWith("/my-build", { replace: true });
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

    await waitFor(
      () => {
        expect(screen.getByTestId("region-branch-horizon")).toBeInTheDocument();
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
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
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
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
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
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
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
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
    mockGetTree.mockRejectedValue(new Error("Network timeout"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText(/Couldn't load the branch tree/)).toBeInTheDocument();
    });
  });

  it("shows generic error message regardless of error type", async () => {
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
    mockGetTree.mockRejectedValue(new Error("Server returned 503"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Failed to load tree")).toBeInTheDocument();
    });
  });

  it("error state has Try Again and Continue buttons", async () => {
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
    mockGetTree.mockRejectedValue(new Error("fail"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Try Again")).toBeInTheDocument();
      expect(screen.getByText(/Continue/)).toBeInTheDocument();
    });
  });

  it("Continue button in error state navigates to /save", async () => {
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
    mockGetTree.mockRejectedValue(new Error("fail"));
    renderScreen();

    await waitFor(() => {
      expect(screen.getByText(/Continue/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Continue/));
    expect(mockNavigate).toHaveBeenCalledWith("/save");
  });

  it("Try Again triggers a re-fetch", async () => {
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
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

  it("calls getTree with the build_id from the store when no cached branches exist", () => {
    useBuildStore.setState({ build: makeBuild({ branches: [] }) });
    mockGetTree.mockReturnValue(new Promise(() => {}));
    renderScreen();

    expect(mockGetTree).toHaveBeenCalledWith("build-test-123", 1);
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

  it("Back to My Build navigates to /my-build", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByText("Back to My Build")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );

    fireEvent.click(screen.getByText("Back to My Build"));
    expect(mockNavigate).toHaveBeenCalledWith("/my-build");
  });

  // Re-baselined for feature-tree-as-map.md §3 layout: tree at
  // tablet:col-span-5 + chat at tablet:col-span-7. The previous
  // tree:col-span-8 + sidebar:col-span-4 split is no longer correct.
  it("wraps tree+chat in PageContainer grid with tree col-span-5 and chat col-span-7 at tablet+", async () => {
    mockGetTree.mockResolvedValue(makeTreeResponse(2));
    mockAskGemma.mockReturnValue(new Promise(() => {})); // never resolves
    renderScreen();

    await waitFor(
      () => {
        expect(screen.getByTestId("page-container")).toBeInTheDocument();
      },
      { timeout: SETTLE_TIMEOUT },
    );

    // Tree column — col-span-5 at tablet+, hidden on mobile.
    const treeCell = document.querySelector("[class*='tablet:col-span-5']");
    expect(treeCell).not.toBeNull();
    expect(treeCell!.className).toContain("hidden");
    expect(treeCell!.className).toContain("tablet:block");

    // Chat column — col-span-7 at tablet+, full-width on mobile.
    const chatCell = document.querySelector("[class*='tablet:col-span-7']");
    expect(chatCell).not.toBeNull();
    expect(chatCell!.className).toContain("col-span-12");
  });

  // ===========================================================================
  // feature-tree-as-map.md §4 — chat-as-guide bidirectional binding tests.
  // ===========================================================================

  // Once we reach the tree state, the embedded chat fires askGemma. Some
  // scope-binding tests need to assert on debounce timing — those use
  // vi.useFakeTimers() locally.

  describe("first load: chat-as-guide auto-opener (P0)", () => {
    it("test_first_load_fires_chat_ask_with_root_branch_scope", async () => {
      mockGetTree.mockResolvedValue(makeTreeResponse(2));
      mockAskGemma.mockResolvedValue({
        response: "Welcome to your branches.",
        tool_calls: [],
      });
      renderScreen();

      // Wait for the screen to enter the tree state and for the embedded
      // chat to auto-fire its opener call.
      await waitFor(
        () => {
          expect(mockAskGemma).toHaveBeenCalled();
        },
        { timeout: SETTLE_TIMEOUT },
      );

      // First call: scope.kind === "branch", target_id === root SOC,
      // build_ids === [build.build_id], history === [].
      const firstCall = mockAskGemma.mock.calls[0]!;
      const scope = firstCall[0];
      const history = firstCall[2];
      expect(scope.kind).toBe("branch");
      expect(scope.target_id).toBe("13-2051"); // root SOC from fixture
      expect(scope.build_ids).toEqual(["build-test-123"]);
      expect(history).toEqual([]);
    });

    it("test_parent_rerender_without_selection_change_does_not_refire", async () => {
      mockGetTree.mockResolvedValue(makeTreeResponse(2));
      mockAskGemma.mockResolvedValue({
        response: "Initial opener.",
        tool_calls: [],
      });

      // Wrap BranchTreeScreen in a parent whose state we can flip. Bumping
      // ``forceTick`` triggers a parent re-render without unmounting
      // BranchTreeScreen — so the screen's effects run only when their
      // (primitive) dependencies actually change.
      let setForceTick: ((n: number) => void) | null = null;
      function Wrapper() {
        const [tick, setTick] = useState(0);
        setForceTick = setTick;
        return (
          <MemoryRouter>
            <div data-tick={tick}>
              <BranchTreeScreen />
            </div>
          </MemoryRouter>
        );
      }
      render(<Wrapper />);

      await waitFor(
        () => {
          expect(mockAskGemma).toHaveBeenCalledTimes(1);
        },
        { timeout: SETTLE_TIMEOUT },
      );

      // Force two parent re-renders without changing selectedNodeId. If
      // chatScope is not memoized on primitive deps OR the opener-fire
      // useEffect depends on object identity, a new chatScope object on
      // each render would re-fire the opener.
      await act(async () => {
        setForceTick!(1);
      });
      await act(async () => {
        setForceTick!(2);
      });
      // Give any async re-firing a chance to land.
      await new Promise((resolve) => setTimeout(resolve, 200));

      expect(mockAskGemma).toHaveBeenCalledTimes(1);
    });

    it("test_gemma_unavailable_renders_fallback_string", async () => {
      mockGetTree.mockResolvedValue(makeTreeResponse(2));
      // The askGemma client surfaces transport failures as thrown
      // errors; the embedded chat's catch path renders the message
      // (current behavior matches the legacy slide-in failure path).
      mockAskGemma.mockRejectedValue(
        new Error("I'm having trouble reaching Gemma right now. Try the question again in a moment."),
      );
      renderScreen();

      await waitFor(
        () => {
          expect(
            screen.getByText(/having trouble reaching Gemma/i),
          ).toBeInTheDocument();
        },
        { timeout: SETTLE_TIMEOUT },
      );
    });
  });

  describe("node click + scope binding (P0)", () => {
    it("test_node_click_updates_scope_and_clears_history", async () => {
      mockGetTree.mockResolvedValue(makeTreeResponse(3));
      mockAskGemma.mockResolvedValue({
        response: "Scoped opener.",
        tool_calls: [],
      });
      renderScreen();

      await waitFor(
        () => {
          expect(mockAskGemma).toHaveBeenCalledTimes(1);
        },
        { timeout: SETTLE_TIMEOUT },
      );

      // First call should be at root.
      expect(mockAskGemma.mock.calls[0]![0].target_id).toBe("13-2051");

      // Click the first child node. Test double exposes a button per
      // node with the production-shape testid.
      const node = await screen.findByTestId("chip-branch-11-3000");
      await act(async () => {
        fireEvent.click(node);
      });

      // After 300ms debounce + opener fire, askGemma fires again with
      // the new target_id (Career 0 in the fixture has soc_code 11-3000).
      await waitFor(
        () => {
          expect(mockAskGemma.mock.calls.length).toBeGreaterThanOrEqual(2);
        },
        { timeout: 2000 },
      );
      const lastCall =
        mockAskGemma.mock.calls[mockAskGemma.mock.calls.length - 1]!;
      // Scope updated to the clicked node.
      expect(lastCall[0].kind).toBe("branch");
      expect(lastCall[0].target_id).toBe("11-3000");
      // History cleared (sessionRef bumped on scope change).
      expect(lastCall[2]).toEqual([]);
    });

    it("test_node_click_debounce_300ms: two rapid selectedNodeId changes produce one askGemma call after debounce", async () => {
      // Use real timers for the tree-fetch settle; once we have the
      // tree state, switch to fake timers to control the debounce.
      mockGetTree.mockResolvedValue(makeTreeResponse(3));
      mockAskGemma.mockResolvedValue({
        response: "Scoped opener.",
        tool_calls: [],
      });
      renderScreen();

      await waitFor(
        () => {
          expect(mockAskGemma).toHaveBeenCalledTimes(1);
        },
        { timeout: SETTLE_TIMEOUT },
      );

      const callsBefore = mockAskGemma.mock.calls.length;

      // Click two different nodes within the 300ms debounce window.
      const node0 = await screen.findByTestId("chip-branch-11-3000");
      const node1 = await screen.findByTestId("chip-branch-11-3001");

      // Rapid double-click — well within 300ms.
      await act(async () => {
        fireEvent.click(node0);
        fireEvent.click(node1);
      });

      // Settle past the debounce window and let any pending opener fire.
      await waitFor(
        () => {
          expect(mockAskGemma.mock.calls.length).toBeGreaterThan(callsBefore);
        },
        { timeout: 2000 },
      );

      // Exactly ONE additional opener fired (debounced). The two rapid
      // clicks collapse into a single askGemma call against the LAST
      // selection.
      const callsAfter = mockAskGemma.mock.calls.length;
      expect(callsAfter - callsBefore).toBe(1);

      // The single call resolves to Career 1 (the LAST click within the
      // debounce window).
      const lastCall = mockAskGemma.mock.calls[callsAfter - 1]!;
      expect(lastCall[0].target_id).toBe("11-3001");
    });

    it("test_stale_opener_dropped_on_rapid_branch_switch", async () => {
      mockGetTree.mockResolvedValue(makeTreeResponse(2));

      // First call: pending forever (mock the slow opener).
      let resolveFirst: (value: { response: string; tool_calls: [] }) => void =
        () => {};
      const firstPromise = new Promise<{
        response: string;
        tool_calls: [];
      }>((resolve) => {
        resolveFirst = resolve;
      });
      mockAskGemma.mockReturnValueOnce(firstPromise);
      // Second call: resolves immediately.
      mockAskGemma.mockResolvedValueOnce({
        response: "New-branch opener.",
        tool_calls: [],
      });

      renderScreen();

      await waitFor(
        () => {
          expect(mockAskGemma).toHaveBeenCalledTimes(1);
        },
        { timeout: SETTLE_TIMEOUT },
      );

      // Click a node → switches scope. The pending root-opener becomes
      // stale; the embedded chat's sessionRef bumps and the stale
      // setHistory write is dropped on resolution.
      const node = await screen.findByTestId("chip-branch-11-3000");
      await act(async () => {
        fireEvent.click(node);
      });

      await waitFor(
        () => {
          expect(mockAskGemma.mock.calls.length).toBeGreaterThanOrEqual(2);
        },
        { timeout: 2000 },
      );

      // New-branch opener has rendered.
      await waitFor(() => {
        expect(screen.getByText("New-branch opener.")).toBeInTheDocument();
      });

      // NOW the stale first call resolves with a "stale-root" response.
      // Because sessionRef bumped on scope change, the stale resolution
      // must be dropped — the prior-branch text must NOT splice into
      // the conversation.
      await act(async () => {
        resolveFirst({
          response: "Stale root opener.",
          tool_calls: [],
        });
      });

      // Give the async resolution a chance to land.
      await new Promise((resolve) => setTimeout(resolve, 100));

      // The stale text never renders — only the current-branch opener.
      expect(screen.queryByText("Stale root opener.")).toBeNull();
      expect(screen.getByText("New-branch opener.")).toBeInTheDocument();
    });
  });

  describe("branch flash (P0)", () => {
    it("test_branch_name_in_response_flashes_node: response containing a node title sets highlightedNodeId", async () => {
      mockGetTree.mockResolvedValue(makeTreeResponse(2));
      mockAskGemma.mockResolvedValue({
        // Response names "Career 0" verbatim — should fire highlight on
        // its node id.
        response:
          "From here, the Career 0 path keeps you closest to your numbers focus. Worth a closer look.",
        tool_calls: [],
      });
      renderScreen();

      await waitFor(
        () => {
          expect(
            screen.getByText("From here,", { exact: false }),
          ).toBeInTheDocument();
        },
        { timeout: SETTLE_TIMEOUT },
      );

      // Wait for BranchHighlightDriver to fire and the screen to apply
      // the className to the matching React Flow node.
      await waitFor(
        () => {
          const flashing = document.querySelector(".branch-flash");
          expect(flashing).not.toBeNull();
        },
        { timeout: 1500 },
      );
    });
  });

  describe("fallback (P0)", () => {
  it("test_fallback_career_renders_chat_at_root: zero-children tree still mounts chat at root SOC", async () => {
      useBuildStore.setState({ build: makeBuild({ branches: [] }) });
      mockGetTree.mockResolvedValue(makeTreeResponse(0));
      mockAskGemma.mockResolvedValue({
        response: "This is a specialized career — what would you like to know?",
        tool_calls: [],
      });
      renderScreen();

      await waitFor(
        () => {
          expect(screen.getByTestId("region-fallback")).toBeInTheDocument();
        },
        { timeout: SETTLE_TIMEOUT },
      );

      // Chat fires at the root SOC even in fallback.
      await waitFor(
        () => {
          expect(mockAskGemma).toHaveBeenCalled();
        },
        { timeout: 2000 },
      );
      const firstCall = mockAskGemma.mock.calls[0]!;
      expect(firstCall[0].kind).toBe("branch");
      expect(firstCall[0].target_id).toBe("13-2051");
    });
  });
});
