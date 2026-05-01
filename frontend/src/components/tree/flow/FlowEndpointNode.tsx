import { Handle, Position } from "@xyflow/react";
import type { FlowNodeData } from "@/data/treeFlowLayout";

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max - 1) + "…" : text;
}

type EndpointNodeProps = { data: FlowNodeData };

export function FlowEndpointNode({ data }: EndpointNodeProps) {
  const wage = data.medianWage
    ? `$${Math.round(data.medianWage).toLocaleString()}`
    : null;
  const targetSide = data.direction === "LR" ? Position.Left : Position.Top;
  const flashClass = data.flashing ? " flow-node-flash" : "";
  const dimStyle = data.dimmed ? { opacity: 0.45 } : {};

  return (
    <div
      className={`flex items-center gap-2${flashClass}`}
      style={dimStyle}
      data-testid={`node-endpoint-${data.socCode}`}
      data-soc={data.socCode}
    >
      <div
        className="w-9 h-9 rounded-full flex items-center justify-center bg-[#232545] border opacity-70 flex-shrink-0"
        style={{ borderColor: data.branchColor }}
      >
        <span className="text-sm">{data.emoji}</span>
      </div>
      <div className="flex flex-col">
        <span className="font-mono text-[11px] text-[#8A8595] whitespace-nowrap">
          {truncate(data.title, 26)}
        </span>
        {wage && (
          <span
            className="font-mono text-[9px] opacity-70"
            style={{ color: data.branchColor }}
          >
            {wage}
          </span>
        )}
      </div>
      <Handle
        type="target"
        position={targetSide}
        className="!bg-transparent !w-1 !h-1 !border-0"
      />
    </div>
  );
}
