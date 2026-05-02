import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  Breadcrumb,
  buildBreadcrumbSegments,
  findPathToNodeId,
  type BreadcrumbSegment,
} from "./Breadcrumb";
import type { TreeNode } from "@/types/tree";

/**
 * T1.4 — Breadcrumb tests.
 *
 * Covers:
 *  - findPathToNodeId — root, L1, L2, miss
 *  - buildBreadcrumbSegments — visible / ghosted / nodeId resolution
 *  - <Breadcrumb /> — clicking a segment fires onSegmentClick with that
 *    segment; ghost segments render with the strikethrough state class
 *
 * useT is short-circuited to identity so we can assert on copy keys
 * directly without coupling to en/es/ar string contents.
 */

vi.mock("@/i18n/useT", () => ({
  useT: () => (key: string) => key,
}));

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

function makeTree(): TreeNode {
  return makeNode({
    soc_code: "ROOT",
    title: "Financial Analyst",
    level: 0,
    children: [
      makeNode({
        soc_code: "L1A",
        title: "Financial Manager",
        children: [
          makeNode({ soc_code: "L2A1", title: "Chief Executive" }),
          makeNode({ soc_code: "L2A2", title: "VP Operations" }),
        ],
      }),
      makeNode({
        soc_code: "L1B",
        title: "Market Research Analyst",
      }),
    ],
  });
}

describe("findPathToNodeId", () => {
  it("returns [root] for the root id", () => {
    const t = makeTree();
    const out = findPathToNodeId(t, "root-ROOT");
    expect(out).not.toBeNull();
    expect(out!.map((n) => n.soc_code)).toEqual(["ROOT"]);
  });

  it("returns [root, L1] for an L1 id", () => {
    const t = makeTree();
    const out = findPathToNodeId(t, "career-L1A-0");
    expect(out!.map((n) => n.soc_code)).toEqual(["ROOT", "L1A"]);
  });

  it("returns [root, L1, L2] for an L2 endpoint id", () => {
    const t = makeTree();
    const out = findPathToNodeId(t, "endpoint-L2A2-0-1");
    expect(out!.map((n) => n.soc_code)).toEqual(["ROOT", "L1A", "L2A2"]);
  });

  it("returns null when the id doesn't match any node", () => {
    const t = makeTree();
    expect(findPathToNodeId(t, "career-NOPE-9")).toBeNull();
    expect(findPathToNodeId(t, "endpoint-NOPE-9-9")).toBeNull();
  });
});

describe("buildBreadcrumbSegments", () => {
  it("returns [] for an empty snapshot (root-only state)", () => {
    expect(buildBreadcrumbSegments([], makeTree(), null)).toEqual([]);
  });

  it("marks the root as isRoot and resolves its nodeId from the tree", () => {
    const segs = buildBreadcrumbSegments(
      [{ socCode: "ROOT", title: "Financial Analyst" }],
      makeTree(),
      "root-ROOT",
    );
    expect(segs).toHaveLength(1);
    expect(segs[0]!.isRoot).toBe(true);
    expect(segs[0]!.hidden).toBe(false);
    expect(segs[0]!.nodeId).toBe("root-ROOT");
  });

  it("resolves an L1 segment's nodeId to its branch index", () => {
    const segs = buildBreadcrumbSegments(
      [
        { socCode: "ROOT", title: "Root" },
        { socCode: "L1B", title: "Market Research Analyst" },
      ],
      makeTree(),
      "career-L1B-1",
    );
    expect(segs[1]!.nodeId).toBe("career-L1B-1");
    expect(segs[1]!.current).toBe(true);
  });

  it("resolves an L2 segment's nodeId to its branch+endpoint index", () => {
    const segs = buildBreadcrumbSegments(
      [
        { socCode: "ROOT", title: "Root" },
        { socCode: "L1A", title: "Financial Manager" },
        { socCode: "L2A2", title: "VP Operations" },
      ],
      makeTree(),
      "endpoint-L2A2-0-1",
    );
    expect(segs[2]!.nodeId).toBe("endpoint-L2A2-0-1");
    expect(segs[2]!.current).toBe(true);
  });

  it("ghost_state_when_node_filtered_out", () => {
    // Snapshot has L1A → L2A2, but the filtered tree has dropped that L1.
    const filtered = makeNode({
      soc_code: "ROOT",
      title: "Root",
      children: [makeNode({ soc_code: "L1B", title: "MRA" })],
    });

    const segs = buildBreadcrumbSegments(
      [
        { socCode: "ROOT", title: "Root" },
        { socCode: "L1A", title: "Financial Manager" },
        { socCode: "L2A2", title: "VP Operations" },
      ],
      filtered,
      "endpoint-L2A2-0-1",
    );

    // Root visible, L1A and L2A2 ghosted.
    expect(segs[0]!.hidden).toBe(false);
    expect(segs[1]!.hidden).toBe(true);
    expect(segs[1]!.nodeId).toBeNull();
    expect(segs[1]!.current).toBe(false); // hidden = never marked current
    expect(segs[2]!.hidden).toBe(true);
    expect(segs[2]!.nodeId).toBeNull();
  });
});

