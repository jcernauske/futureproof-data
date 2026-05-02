import { describe, it, expect } from "vitest";
import { rankNodesForTour } from "./tourRanking";
import type { TreeNode } from "@/types/tree";

/**
 * T1.2 — Tour-chip ranker tests.
 *
 * Tours flatten the tree (excluding root) and surface the top-N node
 * IDs. ID format mirrors treeFlowLayout.ts:
 *   L1: `career-${soc}-${branchIdx}`
 *   L2: `endpoint-${soc}-${branchIdx}-${epIdx}`
 *
 * Root is never returned — the tour shows where the student could go,
 * not where they are.
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

describe("rankNodesForTour — highest_ceiling", () => {
  it("highest_ceiling_picks_top_3_by_wage", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      median_wage: 90_000,
      children: [
        makeNode({ soc_code: "A", median_wage: 200_000 }),
        makeNode({ soc_code: "B", median_wage: 50_000 }),
        makeNode({ soc_code: "C", median_wage: 175_000 }),
        makeNode({ soc_code: "D", median_wage: 150_000 }),
      ],
    });

    const out = rankNodesForTour("highest_ceiling", tree, 3);

    // Top 3 by wage: A (200k), C (175k), D (150k) — branch indexes 0, 2, 3.
    expect(out).toEqual([
      "career-A-0",
      "career-C-2",
      "career-D-3",
    ]);
  });

  it("highest_ceiling skips nodes with null wage", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      children: [
        makeNode({ soc_code: "A", median_wage: null }),
        makeNode({ soc_code: "B", median_wage: 80_000 }),
        makeNode({ soc_code: "C", median_wage: null }),
      ],
    });
    const out = rankNodesForTour("highest_ceiling", tree, 3);
    expect(out).toEqual(["career-B-1"]);
  });

  it("highest_ceiling considers L2 endpoints alongside L1", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      median_wage: 50_000,
      children: [
        makeNode({
          soc_code: "L1",
          median_wage: 90_000,
          children: [
            makeNode({ soc_code: "E1", median_wage: 250_000 }),
            makeNode({ soc_code: "E2", median_wage: 110_000 }),
          ],
        }),
      ],
    });
    const out = rankNodesForTour("highest_ceiling", tree, 3);
    // E1 (250k) > E2 (110k) > L1 (90k)
    expect(out).toEqual([
      "endpoint-E1-0-0",
      "endpoint-E2-0-1",
      "career-L1-0",
    ]);
  });
});

describe("rankNodesForTour — fastest_to_mid", () => {
  it("fastest_to_mid_prefers_low_experience_tier", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      children: [
        makeNode({ soc_code: "SR", experience_tier: "senior", relatedness: 1 }),
        makeNode({ soc_code: "EN", experience_tier: "entry", relatedness: 5 }),
        makeNode({ soc_code: "MD", experience_tier: "mid", relatedness: 2 }),
        makeNode({ soc_code: "EA", experience_tier: "early", relatedness: 3 }),
      ],
    });

    const out = rankNodesForTour("fastest_to_mid", tree, 4);

    // Tier order: entry < early < mid < senior. Within tier no ties here.
    expect(out).toEqual([
      "career-EN-1", // entry
      "career-EA-3", // early
      "career-MD-2", // mid
      "career-SR-0", // senior
    ]);
  });

  it("fastest_to_mid_tiebreaks_by_relatedness_asc", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      children: [
        makeNode({ soc_code: "A", experience_tier: "entry", relatedness: 8 }),
        makeNode({ soc_code: "B", experience_tier: "entry", relatedness: 2 }),
        makeNode({ soc_code: "C", experience_tier: "entry", relatedness: 5 }),
      ],
    });
    const out = rankNodesForTour("fastest_to_mid", tree, 3);
    // All entry-tier — order by relatedness ascending (closer first).
    expect(out).toEqual([
      "career-B-1",
      "career-C-2",
      "career-A-0",
    ]);
  });

  it("fastest_to_mid skips nodes with null experience_tier", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      children: [
        makeNode({ soc_code: "X", experience_tier: null, relatedness: 1 }),
        makeNode({ soc_code: "Y", experience_tier: "entry", relatedness: 1 }),
      ],
    });
    const out = rankNodesForTour("fastest_to_mid", tree, 3);
    expect(out).toEqual(["career-Y-1"]);
  });
});

describe("rankNodesForTour — biggest_pay_jump", () => {
  it("biggest_pay_jump_uses_delta_not_absolute", () => {
    // Root anchored at $200k; the absolute-highest paying node is
    // A ($210k) but the biggest DELTA from root is B at +$80k. The
    // tour must surface B first — confirms delta-vs-root semantics.
    const tree = makeNode({
      soc_code: "ROOT",
      median_wage: 200_000,
      children: [
        makeNode({ soc_code: "A", median_wage: 210_000 }),
        makeNode({
          soc_code: "BR1",
          median_wage: 100_000,
          children: [
            makeNode({ soc_code: "B", median_wage: 280_000 }),
          ],
        }),
        makeNode({ soc_code: "C", median_wage: 250_000 }),
      ],
    });

    const out = rankNodesForTour("biggest_pay_jump", tree, 3);

    // Deltas from root $200k:
    //   A   = +$10k
    //   BR1 = -$100k
    //   B   = +$80k
    //   C   = +$50k
    // Top 3 by delta DESC: B, C, A.
    expect(out).toEqual([
      "endpoint-B-1-0",
      "career-C-2",
      "career-A-0",
    ]);
  });

  it("biggest_pay_jump skips nodes with null wage", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      median_wage: 80_000,
      children: [
        makeNode({ soc_code: "A", median_wage: null }),
        makeNode({ soc_code: "B", median_wage: 120_000 }),
      ],
    });
    const out = rankNodesForTour("biggest_pay_jump", tree, 3);
    expect(out).toEqual(["career-B-1"]);
  });

  it("biggest_pay_jump treats null root wage as 0", () => {
    // root median_wage null → rootWage = 0 in implementation. Result:
    // ranking degenerates into highest absolute wage.
    const tree = makeNode({
      soc_code: "ROOT",
      median_wage: null,
      children: [
        makeNode({ soc_code: "A", median_wage: 100_000 }),
        makeNode({ soc_code: "B", median_wage: 50_000 }),
      ],
    });
    const out = rankNodesForTour("biggest_pay_jump", tree, 2);
    expect(out).toEqual(["career-A-0", "career-B-1"]);
  });
});

describe("rankNodesForTour — empty / degenerate", () => {
  it("ranker_handles_empty_tree_gracefully", () => {
    const empty = makeNode({ soc_code: "ROOT", children: [] });
    expect(rankNodesForTour("highest_ceiling", empty)).toEqual([]);
    expect(rankNodesForTour("ai_resilient", empty)).toEqual([]);
    expect(rankNodesForTour("fastest_to_mid", empty)).toEqual([]);
    expect(rankNodesForTour("biggest_pay_jump", empty)).toEqual([]);
  });

  it("respects topN when fewer than topN qualify", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      median_wage: 50_000,
      children: [makeNode({ soc_code: "A", median_wage: 100_000 })],
    });
    const out = rankNodesForTour("highest_ceiling", tree, 5);
    expect(out).toEqual(["career-A-0"]);
  });

  it("ai_resilient orders by RES desc, tiebreaks by wage desc", () => {
    const tree = makeNode({
      soc_code: "ROOT",
      children: [
        makeNode({ soc_code: "A", res: 8, median_wage: 60_000 }),
        makeNode({ soc_code: "B", res: 8, median_wage: 90_000 }), // tie on RES → wage tiebreak
        makeNode({ soc_code: "C", res: 9, median_wage: 50_000 }),
        makeNode({ soc_code: "D", res: null, median_wage: 200_000 }),
      ],
    });
    const out = rankNodesForTour("ai_resilient", tree, 4);
    // RES desc: C(9), then B/A tied at 8 — B wins on wage. D filtered (null RES).
    expect(out).toEqual([
      "career-C-2",
      "career-B-1",
      "career-A-0",
    ]);
  });
});
