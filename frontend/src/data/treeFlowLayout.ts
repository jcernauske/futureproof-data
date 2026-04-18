/**
 * Converts a recursive TreeNode into React Flow nodes and edges.
 * Reuses color/label logic from treeLayout.ts.
 */

import type { Node, Edge } from "@xyflow/react";
import type { TreeNode } from "@/types/tree";
import type { PositionedNode } from "@/data/treeLayout";

// --- Stat colors (shared with treeLayout.ts) ---

const STAT_COLORS: Record<string, string> = {
  ern: "#F2D477",
  roi: "#7DD4A3",
  res: "#B8A9E8",
  grw: "#7BB8E0",
  hmn: "#E88BA9",
};

const STAT_KEYS = ["ern", "roi", "res", "grw", "hmn"] as const;

// --- Column X positions (scaled for HTML nodes) ---

const COL_ROOT = 0;
const COL_BRANCH_LABEL = 250;
const COL_CAREER = 500;
const COL_ENDPOINT = 800;

// --- Vertical spacing ---

const NODE_V_SPACING = 80;
const BRANCH_V_GAP = 40;

// --- Node data type ---

export interface FlowNodeData extends Record<string, unknown> {
  nodeType: "root" | "branchLabel" | "career" | "endpoint";
  title: string;
  socCode: string;
  level: number;
  emoji: string;
  medianWage: number | null;
  education: string | null;
  branchColor: string;
  branchLabel: string | null;
  stats: {
    ern: number | null;
    roi: number | null;
    res: number | null;
    grw: number | null;
    hmn: number | null;
  };
  bosses: {
    ai: string | null;
    loans: string | null;
    market: string | null;
    burnout: string | null;
    ceiling: string | null;
  };
}

// --- Helpers ---

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

