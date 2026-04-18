import { describe, it, expect } from "vitest";
import { computeLayout } from "./treeLayout";
import type { TreeNode } from "@/types/tree";

/**
 * treeLayout.test.ts — Tests for the pure layout computation function.
 *
 * computeLayout is the most testable code in the branch tree feature:
 * it's a pure function (TreeNode in, TreeLayout out) with zero side effects.
 * Every assertion here tests real production code, not mocks.
 *
 * We're hunting for:
 * - Correct node positioning (root at COL_ROOT=80)
 * - Correct level assignment (root=0, branch=1/2, endpoint=3)
 * - Path group classification (incoming vs outgoing)
 * - Stat/boss mapping from TreeNode fields to PositionedNode structs
 * - Edge cases: empty children, single child, no grandchildren
 * - Branch label derivation logic (specialize, management, lateral, technical)
 * - Dominant stat color computation
 */

// --- Test fixtures ---

function makeLeafNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    soc_code: "99-9999",
    title: "Test Occupation",
    level: 0,
    ern: 50,
    roi: 50,
    res: 50,
    grw: 50,
    hmn: 50,
    median_wage: 60000,
    education: "Bachelor's degree",
    boss_ai: "draw",
    boss_loans: "win",
    boss_market: "win",
    boss_burnout: "lose",
    boss_ceiling: "draw",
    children: [],
    ...overrides,
  };
}

function makeTreeWithBranches(): TreeNode {
  return makeLeafNode({
    soc_code: "13-2051",
    title: "Financial Analyst",
    ern: 72,
    roi: 68,
    res: 45,
    grw: 61,
    hmn: 38,
    median_wage: 95570,
    children: [
      makeLeafNode({
        soc_code: "11-3031",
        title: "Financial Manager",
        level: 1,
        ern: 85,
        roi: 74,
        res: 42,
        grw: 55,
        hmn: 52,
        median_wage: 139790,
        education: "Bachelor's degree + experience",
        children: [
          makeLeafNode({
            soc_code: "11-1011",
            title: "Chief Executive",
            level: 2,
            ern: 95,
            roi: 82,
            res: 38,
            grw: 48,
            hmn: 65,
            median_wage: 189520,
            education: "Master's preferred",
            children: [
              makeLeafNode({
                soc_code: "11-1021",
                title: "General & Operations Manager",
                level: 3,
                ern: 88,
                roi: 78,
                median_wage: 115250,
              }),
            ],
          }),
        ],
      }),
      makeLeafNode({
        soc_code: "13-1161",
        title: "Market Research Analyst",
        level: 1,
        ern: 62,
        roi: 65,
        median_wage: 68230,
        children: [], // leaf branch — no sub-children
      }),
    ],
  });
}

// --- Root node placement ---

describe("computeLayout — root node", () => {
  it("places root at x=80 (COL_ROOT) for a tree with no children", () => {
    const tree = makeLeafNode();
    const layout = computeLayout(tree);

    const root = layout.nodes.find((n) => n.level === 0);
    expect(root).toBeDefined();
    expect(root!.x).toBe(80);
  });

  it("places root at x=80 for a tree with branches", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    const root = layout.nodes.find((n) => n.level === 0);
    expect(root!.x).toBe(80);
  });

  it("root node id starts with 'root-'", () => {
    const tree = makeLeafNode({ soc_code: "13-2051" });
    const layout = computeLayout(tree);

    const root = layout.nodes.find((n) => n.level === 0);
    expect(root!.id).toBe("root-13-2051");
  });

  it("maps all 5 stats from TreeNode fields to PositionedNode stats object", () => {
    const tree = makeLeafNode({
      ern: 72,
      roi: 68,
      res: 45,
      grw: 61,
      hmn: 38,
    });
    const layout = computeLayout(tree);
    const root = layout.nodes.find((n) => n.level === 0)!;

    expect(root.stats).toEqual({
      ern: 72,
      roi: 68,
      res: 45,
      grw: 61,
      hmn: 38,
    });
  });

  it("maps all 5 boss fields from TreeNode to PositionedNode bosses object", () => {
    const tree = makeLeafNode({
      boss_ai: "draw",
      boss_loans: "win",
      boss_market: "lose",
      boss_burnout: null,
      boss_ceiling: "win",
    });
    const layout = computeLayout(tree);
    const root = layout.nodes.find((n) => n.level === 0)!;

    expect(root.bosses).toEqual({
      ai: "draw",
      loans: "win",
      market: "lose",
      burnout: null,
      ceiling: "win",
    });
  });

  it("preserves median_wage and education on root", () => {
    const tree = makeLeafNode({ median_wage: 95570, education: "PhD required" });
    const layout = computeLayout(tree);
    const root = layout.nodes.find((n) => n.level === 0)!;

    expect(root.median_wage).toBe(95570);
    expect(root.education).toBe("PhD required");
  });

  it("root parentId is null", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);
    const root = layout.nodes.find((n) => n.level === 0)!;

    expect(root.parentId).toBeNull();
  });
});

