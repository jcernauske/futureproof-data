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

const STAT_ORDER = ["ERN", "ROI", "RES", "GRW", "HMN"] as const;

function buildStats(stats: CompareStatRow[], buildIndex: number): PentagonStats {
  const map: Record<string, number> = {};
  for (const row of stats) {
    map[row.label] = row.values[buildIndex] ?? 0;
  }
  return {
    ern: map[STAT_ORDER[0]] ?? 0,
    roi: map[STAT_ORDER[1]] ?? 0,
    res: map[STAT_ORDER[2]] ?? 0,
    grw: map[STAT_ORDER[3]] ?? 0,
    hmn: map[STAT_ORDER[4]] ?? 0,
  };
}

export function PentagonOverlay({ result, size = 380, highlightIndex = null }: PentagonOverlayProps) {
  const overlays: PentagonOverlayShape[] = result.builds.map((_, idx) => ({
    stats: buildStats(result.stats, idx),
    color: BUILD_COLORS[idx % BUILD_COLORS.length]!,
    dimmed: highlightIndex !== null && highlightIndex !== idx,
  }));

  const emptyStats: PentagonStats = { ern: 0, roi: 0, res: 0, grw: 0, hmn: 0 };

  return (
    <PentagonChart
      stats={emptyStats}
      size={size}
      animated
      overlays={overlays}
    />
  );
}
