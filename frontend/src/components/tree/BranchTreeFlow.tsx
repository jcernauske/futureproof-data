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
}

export function BranchTreeFlow({
  tree,
  emoji,
  selectedNodeId,
  onSelectNode,
}: BranchTreeFlowProps) {
  const { nodes: baseNodes, edges } = useMemo(
    () => treeToFlow(tree, emoji),
    [tree, emoji],
  );

  // Apply selection/dimming state to node data
  const nodes = useMemo(
    () =>
      baseNodes.map((n) => ({
        ...n,
        selected: n.id === selectedNodeId,
        data: {
          ...n.data,
          selected: n.id === selectedNodeId,
          dimmed:
            selectedNodeId != null && n.id !== selectedNodeId,
        },
      })),
    [baseNodes, selectedNodeId],
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
      className="w-full h-[75vh]"
      data-testid="region-branch-tree"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.1}
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