// --- Fallback: empty tree ---

describe("computeLayout — empty children (fallback)", () => {
  it("returns exactly one node for a tree with no children", () => {
    const tree = makeLeafNode();
    const layout = computeLayout(tree);

    expect(layout.nodes).toHaveLength(1);
    expect(layout.nodes[0]!.level).toBe(0);
  });

  it("returns zero paths for a tree with no children", () => {
    const tree = makeLeafNode();
    const layout = computeLayout(tree);

    expect(layout.paths).toHaveLength(0);
  });

  it("returns zero branch labels for a tree with no children", () => {
    const tree = makeLeafNode();
    const layout = computeLayout(tree);

    expect(layout.branchLabels).toHaveLength(0);
  });

  it("returns viewBoxWidth=750 and viewBoxHeight=400 for fallback", () => {
    const tree = makeLeafNode();
    const layout = computeLayout(tree);

    expect(layout.viewBoxWidth).toBe(750);
    expect(layout.viewBoxHeight).toBe(400);
  });

  it("places fallback root at y=200 (centered in 400px viewbox)", () => {
    const tree = makeLeafNode();
    const layout = computeLayout(tree);
    const root = layout.nodes[0]!;

    expect(root.y).toBe(200);
  });
});

// --- Multi-branch tree ---

describe("computeLayout — multi-branch tree", () => {
  it("creates nodes for root + all branches + career nodes + endpoints", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    // Root (1) + Financial Manager branch: FM(1), CE(1), GenOps endpoint(1) + Market Research(1) = 5
    const root = layout.nodes.filter((n) => n.level === 0);
    const level1 = layout.nodes.filter((n) => n.level === 1);
    const level2 = layout.nodes.filter((n) => n.level === 2);
    const level3 = layout.nodes.filter((n) => n.level === 3);

    expect(root).toHaveLength(1);
    // Market Research is a direct branch (no children), so it's level 1
    expect(level1).toHaveLength(1);
    // Chief Executive is inside Financial Manager's children
    expect(level2).toHaveLength(1);
    // General & Operations Manager is endpoint
    expect(level3).toHaveLength(1);
  });

  it("creates branch labels for each top-level child", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    expect(layout.branchLabels).toHaveLength(2);
  });

  it("branch labels are positioned at x=260 (COL_BRANCH_LABEL)", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    for (const bl of layout.branchLabels) {
      expect(bl.x).toBe(260);
    }
  });

  it("career nodes are positioned at x=420 (COL_CAREER)", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    const careerNodes = layout.nodes.filter((n) => n.level === 1 || n.level === 2);
    for (const cn of careerNodes) {
      expect(cn.x).toBe(420);
    }
  });

  it("endpoint nodes are positioned at x=620 (COL_ENDPOINT)", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    const endpoints = layout.nodes.filter((n) => n.level === 3);
    for (const ep of endpoints) {
      expect(ep.x).toBe(620);
    }
  });

  it("paths are classified as incoming or outgoing", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    const incoming = layout.paths.filter((p) => p.group === "incoming");
    const outgoing = layout.paths.filter((p) => p.group === "outgoing");

    // Incoming: root→branch0, branch0→career, root→branch1, branch1→career = 4
    expect(incoming.length).toBeGreaterThan(0);
    // Outgoing: career→endpoint = 1
    expect(outgoing.length).toBeGreaterThan(0);
  });

  it("outgoing paths connect career nodes to endpoints", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    const outgoing = layout.paths.filter((p) => p.group === "outgoing");
    // Each outgoing path should originate from COL_CAREER + COL_CAREER_WIDTH = 420 + 116 = 536
    for (const p of outgoing) {
      expect(p.fromX).toBe(536);
    }
  });

  it("incoming paths originate from root area (COL_ROOT + 28 = 108)", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    const rootToBranch = layout.paths.filter(
      (p) => p.group === "incoming" && p.fromX === 108,
    );
    // One per top-level branch
    expect(rootToBranch).toHaveLength(2);
  });

  it("creates gradient definitions for each branch", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    expect(layout.gradientDefs.length).toBeGreaterThanOrEqual(2);
    for (const g of layout.gradientDefs) {
      expect(g.fromColor).toBe("#7DD4A3"); // always starts from root green
      expect(g.toColor).toBeTruthy();
    }
  });

  it("viewBoxWidth is always 750", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    expect(layout.viewBoxWidth).toBe(750);
  });

  it("viewBoxHeight is at least 400", () => {
    const tree = makeTreeWithBranches();
    const layout = computeLayout(tree);

    expect(layout.viewBoxHeight).toBeGreaterThanOrEqual(400);
  });
});

