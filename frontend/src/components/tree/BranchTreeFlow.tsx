import { useCallback, useMemo } from "react";
import { ReactFlow, MiniMap, Controls } from "@xyflow/react";
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
import type { TreeNode } from "@/types/tree";

const nodeTypes = {
  root: FlowRootNode,
  career: FlowCareerNode,
  endpoint: FlowEndpointNode,
} as const;

interface BranchTreeFlowProps {
  tree: TreeNode;
  emoji: string;
  direction: FlowDirection;
  selectedNodeId: string | null;
  onSelectNode: (id: string | null) => void;
  highlightedNodeIds?: ReadonlySet<string>;
}

export function BranchTreeFlow({
  tree,
  emoji,
  direction,
  selectedNodeId,
  onSelectNode,
  highlightedNodeIds,
}: BranchTreeFlowProps) {
  const { nodes: baseNodes, edges } = useMemo(
    () => treeToFlow(tree, emoji, direction),
    [tree, emoji, direction],
  );

  const nodes = useMemo(
    () =>
      baseNodes.map((n) => {
        const flashing = highlightedNodeIds?.has(n.id) ?? false;
        const selected = n.id === selectedNodeId;
        const dimmed = selectedNodeId != null && !selected;
        return {
          ...n,
          data: { ...n.data, flashing, selected, dimmed },
        };
      }),
    [baseNodes, selectedNodeId, highlightedNodeIds],
  );

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string; data: FlowNodeData }) => {
      onSelectNode(node.id);
    },
    [onSelectNode],
  );

  const handlePaneClick = useCallback(() => {
    onSelectNode(null);
  }, [onSelectNode]);

  const miniMapColor = useCallback(
    (node: { data?: { branchColor?: string } }) =>
      node.data?.branchColor ?? "#7DD4A3",
    [],
  );

  return (
    <div className="w-full h-full" data-testid="region-future-tree">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        fitView
        // padding tighter so nodes start near max legibility; the
        // fitView floor (minZoom) prevents auto-fit from cramming a
        // tall tree into the viewport at unreadable zoom — user pans
        // instead. maxZoom caps the auto-zoom-IN on tiny trees.
        fitViewOptions={{ padding: 0.12, minZoom: 0.7, maxZoom: 1.0 }}
        minZoom={0.4}
        maxZoom={2.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll
        zoomOnPinch
        proOptions={{ hideAttribution: false }}
      >
        <MiniMap
          nodeColor={miniMapColor}
          maskColor="rgba(15,17,41,0.85)"
          style={{ background: "#1a1c3a" }}
          pannable
          zoomable
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
