import { Handle, Position } from "@xyflow/react";
import { motion } from "framer-motion";
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
      className="relative flex items-center gap-2"
      style={dimStyle}
      data-testid={`node-endpoint-${data.socCode}`}
      data-soc={data.socCode}
    >
      {/* Flash applied to the round avatar so the box-shadow glow
          follows its border-radius. The outer flex row has no rounded
          corners — applying the flash there produces a square glow. */}
      <div
        className={`relative w-9 h-9 rounded-full flex items-center justify-center bg-[#232545] border opacity-70 flex-shrink-0${flashClass}`}
        style={{ borderColor: data.branchColor }}
      >
        <span className="text-sm">{data.emoji}</span>
        {data.flashing && data.flashRarity && (
          <FlashRarityPill tier={data.flashRarity} />
        )}
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

/**
 * Small pill that pops in above a node during a tour-chip flash when
 * the cumulative path is "stretch" or "longshot". Mounted only while
 * `data.flashing` is true; React unmounts it when the flash ends, so
 * the exit transition doesn't need its own AnimatePresence.
 *
 * Coloring uses the same vocabulary as the rail's PathRarityBadge:
 * caution amber for stretch, alert red for longshot. The "no red"
 * rule for edge labels doesn't apply — a longshot signal is meant
 * to read as warning-y.
 */
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
      className={`absolute -top-3 left-1/2 -translate-x-1/2 -translate-y-full inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-data text-[10px] font-bold tracking-wide uppercase border whitespace-nowrap shadow-lg ${tierClass}`}
      style={{ pointerEvents: "none" }}
    >
      <span aria-hidden="true">{glyph}</span>
      <span>{label}</span>
    </motion.span>
  );
}