// --- Branch label derivation ---

describe("computeLayout — branch label derivation", () => {
  it("labels 'Specialize' when education mentions master", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Data Scientist",
          education: "Master's preferred",
          children: [makeLeafNode({ title: "ML Engineer" })],
        }),
      ],
    });
    const layout = computeLayout(tree);

    expect(layout.branchLabels[0]!.label).toBe("Specialize");
  });

  it("labels 'Go Management' when title includes 'Manager'", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Financial Manager",
          education: "Bachelor's degree",
          children: [makeLeafNode({ title: "Director of Finance" })],
        }),
      ],
    });
    const layout = computeLayout(tree);

    expect(layout.branchLabels[0]!.label).toBe("Go Management");
  });

  it("labels 'Go Management' when title includes 'Director'", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Program Director",
          education: "Bachelor's degree",
          children: [makeLeafNode({ title: "VP Ops" })],
        }),
      ],
    });
    const layout = computeLayout(tree);

    expect(layout.branchLabels[0]!.label).toBe("Go Management");
  });

  it("labels 'Pivot Lateral' when branch is a leaf (no children)", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Market Research Analyst",
          education: "Bachelor's degree",
          children: [],
        }),
      ],
    });
    const layout = computeLayout(tree);

    expect(layout.branchLabels[0]!.label).toBe("Pivot Lateral");
  });

  it("labels 'Stay Technical' as the default fallback", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Software Engineer",
          education: "Bachelor's degree",
          children: [makeLeafNode({ title: "Senior Dev" })],
        }),
      ],
    });
    const layout = computeLayout(tree);

    expect(layout.branchLabels[0]!.label).toBe("Stay Technical");
  });

  it("master/doctor detection is case-insensitive", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Researcher",
          education: "DOCTORAL degree required",
          children: [makeLeafNode({ title: "Senior Researcher" })],
        }),
      ],
    });
    const layout = computeLayout(tree);

    expect(layout.branchLabels[0]!.label).toBe("Specialize");
  });
});

// --- Dominant stat color ---

