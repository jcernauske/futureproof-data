import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { FutureScreen } from "./FutureScreen";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { TreeResponse, TreeNode } from "@/types/tree";
import type { Build } from "@/types/build";

const mockAskGemma = vi.fn();
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    askGemma: (...args: unknown[]) => mockAskGemma(...args),
  };
});

// React Flow needs ResizeObserver and getBoundingClientRect — mock the
// tree component so the screen test stays focused on orchestration
// (route guard, fetch, scope binding, sheet behavior).
vi.mock("@/components/tree/BranchTreeFlow", () => ({
  BranchTreeFlow: ({
    tree,
    direction,
    onSelectNode,
    selectedNodeId,
    highlightedNodeIds,
  }: {
    tree: TreeNode;
    direction: "LR" | "TB";
    onSelectNode: (id: string | null) => void;
    selectedNodeId: string | null;
    highlightedNodeIds?: ReadonlySet<string>;
  }) => (
    <div data-testid="region-future-tree" data-direction={direction}>
      {tree.children.map((c, idx) => {
        const id = `career-${c.soc_code}-${idx}`;
        return (
          <button
            key={id}
            type="button"
            data-testid={`tree-node-${c.soc_code}`}
            data-selected={selectedNodeId === id}
            className={highlightedNodeIds?.has(id) ? "flow-node-flash" : ""}
            onClick={() => onSelectNode(id)}
          >
            {c.title}
          </button>
        );
      })}
    </div>
  ),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockGetTree = vi.fn();
vi.mock("@/api/tree", () => ({
  getTree: (...args: unknown[]) => mockGetTree(...args),
}));

function makeBuild(): Build {
  return {
    build_id: "build-test-future",
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
      is_out_of_state: false,
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
  } as Build;
}

function makeTreeResponse(): TreeResponse {
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
      children: [
        {
          soc_code: "11-3031",
          title: "Financial Manager",
          level: 1,
          ern: 85,
          roi: 70,
          res: 50,
          grw: 65,
          hmn: 40,
          median_wage: 140000,
          education: "Bachelor's degree",
          boss_ai: "win",
          boss_loans: "win",
          boss_market: "win",
          boss_burnout: "lose",
          boss_ceiling: "win",
          children: [],
        },
        {
          soc_code: "13-1161",
          title: "Market Research Analyst",
          level: 1,
          ern: 70,
          roi: 65,
          res: 55,
          grw: 75,
          hmn: 50,
          median_wage: 75000,
          education: "Bachelor's degree",
          boss_ai: "lose",
          boss_loans: "win",
          boss_market: "win",
          boss_burnout: "draw",
          boss_ceiling: "draw",
          children: [],
        },
      ],
    },
    stats: {
      total_nodes: 3,
      max_depth_reached: 1,
      mcp_calls: 2,
      dead_ends: 0,
      wall_clock_ms: 1500,
    },
  };
}

function renderScreen() {
  return render(
    <MemoryRouter>
      <FutureScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockGetTree.mockReset();
  mockAskGemma.mockReset();
  // Default opener resolves once with a benign response.
  mockAskGemma.mockResolvedValue({
    text: "Here's a quick orientation.",
    history: [],
    tools_called: [],
  });
  useBuildStore.setState({ build: null });
  useProfileStore.setState({ animalEmoji: "🐻" });
});

describe("FutureScreen — navigation guard", () => {
  it("redirects to /my-build when no build in store", () => {
    renderScreen();
    expect(mockNavigate).toHaveBeenCalledWith("/my-build", { replace: true });
  });
});

describe("FutureScreen — happy path", () => {
  // The screen renders both the desktop (`hidden tablet:block`) and the
  // mobile (`tablet:hidden`) layouts; jsdom doesn't apply Tailwind
  // breakpoint visibility, so both copies live in the DOM. Asserting via
  // `getAllByTestId` keeps the test honest about that.
  it("fetches tree at depth=2 and renders the tree region after success", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("region-future-tree").length).toBeGreaterThan(0);
    });
    expect(mockGetTree).toHaveBeenCalledWith("build-test-future", 2);
  });

  it("renders both tree-node buttons from the tree response", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("tree-node-11-3031").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByTestId("tree-node-13-1161").length).toBeGreaterThan(0);
  });
});

