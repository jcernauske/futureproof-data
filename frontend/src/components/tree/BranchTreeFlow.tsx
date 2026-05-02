import { useCallback, useEffect, useMemo, useRef } from "react";
import { ReactFlow, MiniMap, Controls, useReactFlow } from "@xyflow/react";
import type { Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "@/styles/reactflow-dark.css";

import {
  treeToFlow,
  type FlowDirection,
  type FlowNodeData,
} from "@/data/treeFlowLayout";
import { FlowRootNode } from "./flow/FlowRootNode";
import { FlowCareerNode } from "./flow/FlowCareerNode";
import { FlowEndpointNode } from "./flow/FlowEndpointNode";
import { EdgeWithLabel } from "./flow/EdgeWithLabel";
import { useT } from "@/i18n/useT";
import type { TreeNode } from "@/types/tree";

const nodeTypes = {
  root: FlowRootNode,
  career: FlowCareerNode,
  endpoint: FlowEndpointNode,
} as const;

const edgeTypes = {
  withLabel: EdgeWithLabel,
} as const;

// View tuning for the post-fingerprint re-anchor.
//   - LEFT_ANCHOR_FRACTION = 0.15 → the root node sits 15% in from
//     the viewport's left edge after each filter / build change,
//     vertically centered on its own y. Matches the visual brief:
//     "root in the middle on the far left side."
//   - VIEWPORT_HEIGHT_USAGE = 0.85 → the canvas height should fill
//     ~85% of the viewport height; the chosen zoom is derived from
//     this to make the tree feel tight without overflowing top/
//     bottom edges by too much.
//   - [MIN_ZOOM, MAX_ZOOM] clamp the derived zoom so:
//       - very tall trees (12 branches → ~2400px) still get a
//         readable zoom (don't go below 0.5).
//       - tiny filtered subsets (1-2 branches) don't blow up to
//         comical sizes (don't exceed 1.0).
const LEFT_ANCHOR_FRACTION = 0.15;
const VIEWPORT_HEIGHT_USAGE = 0.85;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 1.0;
const FALLBACK_ZOOM = 0.7;

interface FitOnTreeChangeProps {
  fingerprint: string;
  rootId: string;
  /** Bounds of all nodes in canvas coordinates, used for adaptive zoom. */
  bounds: { width: number; height: number };
  containerRef: React.RefObject<HTMLDivElement | null>;
}

/**
 * Re-anchors the viewport whenever the tree fingerprint changes
 * (filters applied/removed, build switched, layout direction
 * flipped). The default fitView centers the bounding box, which
 * pulls the root toward canvas-center horizontally on tall trees.
 * This component custom-fits with the root pinned 15% from the
 * viewport's left edge and vertically centered on the root's y.
 *
 * Zoom is derived from bounds height so filtered subsets (small
 * trees) zoom in; full trees stay at the floor.
 *
 * The `requestAnimationFrame` defer is critical: when filters
 * change, the React render that emits the new nodes and the effect
 * that calls setCenter happen synchronously, but xyflow's internal
 * store doesn't absorb the new node set until the next frame.
 */
function FitOnTreeChange({
  fingerprint,
  rootId,
  bounds,
  containerRef,
}: FitOnTreeChangeProps) {
  const { setCenter, getNode } = useReactFlow();
  useEffect(() => {
    let frame2 = 0;
    const frame1 = window.requestAnimationFrame(() => {
      const root = getNode(rootId);
      const vpW = containerRef.current?.clientWidth ?? 0;
      const vpH = containerRef.current?.clientHeight ?? 0;
      if (!root || vpW === 0 || vpH === 0 || bounds.height === 0) {
        // One-frame stragglers — try again on frame 2 with a snap.
        frame2 = window.requestAnimationFrame(() => {
          const root2 = getNode(rootId);
          const vpW2 = containerRef.current?.clientWidth ?? 0;
          const vpH2 = containerRef.current?.clientHeight ?? 0;
          if (!root2 || vpW2 === 0 || vpH2 === 0 || bounds.height === 0) return;
          applyAnchoredCenter(root2, bounds, vpW2, vpH2, setCenter, 0);
        });
        return;
      }
      applyAnchoredCenter(root, bounds, vpW, vpH, setCenter, 500);
    });
    return () => {
      window.cancelAnimationFrame(frame1);
      if (frame2) window.cancelAnimationFrame(frame2);
    };
  }, [fingerprint, rootId, bounds, containerRef, setCenter, getNode]);
  return null;
}

/**
 * Imperatively pan + zoom the viewport to a specific node when the
 * `target` prop changes. The `ts` field gates re-runs so a fresh
 * mount or a same-id re-issue still pans (vs. relying on shallow
 * nodeId equality). Used by the tour chip navigate-flash sequence —
 * see `FutureScreen.handlePlayTour`.
 */
function PanToTarget({ target }: { target: PanTarget | null }) {
  const { setCenter, getNode } = useReactFlow();
  const lastTsRef = useRef<number | null>(null);
  useEffect(() => {
    if (!target) return;
    if (lastTsRef.current === target.ts) return;
    lastTsRef.current = target.ts;
    const node = getNode(target.nodeId);
    if (!node) return;
    const w = node.measured?.width ?? node.width ?? 0;
    const h = node.measured?.height ?? node.height ?? 0;
    const cx = node.position.x + w / 2;
    const cy = node.position.y + h / 2;
    void setCenter(cx, cy, {
      zoom: target.zoom ?? 1.4,
      duration: target.duration ?? 550,
    });
  }, [target, setCenter, getNode]);
  return null;
}

function applyAnchoredCenter(
  root: Node,
  bounds: { width: number; height: number },
  vpW: number,
  vpH: number,
  setCenter: ReturnType<typeof useReactFlow>["setCenter"],
  duration: number,
) {
  const targetCanvasHeight = vpH * VIEWPORT_HEIGHT_USAGE;
  const zoomFromHeight =
    bounds.height > 0 ? targetCanvasHeight / bounds.height : FALLBACK_ZOOM;
  const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoomFromHeight));

  // setCenter(cx, cy, ...) places canvas point (cx, cy) at viewport
  // center. To put root at viewport (LEFT_ANCHOR_FRACTION * vpW,
  // vpH / 2), the canvas center must be offset rightward from root
  // by `vpW * (0.5 - LEFT_ANCHOR_FRACTION) / zoom`.
  const rootHeight = root.measured?.height ?? root.height ?? 0;
  const rootCenterY = root.position.y + rootHeight / 2;
  const cx = (vpW * (0.5 - LEFT_ANCHOR_FRACTION)) / zoom;
  const cy = rootCenterY;

  void setCenter(cx, cy, { zoom, duration });
}

