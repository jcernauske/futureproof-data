/**
 * Converts a recursive TreeNode into React Flow nodes and edges for
 * /future. Resurrected from commit a8b9d4a, adapted to:
 *   - drop the PositionedNode dependency (treeLayout was deleted),
 *   - support both LR (desktop) and TB (mobile) layout directions,
 *   - emit unique node IDs that the highlight driver can target.
 */

import type { Node, Edge } from "@xyflow/react";
import type { TreeNode } from "@/types/tree";
import { pickEdgeLabel, pickEdgeHover } from "@/data/edgeLabel";

export type FlowDirection = "LR" | "TB";

type Translator = (key: string) => string;

/**
 * T2.2 — Compute the relatedness-driven stroke width + opacity.
 *
 * Combined-axis encoding over rank ∈ [1, 20] (per @fp-data-reviewer:
 * Silver tier ceiling caps real ranks at 20). Linear interpolation
 * keeps "rank 5 looks twice as bold as rank 10" intuitive.
 *
 * `null` rank clamps to rank 20 (most translucent / thinnest end) —
 * honest "we don't know" per the architect's recommendation.
 *
 * L1 edges (root → career) and L2 edges (career → endpoint) use
 * different ranges so the existing L1-vs-L2 hierarchy is preserved.
 */
function relatednessStyle(
  level: "root-career" | "career-endpoint",
  rank: number | null,
): { strokeWidth: number; opacity: number } {
  const r = Math.max(1, Math.min(20, rank ?? 20));
  const t = (r - 1) / 19; // 0 at rank 1 (closest), 1 at rank 20 (stretch)
  const ranges =
    level === "root-career"
      ? { wMax: 3.2, wMin: 1.4, oMax: 0.95, oMin: 0.4 }
      : { wMax: 2.4, wMin: 0.8, oMax: 0.8, oMin: 0.28 };
  return {
    strokeWidth: ranges.wMax + (ranges.wMin - ranges.wMax) * t,
    opacity: ranges.oMax + (ranges.oMin - ranges.oMax) * t,
  };
}

const STAT_COLORS: Record<string, string> = {
  ern: "#F2D477",
  roi: "#7DD4A3",
  res: "#B8A9E8",
  grw: "#7BB8E0",
  hmn: "#E88BA9",
};

const STAT_KEYS = ["ern", "roi", "res", "grw", "hmn"] as const;

// Rank-axis spacing per level (root → career → endpoint).
// "Rank" = primary flow axis; for LR it's X, for TB it's Y.
// Branch-label nodes were removed — the old heuristic ("Stay Technical"
// / "Specialize" / "Go Management") produced duplicate labels across
// most L1 branches and added editorial noise the data didn't earn.
const RANK_AT_LEVEL = {
  root: 0,
  career: 280,
  endpoint: 540,
};

// Slot-axis spacing.
// "Slot" = perpendicular axis; for LR it's Y, for TB it's X.
// Tightened from the original 80/40 — with depth=2 and 12 L1 branches
// fanning into ~5 L2 children each, the original spacing produced a
// ~4800px column that fitView could only render at ~0.10 zoom (nodes
// became unreadable). The staircase per-branch rank offset (below)
// spreads branches diagonally so we can afford a tad more vertical
// room per endpoint without re-bloating the canvas:
//   - The endpoint cluster (avatar + 2-line label) is ~50px tall.
//     SLOT_PER_NODE was 36 → labels stacked tight enough to brush each
//     other AND collide with edge-label pills (T1.1). 48 gives ~4-6px
//     of breathing room between clusters without bloating the canvas
//     (a +33% vertical expansion vs the previous +50%+ alternatives).
//   - SLOT_BRANCH_GAP keeps a small visible break between adjacent
//     branches' L2 columns.
const SLOT_PER_NODE = 48;
const SLOT_BRANCH_GAP = 10;

// Staircase: each successive branch is offset along the rank axis so
// the tree spreads diagonally instead of stacking in one tall column.
// Improves the aspect ratio in LR mode (root left, branches cascading
// to the lower-right) — viewport, fit-view zoom, and the minimap all
// read better when the canvas is closer to square.
const STAIR_RANK_PER_BRANCH = 90;

export interface FlowNodeData extends Record<string, unknown> {
  nodeType: "root" | "career" | "endpoint";
  title: string;
  socCode: string;
  level: number;
  emoji: string;
  medianWage: number | null;
  education: string | null;
  branchColor: string;
  branchLabel: string | null;
  direction: FlowDirection;
  flashing: boolean;
  /** When set during a tour-chip flash, the node renders a small
   *  rarity pill that fades in with the flash and out with it. Only
   *  populated for "stretch" / "longshot" paths (direct/adjacent get
   *  nothing — absence is the signal). */
  flashRarity?: "stretch" | "longshot" | null;
  selected: boolean;
  dimmed: boolean;
  stats: {
    ern: number | null;
    roi: number | null;
    res: number | null;
    grw: number | null;
    hmn: number | null;
  };
}

function dominantStatColor(root: TreeNode, child: TreeNode): string {
  let maxDelta = -Infinity;
  let maxStat = "ern";
  for (const key of STAT_KEYS) {
    const rootVal = root[key];
    const childVal = child[key];
    if (rootVal != null && childVal != null) {
      const delta = childVal - rootVal;
      if (delta > maxDelta) {
        maxDelta = delta;
        maxStat = key;
      }
    }
  }
  return STAT_COLORS[maxStat] ?? "#F2D477";
}

