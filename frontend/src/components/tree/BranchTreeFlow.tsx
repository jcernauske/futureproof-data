import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "@/styles/reactflow-dark.css";

import { treeToFlow } from "@/data/treeFlowLayout";
import { FlowRootNode } from "./flow/FlowRootNode";
import { FlowBranchLabel } from "./flow/FlowBranchLabel";
import { FlowCareerNode } from "./flow/FlowCareerNode";
import { FlowEndpointNode } from "./flow/FlowEndpointNode";
import type { TreeNode } from "@/types/tree";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const nodeTypes: Record<string, any> = {
  root: FlowRootNode,
  branchLabel: FlowBranchLabel,
  career: FlowCareerNode,
  endpoint: FlowEndpointNode,
};

interface BranchTreeFlowProps {
  tree: TreeNode;
  emoji: string;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  /**
   * Set of node ids currently flashing. Each id is independently
   * scheduled in/out by the screen so multiple simultaneous matches
   * (one Gemma response naming 3 branches) all animate concurrently
   * instead of overwriting each other.
   *
   * Invariant (feature-tree-as-map.md fp-architect condition #5):
   * ``onHighlight`` (the driver's emit callback that drives this prop)
   * MUST be presentational only. Wiring it into ``selectedNodeId`` will
   * create an infinite re-fire loop (assistant names branch → highlight
   * fires → selection moves → opener re-fires → assistant names another
   * branch → …).
   */
  highlightedNodeIds?: ReadonlySet<string>;
  /** When true, render the map in compact form: drop the minimap and shrink controls. */
  compact?: boolean;
  /** Override the default tree height. Used by /branch-tree's tree-as-map view. */
  heightClassName?: string;
}

export function BranchTreeFlow({
  tree,
  emoji,
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds,
  compact = false,
  heightClassName = "h-[75vh]",
}: BranchTreeFlowProps) {
  const { nodes: baseNodes, edges } = useMemo(
    () => treeToFlow(tree, emoji),
    [tree, emoji],
  );

  // Apply selection/dimming/highlight state to node data + className.
  // ``branch-flash`` className triggers the CSS keyframe animation in
  // ``reactflow-dark.css`` — applied at the node-wrapper level so the
  // 4 FlowNode components stay framer-motion-free.
  const nodes = useMemo(
    () =>
      baseNodes.map((n) => {
        const flashing = highlightedNodeIds?.has(n.id) ?? false;
        return {
          ...n,
          selected: n.id === selectedNodeId,
          className: flashing ? "branch-flash" : undefined,
          data: {
            ...n.data,
            selected: n.id === selectedNodeId,
            dimmed:
              selectedNodeId != null && n.id !== selectedNodeId,
            highlighted: flashing,
          },
        };
      }),
    [baseNodes, selectedNodeId, highlightedNodeIds],
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: any) => {
      onSelectNode(node.id);
    },
    [onSelectNode],
  );

  const handlePaneClick = useCallback(() => {
    onSelectNode(null);
  }, [onSelectNode]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const miniMapColor = useCallback(
    (node: any) =>
      node.data?.branchColor ?? "#7DD4A3",
    [],
  );

  return (
    <div
      className={`w-full ${heightClassName}`}
      data-testid="region-branch-tree"
      data-compact={compact ? "true" : "false"}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        fitView
        fitViewOptions={
          compact
            ? { padding: 0.1, minZoom: 0.55, maxZoom: 1.0 }
            : { padding: 0.3 }
        }
        minZoom={0.1}
        maxZoom={2.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnPinch
        proOptions={{ hideAttribution: false }}
      >
        {!compact && (
          <MiniMap
            nodeColor={miniMapColor}
            maskColor="rgba(15,17,41,0.85)"
            style={{ background: "#1a1c3a" }}
            pannable
            zoomable
          />
        )}
        <Controls
          showInteractive={false}
          position={compact ? "bottom-right" : "bottom-left"}
          style={
            compact ? { transform: "scale(0.85)", transformOrigin: "bottom right" } : undefined
          }
        />
      </ReactFlow>
    </div>
  );
}
