import { describe, it, expect } from "vitest";
import { computePathRarity } from "./pathRarity";
import type { TreeNode } from "@/types/tree";

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    soc_code: "00-0000",
    title: "Test",
    level: 0,
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

describe("computePathRarity", () => {
  it("returns null for an empty path", () => {
    expect(computePathRarity([])).toBeNull();
  });

  it("returns null for a root-only path (no hops)", () => {
    expect(computePathRarity([makeNode({ relatedness: null })])).toBeNull();
  });

  it("returns null when every non-root hop has null relatedness", () => {
    const path = [
      makeNode(),
      makeNode({ relatedness: null }),
      makeNode({ relatedness: null }),
    ];
    expect(computePathRarity(path)).toBeNull();
  });

  it("classifies max rank ≤ 5 as 'direct'", () => {
    const path = [makeNode(), makeNode({ relatedness: 3 })];
    expect(computePathRarity(path)).toEqual({
      tier: "direct",
      maxRank: 3,
      hopCount: 1,
    });
  });

  it("boundary: max rank == 5 stays 'direct'", () => {
    const path = [makeNode(), makeNode({ relatedness: 5 })];
    expect(computePathRarity(path)?.tier).toBe("direct");
  });

  it("boundary: max rank == 6 becomes 'adjacent'", () => {
    const path = [makeNode(), makeNode({ relatedness: 6 })];
    expect(computePathRarity(path)?.tier).toBe("adjacent");
  });

  it("boundary: max rank == 10 stays 'adjacent'", () => {
    const path = [makeNode(), makeNode({ relatedness: 10 })];
    expect(computePathRarity(path)?.tier).toBe("adjacent");
  });

  it("boundary: max rank == 11 becomes 'stretch'", () => {
    const path = [makeNode(), makeNode({ relatedness: 11 })];
    expect(computePathRarity(path)?.tier).toBe("stretch");
  });

  it("boundary: max rank == 15 stays 'stretch'", () => {
    const path = [makeNode(), makeNode({ relatedness: 15 })];
    expect(computePathRarity(path)?.tier).toBe("stretch");
  });

  it("boundary: max rank == 16 becomes 'longshot'", () => {
    const path = [makeNode(), makeNode({ relatedness: 16 })];
    expect(computePathRarity(path)?.tier).toBe("longshot");
  });

  it("uses the WORST hop along a multi-hop path (weakest link)", () => {
    // L1 close (rank 2), L2 stretch (rank 13). Path is dominated by L2.
    const path = [
      makeNode(),
      makeNode({ relatedness: 2 }),
      makeNode({ relatedness: 13 }),
    ];
    expect(computePathRarity(path)).toEqual({
      tier: "stretch",
      maxRank: 13,
      hopCount: 2,
    });
  });

  it("Fish & Wildlife → Operations → CEO scenario lands as 'longshot'", () => {
    // L1 stretch (rank 17), L2 close (rank 2). Path inherits the
    // weakest link — even though CEOs are commonly reached from
    // Operations, getting from Fish & Wildlife to Operations is the
    // unusual hop that defines the path's rarity.
    const path = [
      makeNode({ title: "Fish and Wildlife Supervisor" }),
      makeNode({ title: "Operations Manager", relatedness: 17 }),
      makeNode({ title: "CEO", relatedness: 2 }),
    ];
    expect(computePathRarity(path)?.tier).toBe("longshot");
  });

  it("ignores null hops when computing max", () => {
    const path = [
      makeNode(),
      makeNode({ relatedness: null }), // skipped
      makeNode({ relatedness: 7 }),
    ];
    const result = computePathRarity(path);
    expect(result?.tier).toBe("adjacent");
    expect(result?.maxRank).toBe(7);
    expect(result?.hopCount).toBe(1);
  });
});