describe("<Breadcrumb />", () => {
  function makeSegment(
    overrides: Partial<BreadcrumbSegment>,
  ): BreadcrumbSegment {
    return {
      socCode: "13-2051",
      title: "Financial Analyst",
      nodeId: null,
      hidden: false,
      current: false,
      isRoot: false,
      ...overrides,
    };
  }

  it("renders nothing when there are 0 or 1 segments (root-only mode)", () => {
    const onClick = vi.fn();

    const { container: c1 } = render(
      <Breadcrumb segments={[]} onSegmentClick={onClick} />,
    );
    expect(c1.firstChild).toBeNull();

    const { container: c2 } = render(
      <Breadcrumb
        segments={[
          makeSegment({ socCode: "ROOT", isRoot: true, nodeId: "root-ROOT" }),
        ]}
        onSegmentClick={onClick}
      />,
    );
    expect(c2.firstChild).toBeNull();
  });

  it("renders one button per segment with stable testids", () => {
    const segments: BreadcrumbSegment[] = [
      makeSegment({ socCode: "ROOT", isRoot: true, nodeId: "root-ROOT" }),
      makeSegment({
        socCode: "L1A",
        title: "Financial Manager",
        nodeId: "career-L1A-0",
      }),
      makeSegment({
        socCode: "L2A2",
        title: "VP Operations",
        nodeId: "endpoint-L2A2-0-1",
        current: true,
      }),
    ];
    render(<Breadcrumb segments={segments} onSegmentClick={() => {}} />);
    expect(screen.getByTestId("breadcrumb-0-ROOT")).toBeInTheDocument();
    expect(screen.getByTestId("breadcrumb-1-L1A")).toBeInTheDocument();
    expect(screen.getByTestId("breadcrumb-2-L2A2")).toBeInTheDocument();
    // Current segment carries data-current="true" for downstream styling.
    expect(
      screen.getByTestId("breadcrumb-2-L2A2").getAttribute("data-current"),
    ).toBe("true");
  });

  it("clicking_segment_re_selects_that_node", () => {
    const onClick = vi.fn();
    const targetSegment = makeSegment({
      socCode: "L1A",
      title: "Financial Manager",
      nodeId: "career-L1A-0",
    });
    const segments: BreadcrumbSegment[] = [
      makeSegment({ socCode: "ROOT", isRoot: true, nodeId: "root-ROOT" }),
      targetSegment,
    ];
    render(<Breadcrumb segments={segments} onSegmentClick={onClick} />);

    fireEvent.click(screen.getByTestId("breadcrumb-1-L1A"));

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(targetSegment);
  });

  it("ghost_state_when_node_filtered_out renders strikethrough class + tooltip key", () => {
    const ghost = makeSegment({
      socCode: "L1A",
      title: "Financial Manager",
      nodeId: null,
      hidden: true,
    });
    const segments: BreadcrumbSegment[] = [
      makeSegment({ socCode: "ROOT", isRoot: true, nodeId: "root-ROOT" }),
      ghost,
    ];
    render(<Breadcrumb segments={segments} onSegmentClick={() => {}} />);

    const btn = screen.getByTestId("breadcrumb-1-L1A");
    expect(btn.getAttribute("data-hidden")).toBe("true");
    // Strikethrough class is applied to the button (state styling).
    expect(btn.className).toMatch(/line-through/);
    // Tooltip text comes through identity translator.
    expect(btn.getAttribute("title")).toBe("future.breadcrumb.hiddenTooltip");
  });

  it("ghost segment is still clickable (caller decides what to do)", () => {
    const onClick = vi.fn();
    const ghost = makeSegment({
      socCode: "L1A",
      title: "Financial Manager",
      nodeId: null,
      hidden: true,
    });
    const segments: BreadcrumbSegment[] = [
      makeSegment({ socCode: "ROOT", isRoot: true, nodeId: "root-ROOT" }),
      ghost,
    ];
    render(<Breadcrumb segments={segments} onSegmentClick={onClick} />);
    fireEvent.click(screen.getByTestId("breadcrumb-1-L1A"));
    expect(onClick).toHaveBeenCalledWith(ghost);
  });

  it("truncates long titles with ellipsis at max chars", () => {
    const longTitle = "Postsecondary Education Administrators And Curriculum Designers";
    const segments: BreadcrumbSegment[] = [
      makeSegment({ socCode: "ROOT", isRoot: true, nodeId: "root-ROOT" }),
      makeSegment({
        socCode: "L1A",
        title: longTitle,
        nodeId: "career-L1A-0",
      }),
    ];
    render(
      <Breadcrumb
        segments={segments}
        onSegmentClick={() => {}}
        maxCharsPerSegment={16}
      />,
    );
    const btn = screen.getByTestId("breadcrumb-1-L1A");
    expect(btn.textContent).toMatch(/…$/);
    expect(btn.textContent!.length).toBeLessThanOrEqual(16);
    // Full title surfaces as the title attribute (truncation tooltip).
    expect(btn.getAttribute("title")).toBe(longTitle);
  });
});
