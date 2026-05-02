import { Handle, Position } from "@xyflow/react";
import { motion } from "framer-motion";
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
      className={`relative px-3 py-1.5 rounded-xl bg-[#232545] border transition-all duration-200${flashClass}`}
      style={{
        borderColor: data.selected ? data.branchColor : "rgba(255,255,255,0.1)",
        borderWidth: data.selected ? 2 : 1,
        ...dimStyle,
      }}
      data-testid={`node-career-${data.socCode}`}
      data-soc={data.socCode}
    >
      {data.flashing && data.flashRarity && (
        <FlashRarityPill tier={data.flashRarity} />
      )}
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

/** In-tree pill shown above a flashing node when its cumulative path
 *  is "stretch" or "longshot". Mirrors the same component in
 *  FlowEndpointNode — duplicated rather than shared because both node
 *  types own different layout chrome around the pill anchor. */
function FlashRarityPill({ tier }: { tier: "stretch" | "longshot" }) {
  const label = tier === "longshot" ? "Long shot" : "Stretch";
  const glyph = tier === "longshot" ? "↯" : "↗";
  const tierClass =
    tier === "longshot"
      ? "border-accent-alert text-accent-alert bg-bp-mid"
      : "border-accent-caution text-accent-caution bg-bp-mid";
  return (
    <motion.span
      data-testid={`flash-rarity-${tier}`}
      initial={{ opacity: 0, y: 6, scale: 0.85 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 6, scale: 0.85 }}
      transition={{ type: "spring", stiffness: 360, damping: 24 }}
      className={`absolute -top-3 left-1/2 -translate-x-1/2 -translate-y-full inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-data text-[10px] font-bold tracking-wide uppercase border whitespace-nowrap shadow-lg z-10 ${tierClass}`}
      style={{ pointerEvents: "none" }}
    >
      <span aria-hidden="true">{glyph}</span>
      <span>{label}</span>
    </motion.span>
  );
}
