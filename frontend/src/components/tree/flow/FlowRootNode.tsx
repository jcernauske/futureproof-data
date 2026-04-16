import { Handle, Position } from "@xyflow/react";
import type { FlowNodeData } from "@/data/treeFlowLayout";

type RootNodeProps = { data: FlowNodeData; selected: boolean };

export function FlowRootNode({ data }: RootNodeProps) {
  const wage = data.medianWage
    ? `$${Math.round(data.medianWage).toLocaleString()}`
    : null;

  return (
    <div
      className="flex flex-col items-center"
      data-testid="node-root"
    >
      <div
        className="w-[100px] h-[100px] rounded-full flex items-center justify-center border-[2.5px] border-[#7DD4A3] bg-[#232545]"
        style={{ boxShadow: "0 0 40px rgba(125,212,163,0.15)" }}
      >
        <span className="text-3xl">{data.emoji}</span>
      </div>
      <span className="mt-2 font-display font-semibold text-[12px] text-[#F5F0E8] text-center max-w-[140px] leading-tight">
        {data.title}
      </span>
      {wage && (
        <span className="mt-0.5 font-mono text-[10px] text-[#8A8595]">
          {wage}
        </span>
      )}
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-[#7DD4A3] !w-2 !h-2 !border-0"
      />
    </div>
  );
}
