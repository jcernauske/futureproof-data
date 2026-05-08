import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { FutureScreen } from "./FutureScreen";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import type { TreeResponse, TreeNode } from "@/types/tree";
import type { Build } from "@/types/build";

const mockAskGemma = vi.fn();
// askGemmaStream — happy-path SSE-equivalent default. Auto-opener
// fires on mount + on every selectedRef change; both paths now go
// through askGemmaStream. Per Authorized Test Modifications (§4 / C7).
const mockAskGemmaStream = vi.fn().mockImplementation(
  async (..._args: unknown[]) => {
    const final = { type: "final_text" as const, response: "ok" };
    const done = { type: "done" as const };
    const onEvent = _args[3] as ((e: unknown) => void) | undefined;
    if (onEvent) {
      onEvent(final);
      onEvent(done);
    }
    return { response: "ok", events: [final, done] };
  },
);
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    askGemma: (...args: unknown[]) => mockAskGemma(...args),
    askGemmaStream: (...args: Parameters<typeof import("@/api/menu").askGemmaStream>) =>
      mockAskGemmaStream(...args),
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
      wage_p10: null,
      wage_p25: null,
      wage_p75: null,
      wage_p90: null,
      earnings_1yr_median: 45000,
      earnings_1yr_p25: 35000,
      earnings_1yr_p75: 55000,
      debt_median: 25000,
      debt_to_earnings_annual: 0.56,
      education_level_name: "Bachelor's degree",
      growth_category: "Faster than average",
      work_experience_code: null,
      net_price_annual: null,
      cost_of_attendance_annual: null,
      published_cost_4yr: null,
      modeled_total_debt: null,
      debt_median_reference: null,
      institution_control: null,
      tuition_in_state: null,
      tuition_out_of_state: null,
      is_out_of_state: false,
      room_board_on_campus: null,
      stats: { ern: 72, roi: 68, res: 45, grw: 61, aura: 38 },
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
      aura: 38,
      median_wage: 95570,
      education: "Bachelor's degree",
      experience_years: null,
      experience_tier: null,
      relatedness: null,
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
          aura: 40,
          median_wage: 140000,
          education: "Bachelor's degree",
          experience_years: null,
          experience_tier: null,
          relatedness: null,
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
          aura: 50,
          median_wage: 75000,
          education: "Bachelor's degree",
          experience_years: null,
          experience_tier: null,
          relatedness: null,
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

describe("FutureScreen — breadcrumb persistence (T1.4 regression)", () => {
  // Regression for staff-engineer Finding #1 (§8). Filter hides the
  // selected node → selectedNodeId resets to null via the cascade.
  // Snapshot must NOT wipe — the breadcrumb is what tells the student
  // "your selection is still here, the filter is just hiding it."
  it("breadcrumb persists across a filter that hides the selected node", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedEducationTreeFixture());

    renderScreen();

    // Wait for tree to render then click a Master's-required L1.
    await waitFor(() => {
      expect(
        screen.getAllByTestId("tree-node-13-1161").length,
      ).toBeGreaterThan(0);
    });

    await act(async () => {
      const node = screen.getAllByTestId("tree-node-13-1161")[0];
      if (!node) throw new Error("expected target tree node");
      node.click();
    });

    // Breadcrumb should now show two segments (root + selected).
    await waitFor(() => {
      const segments = screen.queryAllByTestId(/breadcrumb-\d+-/);
      expect(segments.length).toBeGreaterThanOrEqual(2);
    });

    // Apply a filter that excludes the selected branch.
    await act(async () => {
      const chip = screen.getAllByTestId("filter-chip-bachelors")[0];
      if (!chip) throw new Error("expected bachelors filter chip");
      chip.click();
    });

    // Selected branch is now filter-hidden, but the breadcrumb still
    // renders and the leaf segment is in ghost state.
    await waitFor(() => {
      const segments = screen.queryAllByTestId(/breadcrumb-\d+-/);
      expect(segments.length).toBeGreaterThanOrEqual(2);
    });
    const ghostSegments = screen
      .queryAllByTestId(/breadcrumb-\d+-/)
      .filter((el) => el.getAttribute("data-hidden") === "true");
    expect(ghostSegments.length).toBeGreaterThan(0);
  });
});