/**
 * Imperative pan-target signal for the tour-chip navigate-flash
 * sequence. The `ts` field is the gate — same nodeId can be panned to
 * twice in a row by bumping ts, and a stale signal (matching ts) is a
 * no-op.
 */
export interface PanTarget {
  nodeId: string;
  ts: number;
  zoom?: number;
  duration?: number;
}

interface BranchTreeFlowProps {
  tree: TreeNode;
  emoji: string;
  direction: FlowDirection;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  highlightedNodeIds?: ReadonlySet<string>;
  /**
   * When set, pans + zooms the viewport to center on the given node.
   * Used by the tour chip navigate-flash sequence so highlights are
   * visible at fitView zoom (where the flash glow disappears).
   */
  panTarget?: PanTarget | null;
  /**
   * Bumping this number forces FitOnTreeChange to re-fit even when
   * the tree shape hasn't changed. Used by the companion rail when
   * its width settles to a new value — the tree pane's container
   * width changes but React Flow doesn't auto-re-fit on container
   * resize alone.
   */
  refitToken?: number;
  /**
   * Map of nodeId → path-rarity tier for nodes the tour chip is
   * flashing. Only `"stretch"` and `"longshot"` entries are passed
   * through; the node renders a small floating pill that fades in
   * with the flash and out with it, giving the student an in-tree
   * signal that the highlighted result is statistically unusual.
   */
  flashRarityById?: ReadonlyMap<string, "stretch" | "longshot">;
}

