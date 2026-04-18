/**
 * Layout computation for the career branch tree.
 * Converts a recursive TreeNode into positioned SVG elements.
 */

import type { TreeNode } from "@/types/tree";

// --- Stat color mapping ---

const STAT_COLORS: Record<string, string> = {
  ern: "#F2D477",
  roi: "#7DD4A3",
  res: "#B8A9E8",
  grw: "#7BB8E0",
  hmn: "#E88BA9",
};

const STAT_KEYS = ["ern", "roi", "res", "grw", "hmn"] as const;

// --- Column X positions ---

const COL_ROOT = 80;
const COL_BRANCH_LABEL = 260;
const COL_CAREER = 420;
const COL_CAREER_WIDTH = 116;
const COL_ENDPOINT = 620;

// --- Vertical spacing ---

const NODE_V_SPACING = 60;
const BRANCH_V_GAP = 24;

// --- Positioned types ---

export interface PositionedNode {
  id: string;
  soc_code: string;
  title: string;
  level: number;
  x: number;
  y: number;
  stats: { ern: number | null; roi: number | null; res: number | null; grw: number | null; hmn: number | null };
  bosses: {
    ai: string | null;
    loans: string | null;
    market: string | null;
    burnout: string | null;
    ceiling: string | null;
  };
  median_wage: number | null;
  education: string | null;
  parentId: string | null;
  branchColor: string;
  branchLabel: string | null;
}

export interface PositionedPath {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  gradientId: string;
  strokeWidth: number;
  opacity: number;
  group: "incoming" | "outgoing";
}

export interface TreeLayout {
  nodes: PositionedNode[];
  paths: PositionedPath[];
  branchLabels: Array<{ id: string; label: string; x: number; y: number; color: string }>;
  viewBoxWidth: number;
  viewBoxHeight: number;
  gradientDefs: Array<{ id: string; fromColor: string; toColor: string }>;
}

// --- Branch direction labels ---

function deriveBranchLabel(child: TreeNode, _index: number): string {
  if (child.education?.toLowerCase().includes("master") || child.education?.toLowerCase().includes("doctor")) {
    return "Specialize";
  }
  if (child.title.toLowerCase().includes("manager") || child.title.toLowerCase().includes("director")) {
    return "Go Management";
  }
  if (child.children.length === 0) {
    return "Pivot Lateral";
  }
  return "Stay Technical";
}

// --- Dominant stat color for a branch ---

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

// --- Main layout computation ---

