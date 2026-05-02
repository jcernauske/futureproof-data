import { describe, it, expect } from "vitest";
import {
  filterTreeByBoss,
  nodePassesAllBossFilters,
  nodePassesBossFilter,
  type BossFilter,
} from "./bossFilter";
import type { TreeNode } from "@/types/tree";

/**
 * T2.1 — Boss-outcome ("SURVIVES") filter tests.
 *
 * Survival = outcome ∈ {"win", "draw"}.
 * "lose" and "unknown" both fail — the contract is "SURVIVES", not
 * "didn't lose". We don't claim survival on data we can't compute.
 *
 * Within row: AND. Across rows (vs education / stat filters): also AND
 * — applied separately, but composes as AND when used together.
 */

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    soc_code: "13-0000",
    title: "Test",
    level: 1,
    ern: null,
    roi: null,
    res: null,
    grw: null,
    aura: null,
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

describe("nodePassesBossFilter", () => {
  it("filter_keeps_node_with_win_outcome", () => {
    expect(
      nodePassesBossFilter(makeNode({ boss_ai: "win" }), "boss_ai"),
    ).toBe(true);
    expect(
      nodePassesBossFilter(makeNode({ boss_market: "win" }), "boss_market"),
    ).toBe(true);
    expect(
      nodePassesBossFilter(makeNode({ boss_burnout: "win" }), "boss_burnout"),
    ).toBe(true);
  });

  it("filter_keeps_node_with_draw_outcome", () => {
    expect(
      nodePassesBossFilter(makeNode({ boss_ai: "draw" }), "boss_ai"),
    ).toBe(true);
    expect(
      nodePassesBossFilter(makeNode({ boss_market: "draw" }), "boss_market"),
    ).toBe(true);
    expect(
      nodePassesBossFilter(makeNode({ boss_burnout: "draw" }), "boss_burnout"),
    ).toBe(true);
  });

  it("filter_drops_node_with_lose_outcome", () => {
    expect(
      nodePassesBossFilter(makeNode({ boss_ai: "lose" }), "boss_ai"),
    ).toBe(false);
    expect(
      nodePassesBossFilter(makeNode({ boss_market: "lose" }), "boss_market"),
    ).toBe(false);
    expect(
      nodePassesBossFilter(makeNode({ boss_burnout: "lose" }), "boss_burnout"),
    ).toBe(false);
  });

  it("filter drops 'unknown' — we don't claim survival without data", () => {
    expect(
      nodePassesBossFilter(makeNode({ boss_ai: "unknown" }), "boss_ai"),
    ).toBe(false);
  });

  it("filter drops null outcomes", () => {
    expect(
      nodePassesBossFilter(makeNode({ boss_ai: null }), "boss_ai"),
    ).toBe(false);
  });
});

describe("nodePassesAllBossFilters", () => {
  it("returns true when filter set is empty (no filter applied)", () => {
    expect(nodePassesAllBossFilters(makeNode(), new Set())).toBe(true);
    expect(
      nodePassesAllBossFilters(
        makeNode({ boss_ai: "lose", boss_market: "lose" }),
        new Set(),
      ),
    ).toBe(true);
  });

  it("multi_select_AND_within_row", () => {
    const win_win_lose = makeNode({
      boss_ai: "win",
      boss_market: "win",
      boss_burnout: "lose",
    });
    const win_win_win = makeNode({
      boss_ai: "win",
      boss_market: "draw",
      boss_burnout: "win",
    });

    // Single filter: win passes.
    expect(
      nodePassesAllBossFilters(win_win_lose, new Set<BossFilter>(["boss_ai"])),
    ).toBe(true);
    // Two filters: both win → passes.
    expect(
      nodePassesAllBossFilters(
        win_win_lose,
        new Set<BossFilter>(["boss_ai", "boss_market"]),
      ),
    ).toBe(true);
    // Three filters: burnout=lose fails → whole node fails.
    expect(
      nodePassesAllBossFilters(
        win_win_lose,
        new Set<BossFilter>(["boss_ai", "boss_market", "boss_burnout"]),
      ),
    ).toBe(false);
    // Same three filters on a node that passes them all.
    expect(
      nodePassesAllBossFilters(
        win_win_win,
        new Set<BossFilter>(["boss_ai", "boss_market", "boss_burnout"]),
      ),
    ).toBe(true);
  });
});