function makeStats(node: TreeNode) {
  return {
    ern: node.ern,
    roi: node.roi,
    res: node.res,
    grw: node.grw,
    hmn: node.hmn,
  };
}

/**
 * Map (rank, slot) → React Flow (x, y) given a direction.
 *   LR: rank → x, slot → y
 *   TB: rank → y, slot → x
 */
function place(
  rank: number,
  slot: number,
  direction: FlowDirection,
): { x: number; y: number } {
  if (direction === "LR") return { x: rank, y: slot };
  return { x: slot, y: rank };
}

export interface FlowLayoutResult {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
}

export function treeToFlow(
  tree: TreeNode,
  emoji: string,
  direction: FlowDirection = "LR",
  t: Translator = (key: string) => key,
): FlowLayoutResult {
  const nodes: Node<FlowNodeData>[] = [];
  const edges: Edge[] = [];

  const branches = tree.children;
  const rootId = `root-${tree.soc_code}`;
  const rootColor = "#7DD4A3";

  const baseData = {
    direction,
    flashing: false,
    selected: false,
    dimmed: false,
  } as const;

  if (branches.length === 0) {
    nodes.push({
      id: rootId,
      type: "root",
      position: place(RANK_AT_LEVEL.root, 200, direction),
      width: 140,
      height: 140,
      data: {
        ...baseData,
        nodeType: "root",
        title: tree.title,
        socCode: tree.soc_code,
        level: 0,
        emoji,
        medianWage: tree.median_wage,
        education: tree.education,
        branchColor: rootColor,
        branchLabel: null,
        stats: makeStats(tree),
      },
    });
    return { nodes, edges };
  }

  let totalSlots = 0;
  for (const branch of branches) {
    // Each L1 branch occupies max(L2 count, 1) slots — its career node
    // centers vertically over its L2 endpoints.
    totalSlots += Math.max(branch.children.length, 1);
  }
  const totalSpan =
    totalSlots * SLOT_PER_NODE +
    (branches.length - 1) * SLOT_BRANCH_GAP +
    120;
  const rootSlot = totalSpan / 2;

  nodes.push({
    id: rootId,
    type: "root",
    position: place(RANK_AT_LEVEL.root, rootSlot - 60, direction),
    width: 140,
    height: 140,
    data: {
      ...baseData,
      nodeType: "root",
      title: tree.title,
      socCode: tree.soc_code,
      level: 0,
      emoji,
      medianWage: tree.median_wage,
      education: tree.education,
      branchColor: rootColor,
      branchLabel: null,
      stats: makeStats(tree),
    },
  });

  let cursor = 60;

  branches.forEach((branch, branchIdx) => {
    const branchColor = dominantStatColor(tree, branch);

    // Staircase: shift each branch's L1 + L2 columns further along
    // the rank axis. Branch 0 sits at the base column, each
    // subsequent branch is STAIR_RANK_PER_BRANCH further out.
    const branchRankOffset = branchIdx * STAIR_RANK_PER_BRANCH;
    const careerRank = RANK_AT_LEVEL.career + branchRankOffset;
    const endpointRank = RANK_AT_LEVEL.endpoint + branchRankOffset;

    // Each L1 branch always has a career node. Its L2 children (if any)
    // become endpoints. No more branch-label intermediary.
    const endpoints = branch.children;
    const careerSlots = Math.max(endpoints.length, 1);
    const careerSpan = careerSlots * SLOT_PER_NODE;
    const careerCenter = cursor + careerSpan / 2;
    const careerId = `career-${branch.soc_code}-${branchIdx}`;

    nodes.push({
      id: careerId,
      type: "career",
      position: place(careerRank, careerCenter - 18, direction),
      width: 200,
      height: 56,
      data: {
        ...baseData,
        nodeType: "career",
        title: branch.title,
        socCode: branch.soc_code,
        level: 1,
        emoji,
        medianWage: branch.median_wage,
        education: branch.education,
        branchColor,
        branchLabel: null,
        stats: makeStats(branch),
      },
    });

    {
      const style = relatednessStyle("root-career", branch.relatedness);
      edges.push({
        id: `edge-root-${careerId}`,
        source: rootId,
        target: careerId,
        type: "withLabel",
        data: {
          label: pickEdgeLabel(tree, branch, t),
          hoverContext: pickEdgeHover(tree, branch),
          stroke: branchColor,
          strokeWidth: style.strokeWidth,
          opacity: style.opacity,
        },
      });
    }

    endpoints.forEach((ep, epIdx) => {
      const epSlot = cursor + epIdx * SLOT_PER_NODE + SLOT_PER_NODE / 2;
      const epId = `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`;

      nodes.push({
        id: epId,
        type: "endpoint",
        position: place(endpointRank, epSlot - 25, direction),
        width: 220,
        height: 50,
        data: {
          ...baseData,
          nodeType: "endpoint",
          title: ep.title,
          socCode: ep.soc_code,
          level: 2,
          emoji,
          medianWage: ep.median_wage,
          education: ep.education,
          branchColor,
          branchLabel: null,
          stats: makeStats(ep),
        },
      });

      {
        const style = relatednessStyle("career-endpoint", ep.relatedness);
        edges.push({
          id: `edge-${careerId}-${epId}`,
          source: careerId,
          target: epId,
          type: "withLabel",
          data: {
            label: pickEdgeLabel(branch, ep, t),
            hoverContext: pickEdgeHover(branch, ep),
            stroke: branchColor,
            strokeWidth: style.strokeWidth,
            opacity: style.opacity,
          },
        });
      }
    });

    cursor += careerSpan + SLOT_BRANCH_GAP;
  });

  return { nodes, edges };
}