describe("FutureScreen — mobile bottom sheet", () => {
  it("renders the bottom sheet handle in the document", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(screen.getByTestId("future-chat-sheet")).toBeInTheDocument();
    });
    expect(screen.getByTestId("future-chat-sheet-handle")).toBeInTheDocument();
  });

  it("starts collapsed (no data-open attribute)", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(screen.getByTestId("future-chat-sheet")).toBeInTheDocument();
    });
    const sheet = screen.getByTestId("future-chat-sheet");
    expect(sheet.getAttribute("data-open")).toBeNull();
  });

  it("expands the sheet when a tree node is selected", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("tree-node-11-3031").length).toBeGreaterThan(0);
    });

    await act(async () => {
      // Click the first instance — both desktop + mobile render the
      // same tree-node button; clicking either drives onSelectNode.
      const node = screen.getAllByTestId("tree-node-11-3031")[0];
      if (!node) throw new Error("expected at least one tree-node button");
      node.click();
    });

    const sheet = screen.getByTestId("future-chat-sheet");
    expect(sheet.getAttribute("data-open")).toBe("true");
  });
});

describe("FutureScreen — selected-node card", () => {
  it("renders the SelectedNodeCard anchored at the root by default", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("selected-node-card").length).toBeGreaterThan(
        0,
      );
    });
    // Default anchor is the root career SOC (Financial Analyst, 13-2051).
    const cards = screen.getAllByTestId("selected-node-card");
    expect(cards[0]?.getAttribute("data-soc")).toBe("13-2051");
  });

  it("swaps the card to the selected node's SOC after a click", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("tree-node-11-3031").length).toBeGreaterThan(
        0,
      );
    });

    await act(async () => {
      const node = screen.getAllByTestId("tree-node-11-3031")[0];
      if (!node) throw new Error("expected at least one tree-node button");
      node.click();
    });

    // The screen debounces selection (NODE_DEBOUNCE_MS = 300) before the
    // card swaps. Wait for the swap rather than asserting synchronously.
    await waitFor(
      () => {
        const cards = screen.getAllByTestId("selected-node-card");
        expect(cards.length).toBeGreaterThan(0);
        for (const card of cards) {
          expect(card.getAttribute("data-soc")).toBe("11-3031");
        }
      },
      { timeout: 1000 },
    );
  });
});