describe("filterTreeByBoss", () => {
  function makeTree(): TreeNode {
    return makeNode({
      soc_code: "ROOT",
      title: "Root",
      level: 0,
      // Root outcomes intentionally "lose" — root is preserved REGARDLESS
      // of whether it passes the filter (it IS the reference).
      boss_ai: "lose",
      boss_market: "lose",
      boss_burnout: "lose",
      children: [
        makeNode({
          soc_code: "L1A",
          title: "L1 passes AI",
          boss_ai: "win",
          boss_market: "lose",
          boss_burnout: "win",
          children: [
            makeNode({
              soc_code: "L2A",
              boss_ai: "win",
              boss_market: "lose",
            }),
            makeNode({
              soc_code: "L2B",
              boss_ai: "lose",
              boss_market: "lose",
            }),
          ],
        }),
        makeNode({
          soc_code: "L1B",
          title: "L1 fails AI",
          boss_ai: "lose",
          boss_market: "win",
          boss_burnout: "win",
        }),
      ],
    });
  }

  it("returns tree unchanged when no filters are active", () => {
    const tree = makeTree();
    const out = filterTreeByBoss(tree, new Set());
    expect(out).toBe(tree);
  });

  it("preserves the root regardless of filter (root is the reference)", () => {
    const out = filterTreeByBoss(
      makeTree(),
      new Set<BossFilter>(["boss_ai"]),
    );
    expect(out.soc_code).toBe("ROOT");
    // The root has boss_ai=lose but stays in the output anyway.
  });

  it("filter_recursive_to_L2", () => {
    // Filter on boss_ai=SURVIVES.
    // L1A passes (win) — kept; L1B fails (lose) — dropped.
    // Under the surviving L1A: L2A passes (win), L2B fails (lose) → only L2A remains.
    const out = filterTreeByBoss(
      makeTree(),
      new Set<BossFilter>(["boss_ai"]),
    );
    expect(out.children.map((c) => c.soc_code)).toEqual(["L1A"]);
    expect(out.children[0]?.children.map((c) => c.soc_code)).toEqual(["L2A"]);
  });

  it("multi-select AND across L1 hides L1s that fail any chip", () => {
    // boss_ai + boss_market both required.
    // L1A: ai=win, market=lose → fails.
    // L1B: ai=lose, market=win → fails.
    // → no L1 survives, root keeps empty children list.
    const out = filterTreeByBoss(
      makeTree(),
      new Set<BossFilter>(["boss_ai", "boss_market"]),
    );
    expect(out.soc_code).toBe("ROOT");
    expect(out.children).toEqual([]);
  });

  it("retains an L1 with zero passing L2s (the L1 itself satisfies)", () => {
    // L1A passes ai=win. Both its L2 children would be evaluated and L2B
    // (ai=lose) is dropped. L2A (ai=win) survives. L1A is kept either way.
    const tree = makeNode({
      soc_code: "ROOT",
      level: 0,
      children: [
        makeNode({
          soc_code: "L1",
          boss_ai: "win",
          children: [
            makeNode({ soc_code: "EP1", boss_ai: "lose" }),
            makeNode({ soc_code: "EP2", boss_ai: "lose" }),
          ],
        }),
      ],
    });
    const out = filterTreeByBoss(tree, new Set<BossFilter>(["boss_ai"]));
    expect(out.children).toHaveLength(1);
    expect(out.children[0]?.children).toEqual([]); // both L2s dropped
  });

  it("does not mutate the input tree", () => {
    const tree = makeTree();
    const before = JSON.stringify(tree);
    filterTreeByBoss(tree, new Set<BossFilter>(["boss_ai"]));
    expect(JSON.stringify(tree)).toBe(before);
  });
});
