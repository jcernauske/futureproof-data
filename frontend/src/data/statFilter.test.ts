import { describe, it, expect } from "vitest";
import {
  filterTreeByStats,
  nodePassesAllStatFilters,
  nodePassesStatFilter,
  type StatFilter,
} from "./statFilter";
import type { TreeNode } from "@/types/tree";

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    soc_code: "13-0000",
    title: "Test",
    level: 1,
    ern: null,
    roi: null,
    res: null,
    grw: null,
    hmn: null,
    median_wage: null,
    education: null,
    experience_years: null,
    experience_tier: null,
    relatedness: null,
    boss_ai: null,
    boss_loans: null,
    boss_market: null,
    boss_burnout: null,
    boss_ceiling: null,
    children: [],
    ...overrides,
  };
}

describe("nodePassesStatFilter", () => {
  const root = makeNode({
    soc_code: "13-2051",
    median_wage: 95570,
    res: 5,
    grw: 6,
  });

  it("earnings: strictly greater median_wage passes", () => {
    expect(
      nodePassesStatFilter(makeNode({ median_wage: 100000 }), root, "earnings"),
    ).toBe(true);
  });

  it("earnings: equal median_wage fails (strict comparison)", () => {
    expect(
      nodePassesStatFilter(makeNode({ median_wage: 95570 }), root, "earnings"),
    ).toBe(false);
  });

  it("earnings: lower median_wage fails", () => {
    expect(
      nodePassesStatFilter(makeNode({ median_wage: 50000 }), root, "earnings"),
    ).toBe(false);
  });

  it("earnings: null on either side fails (no claim without data)", () => {
    expect(
      nodePassesStatFilter(makeNode({ median_wage: null }), root, "earnings"),
    ).toBe(false);
    const nullRoot = makeNode({ median_wage: null });
    expect(
      nodePassesStatFilter(makeNode({ median_wage: 100000 }), nullRoot, "earnings"),
    ).toBe(false);
  });

  it("ai_resilient: strictly greater RES passes", () => {
    expect(
      nodePassesStatFilter(makeNode({ res: 8 }), root, "ai_resilient"),
    ).toBe(true);
    expect(
      nodePassesStatFilter(makeNode({ res: 5 }), root, "ai_resilient"),
    ).toBe(false);
    expect(
      nodePassesStatFilter(makeNode({ res: 3 }), root, "ai_resilient"),
    ).toBe(false);
  });

  it("growth: strictly greater GRW passes", () => {
    expect(nodePassesStatFilter(makeNode({ grw: 9 }), root, "growth")).toBe(true);
    expect(nodePassesStatFilter(makeNode({ grw: 6 }), root, "growth")).toBe(false);
    expect(nodePassesStatFilter(makeNode({ grw: 4 }), root, "growth")).toBe(false);
  });
});

describe("nodePassesAllStatFilters", () => {
  const root = makeNode({ median_wage: 95570, res: 5, grw: 6 });

  it("returns true when filter set is empty", () => {
    expect(nodePassesAllStatFilters(makeNode(), root, new Set())).toBe(true);
  });

  it("AND semantic: all filters must pass", () => {
    const node = makeNode({ median_wage: 100000, res: 8, grw: 4 });
    // Earnings + AI both improve → passes both alone
    expect(
      nodePassesAllStatFilters(node, root, new Set<StatFilter>(["earnings"])),
    ).toBe(true);
    expect(
      nodePassesAllStatFilters(node, root, new Set<StatFilter>(["ai_resilient"])),
    ).toBe(true);
    // Growth fails (4 < 6) — fails when growth is in the filter set
    expect(
      nodePassesAllStatFilters(node, root, new Set<StatFilter>(["growth"])),
    ).toBe(false);
    // Combined (earnings + growth) — fails because growth fails
    expect(
      nodePassesAllStatFilters(
        node,
        root,
        new Set<StatFilter>(["earnings", "growth"]),
      ),
    ).toBe(false);
    // All three — fails for the same reason
    expect(
      nodePassesAllStatFilters(
        node,
        root,
        new Set<StatFilter>(["earnings", "ai_resilient", "growth"]),
      ),
    ).toBe(false);
  });

  it("strict node passes all three when truly improved", () => {
    const node = makeNode({ median_wage: 120000, res: 8, grw: 9 });
    expect(
      nodePassesAllStatFilters(
        node,
        root,
        new Set<StatFilter>(["earnings", "ai_resilient", "growth"]),
      ),
    ).toBe(true);
  });
});

