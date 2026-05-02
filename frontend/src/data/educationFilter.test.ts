import { describe, it, expect } from "vitest";
import {
  filterTreeByEducation,
  nodeMatchesAny,
  nodeMatchesFilter,
  type EducationFilter,
} from "./educationFilter";
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

describe("nodeMatchesFilter", () => {
  it("bachelors filter matches Bachelor's degree and below", () => {
    const levels = [
      "Bachelor's degree",
      "Associate's degree",
      "Postsecondary nondegree award",
      "Some college, no degree",
      "High school diploma or equivalent",
      "No formal educational credential",
    ];
    for (const lvl of levels) {
      expect(nodeMatchesFilter(makeNode({ education: lvl }), "bachelors")).toBe(
        true,
      );
    }
  });

  it("bachelors filter rejects Master's and Doctoral", () => {
    expect(
      nodeMatchesFilter(makeNode({ education: "Master's degree" }), "bachelors"),
    ).toBe(false);
    expect(
      nodeMatchesFilter(
        makeNode({ education: "Doctoral or professional degree" }),
        "bachelors",
      ),
    ).toBe(false);
  });

  it("masters filter matches only Master's degree", () => {
    expect(
      nodeMatchesFilter(makeNode({ education: "Master's degree" }), "masters"),
    ).toBe(true);
    expect(
      nodeMatchesFilter(makeNode({ education: "Bachelor's degree" }), "masters"),
    ).toBe(false);
  });

  it("doctoral filter matches Doctoral or professional degree", () => {
    expect(
      nodeMatchesFilter(
        makeNode({ education: "Doctoral or professional degree" }),
        "doctoral",
      ),
    ).toBe(true);
    expect(
      nodeMatchesFilter(makeNode({ education: "Master's degree" }), "doctoral"),
    ).toBe(false);
  });

  it("returns false for null education across all filters", () => {
    const filters: EducationFilter[] = ["bachelors", "masters", "doctoral"];
    for (const f of filters) {
      expect(nodeMatchesFilter(makeNode({ education: null }), f)).toBe(false);
    }
  });

  it("returns false for unknown education strings", () => {
    expect(
      nodeMatchesFilter(
        makeNode({ education: "Some non-BLS string" }),
        "bachelors",
      ),
    ).toBe(false);
  });
});

describe("nodeMatchesAny", () => {
  it("returns true when filter set is empty (no filter applied)", () => {
    expect(nodeMatchesAny(makeNode({ education: "Bachelor's degree" }), new Set())).toBe(
      true,
    );
    expect(nodeMatchesAny(makeNode({ education: null }), new Set())).toBe(true);
  });

  it("ORs multiple active filters together", () => {
    const node = makeNode({ education: "Master's degree" });
    expect(nodeMatchesAny(node, new Set<EducationFilter>(["bachelors"]))).toBe(false);
    expect(
      nodeMatchesAny(node, new Set<EducationFilter>(["bachelors", "masters"])),
    ).toBe(true);
  });
});

