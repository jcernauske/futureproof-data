import { STAT_COLORS } from "./bossData";

interface StatBarRowProps {
  stat: string;
  value: number | null;
}

export function StatBarRow({ stat, value }: StatBarRowProps) {
  const colors = STAT_COLORS[stat];
  // Pentagon-stat-reshape §3 missing-data treatment: when the stat is
  // null (e.g. ~10% of unitids have no AURA coverage) render an em-dash
  // numeric and a hollow track instead of a "0" with empty bar.
  const isAbsent = value === null || value === undefined;
  const v = isAbsent ? 0 : Math.max(0, Math.min(10, value));
  const fillPct = (v / 10) * 100;

  return (
    <div className="flex items-center gap-2" data-state={isAbsent ? "absent" : undefined}>
      <span
        className="font-data uppercase font-bold"
        style={{ fontSize: 11, width: 28, color: colors?.text }}
      >
        {stat.toUpperCase()}
      </span>
      <div
        className="flex-1 h-1 rounded-full bg-bp-deep"
        style={isAbsent ? { border: "1px dashed var(--color-text-muted)", opacity: 0.4 } : undefined}
      >
        {!isAbsent && (
          <div
            className="h-full rounded-full"
            style={{
              width: `${fillPct}%`,
              background: colors?.text,
              opacity: 0.8,
              transition: "width 0.4s ease-out",
            }}
          />
        )}
      </div>
      <span
        className="font-data text-text-secondary"
        style={{ fontSize: 11, width: 16, textAlign: "right" }}
      >
        {isAbsent ? "—" : v}
      </span>
    </div>
  );
}