export function computeLayout(tree: TreeNode): TreeLayout {
  const nodes: PositionedNode[] = [];
  const paths: PositionedPath[] = [];
  const branchLabels: TreeLayout["branchLabels"] = [];
  const gradientDefs: TreeLayout["gradientDefs"] = [];
  const gradientSet = new Set<string>();

  const branches = tree.children;
  if (branches.length === 0) {
    // Fallback: only root node
    const rootNode: PositionedNode = {
      id: `root-${tree.soc_code}`,
      soc_code: tree.soc_code,
      title: tree.title,
      level: 0,
      x: COL_ROOT,
      y: 200,
      stats: { ern: tree.ern, roi: tree.roi, res: tree.res, grw: tree.grw, hmn: tree.hmn },
      bosses: {
        ai: tree.boss_ai,
        loans: tree.boss_loans,
        market: tree.boss_market,
        burnout: tree.boss_burnout,
        ceiling: tree.boss_ceiling,
      },
      median_wage: tree.median_wage,
      education: tree.education,
      parentId: null,
      branchColor: "#F2D477",
      branchLabel: null,
    };
    nodes.push(rootNode);
    return { nodes, paths, branchLabels, viewBoxWidth: 750, viewBoxHeight: 400, gradientDefs };
  }

  // Count total vertical slots needed
  let totalSlots = 0;
  for (const branch of branches) {
    const careerChildren = branch.children;
    const endpointCount = careerChildren.reduce((sum, c) => sum + Math.max(c.children.length, 1), 0);
    totalSlots += Math.max(endpointCount, 1);
  }

  const totalHeight = totalSlots * NODE_V_SPACING + (branches.length - 1) * BRANCH_V_GAP + 120;
  const rootY = totalHeight / 2;

  // Root node
  const rootId = `root-${tree.soc_code}`;
  nodes.push({
    id: rootId,
    soc_code: tree.soc_code,
    title: tree.title,
    level: 0,
    x: COL_ROOT,
    y: rootY,
    stats: { ern: tree.ern, roi: tree.roi, res: tree.res, grw: tree.grw, hmn: tree.hmn },
    bosses: {
      ai: tree.boss_ai,
      loans: tree.boss_loans,
      market: tree.boss_market,
      burnout: tree.boss_burnout,
      ceiling: tree.boss_ceiling,
    },
    median_wage: tree.median_wage,
    education: tree.education,
    parentId: null,
    branchColor: "#7DD4A3",
    branchLabel: null,
  });

  // Place branches
  let currentY = 60;

  branches.forEach((branch, branchIdx) => {
    const branchColor = dominantStatColor(tree, branch);
    const label = deriveBranchLabel(branch, branchIdx);
    const branchId = `branch-${branchIdx}`;

    // Collect all career nodes and endpoints for this branch
    const careerChildren = branch.children.length > 0 ? branch.children : [branch];
    const isDirectBranch = branch.children.length === 0;

    // Count endpoints to determine vertical span
    let branchSlots = 0;
    for (const career of careerChildren) {
      branchSlots += Math.max(career.children.length, 1);
    }
    branchSlots = Math.max(branchSlots, 1);

    const branchSpan = branchSlots * NODE_V_SPACING;
    const branchCenterY = currentY + branchSpan / 2;

    // Gradient def
    const gradId = `grad-${branchIdx}`;
    if (!gradientSet.has(gradId)) {
      gradientSet.add(gradId);
      gradientDefs.push({ id: gradId, fromColor: "#7DD4A3", toColor: branchColor });
    }

    // Branch label
    branchLabels.push({
      id: branchId,
      label,
      x: COL_BRANCH_LABEL,
      y: branchCenterY,
      color: branchColor,
    });

    // Path: root → branch label
    paths.push({
      id: `path-root-${branchId}`,
      fromX: COL_ROOT + 28,
      fromY: rootY,
      toX: COL_BRANCH_LABEL - 40,
      toY: branchCenterY,
      gradientId: gradId,
      strokeWidth: 2.5,
      opacity: 1,
      group: "incoming",
    });

    if (isDirectBranch) {
      // Branch is a leaf — render as a career node directly
      const careerId = `career-${branch.soc_code}-${branchIdx}`;
      nodes.push({
        id: careerId,
        soc_code: branch.soc_code,
        title: branch.title,
        level: 1,
        x: COL_CAREER,
        y: branchCenterY,
        stats: { ern: branch.ern, roi: branch.roi, res: branch.res, grw: branch.grw, hmn: branch.hmn },
        bosses: {
          ai: branch.boss_ai,
          loans: branch.boss_loans,
          market: branch.boss_market,
          burnout: branch.boss_burnout,
          ceiling: branch.boss_ceiling,
        },
        median_wage: branch.median_wage,
        education: branch.education,
        parentId: rootId,
        branchColor,
        branchLabel: label,
      });

      paths.push({
        id: `path-${branchId}-${careerId}`,
        fromX: COL_BRANCH_LABEL + 40,
        fromY: branchCenterY,
        toX: COL_CAREER,
        toY: branchCenterY,
        gradientId: gradId,
        strokeWidth: 2,
        opacity: 1,
        group: "incoming",
      });
    } else {
      // Place career nodes and their endpoints
      let careerY = currentY;

      for (const career of careerChildren) {
        const endpoints = career.children;
        const careerSlots = Math.max(endpoints.length, 1);
        const careerSpan = careerSlots * NODE_V_SPACING;
        const careerCenterY = careerY + careerSpan / 2;

        const careerId = `career-${career.soc_code}-${branchIdx}`;

        nodes.push({
          id: careerId,
          soc_code: career.soc_code,
          title: career.title,
          level: 2,
          x: COL_CAREER,
          y: careerCenterY,
          stats: { ern: career.ern, roi: career.roi, res: career.res, grw: career.grw, hmn: career.hmn },
          bosses: {
            ai: career.boss_ai,
            loans: career.boss_loans,
            market: career.boss_market,
            burnout: career.boss_burnout,
            ceiling: career.boss_ceiling,
          },
          median_wage: career.median_wage,
          education: career.education,
          parentId: rootId,
          branchColor,
          branchLabel: label,
        });

        // Path: branch label → career node
        paths.push({
          id: `path-${branchId}-${careerId}`,
          fromX: COL_BRANCH_LABEL + 40,
          fromY: branchCenterY,
          toX: COL_CAREER,
          toY: careerCenterY,
          gradientId: gradId,
          strokeWidth: 2,
          opacity: 1,
          group: "incoming",
        });

        // Place endpoints
        if (endpoints.length > 0) {
          endpoints.forEach((ep, epIdx) => {
            const epY = careerY + epIdx * NODE_V_SPACING + NODE_V_SPACING / 2;
            const epId = `endpoint-${ep.soc_code}-${branchIdx}-${epIdx}`;

            nodes.push({
              id: epId,
              soc_code: ep.soc_code,
              title: ep.title,
              level: 3,
              x: COL_ENDPOINT,
              y: epY,
              stats: { ern: ep.ern, roi: ep.roi, res: ep.res, grw: ep.grw, hmn: ep.hmn },
              bosses: {
                ai: ep.boss_ai,
                loans: ep.boss_loans,
                market: ep.boss_market,
                burnout: ep.boss_burnout,
                ceiling: ep.boss_ceiling,
              },
              median_wage: ep.median_wage,
              education: ep.education,
              parentId: careerId,
              branchColor,
              branchLabel: label,
            });

            // Outgoing path: career node → endpoint
            paths.push({
              id: `path-${careerId}-${epId}`,
              fromX: COL_CAREER + COL_CAREER_WIDTH,
              fromY: careerCenterY,
              toX: COL_ENDPOINT - 20,
              toY: epY,
              gradientId: gradId,
              strokeWidth: 1.5,
              opacity: 0.7,
              group: "outgoing",
            });
          });
        }

        careerY += careerSpan;
      }
    }

    currentY += branchSpan + BRANCH_V_GAP;
  });

  return {
    nodes,
    paths,
    branchLabels,
    viewBoxWidth: 750,
    viewBoxHeight: Math.max(totalHeight, 400),
    gradientDefs,
  };
}