describe("filterTreeByEducation", () => {
  function makeTree(): TreeNode {
    return makeNode({
      soc_code: "13-2051",
      title: "Financial Analyst",
      level: 0,
      education: "Bachelor's degree",
      children: [
        makeNode({
          soc_code: "11-3031",
          title: "Financial Manager",
          education: "Bachelor's degree",
          children: [
            makeNode({
              soc_code: "11-1011",
              title: "Chief Executive",
              education: "Bachelor's degree",
            }),
          ],
        }),
        makeNode({
          soc_code: "13-1161",
          title: "Market Research Analyst",
          education: "Master's degree",
          children: [],
        }),
        makeNode({
          soc_code: "23-1011",
          title: "Lawyer",
          education: "Doctoral or professional degree",
          children: [],
        }),
      ],
    });
  }

  it("returns the tree unchanged when no filters are active", () => {
    const tree = makeTree();
    const out = filterTreeByEducation(tree, new Set());
    expect(out).toBe(tree);
  });

  it("preserves the root regardless of filter", () => {
    const tree = makeTree();
    const out = filterTreeByEducation(
      tree,
      new Set<EducationFilter>(["doctoral"]),
    );
    expect(out.soc_code).toBe("13-2051");
    expect(out.title).toBe("Financial Analyst");
  });

  it("masters filter keeps only Master's-required L1 branches", () => {
    const out = filterTreeByEducation(
      makeTree(),
      new Set<EducationFilter>(["masters"]),
    );
    expect(out.children.map((c) => c.soc_code)).toEqual(["13-1161"]);
  });

  it("doctoral filter keeps only Doctoral/professional L1 branches", () => {
    const out = filterTreeByEducation(
      makeTree(),
      new Set<EducationFilter>(["doctoral"]),
    );
    expect(out.children.map((c) => c.soc_code)).toEqual(["23-1011"]);
  });

  it("multi-select OR: masters + doctoral keeps both", () => {
    const out = filterTreeByEducation(
      makeTree(),
      new Set<EducationFilter>(["masters", "doctoral"]),
    );
    expect(out.children.map((c) => c.soc_code).sort()).toEqual([
      "13-1161",
      "23-1011",
    ]);
  });

  it("L2 children with matching education come along with their kept L1 parent", () => {
    // Bachelor's filter keeps the Financial Manager L1, which carries
    // its Chief Executive L2 child (Bachelor's-level too).
    const out = filterTreeByEducation(
      makeTree(),
      new Set<EducationFilter>(["bachelors"]),
    );
    expect(out.children.map((c) => c.soc_code)).toEqual(["11-3031"]);
    expect(out.children[0]?.children.map((c) => c.soc_code)).toEqual([
      "11-1011",
    ]);
  });

  it("L2 endpoints failing the filter are dropped from a kept L1", () => {
    // L1 is Master's-required (passes) — L2 children that are
    // Bachelor's-level get filtered out of the L1's children list.
    const tree = makeNode({
      soc_code: "13-2051",
      title: "Financial Analyst",
      education: "Bachelor's degree",
      children: [
        makeNode({
          soc_code: "13-1161",
          title: "Market Research Analyst",
          education: "Master's degree",
          children: [
            makeNode({
              soc_code: "11-3031",
              title: "Financial Manager",
              education: "Bachelor's degree",
            }),
            makeNode({
              soc_code: "11-2021",
              title: "Marketing Manager",
              education: "Master's degree",
            }),
          ],
        }),
      ],
    });
    const out = filterTreeByEducation(
      tree,
      new Set<EducationFilter>(["masters"]),
    );
    expect(out.children).toHaveLength(1);
    // Only the Master's-level L2 survives.
    expect(out.children[0]?.children.map((c) => c.soc_code)).toEqual([
      "11-2021",
    ]);
  });

  it("dropping all branches yields an empty children list (root retained)", () => {
    const tree = makeNode({
      soc_code: "13-2051",
      title: "Financial Analyst",
      education: "Bachelor's degree",
      children: [
        makeNode({
          soc_code: "13-1161",
          education: "Bachelor's degree",
        }),
      ],
    });
    const out = filterTreeByEducation(
      tree,
      new Set<EducationFilter>(["doctoral"]),
    );
    expect(out.soc_code).toBe("13-2051");
    expect(out.children).toEqual([]);
  });

  // Path-permissive recursion regression — keep a Bachelor's L1 if its
  // L2 child requires Master's and the user is filtering for Master's.
  // The L1 is a stepping stone toward a matching destination; without
  // this the destination is unreachable from the tree.
  it("keeps a non-matching L1 when one of its L2 children matches", () => {
    const tree = makeNode({
      soc_code: "13-2051",
      children: [
        makeNode({
          soc_code: "13-2061",
          education: "Bachelor's degree", // L1 fails masters filter
          children: [
            makeNode({
              soc_code: "11-1011",
              education: "Master's degree", // L2 matches
            }),
            makeNode({
              soc_code: "43-9061",
              education: "Bachelor's degree", // L2 fails
            }),
          ],
        }),
      ],
    });
    const out = filterTreeByEducation(
      tree,
      new Set<EducationFilter>(["masters"]),
    );
    expect(out.children).toHaveLength(1);
    expect(out.children[0]?.education).toBe("Bachelor's degree");
    expect(out.children[0]?.children).toHaveLength(1);
    expect(out.children[0]?.children[0]?.education).toBe("Master's degree");
  });
});
