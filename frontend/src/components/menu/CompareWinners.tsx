import { useMemo } from "react";
import { motion } from "framer-motion";
import type { CompareResult } from "@/api/menu";
import { useT } from "@/i18n/useT";
import { springs, staggerContainer, staggerItem } from "@/styles/motion";

type T = (key: string, vars?: Record<string, string | number>) => string;

/* ------------------------------------------------------------------ */
/*  Build Colors — one per compared build (max 4)                     */
/* ------------------------------------------------------------------ */

/**
 * Tailwind classes for each build-color dot.
 * We use bg-accent-* so everything goes through the design system.
 */
const BUILD_DOT_CLASSES = [
  "bg-accent-thrive",
  "bg-accent-info",
  "bg-accent-caution",
  "bg-accent-empathy",
];

/* ------------------------------------------------------------------ */
/*  Stat / Dimension metadata                                         */
/* ------------------------------------------------------------------ */

type Direction = "max" | "min";

interface Dimension {
  code: string;
  label: string;
  direction: Direction;
  values: (number | null)[];
  format: (v: number) => string;
}

interface WinnerOutcome {
  dim: Dimension;
  winnerIndex: number | null; // null when all values missing
  tied: boolean;
  // Number of builds within ½-pt tolerance of the leading value. Used
  // to phrase the tied state correctly for 2-, 3-, and 4-way ties
  // ("Both at 5" vs "All 4 at 5"). Always 0 when ``tied === false``.
  tiedCount: number;
  // Total number of builds with a finite value for this dimension.
  // Used to detect "all-builds-tied" vs "subset tied" so the copy can
  // choose between "All N at X" and "N-way tie at X".
  finiteCount: number;
  winnerValue: number | null;
  runnerUpValue: number | null;
}

/**
 * Design-system class mappings per stat dimension.
 *
 * Every value here is a Tailwind utility that traces to a token in
 * DESIGN.md / tokens.css / tailwind.config.ts. No raw hex or rgba().
 *
 * - borderClass:    Left accent bar — 3px stat-colored border
 * - textClass:      Stat label text color
 * - glowClass:      Shadow glow for the highlighted state
 * - valueTextClass: Value number color (same as textClass)
 */
interface DimStyle {
  borderClass: string;
  textClass: string;
  glowClass: string;
}

const DIM_STYLES: Record<string, DimStyle> = {
  ERN: {
    borderClass: "border-l-stat-ern",
    textClass: "text-stat-ern",
    glowClass: "shadow-glow-caution",
  },
  ROI: {
    borderClass: "border-l-stat-roi",
    textClass: "text-stat-roi",
    glowClass: "shadow-glow-thrive",
  },
  RES: {
    borderClass: "border-l-stat-res",
    textClass: "text-stat-res",
    glowClass: "shadow-glow-insight",
  },
  GRW: {
    borderClass: "border-l-stat-grw",
    textClass: "text-stat-grw",
    glowClass: "shadow-glow-info",
  },
  AURA: {
    borderClass: "border-l-stat-aura",
    textClass: "text-stat-aura",
    glowClass: "shadow-glow-aura",
  },
  COST: {
    borderClass: "border-l-accent-alert",
    textClass: "text-accent-alert",
    glowClass: "shadow-glow-alert",
  },
};

const FALLBACK_STYLE: DimStyle = {
  borderClass: "border-l-stat-ern",
  textClass: "text-stat-ern",
  glowClass: "shadow-glow-caution",
};

const STAT_LABEL_KEYS: Record<string, string> = {
  ERN: "compare.stat.ern",
  ROI: "compare.stat.roi",
  RES: "compare.stat.res",
  GRW: "compare.stat.grw",
  AURA: "compare.stat.aura",
};

/* ------------------------------------------------------------------ */
/*  Winner computation (pure functions)                                */
/* ------------------------------------------------------------------ */

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

function tiedPhrase(
  t: T,
  tiedCount: number,
  finiteCount: number,
  formattedValue: string,
): string {
  // 2-way tie → familiar "Both at X". 3+ way tie → "All N at X" when
  // every finite-valued build is part of the tie; otherwise an
  // explicit "N-way tie at X" so the reader knows it's not unanimous.
  if (tiedCount <= 2) return t("compare.winners.bothAt", { value: formattedValue });
  if (tiedCount === finiteCount) {
    return t("compare.winners.allAt", { n: tiedCount, value: formattedValue });
  }
  return t("compare.winners.nWayTie", { n: tiedCount, value: formattedValue });
}


function tieCounts(
  values: (number | null)[],
  direction: Direction,
): { tiedCount: number; finiteCount: number } {
  const finite = values.filter(
    (v): v is number => v !== null && Number.isFinite(v),
  );
  if (finite.length === 0) return { tiedCount: 0, finiteCount: 0 };
  const leader = direction === "max" ? Math.max(...finite) : Math.min(...finite);
  // Same ½-pt tolerance as isTied so the count and the boolean agree.
  const tiedCount = finite.filter((v) => Math.abs(v - leader) < 0.5).length;
  return { tiedCount, finiteCount: finite.length };
}

function buildDimensions(result: CompareResult, t: T): Dimension[] {
  const dims: Dimension[] = [];

  for (const row of result.stats) {
    const labelKey = STAT_LABEL_KEYS[row.label];
    if (!labelKey) continue;
    dims.push({
      code: row.label,
      label: t(labelKey),
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
      label: t("compare.winners.lower4yr"),
      direction: "min",
      values: costValues,
      format: (v) => `$${Math.round(v / 1000).toLocaleString()}k`,
    });
  }

  return dims;
}

