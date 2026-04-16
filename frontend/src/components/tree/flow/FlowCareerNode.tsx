import { Handle, Position } from "@xyflow/react";
import type { FlowNodeData } from "@/data/treeFlowLayout";

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max - 1) + "\u2026" : text;
}

type CareerNodeProps = { data: FlowNodeData; selected: boolean };

export function FlowCareerNode({ data, selected }: CareerNodeProps) {
  const wage = data.medianWage
    ? `$${Math.round(data.medianWage).toLocaleString()}`
    : null;

  return (
    <div
      className="px-3 py-1.5 rounded-xl bg-[#232545] border transition-all duration-200"
      style={{
        borderColor: selected ? data.branchColor : "rgba(255,255,255,0.1)",
        borderWidth: selected ? 2 : 1,
      }}
      data-testid={`node-career-${data.socCode}`}
    >
      <div className="font-body text-[11px] font-semibold text-[#C4BFB0] whitespace-nowrap">
        {truncate(data.title, 24)}
      </div>
      {wage && (
        <div className="font-mono text-[9px] text-[#8A8595] mt-0.5">
          {wage}
        </div>
      )}
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
