import { motion, AnimatePresence } from "framer-motion";
import { springs } from "@/styles/motion";
import type { PositionedNode } from "@/data/treeLayout";

interface TreeNodeDetailPanelProps {
  node: PositionedNode | null;
  rootNode: PositionedNode | null;
  onClose: () => void;
  /**
   * `modal` — floats over the tree in the top-right corner (default, used
   * on mobile/tablet where the tree takes the full grid width).
   * `sidebar` — renders inline in a grid cell (used on desktop+ where the
   * detail panel lives in a persistent right-side column).
   */
  variant?: "modal" | "sidebar";
}

const STAT_LABELS: Record<string, { label: string; color: string }> = {
  ern: { label: "ERN", color: "#F2D477" },
  roi: { label: "ROI", color: "#7DD4A3" },
  res: { label: "RES", color: "#B8A9E8" },
  grw: { label: "GRW", color: "#7BB8E0" },
  hmn: { label: "HMN", color: "#E88BA9" },
};

const BOSS_META: Record<string, { label: string; emoji: string }> = {
  ai: { label: "Fight AI", emoji: "\uD83E\uDD16" },
  loans: { label: "Student Loans", emoji: "\uD83D\uDCB8" },
  market: { label: "The Market", emoji: "\uD83C\uDF0A" },
  burnout: { label: "Burnout", emoji: "\uD83D\uDD25" },
  ceiling: { label: "The Ceiling", emoji: "\uD83E\uDDE1" },
};

function resultPill(result: string | null) {
  if (!result || result === "unknown") return null;
  const colors: Record<string, { bg: string; text: string }> = {
    win: { bg: "rgba(125,212,163,0.2)", text: "#7DD4A3" },
    lose: { bg: "rgba(244,169,126,0.2)", text: "#F4A97E" },
    draw: { bg: "rgba(242,212,119,0.2)", text: "#F2D477" },
  };
  const c = colors[result] ?? { bg: "rgba(242,212,119,0.2)", text: "#F2D477" };
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full font-data text-[11px] font-bold uppercase"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {result}
    </span>
  );
}

export function TreeNodeDetailPanel({
  node,
  rootNode,
  onClose,
  variant = "modal",
}: TreeNodeDetailPanelProps) {
  const salary =
    node?.median_wage != null ? `$${node.median_wage.toLocaleString()}` : null;

  const positionClasses =
    variant === "sidebar"
      ? "w-full rounded-xl border border-border p-5 sticky top-24"
      : "absolute top-10 right-8 w-[280px] rounded-xl border border-border p-5 z-50";

  return (
    <AnimatePresence>
      {node && (
        <motion.div
          key="detail-panel"
          className={positionClasses}
          style={{ background: "#232545" }}
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 12 }}
          transition={{ ...springs.smooth, duration: 0.3 }}
          role="dialog"
          aria-label={`Details for ${node.title}`}
          data-testid={variant === "sidebar" ? "panel-node-detail-sidebar" : "panel-node-detail"}
        >
          {/* Close button */}
          <button
            className="absolute top-2.5 right-2.5 w-7 h-7 rounded-full flex items-center justify-center text-text-muted hover:text-text-primary transition-colors duration-normal"
            style={{ background: "#2D3060" }}
            onClick={onClose}
            aria-label="Close detail panel"
            data-testid="btn-close-detail"
          >
            &times;
          </button>

          {/* Title */}
          <h3 className="font-display font-semibold text-[18px] text-text-primary pr-8 mb-1">
            {node.title}
          </h3>

          {/* SOC + salary */}
          <p className="font-data text-[12px] text-text-muted mb-4">
            SOC {node.soc_code}{salary ? ` \u00B7 ${salary}` : ""}
          </p>

          {/* Unlock requirement */}
          {node.education && (
            <div
              className="rounded-md p-3 mb-4"
              style={{ background: "#2D3060", borderLeft: "3px solid #7BB8E0" }}
            >
              <p className="font-body text-[13px] text-text-secondary">
                {node.education}
              </p>
            </div>
          )}

          {/* Stats section */}
          <p className="font-display font-semibold text-[13px] text-text-secondary mb-2">
            Stats at this node
          </p>
          <div className="grid grid-cols-2 gap-1.5 mb-4">
            {Object.entries(STAT_LABELS).map(([key, meta]) => {
              const val = node.stats[key as keyof typeof node.stats];
              const rootVal = rootNode?.stats[key as keyof typeof node.stats] ?? null;
              const delta = val != null && rootVal != null ? val - rootVal : null;

              return (
                <div
                  key={key}
                  className="rounded-sm px-2.5 py-1.5 flex items-center justify-between"
                  style={{ background: "#2D3060" }}
                >
                  <div>
                    <span
                      className="font-data text-[11px] font-bold block"
                      style={{ color: meta.color }}
                    >
                      {meta.label}
                    </span>
                    {delta != null && delta !== 0 && (
                      <span
                        className="font-data text-[11px]"
                        style={{ color: delta > 0 ? "#7DD4A3" : "#F4A97E" }}
                      >
                        {delta > 0 ? "+" : ""}{delta}
                      </span>
                    )}
                    {delta === 0 && (
                      <span className="font-data text-[11px] text-text-muted">&mdash;</span>
                    )}
                  </div>
                  <span
                    className="font-data text-[16px] font-bold"
                    style={{ color: meta.color }}
                  >
                    {val ?? "\u2014"}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Boss fight projection */}
          <p className="font-display font-semibold text-[13px] text-text-secondary mb-2">
            Boss fight projection
          </p>
          <div className="flex flex-col gap-1">
            {Object.entries(BOSS_META).map(([key, meta]) => {
              const result = node.bosses[key as keyof typeof node.bosses];
              if (!result || result === "unknown") return null;
              return (
                <div
                  key={key}
                  className="rounded-sm px-2.5 py-1.5 flex items-center justify-between"
                  style={{ background: "#2D3060" }}
                >
                  <span className="font-body text-[13px] text-text-secondary">
                    {meta.emoji} {meta.label}
                  </span>
                  {resultPill(result)}
                </div>
              );
            })}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
