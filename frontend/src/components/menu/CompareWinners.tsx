import { useMemo } from "react";
import type { CompareResult } from "@/api/menu";

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-caution)",
  "var(--color-accent-empathy)",
];

type Direction = "max" | "min";

interface Dimension {
  code: string;
  label: string;
  glyph: string;
  direction: Direction;
  values: (number | null)[];
  format: (v: number) => string;
}

interface WinnerOutcome {
  dim: Dimension;
  winnerIndex: number | null; // null when all values missing
  tied: boolean;
  winnerValue: number | null;
  runnerUpValue: number | null;
}

const STAT_GLYPHS: Record<string, { label: string; glyph: string }> = {
  ERN: { label: "Earnings", glyph: "💰" },
  ROI: { label: "ROI", glyph: "📈" },
  RES: { label: "AI Resilience", glyph: "🤖" },
  GRW: { label: "Growth", glyph: "🌱" },
  AURA: { label: "Brand Gravity", glyph: "🫶" },
};

function pickWinner(values: (number | null)[], direction: Direction): WinnerOutcome["winnerIndex"] {
  const entries = values
    .map((v, i) => ({ v, i }))
    .filter((e): e is { v: number; i: number } => e.v !== null && Number.isFinite(e.v));
  if (entries.length === 0) return null;
  const sorted = [...entries].sort((a, b) =>
    direction === "max" ? b.v - a.v : a.v - b.v,
  );
  return sorted[0]!.i;
}

function isTied(values: (number | null)[]): boolean {
  const finite = values.filter(
    (v): v is number => v !== null && Number.isFinite(v),
  );
  if (finite.length < 2) return false;
  const max = Math.max(...finite);
  const min = Math.min(...finite);
  return max - min < 0.5; // pentagon-stat tolerance: half a point
}

function buildDimensions(result: CompareResult): Dimension[] {
  const dims: Dimension[] = [];

  for (const row of result.stats) {
    const meta = STAT_GLYPHS[row.label];
    if (!meta) continue;
    dims.push({
      code: row.label,
      label: meta.label,
      glyph: meta.glyph,
      direction: "max",
      values: row.values,
      format: (v) => v.toFixed(0),
    });
  }

  const costValues = result.builds.map((b) =>
    b.net_price_annual !== null ? b.net_price_annual * 4 : null,
  );
  if (costValues.some((v) => v !== null)) {
    dims.push({
      code: "COST",
      label: "Lower 4-yr cost",
      glyph: "💵",
      direction: "min",
      values: costValues,
      format: (v) => `$${Math.round(v / 1000).toLocaleString()}k`,
    });
  }

  return dims;
}

function shortBuildLabel(name: string, maxLen = 22): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen - 1).trimEnd() + "…";
}

interface CompareWinnersProps {
  result: CompareResult;
  highlightIndex: number | null;
  onSelectWinner?: (buildId: string, dimensionLabel: string) => void;
}

export function CompareWinners({
  result,
  highlightIndex,
  onSelectWinner,
}: CompareWinnersProps) {
  const outcomes = useMemo<WinnerOutcome[]>(() => {
    const dims = buildDimensions(result);
    return dims.map((dim) => {
      const winnerIndex = pickWinner(dim.values, dim.direction);
      const tied = isTied(dim.values);
      const winnerValue = winnerIndex !== null ? dim.values[winnerIndex] ?? null : null;

      const runnerUpValue = (() => {
        if (winnerIndex === null) return null;
        const others = dim.values
          .map((v, i) => ({ v, i }))
          .filter((e): e is { v: number; i: number } =>
            e.v !== null && Number.isFinite(e.v) && e.i !== winnerIndex,
          )
          .map((e) => e.v);
        if (others.length === 0) return null;
        return dim.direction === "max" ? Math.max(...others) : Math.min(...others);
      })();

      return { dim, winnerIndex, tied, winnerValue, runnerUpValue };
    });
  }, [result]);

  if (outcomes.length === 0) return null;

  return (
    <div
      data-testid="compare-winners-grid"
      className="grid grid-cols-2 tablet:grid-cols-3 gap-3"
    >
      {outcomes.map(({ dim, winnerIndex, tied, winnerValue, runnerUpValue }) => {
        const winnerBuild = winnerIndex !== null ? result.builds[winnerIndex] : null;
        const winnerColor = winnerIndex !== null ? BUILD_COLORS[winnerIndex] : undefined;
        const dim_unavailable = winnerIndex === null;
        const isHighlighted =
          highlightIndex !== null && highlightIndex === winnerIndex;

        const delta =
          winnerValue !== null && runnerUpValue !== null
            ? Math.abs(winnerValue - runnerUpValue)
            : null;

        return (
          <button
            type="button"
            key={dim.code}
            data-testid={`winner-chip-${dim.code.toLowerCase()}`}
            disabled={dim_unavailable || !onSelectWinner || !winnerBuild}
            onClick={() => {
              if (winnerBuild && onSelectWinner) {
                onSelectWinner(winnerBuild.build_id, dim.label);
              }
            }}
            className={[
              "text-left rounded-xl p-3 border transition-all duration-normal",
              "bg-bp-deep/50 border-border-subtle",
              "enabled:hover:border-accent-thrive enabled:hover:bg-bp-surface enabled:cursor-pointer",
              "disabled:opacity-50 disabled:cursor-default",
              isHighlighted ? "ring-1 ring-accent-thrive/60" : "",
            ].join(" ")}
            style={{
              borderLeftColor: winnerColor,
              borderLeftWidth: winnerColor ? 3 : undefined,
            }}
          >
            <div className="flex items-center gap-1.5 text-text-muted font-data text-micro uppercase tracking-widest">
              <span aria-hidden>{dim.glyph}</span>
              <span>{dim.label}</span>
            </div>
            {dim_unavailable ? (
              <p className="font-body text-small text-text-muted mt-2">
                Insufficient data
              </p>
            ) : tied ? (
              <p className="font-body text-small font-semibold text-text-primary mt-2">
                Tied across builds
              </p>
            ) : (
              <>
                <p className="font-body text-small font-semibold text-text-primary mt-2 line-clamp-1">
                  {winnerBuild ? shortBuildLabel(winnerBuild.school_name) : ""}
                </p>
                <p className="font-data text-micro text-text-secondary mt-0.5">
                  {winnerValue !== null ? dim.format(winnerValue) : "—"}
                  {delta !== null && delta > 0.5 && (
                    <span className="text-text-muted ml-1.5">
                      · +{dim.format(delta)} vs runner-up
                    </span>
                  )}
                </p>
              </>
            )}
          </button>
        );
      })}
    </div>
  );
}