describe("filterTreeByStats", () => {
  function makeTree(): TreeNode {
    return makeNode({
      soc_code: "13-2051",
      title: "Financial Analyst",
      median_wage: 95570,
      res: 5,
      grw: 6,
      children: [
        // Higher earnings + same RES + same GRW
        makeNode({
          soc_code: "11-3031",
          title: "Financial Manager",
          median_wage: 140000,
          res: 5,
          grw: 6,
        }),
        // Same earnings + higher RES + lower GRW
        makeNode({
          soc_code: "13-1161",
          title: "Market Research Analyst",
          median_wage: 95570,
          res: 8,
          grw: 4,
        }),
        // Higher all three
        makeNode({
          soc_code: "11-1011",
          title: "Chief Executive",
          median_wage: 200000,
          res: 9,
          grw: 8,
        }),
      ],
    });
  }

  it("returns tree unchanged when filters empty", () => {
    const tree = makeTree();
    const out = filterTreeByStats(tree, new Set());
    expect(out).toBe(tree);
  });

  it("preserves the root regardless of filter", () => {
    const out = filterTreeByStats(
      makeTree(),
      new Set<StatFilter>(["earnings"]),
    );
    expect(out.soc_code).toBe("13-2051");
  });

  it("earnings filter keeps only branches with strictly higher wage", () => {
    const out = filterTreeByStats(
      makeTree(),
      new Set<StatFilter>(["earnings"]),
    );
    expect(out.children.map((c) => c.soc_code).sort()).toEqual([
      "11-1011",
      "11-3031",
    ]);
  });

  it("AND multi-select: earnings + growth keeps only branches improving both", () => {
    const out = filterTreeByStats(
      makeTree(),
      new Set<StatFilter>(["earnings", "growth"]),
    );
    expect(out.children.map((c) => c.soc_code)).toEqual(["11-1011"]);
  });

  it("all three filters: only the strictly-better-everywhere branch remains", () => {
    const out = filterTreeByStats(
      makeTree(),
      new Set<StatFilter>(["earnings", "ai_resilient", "growth"]),
    );
    expect(out.children.map((c) => c.soc_code)).toEqual(["11-1011"]);
  });

  it("filter applies recursively to L2 endpoints, not just L1 branches", () => {
    // L1 passes (Sales Mgrs > root wage); L2 children below root wage
    // should be dropped from the surfaced L1's children list.
    // Repro of the on-screen bug: Advertising → Sales Managers $138k
    // (passes) → Customer Service Reps $42k / Brokerage Clerks $62k
    // (fail) — the L2s were rendering anyway pre-fix.
    const tree = makeNode({
      soc_code: "11-2011",
      median_wage: 126960,
      children: [
        makeNode({
          soc_code: "11-2022",
          title: "Sales Managers",
          median_wage: 138060,
          children: [
            makeNode({
              soc_code: "43-4051",
              title: "Customer Service Representatives",
              median_wage: 42830,
            }),
            makeNode({
              soc_code: "43-4011",
              title: "Brokerage Clerks",
              median_wage: 62940,
            }),
            makeNode({
              soc_code: "11-3061",
              title: "Purchasing Managers",
              median_wage: 145000,
            }),
          ],
        }),
      ],
    });
    const out = filterTreeByStats(tree, new Set<StatFilter>(["earnings"]));
    expect(out.children).toHaveLength(1);
    expect(out.children[0]?.soc_code).toBe("11-2022");
    // Only the L2 with wage > root.wage survives.
    expect(out.children[0]?.children.map((c) => c.soc_code)).toEqual([
      "11-3061",
    ]);
  });

  it("L1 with zero passing L2s is retained (its own criterion is met)", () => {
    const tree = makeNode({
      soc_code: "11-2011",
      median_wage: 126960,
      children: [
        makeNode({
          soc_code: "11-2022",
          title: "Sales Managers",
          median_wage: 138060,
          children: [
            makeNode({ soc_code: "43-4051", median_wage: 42830 }),
            makeNode({ soc_code: "43-4011", median_wage: 62940 }),
          ],
        }),
      ],
    });
    const out = filterTreeByStats(tree, new Set<StatFilter>(["earnings"]));
    expect(out.children).toHaveLength(1);
    expect(out.children[0]?.children).toEqual([]);
  });

  // Path-permissive recursion regression — an L1 that doesn't itself
  // pass the filter is kept when at least one of its L2 children does.
  // The L1 acts as a transit "stepping stone" to a matching destination.
  // Caught case: Public Relations Specialists L1 ($67k, fails earnings
  // vs root $127k) hides Chief Executives L2 ($206k, easily passes).
  it("keeps a non-matching L1 when one of its L2 children passes", () => {
    const tree = makeNode({
      soc_code: "11-2011",
      median_wage: 126_960,
      children: [
        makeNode({
          soc_code: "11-2031",
          title: "Public Relations Specialists",
          median_wage: 67_000, // fails earnings vs root
          children: [
            makeNode({
              soc_code: "11-1011",
              title: "Chief Executives",
              median_wage: 206_420, // passes
            }),
            makeNode({
              soc_code: "43-9061",
              title: "Office Clerks",
              median_wage: 38_000, // fails
            }),
          ],
        }),
      ],
    });
    const out = filterTreeByStats(tree, new Set<StatFilter>(["earnings"]));
    expect(out.children).toHaveLength(1);
    expect(out.children[0]?.title).toBe("Public Relations Specialists");
    // Only the matching L2 survives; the failing L2 is still pruned.
    expect(out.children[0]?.children).toHaveLength(1);
    expect(out.children[0]?.children[0]?.title).toBe("Chief Executives");
  });

  it("drops a non-matching L1 when no L2 child passes either", () => {
    const tree = makeNode({
      soc_code: "11-2011",
      median_wage: 126_960,
      children: [
        makeNode({
          soc_code: "11-2031",
          median_wage: 67_000, // L1 fails
          children: [
            makeNode({ soc_code: "43-9061", median_wage: 38_000 }), // L2 fails
            makeNode({ soc_code: "43-9062", median_wage: 51_000 }), // L2 fails
          ],
        }),
      ],
    });
    const out = filterTreeByStats(tree, new Set<StatFilter>(["earnings"]));
    expect(out.children).toHaveLength(0);
  });
});