export function BranchTreeFlow({
  tree,
  emoji,
  direction,
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds,
  panTarget,
  refitToken,
  flashRarityById,
}: BranchTreeFlowProps) {
  const t = useT();
  const { nodes: baseNodes, edges: baseEdges } = useMemo(
    () => treeToFlow(tree, emoji, direction, t),
    [tree, emoji, direction, t],
  );

  // Mark edges as selected-adjacent (parent-of-selected or child-of-selected)
  // so EdgeWithLabel can lift its pill emphasis. Compared to selection
  // dimming on nodes, this is purely visual sugar — does not change
  // pointer events or hit-testing.
  const edges = useMemo(() => {
    if (!selectedNodeId) return baseEdges;
    return baseEdges.map((e) => {
      const adjacent = e.source === selectedNodeId || e.target === selectedNodeId;
      if (!adjacent) return e;
      return {
        ...e,
        data: { ...(e.data ?? {}), selectedAdjacent: true },
      };
    });
  }, [baseEdges, selectedNodeId]);

  const nodes = useMemo(
    () =>
      baseNodes.map((n) => {
        const flashing = highlightedNodeIds?.has(n.id) ?? false;
        const selected = n.id === selectedNodeId;
        const dimmed = selectedNodeId != null && !selected;
        const flashRarity = flashing
          ? (flashRarityById?.get(n.id) ?? null)
          : null;
        return {
          ...n,
          data: { ...n.data, flashing, selected, dimmed, flashRarity },
        };
      }),
    [baseNodes, selectedNodeId, highlightedNodeIds, flashRarityById],
  );

  // Fingerprint of the structural shape — used by FitOnTreeChange to
  // detect filter-driven shape shifts. Excludes selection/highlight/
  // dim state so a chip click doesn't trigger a re-fit; only true
  // node-set changes do.
  const treeFingerprint = useMemo(
    () =>
      `${direction}|${baseNodes.length}|${baseNodes
        .map((n) => n.id)
        .join(",")}|refit-${refitToken ?? 0}`,
    [direction, baseNodes, refitToken],
  );

  // Find the root node id + canvas bounds for the anchored re-fit.
  const rootId = useMemo(
    () => baseNodes.find((n) => n.data.nodeType === "root")?.id ?? "",
    [baseNodes],
  );
  const treeBounds = useMemo(() => {
    if (baseNodes.length === 0) return { width: 0, height: 0 };
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    for (const n of baseNodes) {
      const w = n.width ?? 0;
      const h = n.height ?? 0;
      const x = n.position.x;
      const y = n.position.y;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x + w > maxX) maxX = x + w;
      if (y + h > maxY) maxY = y + h;
    }
    return {
      width: Math.max(0, maxX - minX),
      height: Math.max(0, maxY - minY),
    };
  }, [baseNodes]);

  const containerRef = useRef<HTMLDivElement>(null);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string; data: FlowNodeData }) => {
      onSelectNode(node.id);
    },
    [onSelectNode],
  );

  const handlePaneClick = useCallback(() => {
    onSelectNode(null);
  }, [onSelectNode]);

  // Minimap node fill — root pops green, L1/L2 inherit their branch
  // color so the minimap reads as a colored map of the tree, not a
  // wall of grey rectangles.
  const miniMapNodeColor = useCallback(
    (node: { data?: { nodeType?: string; branchColor?: string } }) => {
      if (node.data?.nodeType === "root") return "#7DD4A3";
      return node.data?.branchColor ?? "#5b6190";
    },
    [],
  );

  // Slightly larger size for L1/L2 in minimap so the dots are
  // distinguishable; root gets a bigger swatch since it's the anchor.
  const miniMapNodeStrokeColor = useCallback(
    (node: { data?: { nodeType?: string } }) =>
      node.data?.nodeType === "root" ? "#F5F0E8" : "rgba(245,240,232,0.4)",
    [],
  );

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      data-testid="region-future-tree"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        // No `fitView` prop: FitOnTreeChange handles initial framing
        // and every subsequent re-anchor from a single code path so
        // the root always lands on the left at the same zoom band.
        minZoom={0.2}
        maxZoom={2.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnPinch
        proOptions={{ hideAttribution: false }}
      >
        <FitOnTreeChange
          fingerprint={treeFingerprint}
          rootId={rootId}
          bounds={treeBounds}
          containerRef={containerRef}
        />
        {/* T1.2 — imperative pan target for tour chip navigate-flash. */}
        <PanToTarget target={panTarget ?? null} />
        <MiniMap
          // Read-only-ish minimap — pannable lets the student drag the
          // viewport rectangle to navigate; zoomable lets pinch/scroll
          // zoom the main canvas while hovering the minimap.
          pannable
          zoomable
          // Light mask so unviewed area stays visible (the original
          // 0.85 opacity rendered the entire minimap as a black slab
          // with a tiny rectangle on it).
          maskColor="rgba(15, 17, 41, 0.35)"
          maskStrokeColor="var(--color-accent-info)"
          maskStrokeWidth={2}
          // Larger node footprint so dots are visible at minimap scale.
          nodeColor={miniMapNodeColor}
          nodeStrokeColor={miniMapNodeStrokeColor}
          nodeStrokeWidth={2}
          nodeBorderRadius={3}
          // Background lighter than the canvas so the minimap reads as
          // a distinct surface, not a hole punched in the tree pane.
          style={{
            background: "var(--color-bg-mid)",
            border: "1px solid var(--color-border-subtle)",
            borderRadius: 8,
          }}
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
