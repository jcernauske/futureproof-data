/**
 * Converts a recursive TreeNode into React Flow nodes and edges for
 * /future. Resurrected from commit a8b9d4a, adapted to:
 *   - drop the PositionedNode dependency (treeLayout was deleted),
 *   - support both LR (desktop) and TB (mobile) layout directions,
 *   - emit unique node IDs that the highlight driver can target.
 */

import type { Node, Edge } from "@xyflow/react";
import type { TreeNode } from "@/types/tree";

export type FlowDirection = "LR" | "TB";

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
// became unreadable). 48/12 keeps siblings legible without colliding.
const SLOT_PER_NODE = 48;
const SLOT_BRANCH_GAP = 12;

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
      position: place(RANK_AT_LEVEL.career, careerCenter - 18, direction),
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

    edges.push({
      id: `edge-root-${careerId}`,
      source: rootId,
      target: careerId,
      type: "default",
      style: { stroke: branchColor, strokeWidth: 2, opacity: 0.8 },
    });

    endpoints.forEach((ep, epIdx) => {
      const epSlot = cursor + epIdx * SLOT_PER_NODE + SLOT_PER_NODE / 2;
      const epId = `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`;

      nodes.push({
        id: epId,
        type: "endpoint",
        position: place(RANK_AT_LEVEL.endpoint, epSlot - 25, direction),
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

      edges.push({
        id: `edge-${careerId}-${epId}`,
        source: careerId,
        target: epId,
        type: "default",
        style: { stroke: branchColor, strokeWidth: 1.5, opacity: 0.5 },
      });
    });

    cursor += careerSpan + SLOT_BRANCH_GAP;
  });

  return { nodes, edges };
}