describe("FutureScreen — education filters", () => {
  function makeMixedEducationTree(): TreeResponse {
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
        children: [
          {
            soc_code: "11-3031",
            title: "Financial Manager",
            level: 1,
            ern: 85,
            roi: 70,
            res: 50,
            grw: 65,
            hmn: 40,
            median_wage: 140000,
            education: "Bachelor's degree",
            boss_ai: "win",
            boss_loans: "win",
            boss_market: "win",
            boss_burnout: "lose",
            boss_ceiling: "win",
            children: [],
          },
          {
            soc_code: "13-1161",
            title: "Market Research Analyst",
            level: 1,
            ern: 70,
            roi: 65,
            res: 55,
            grw: 75,
            hmn: 50,
            median_wage: 75000,
            education: "Master's degree",
            boss_ai: "lose",
            boss_loans: "win",
            boss_market: "win",
            boss_burnout: "draw",
            boss_ceiling: "draw",
            children: [],
          },
          {
            soc_code: "23-1011",
            title: "Lawyer",
            level: 1,
            ern: 90,
            roi: 60,
            res: 70,
            grw: 60,
            hmn: 60,
            median_wage: 145000,
            education: "Doctoral or professional degree",
            boss_ai: "win",
            boss_loans: "draw",
            boss_market: "draw",
            boss_burnout: "lose",
            boss_ceiling: "win",
            children: [],
          },
        ],
      },
      stats: {
        total_nodes: 4,
        max_depth_reached: 1,
        mcp_calls: 3,
        dead_ends: 0,
        wall_clock_ms: 1500,
      },
    };
  }

  it("renders all 3 filter chips above the tree", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedEducationTree());

    renderScreen();

    await waitFor(() => {
      expect(
        screen.getAllByTestId("filter-chip-bachelors").length,
      ).toBeGreaterThan(0);
    });
    expect(
      screen.getAllByTestId("filter-chip-masters").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByTestId("filter-chip-doctoral").length,
    ).toBeGreaterThan(0);
  });

  it("toggling Master's filter hides Bachelor's and Doctoral nodes", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedEducationTree());

    renderScreen();

    // Wait for all 3 nodes to render initially.
    await waitFor(() => {
      expect(
        screen.getAllByTestId("tree-node-13-1161").length,
      ).toBeGreaterThan(0);
    });
    expect(screen.getAllByTestId("tree-node-11-3031").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("tree-node-23-1011").length).toBeGreaterThan(0);

    // Toggle Master's. Click the desktop chip — both desktop + mobile
    // copies live in the DOM but only one needs to fire onToggle.
    await act(async () => {
      const chip = screen.getAllByTestId("filter-chip-masters")[0];
      if (!chip) throw new Error("expected master's filter chip");
      chip.click();
    });

    // Only the Master's-required node remains in the tree.
    expect(screen.queryByTestId("tree-node-11-3031")).toBeNull();
    expect(screen.queryByTestId("tree-node-23-1011")).toBeNull();
    expect(
      screen.getAllByTestId("tree-node-13-1161").length,
    ).toBeGreaterThan(0);
  });

  it("renders the empty-state overlay when a filter hides every L1 branch", async () => {
    useBuildStore.setState({ build: makeBuild() });
    // Mixed tree contains zero Doctoral L1s? Actually the fixture has
    // one (23-1011 Lawyer). Use a Bachelor's-only fixture so toggling
    // Master's leaves an empty tree.
    mockGetTree.mockResolvedValue(makeTreeResponse());

    renderScreen();

    await waitFor(() => {
      expect(
        screen.getAllByTestId("tree-node-11-3031").length,
      ).toBeGreaterThan(0);
    });

    await act(async () => {
      const masters = screen.getAllByTestId("filter-chip-masters")[0];
      if (!masters) throw new Error("expected master's filter chip");
      masters.click();
    });

    // No Bachelor's branches match → empty state surfaces.
    await waitFor(() => {
      expect(
        screen.getAllByTestId("filter-empty-state").length,
      ).toBeGreaterThan(0);
    });
    // Clear button restores the unfiltered tree.
    await act(async () => {
      const clear = screen.getAllByTestId("btn-clear-education-filters")[0];
      if (!clear) throw new Error("expected clear filters button");
      clear.click();
    });
    await waitFor(() => {
      expect(screen.queryByTestId("filter-empty-state")).toBeNull();
    });
    expect(
      screen.getAllByTestId("tree-node-11-3031").length,
    ).toBeGreaterThan(0);
  });

  it("filters OR together (multi-select)", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedEducationTree());

    renderScreen();

    await waitFor(() => {
      expect(
        screen.getAllByTestId("tree-node-13-1161").length,
      ).toBeGreaterThan(0);
    });

    // Toggle Master's + Doctoral.
    await act(async () => {
      const masters = screen.getAllByTestId("filter-chip-masters")[0];
      if (!masters) throw new Error("expected master's filter chip");
      masters.click();
    });
    await act(async () => {
      const doctoral = screen.getAllByTestId("filter-chip-doctoral")[0];
      if (!doctoral) throw new Error("expected doctoral filter chip");
      doctoral.click();
    });

    // Bachelor's-only node hidden; Master's + Doctoral both visible.
    expect(screen.queryByTestId("tree-node-11-3031")).toBeNull();
    expect(
      screen.getAllByTestId("tree-node-13-1161").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByTestId("tree-node-23-1011").length,
    ).toBeGreaterThan(0);
  });
});

describe("FutureScreen — error state", () => {
  it("shows error UI when tree fetch fails", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockRejectedValue(new Error("boom"));

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText(/Couldn't load/i)).toBeInTheDocument();
    });
  });
});
