import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import type { CareerOutcome } from "@/types/build";
import { STAT_MAP, type StatKey } from "@/data/statExplanations";
import { socEmoji } from "@/data/socEmoji";

interface CareerCardProps {
  career: CareerOutcome;
  picked: boolean;
  onSelect: () => void;
  ernShift?: number;
  /**
   * Optional education label rendered under the wage (e.g.
   * "Bachelor's degree"). Used by /future where education is part of
   * the card's at-a-glance summary; pick-your-career flow leaves it
   * undefined so the card stays compact.
   */
  educationLabel?: string | null;
  /**
   * When true, stat bars whose value is null are omitted entirely
   * instead of rendering with "—". /future uses this to drop ERN on L1
   * and L2 nodes (program-specific data only available at the root).
   */
  hideNullStats?: boolean;
}

const STAT_ORDER: StatKey[] = ["ern", "roi", "res", "grw", "aura"];

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

function formatDelta(d: number): string {
  return d > 0 ? `+${d}` : `${d}`;
}

function StatBar({
  statKey,
  displayValue,
  delta,
  index,
}: {
  statKey: StatKey;
  displayValue: number | null;
  delta: number;
  index: number;
}) {
  const stat = STAT_MAP[statKey];
  const v = displayValue ?? 0;
  const pct = `${(v / 10) * 100}%`;

  const [showDelta, setShowDelta] = useState(false);
  const prevDeltaRef = useRef(delta);

  useEffect(() => {
    if (delta === prevDeltaRef.current) return;
    prevDeltaRef.current = delta;
    if (delta === 0) return;
    setShowDelta(true);
    const id = window.setTimeout(() => setShowDelta(false), 1800);
    return () => window.clearTimeout(id);
  }, [delta]);

  return (
    <div className="flex items-center gap-2 relative">
      <span
        className={`font-data text-micro uppercase w-7 shrink-0 ${stat.textClass}`}
      >
        {statKey.toUpperCase()}
      </span>
      <div className="flex-1 h-1 rounded-full bg-bp-deep overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${stat.bgClass} opacity-80`}
          initial={{ width: 0 }}
          animate={{ width: pct }}
          transition={{ ...springs.smooth, delay: 0.2 + index * stagger.fast }}
        />
      </div>
      <span className="font-data text-micro text-text-secondary w-4 text-right tabular-nums">
        {displayValue ?? "—"}
      </span>
      <AnimatePresence>
        {showDelta && delta !== 0 && (
          <motion.span
            key={`delta-${delta}`}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: -2 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4 }}
            className={`absolute -right-1 -top-3.5 font-data text-[10px] font-bold ${
              delta > 0 ? "text-accent-thrive" : "text-accent-alert"
            }`}
            aria-label={`${statKey.toUpperCase()} ${formatDelta(delta)}`}
          >
            {formatDelta(delta)}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}

export function CareerCard({
  career,
  picked,
  onSelect,
  ernShift = 0,
  educationLabel,
  hideNullStats = false,
}: CareerCardProps) {
  const wage = career.median_annual_wage;
  const reducedMotion = useReducedMotion() ?? false;

  return (
    <motion.button
      type="button"
      id={`career-${career.soc_code}`}
      aria-label={`${career.occupation_title}${picked ? " (selected)" : ""}`}
      aria-pressed={picked}
      onClick={onSelect}
      className={`w-full text-left rounded-xl p-5 border cursor-pointer transition-all duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] ${
        picked
          ? "bg-bp-surface border-accent-thrive/40 shadow-glow-thrive -translate-y-0.5"
          : "bg-bp-mid border-border-subtle hover:bg-bp-surface hover:border-border hover:shadow-lg hover:-translate-y-0.5"
      }`}
      whileTap={reducedMotion ? undefined : { scale: 0.98 }}
      transition={springs.snappy}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="text-[28px] leading-none select-none flex-shrink-0"
        >
          {socEmoji(career.soc_code)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-body font-bold text-body-lg text-text-primary line-clamp-2">
              {career.occupation_title}
            </h3>
            {picked && (
              <span
                aria-hidden="true"
                className="shrink-0 inline-flex items-center bg-accent-thrive/15 text-accent-thrive font-data text-micro font-bold uppercase tracking-[2px] rounded-full px-2 py-0.5"
              >
                Selected
              </span>
            )}
          </div>
          {wage !== null && (
            <p className="font-data text-data text-stat-ern mt-1">
              ${wage.toLocaleString()}/yr median
            </p>
          )}
          {educationLabel && (
            <p className="font-body text-small text-text-secondary mt-1">
              {educationLabel}
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mt-4">
        {STAT_ORDER.map((key, i) => {
          const base = career.stats[key];
          const shifted = key === "ern" && base != null
            ? clamp(base + ernShift, 1, 10)
            : base;
          if (hideNullStats && shifted == null) return null;
          return (
            <StatBar
              key={key}
              statKey={key}
              displayValue={shifted}
              delta={key === "ern" ? ernShift : 0}
              index={i}
            />
          );
        })}
      </div>
    </motion.button>
  );
}
