import { Handle, Position } from "@xyflow/react";
import type { FlowNodeData } from "@/data/treeFlowLayout";

type BranchLabelProps = { data: FlowNodeData; selected: boolean };

export function FlowBranchLabel({ data }: BranchLabelProps) {
  return (
    <div
      className="px-4 py-1.5 rounded-full bg-[#232545] border text-center whitespace-nowrap"
      style={{ borderColor: data.branchColor }}
    >
      <span className="font-body text-[13px] font-bold text-[#F5F0E8]">
        {data.title}
      </span>
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-transparent !w-1 !h-1 !border-0"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-transparent !w-1 !h-1 !border-0"
      />
    </div>
  );
}