describe("computeLayout — dominant stat color", () => {
  it("assigns branch color based on largest positive stat delta vs root", () => {
    const tree = makeLeafNode({
      ern: 50,
      roi: 50,
      res: 50,
      grw: 50,
      hmn: 50,
      children: [
        makeLeafNode({
          title: "High GRW Career",
          ern: 52,
          roi: 51,
          res: 51,
          grw: 90, // biggest delta = +40
          hmn: 51,
          children: [makeLeafNode()],
        }),
      ],
    });
    const layout = computeLayout(tree);

    // GRW color is #7BB8E0
    const careerNode = layout.nodes.find((n) => n.level !== 0);
    expect(careerNode!.branchColor).toBe("#7BB8E0");
  });

  it("falls back to ERN color (#F2D477) when all deltas are equal", () => {
    const tree = makeLeafNode({
      ern: 50,
      roi: 50,
      res: 50,
      grw: 50,
      hmn: 50,
      children: [
        makeLeafNode({
          title: "Same Stats",
          ern: 60,
          roi: 60,
          res: 60,
          grw: 60,
          hmn: 60,
          children: [makeLeafNode()],
        }),
      ],
    });
    const layout = computeLayout(tree);

    // When all deltas are equal, the first one checked (ern) wins
    const careerNode = layout.nodes.find((n) => n.level !== 0);
    expect(careerNode!.branchColor).toBe("#F2D477");
  });

  it("handles null stats in root or child without crashing", () => {
    const tree = makeLeafNode({
      ern: null,
      roi: null,
      res: null,
      grw: null,
      hmn: null,
      children: [
        makeLeafNode({
          title: "All null",
          ern: null,
          roi: null,
          res: null,
          grw: null,
          hmn: null,
          children: [makeLeafNode()],
        }),
      ],
    });

    // Should not throw
    const layout = computeLayout(tree);
    expect(layout.nodes.length).toBeGreaterThan(0);
  });
});

// --- Single-child branches ---

describe("computeLayout — single-child branch", () => {
  it("handles a single branch with a single career child", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Only Branch",
          children: [
            makeLeafNode({ title: "Only Career", children: [] }),
          ],
        }),
      ],
    });
    const layout = computeLayout(tree);

    // root + branch career (level 2) + branch direct career mapped at level 2
    const nonRoot = layout.nodes.filter((n) => n.level !== 0);
    expect(nonRoot.length).toBeGreaterThanOrEqual(1);
    expect(layout.branchLabels).toHaveLength(1);
  });

  it("root y is at vertical center of total height for single branch", () => {
    const tree = makeLeafNode({
      children: [
        makeLeafNode({
          title: "Only Branch",
          children: [],
        }),
      ],
    });
    const layout = computeLayout(tree);

    const root = layout.nodes.find((n) => n.level === 0)!;
    // Root y should equal totalHeight / 2
    // For a single leaf branch: totalSlots=1, totalHeight = 1*60 + 0*24 + 120 = 180
    // rootY = 180 / 2 = 90
    expect(root.y).toBe(90);
  });
});

// --- Null stat handling ---

describe("computeLayout — null handling", () => {
  it("preserves null median_wage on positioned nodes", () => {
    const tree = makeLeafNode({ median_wage: null });
    const layout = computeLayout(tree);

    expect(layout.nodes[0]!.median_wage).toBeNull();
  });

  it("preserves null education on positioned nodes", () => {
    const tree = makeLeafNode({ education: null });
    const layout = computeLayout(tree);

    expect(layout.nodes[0]!.education).toBeNull();
  });

  it("preserves null stat values on positioned nodes", () => {
    const tree = makeLeafNode({
      ern: null,
      roi: 50,
      res: null,
      grw: 70,
      hmn: null,
    });
    const layout = computeLayout(tree);
    const root = layout.nodes[0]!;

    expect(root.stats.ern).toBeNull();
    expect(root.stats.roi).toBe(50);
    expect(root.stats.res).toBeNull();
    expect(root.stats.grw).toBe(70);
    expect(root.stats.hmn).toBeNull();
  });
});
