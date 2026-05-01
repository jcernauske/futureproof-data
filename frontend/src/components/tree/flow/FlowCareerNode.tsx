import { Handle, Position } from "@xyflow/react";
import type { FlowNodeData } from "@/data/treeFlowLayout";

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max - 1) + "…" : text;
}

type CareerNodeProps = { data: FlowNodeData };

export function FlowCareerNode({ data }: CareerNodeProps) {
  const wage = data.medianWage
    ? `$${Math.round(data.medianWage).toLocaleString()}`
    : null;
  const isLR = data.direction === "LR";
  const targetSide = isLR ? Position.Left : Position.Top;
  const sourceSide = isLR ? Position.Right : Position.Bottom;
  const flashClass = data.flashing ? " flow-node-flash" : "";
  const dimStyle = data.dimmed ? { opacity: 0.45 } : {};

  return (
    <div
      className={`px-3 py-1.5 rounded-xl bg-[#232545] border transition-all duration-200${flashClass}`}
      style={{
        borderColor: data.selected ? data.branchColor : "rgba(255,255,255,0.1)",
        borderWidth: data.selected ? 2 : 1,
        ...dimStyle,
      }}
      data-testid={`node-career-${data.socCode}`}
      data-soc={data.socCode}
    >
      <div className="font-body text-[11px] font-semibold text-[#C4BFB0] whitespace-nowrap">
        {truncate(data.title, 24)}
      </div>
      {wage && (
        <div className="font-mono text-[9px] text-[#8A8595] mt-0.5">{wage}</div>
      )}
      <Handle
        type="target"
        position={targetSide}
        className="!bg-transparent !w-1 !h-1 !border-0"
      />
      <Handle
        type="source"
        position={sourceSide}
        className="!bg-transparent !w-1 !h-1 !border-0"
      />
    </div>
  );
}