function shortBuildLabel(name: string, maxLen = 24): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen - 1).trimEnd() + "…";
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

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
  const t = useT();
  const outcomes = useMemo<WinnerOutcome[]>(() => {
    const dims = buildDimensions(result, t);
    return dims.map((dim) => {
      const winnerIndex = pickWinner(dim.values, dim.direction);
      const tied = isTied(dim.values);
      const { tiedCount, finiteCount } = tieCounts(dim.values, dim.direction);
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

      return {
        dim,
        winnerIndex,
        tied,
        tiedCount,
        finiteCount,
        winnerValue,
        runnerUpValue,
      };
    });
  }, [result, t]);

  if (outcomes.length === 0) return null;

  return (
    <motion.div
      data-testid="compare-winners-grid"
      className="grid grid-cols-2 tablet:grid-cols-3 gap-4"
      variants={staggerContainer(0)}
      initial="hidden"
      animate="visible"
    >
      {outcomes.map(({ dim, winnerIndex, tied, tiedCount, finiteCount, winnerValue, runnerUpValue }) => {
        const winnerBuild = winnerIndex !== null ? result.builds[winnerIndex] : null;
        const dimUnavailable = winnerIndex === null;
        const isHighlighted =
          highlightIndex !== null && highlightIndex === winnerIndex;
        const isDimmed =
          highlightIndex !== null && highlightIndex !== winnerIndex;

        const delta =
          winnerValue !== null && runnerUpValue !== null
            ? Math.abs(winnerValue - runnerUpValue)
            : null;

        const style = DIM_STYLES[dim.code] ?? FALLBACK_STYLE;

        return (
          <motion.button
            type="button"
            key={dim.code}
            data-testid={`winner-chip-${dim.code.toLowerCase()}`}
            disabled={dimUnavailable || !onSelectWinner || !winnerBuild}
            onClick={() => {
              if (winnerBuild && onSelectWinner) {
                onSelectWinner(winnerBuild.build_id, dim.label);
              }
            }}
            variants={staggerItem}
            whileHover={
              !dimUnavailable
                ? { scale: 1.02, transition: springs.snappy }
                : undefined
            }
            whileTap={
              !dimUnavailable
                ? { scale: 0.98, transition: springs.snappy }
                : undefined
            }
            className={[
              // Layout
              "relative text-left overflow-hidden",
              // Shape — plush card feel
              "rounded-xl",
              // Left accent bar — stat-colored, 3px, the horizon-map lane pattern
              "border-l-[3px]",
              style.borderClass,
              // Remaining borders — subtle default
              "border border-border-subtle",
              // Background — elevated mid surface
              "bg-bp-mid",
              // Shadow — medium card shadow
              "shadow-md",
              // Padding — generous, breathable
              "p-5",
              // Transitions
              "transition-all duration-normal",
              // Hover — lift to surface tier, strengthen border
              "enabled:hover:bg-bp-surface enabled:hover:border-border enabled:hover:shadow-lg enabled:hover:-translate-y-0.5",
              "enabled:cursor-pointer",
              "disabled:cursor-default",
              // Focus ring — accessibility
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]",
              // Highlight system
              isHighlighted ? style.glowClass : "",
              isDimmed ? "opacity-50" : "",
            ].join(" ")}
          >
            {/* Stat dimension label */}
            <p
              className={[
                "font-body text-body-sm font-bold uppercase tracking-widest mb-3",
                style.textClass,
              ].join(" ")}
            >
              {dim.label}
            </p>

            {dimUnavailable ? (
              /* ---- UNAVAILABLE STATE ---- */
              <p className="font-body text-body-sm text-text-muted">
                {t("compare.callout.insufficient")}
              </p>
            ) : tied ? (
              /* ---- TIED STATE ---- */
              <div>
                <p className="font-body text-body-lg font-bold text-text-primary mb-1">
                  {t("compare.winners.tied")}
                </p>
                {winnerValue !== null && (
                  <p className="font-data text-data-sm text-text-secondary">
                    {tiedPhrase(t, tiedCount, finiteCount, dim.format(winnerValue))}
                  </p>
                )}
              </div>
            ) : (
              /* ---- WINNER STATE ---- */
              <div>
                {/* Winner build name with color dot */}
                <div className="flex items-center gap-2 mb-2">
                  {winnerIndex !== null && (
                    <span
                      className={[
                        "inline-block w-2.5 h-2.5 rounded-full shrink-0",
                        BUILD_DOT_CLASSES[winnerIndex] ?? "bg-accent-thrive",
                      ].join(" ")}
                    />
                  )}
                  <p className="font-body text-body-lg font-bold text-text-primary truncate">
                    {winnerBuild ? shortBuildLabel(winnerBuild.school_name) : ""}
                  </p>
                </div>

                {/* Value + delta */}
                <div className="flex items-baseline gap-2">
                  <span
                    className={[
                      "font-data text-data-lg font-bold",
                      style.textClass,
                    ].join(" ")}
                  >
                    {winnerValue !== null ? dim.format(winnerValue) : "—"}
                  </span>
                  {delta !== null && delta > 0.5 && (
                    <span className="font-data text-data-sm text-text-secondary">
                      {t("compare.winners.aheadBy", { value: dim.format(delta) })}
                    </span>
                  )}
                </div>
              </div>
            )}
          </motion.button>
        );
      })}
    </motion.div>
  );
}