function deriveBranchLabel(child: TreeNode): string {
  if (
    child.education?.toLowerCase().includes("master") ||
    child.education?.toLowerCase().includes("doctor")
  ) {
    return "Specialize";
  }
  if (
    child.title.toLowerCase().includes("manager") ||
    child.title.toLowerCase().includes("director")
  ) {
    return "Go Management";
  }
  if (child.children.length === 0) {
    return "Pivot Lateral";
  }
  return "Stay Technical";
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

function makeBosses(node: TreeNode) {
  return {
    ai: node.boss_ai,
    loans: node.boss_loans,
    market: node.boss_market,
    burnout: node.boss_burnout,
    ceiling: node.boss_ceiling,
  };
}

function toPositionedNode(
  id: string,
  node: TreeNode,
  level: number,
  x: number,
  y: number,
  parentId: string | null,
  branchColor: string,
  branchLabel: string | null,
): PositionedNode {
  return {
    id,
    soc_code: node.soc_code,
    title: node.title,
    level,
    x,
    y,
    stats: makeStats(node),
    bosses: makeBosses(node),
    median_wage: node.median_wage,
    education: node.education,
    parentId,
    branchColor,
    branchLabel,
  };
}

// --- Main conversion ---

export interface FlowLayoutResult {
  nodes: Node<FlowNodeData>[];
  edges: Edge[];
  nodeMap: Map<string, PositionedNode>;
}

export function treeToFlow(tree: TreeNode, emoji: string): FlowLayoutResult {
  const nodes: Node<FlowNodeData>[] = [];
  const edges: Edge[] = [];
  const nodeMap = new Map<string, PositionedNode>();

  const branches = tree.children;

  // Root node
  const rootId = `root-${tree.soc_code}`;
  const rootColor = "#7DD4A3";

  if (branches.length === 0) {
    nodes.push({
      id: rootId,
      type: "root",
      position: { x: COL_ROOT, y: 200 },
      data: {
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
        bosses: makeBosses(tree),
      },
    });
    nodeMap.set(
      rootId,
      toPositionedNode(rootId, tree, 0, COL_ROOT, 200, null, rootColor, null),
    );
    return { nodes, edges, nodeMap };
  }

  // Count total slots for vertical sizing
  let totalSlots = 0;
  for (const branch of branches) {
    const careerChildren = branch.children;
    const epCount = careerChildren.reduce(
      (sum, c) => sum + Math.max(c.children.length, 1),
      0,
    );
    totalSlots += Math.max(epCount, 1);
  }

  const totalHeight =
    totalSlots * NODE_V_SPACING +
    (branches.length - 1) * BRANCH_V_GAP +
    120;
  const rootY = totalHeight / 2;

  nodes.push({
    id: rootId,
    type: "root",
    position: { x: COL_ROOT, y: rootY - 60 },
    data: {
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
      bosses: makeBosses(tree),
    },
  });
  nodeMap.set(
    rootId,
    toPositionedNode(rootId, tree, 0, COL_ROOT, rootY, null, rootColor, null),
  );

  let currentY = 60;

  branches.forEach((branch, branchIdx) => {
    const branchColor = dominantStatColor(tree, branch);
    const label = deriveBranchLabel(branch);
    const branchLabelId = `branch-${branchIdx}`;

    const careerChildren =
      branch.children.length > 0 ? branch.children : [branch];
    const isDirectBranch = branch.children.length === 0;

    let branchSlots = 0;
    for (const career of careerChildren) {
      branchSlots += Math.max(career.children.length, 1);
    }
    branchSlots = Math.max(branchSlots, 1);

    const branchSpan = branchSlots * NODE_V_SPACING;
    const branchCenterY = currentY + branchSpan / 2;

    // Branch label node
    nodes.push({
      id: branchLabelId,
      type: "branchLabel",
      position: { x: COL_BRANCH_LABEL, y: branchCenterY - 18 },
      data: {
        nodeType: "branchLabel",
        title: label,
        socCode: branch.soc_code,
        level: -1,
        emoji,
        medianWage: null,
        education: null,
        branchColor,
        branchLabel: label,
        stats: makeStats(branch),
        bosses: makeBosses(branch),
      },
    });

    // Edge: root → branch label
    edges.push({
      id: `edge-root-${branchLabelId}`,
      source: rootId,
      target: branchLabelId,
      type: "default",
      style: { stroke: branchColor, strokeWidth: 2.5, opacity: 0.8 },
      animated: false,
    });

    if (isDirectBranch) {
      const careerId = `career-${branch.soc_code}-${branchIdx}`;

      nodes.push({
        id: careerId,
        type: "career",
        position: { x: COL_CAREER, y: branchCenterY - 18 },
        data: {
          nodeType: "career",
          title: branch.title,
          socCode: branch.soc_code,
          level: 1,
          emoji,
          medianWage: branch.median_wage,
          education: branch.education,
          branchColor,
          branchLabel: label,
          stats: makeStats(branch),
          bosses: makeBosses(branch),
        },
      });
      nodeMap.set(
        careerId,
        toPositionedNode(
          careerId,
          branch,
          1,
          COL_CAREER,
          branchCenterY,
          rootId,
          branchColor,
          label,
        ),
      );

      edges.push({
        id: `edge-${branchLabelId}-${careerId}`,
        source: branchLabelId,
        target: careerId,
        type: "default",
        style: { stroke: branchColor, strokeWidth: 2, opacity: 0.8 },
      });
    } else {
      let careerY = currentY;

      for (const career of careerChildren) {
        const endpoints = career.children;
        const careerSlots = Math.max(endpoints.length, 1);
        const careerSpan = careerSlots * NODE_V_SPACING;
        const careerCenterY = careerY + careerSpan / 2;

        const careerId = `career-${career.soc_code}-${branchIdx}`;

        nodes.push({
          id: careerId,
          type: "career",
          position: { x: COL_CAREER, y: careerCenterY - 18 },
          data: {
            nodeType: "career",
            title: career.title,
            socCode: career.soc_code,
            level: 2,
            emoji,
            medianWage: career.median_wage,
            education: career.education,
            branchColor,
            branchLabel: label,
            stats: makeStats(career),
            bosses: makeBosses(career),
          },
        });
        nodeMap.set(
          careerId,
          toPositionedNode(
            careerId,
            career,
            2,
            COL_CAREER,
            careerCenterY,
            rootId,
            branchColor,
            label,
          ),
        );

        edges.push({
          id: `edge-${branchLabelId}-${careerId}`,
          source: branchLabelId,
          target: careerId,
          type: "default",
          style: { stroke: branchColor, strokeWidth: 2, opacity: 0.8 },
        });

        if (endpoints.length > 0) {
          endpoints.forEach((ep, epIdx) => {
            const epY =
              careerY + epIdx * NODE_V_SPACING + NODE_V_SPACING / 2;
            const epId = `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`;

            nodes.push({
              id: epId,
              type: "endpoint",
              position: { x: COL_ENDPOINT, y: epY - 25 },
              data: {
                nodeType: "endpoint",
                title: ep.title,
                socCode: ep.soc_code,
                level: 3,
                emoji,
                medianWage: ep.median_wage,
                education: ep.education,
                branchColor,
                branchLabel: label,
                stats: makeStats(ep),
                bosses: makeBosses(ep),
              },
            });
            nodeMap.set(
              epId,
              toPositionedNode(
                epId,
                ep,
                3,
                COL_ENDPOINT,
                epY,
                careerId,
                branchColor,
                label,
              ),
            );

            edges.push({
              id: `edge-${careerId}-${epId}`,
              source: careerId,
              target: epId,
              type: "default",
              style: {
                stroke: branchColor,
                strokeWidth: 1.5,
                opacity: 0.5,
              },
            });
          });
        }

        careerY += careerSpan;
      }
    }

    currentY += branchSpan + BRANCH_V_GAP;
  });

  return { nodes, edges, nodeMap };
}