// Local fixture for the breadcrumb test — mirrors the description-level
// makeMixedEducationTree() shape but available outside its closure.
function makeMixedEducationTreeFixture(): TreeResponse {
  return {
    tree: {
      soc_code: "13-2051",
      title: "Financial Analyst",
      level: 0,
      ern: 72,
      roi: 68,
      res: 45,
      grw: 61,
      aura: 38,
      median_wage: 95570,
      education: "Bachelor's degree",
      experience_years: null,
      experience_tier: null,
      relatedness: null,
      boss_ai: "draw",
      boss_loans: "win",
      boss_market: "win",
      boss_burnout: "lose",
      boss_ceiling: "draw",
      children: [
        {
          soc_code: "13-1161",
          title: "Market Research Analyst",
          level: 1,
          ern: 70,
          roi: 65,
          res: 55,
          grw: 75,
          aura: 50,
          median_wage: 75000,
          education: "Master's degree",
          experience_years: null,
          experience_tier: null,
          relatedness: null,
          boss_ai: "lose",
          boss_loans: "win",
          boss_market: "win",
          boss_burnout: "draw",
          boss_ceiling: "draw",
          children: [],
        },
        // Sibling Bachelor's L1 so the Bachelor's filter chip is
        // available — without it the new "available chips only" logic
        // would hide the chip and the click below would fail.
        {
          soc_code: "11-3031",
          title: "Financial Manager",
          level: 1,
          ern: 70,
          roi: 65,
          res: 50,
          grw: 60,
          aura: 45,
          median_wage: 140000,
          education: "Bachelor's degree",
          experience_years: null,
          experience_tier: null,
          relatedness: null,
          boss_ai: "draw",
          boss_loans: "win",
          boss_market: "win",
          boss_burnout: "draw",
          boss_ceiling: "win",
          children: [],
        },
      ],
    },
    stats: {
      total_nodes: 3,
      max_depth_reached: 1,
      mcp_calls: 2,
      dead_ends: 0,
      wall_clock_ms: 1000,
    },
  };
}

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
        aura: 38,
        median_wage: 95570,
        education: "Bachelor's degree",
        experience_years: null,
        experience_tier: null,
        relatedness: null,
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
            aura: 40,
            median_wage: 140000,
            education: "Bachelor's degree",
            experience_years: null,
            experience_tier: null,
            relatedness: null,
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
            aura: 50,
            median_wage: 75000,
            education: "Master's degree",
            experience_years: null,
            experience_tier: null,
            relatedness: null,
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
            aura: 60,
            median_wage: 145000,
            education: "Doctoral or professional degree",
            experience_years: null,
            experience_tier: null,
            relatedness: null,
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

  it("renders the empty-state overlay when a filter combo hides every L1 branch", async () => {
    // Combined Master's edu + Higher-pay stat filters are individually
    // available against the mixed fixture (Bachelor's L1, Master's L1,
    // Doctoral L1 — Master's is $75k, others top $140k). The AND
    // intersection is empty: no L1 is BOTH Master's AND higher pay.
    // The new "available chips only" logic still renders both chips
    // (each individually has a match); the empty-state surfaces from
    // their combination.
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedEducationTree());

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
    await act(async () => {
      const earnings = screen.getAllByTestId("stat-filter-chip-earnings")[0];
      if (!earnings) throw new Error("expected earnings filter chip");
      earnings.click();
    });

    // Master's L1 fails earnings ($75k < $95k) AND Bachelor's/Doctoral
    // L1s fail edu → no L1 passes both → empty state surfaces.
    await waitFor(() => {
      expect(
        screen.getAllByTestId("filter-empty-state").length,
      ).toBeGreaterThan(0);
    });
    // Clear button restores the unfiltered tree.
    await act(async () => {
      const clear = screen.getAllByTestId("btn-clear-all-filters")[0];
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

describe("FutureScreen — stat filters", () => {
  function makeMixedStatsTree(): TreeResponse {
    return {
      tree: {
        soc_code: "13-2051",
        title: "Financial Analyst",
        level: 0,
        ern: 72,
        roi: 68,
        res: 5,
        grw: 6,
        aura: 38,
        median_wage: 95570,
        education: "Bachelor's degree",
        experience_years: null,
        experience_tier: null,
        relatedness: null,
        boss_ai: "draw",
        boss_loans: "win",
        boss_market: "win",
        boss_burnout: "lose",
        boss_ceiling: "draw",
        children: [
          {
            // Higher earnings only.
            soc_code: "11-3031",
            title: "Financial Manager",
            level: 1,
            ern: null,
            roi: 70,
            res: 5,
            grw: 6,
            aura: 40,
            median_wage: 140000,
            education: "Bachelor's degree",
            experience_years: null,
            experience_tier: null,
            relatedness: null,
            boss_ai: "win",
            boss_loans: "win",
            boss_market: "win",
            boss_burnout: "lose",
            boss_ceiling: "win",
            children: [],
          },
          {
            // Higher RES + GRW only, same wage.
            soc_code: "15-1252",
            title: "Software Developer",
            level: 1,
            ern: null,
            roi: 65,
            res: 8,
            grw: 9,
            aura: 45,
            median_wage: 95570,
            education: "Bachelor's degree",
            experience_years: null,
            experience_tier: null,
            relatedness: null,
            boss_ai: "draw",
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

  it("renders all 3 stat filter chips above the tree", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedStatsTree());

    renderScreen();

    await waitFor(() => {
      expect(
        screen.getAllByTestId("stat-filter-chip-earnings").length,
      ).toBeGreaterThan(0);
    });
    expect(
      screen.getAllByTestId("stat-filter-chip-ai_resilient").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByTestId("stat-filter-chip-growth").length,
    ).toBeGreaterThan(0);
  });

  it("higher-earnings filter hides branches with same/lower wage", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedStatsTree());

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("tree-node-11-3031").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByTestId("tree-node-15-1252").length).toBeGreaterThan(0);

    await act(async () => {
      const chip = screen.getAllByTestId("stat-filter-chip-earnings")[0];
      if (!chip) throw new Error("expected earnings filter chip");
      chip.click();
    });

    expect(
      screen.getAllByTestId("tree-node-11-3031").length,
    ).toBeGreaterThan(0);
    expect(screen.queryByTestId("tree-node-15-1252")).toBeNull();
  });

  it("AND semantic: combining earnings + growth filters out branches that improve only one", async () => {
    useBuildStore.setState({ build: makeBuild() });
    mockGetTree.mockResolvedValue(makeMixedStatsTree());

    renderScreen();

    await waitFor(() => {
      expect(screen.getAllByTestId("tree-node-11-3031").length).toBeGreaterThan(0);
    });

    // 11-3031 improves earnings only; 15-1252 improves growth only.
    // Combining both filters → neither matches → empty state appears.
    await act(async () => {
      const earnings = screen.getAllByTestId("stat-filter-chip-earnings")[0];
      if (!earnings) throw new Error("expected earnings filter chip");
      earnings.click();
    });
    await act(async () => {
      const growth = screen.getAllByTestId("stat-filter-chip-growth")[0];
      if (!growth) throw new Error("expected growth filter chip");
      growth.click();
    });

    expect(screen.queryByTestId("tree-node-11-3031")).toBeNull();
    expect(screen.queryByTestId("tree-node-15-1252")).toBeNull();
    await waitFor(() => {
      expect(
        screen.getAllByTestId("filter-empty-state").length,
      ).toBeGreaterThan(0);
    });
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
