import type { CompareResult, CompareStatRow } from "@/api/menu";
import { PentagonChart, type PentagonOverlayShape } from "@/components/PentagonChart";
import type { PentagonStats } from "@/types/build";

interface PentagonOverlayProps {
  result: CompareResult;
  size?: number;
  highlightIndex?: number | null;
}

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-caution)",
  "var(--color-accent-empathy)",
];

const STAT_ORDER = ["ERN", "ROI", "RES", "GRW", "AURA"] as const;

function buildStats(stats: CompareStatRow[], buildIndex: number): PentagonStats {
  // Pentagon-stat-reshape §3 missing-data treatment: preserve nulls all
  // the way through to PentagonChart so its open-ring fallback fires
  // for the ~10% of unitids without AURA coverage. Coercing to 0 here
  // would silently make missing data look like a zero score.
  const map: Record<string, number | null> = {};
  for (const row of stats) {
    const v = row.values[buildIndex];
    map[row.label] = v === undefined ? null : v;
  }
  return {
    ern: map[STAT_ORDER[0]] ?? null,
    roi: map[STAT_ORDER[1]] ?? null,
    res: map[STAT_ORDER[2]] ?? null,
    grw: map[STAT_ORDER[3]] ?? null,
    aura: map[STAT_ORDER[4]] ?? null,
  };
}

export function PentagonOverlay({ result, size = 380, highlightIndex = null }: PentagonOverlayProps) {
  const overlays: PentagonOverlayShape[] = result.builds.map((_, idx) => ({
    stats: buildStats(result.stats, idx),
    color: BUILD_COLORS[idx % BUILD_COLORS.length]!,
    dimmed: highlightIndex !== null && highlightIndex !== idx,
  }));

  const emptyStats: PentagonStats = { ern: null, roi: null, res: null, grw: null, aura: null };

  return (
    <PentagonChart
      stats={emptyStats}
      size={size}
      animated
      overlays={overlays}
    />
  );
}
