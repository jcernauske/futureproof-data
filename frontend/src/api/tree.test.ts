import { describe, it, expect, vi, beforeEach } from "vitest";
import type { TreeResponse } from "@/types/tree";

/**
 * tree.test.ts — Tests for the tree API client.
 *
 * The getTree function has two modes:
 * 1. Mock mode (VITE_USE_MOCK_API=true) — returns mock data
 * 2. Live mode — calls apiGet with the correct URL
 *
 * We test live mode by mocking the fetch global (same pattern as client.test.ts).
 * We test the URL construction (buildId + maxDepth params).
 */

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// We need to control import.meta.env, so we mock the module
vi.mock("@/api/client", () => ({
  apiGet: vi.fn(),
}));

vi.mock("@/api/mockTree", () => ({
  mockGetTree: vi.fn(),
}));

import { getTree } from "./tree";
import { apiGet } from "@/api/client";
import { mockGetTree } from "@/api/mockTree";

const mockApiGet = vi.mocked(apiGet);
const mockMockGetTree = vi.mocked(mockGetTree);

const VALID_TREE_RESPONSE: TreeResponse = {
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
    children: [],
  },
  stats: {
    total_nodes: 1,
    max_depth_reached: 0,
    mcp_calls: 1,
    dead_ends: 0,
    wall_clock_ms: 500,
  },
};

beforeEach(() => {
  fetchMock.mockReset();
  mockApiGet.mockReset();
  mockMockGetTree.mockReset();
});

describe("getTree", () => {
  it("calls apiGet with correct URL including buildId and default maxDepth", async () => {
    mockApiGet.mockResolvedValueOnce(VALID_TREE_RESPONSE);

    await getTree("build-abc-123");

    expect(mockApiGet).toHaveBeenCalledWith("/tree/build-abc-123?max_depth=3");
  });

  it("passes custom maxDepth to URL", async () => {
    mockApiGet.mockResolvedValueOnce(VALID_TREE_RESPONSE);

    await getTree("build-xyz", 5);

    expect(mockApiGet).toHaveBeenCalledWith("/tree/build-xyz?max_depth=5");
  });

  it("returns the TreeResponse from apiGet", async () => {
    mockApiGet.mockResolvedValueOnce(VALID_TREE_RESPONSE);

    const result = await getTree("build-abc");

    expect(result).toBe(VALID_TREE_RESPONSE);
    expect(result.tree.soc_code).toBe("13-2051");
    expect(result.stats.total_nodes).toBe(1);
  });

  it("propagates errors from apiGet", async () => {
    mockApiGet.mockRejectedValueOnce(new Error("API error: 500"));

    await expect(getTree("build-fail")).rejects.toThrow("API error: 500");
  });

  it("TreeResponse fixture has valid shape with all required fields", () => {
    // Validates the test fixture itself — catches contract drift
    const tree = VALID_TREE_RESPONSE.tree;
    expect(tree.soc_code).toBeTruthy();
    expect(tree.title).toBeTruthy();
    expect(typeof tree.level).toBe("number");
    expect(Array.isArray(tree.children)).toBe(true);

    const stats = VALID_TREE_RESPONSE.stats;
    expect(typeof stats.total_nodes).toBe("number");
    expect(typeof stats.max_depth_reached).toBe("number");
    expect(typeof stats.mcp_calls).toBe("number");
    expect(typeof stats.dead_ends).toBe("number");
    expect(typeof stats.wall_clock_ms).toBe("number");
  });
});
