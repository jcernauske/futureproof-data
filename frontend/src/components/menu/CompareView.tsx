import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { getBuild } from "@/api/build";
import { useBuildStore } from "@/store/buildStore";
import {
  compareBuilds,
  compareInsights,
  type AskScope,
  type CompareResult,
  type CompareInsights,
} from "@/api/menu";
import { PentagonOverlay } from "@/components/menu/PentagonOverlay";
import { RiskHeadlineGrid } from "@/components/menu/RiskHeadlineCard";
import { CharacterCard } from "@/components/menu/CharacterCard";
import { MoneySection } from "@/components/menu/MoneySection";
import { BranchPreview } from "@/components/menu/BranchPreview";
import { CompareWinners } from "@/components/menu/CompareWinners";
import { CompareProsCons } from "@/components/menu/CompareProsCons";
import { CompareAccordion } from "@/components/menu/CompareAccordion";
import { CompareCostBreakdown } from "@/components/menu/CompareCostBreakdown";
import { CompareSchoolProfile } from "@/components/menu/CompareSchoolProfile";
import { Button } from "@/components/ui/Button";
import { GemmaSpinner } from "@/components/ui/GemmaSpinner";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { useT } from "@/i18n/useT";

interface CompareViewProps {
  buildIds: string[];
  onBack: () => void;
}

type Phase = "loading" | "ready" | "error";

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-caution)",
  "var(--color-accent-empathy)",
];

const STAT_LABELS: Record<string, string> = {
  ERN: "Earnings",
  ROI: "ROI",
  RES: "AI resilience",
  GRW: "Growth",
  AURA: "Brand gravity",
};

const STAT_COLORS: Record<string, string> = {
  ERN: "var(--color-stat-ern)",
  ROI: "var(--color-stat-roi)",
  RES: "var(--color-stat-res)",
  GRW: "var(--color-stat-grw)",
  AURA: "var(--color-stat-aura)",
};

const BOSS_TONE: Record<string, string> = {
  WIN: "bg-accent-thrive/20 text-accent-thrive border-accent-thrive/30",
  DRAW: "bg-accent-caution/20 text-accent-caution border-accent-caution/30",
  LOSE: "bg-accent-alert/20 text-accent-alert border-accent-alert/30",
};

function formatMoney(value: number | null, compact = false): string {
  if (value == null) return "n/a";
  if (compact) return `$${Math.round(value / 1000)}K`;
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

function clampPct(value: number): number {
  return Math.max(0, Math.min(100, value));
}

function shortName(name: string, maxLen = 26): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen - 1).trimEnd() + "…";
}

function statValue(result: CompareResult, label: string, buildIndex: number): number | null {
  const row = result.stats.find((s) => s.label === label);
  const value = row?.values[buildIndex];
  return value == null ? null : value;
}

function averageStats(result: CompareResult, buildIndex: number, labels: string[]): number | null {
  const values = labels
    .map((label) => statValue(result, label, buildIndex))
    .filter((value): value is number => value !== null && Number.isFinite(value));
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function costPressure(build: CompareResult["builds"][number]): number | null {
  const netFourYear = build.net_price_annual != null ? build.net_price_annual * 4 : null;
  const debt = build.modeled_total_debt;
  if (netFourYear == null && debt == null) return null;
  return (netFourYear ?? 0) + (debt ?? 0);
}

function bestIndex(values: (number | null)[], direction: "high" | "low"): number | null {
  const entries = values
    .map((value, index) => ({ value, index }))
    .filter((entry): entry is { value: number; index: number } =>
      entry.value !== null && Number.isFinite(entry.value),
    );
  if (entries.length === 0) return null;
  const sorted = [...entries].sort((a, b) =>
    direction === "high" ? b.value - a.value : a.value - b.value,
  );
  return sorted[0]!.index;
}

function heroHeadline({
  builds,
  lowestCostIndex,
  highestUpsideIndex,
  strongestResilienceIndex,
}: {
  builds: CompareResult["builds"];
  lowestCostIndex: number | null;
  highestUpsideIndex: number | null;
  strongestResilienceIndex: number | null;
}): string {
  const cost = lowestCostIndex !== null ? builds[lowestCostIndex] : null;
  const upside = highestUpsideIndex !== null ? builds[highestUpsideIndex] : null;
  const resilience =
    strongestResilienceIndex !== null ? builds[strongestResilienceIndex] : null;

  if (cost && upside && cost.build_id !== upside.build_id) {
    return `${cost.school_name} lowers pressure. ${upside.school_name} raises upside.`;
  }
  if (upside && resilience && upside.build_id !== resilience.build_id) {
    return `${upside.school_name} has the upside. ${resilience.school_name} has the cushion.`;
  }
  if (upside) return `${upside.school_name} is setting the pace.`;
  return "Compare pressure, risk, and upside before you choose.";
}

function BigChoiceLoading() {
  return (
    <div className="flex items-center gap-3 py-2" role="status" aria-label="Loading Big Choice">
      <GemmaSpinner size={34} className="shrink-0" />
      <span className="font-display text-[28px] font-bold leading-tight text-text-muted animate-gemma-shimmer-loop tablet:text-[36px]">
        Reading the tradeoffs
      </span>
    </div>
  );
}

function SummaryCallout({
  label,
  build,
  value,
  color = "var(--color-border-default)",
}: {
  label: string;
  build: CompareResult["builds"][number] | null;
  value: string;
  color?: string;
}) {
  return (
    <div
      className="rounded-md border border-border-subtle bg-bp-void/50 px-4 py-3"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <p className="font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
        {label}
      </p>
      <p className="mt-1 truncate font-display text-[18px] font-semibold text-text-primary">
        {build ? shortName(build.school_name, 24) : "Insufficient data"}
      </p>
      <p className="font-data text-data-sm text-text-secondary">{value}</p>
    </div>
  );
}

function TopRailStats({
  result,
  buildIndex,
}: {
  result: CompareResult;
  buildIndex: number;
}) {
  return (
    <div className="mt-3 flex flex-col gap-1.5" aria-label="Build stat bars">
      {Object.keys(STAT_LABELS).map((label) => {
        const raw = statValue(result, label, buildIndex);
        const isAbsent = raw == null;
        const value = isAbsent ? 0 : Math.max(0, Math.min(10, raw));
        const color = STAT_COLORS[label] ?? "var(--color-text-muted)";
        return (
          <div
            key={label}
            className="grid min-w-0 items-center gap-2"
            style={{ gridTemplateColumns: "34px minmax(72px, 1fr) 22px" }}
            title={`${STAT_LABELS[label]}: ${isAbsent ? "unavailable" : value}`}
          >
            <span
              className="font-data text-[10px] font-bold uppercase tracking-wider"
              style={{ color }}
            >
              {label}
            </span>
            <div
              className="h-1.5 rounded-full bg-white/[0.06]"
              style={isAbsent ? { border: "1px dashed var(--color-text-muted)", opacity: 0.45 } : undefined}
            >
              {!isAbsent && (
                <div
                  className="h-full rounded-full"
                  style={{ width: `${(value / 10) * 100}%`, background: color }}
                />
              )}
            </div>
            <span className="text-right font-data text-[10px] font-bold" style={{ color }}>
              {isAbsent ? "—" : value}
            </span>
          </div>
        );
      })}
    </div>
  );
}

interface MapPoint {
  build: CompareResult["builds"][number];
  idx: number;
  x: number;
  y: number;
  color: string;
  costText: string;
  upsideText: string;
}

function TradeoffMap({
  result,
  buildColors,
  costValues,
  upsideValues,
  highlightIndex,
  maxCost,
}: {
  result: CompareResult;
  buildColors: string[];
  costValues: (number | null)[];
  upsideValues: (number | null)[];
  highlightIndex: number | null;
  maxCost: number;
}) {
  const mapPoints: MapPoint[] = result.builds.map((build, idx) => {
    const x =
      costValues[idx] == null
        ? 50
        : clampPct((costValues[idx]! / maxCost) * 86 + 7);
    const y =
      upsideValues[idx] == null
        ? 50
        : clampPct(93 - (upsideValues[idx]! / 10) * 86);
    return {
      build,
      idx,
      x,
      y,
      color: buildColors[idx] ?? "var(--color-accent-info)",
      costText: formatMoney(costValues[idx] ?? null, true),
      upsideText: upsideValues[idx] == null ? "n/a" : `${upsideValues[idx]!.toFixed(1)} up`,
    };
  });

  return (
    <div className="rounded-lg border border-border-subtle bg-bp-deep p-5 tablet:p-6 shadow-lg">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="font-data text-[11px] font-bold uppercase tracking-widest text-text-muted">
            Cost x Upside Map
          </p>
          <h2 className="mt-1 font-display text-subheading font-semibold text-text-primary">
            Which tradeoff can you live with?
          </h2>
          <p className="mt-2 max-w-[620px] font-body text-small leading-relaxed text-text-secondary">
            Pressure combines estimated four-year net price and modeled debt. Low pressure means less money at risk; high pressure means the path costs more upfront or leaves more debt to carry. Upside averages earnings, ROI, and growth.
          </p>
        </div>
        <div className="hidden tablet:flex items-center gap-2 font-data text-data-sm text-text-muted">
          <span>Lower cost</span>
          <span className="h-px w-8 bg-border" />
          <span>Higher cost</span>
        </div>
      </div>

      <div className="relative h-[340px] overflow-hidden rounded-md border border-border-subtle bg-bp-void">
        <div className="absolute inset-x-6 top-1/2 h-px bg-border-subtle" />
        <div className="absolute inset-y-6 left-1/2 w-px bg-border-subtle" />
        <div className="absolute left-4 top-3 font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          Higher upside
        </div>
        <div className="absolute bottom-3 right-4 font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          Higher pressure
        </div>

        {mapPoints.map((point) => {
          const dimmed = highlightIndex !== null && highlightIndex !== point.idx;
          return (
            <span
              key={`point-${point.build.build_id}`}
              data-col={point.idx + 1}
              className={[
                "absolute z-10 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 bg-bp-void shadow-md",
                "transition-all duration-normal",
                dimmed ? "opacity-35" : "opacity-100",
              ].join(" ")}
              style={{
                left: `${point.x}%`,
                top: `${point.y}%`,
                borderColor: point.color,
                boxShadow: `0 0 18px ${point.color}`,
              }}
              title={`${point.build.school_name}: ${point.costText}, ${point.upsideText}`}
            />
          );
        })}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 tablet:grid-cols-2">
        {mapPoints.map((point) => {
          const dimmed = highlightIndex !== null && highlightIndex !== point.idx;
          return (
            <button
              key={`legend-${point.build.build_id}`}
              type="button"
              data-col={point.idx + 1}
              className={[
                "inline-flex min-w-0 items-center gap-2 rounded-md border border-border-subtle bg-bp-void/55 px-3 py-2 text-left",
                "transition-all duration-normal hover:bg-bp-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
                dimmed ? "opacity-40" : "opacity-100",
              ].join(" ")}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: point.color, boxShadow: `0 0 12px ${point.color}` }}
              />
              <span className="min-w-0">
                <span className="block truncate font-body text-small font-bold text-text-primary">
                  {shortName(point.build.school_name, 28)}
                </span>
                <span className="block font-data text-[11px] text-text-muted">
                  {point.costText} pressure / {point.upsideText}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DecisionRow({
  title,
  labelLeft,
  labelRight,
  builds,
  buildColors,
  highlightIndex,
  values,
}: {
  title: string;
  labelLeft: string;
  labelRight: string;
  builds: CompareResult["builds"];
  buildColors: string[];
  highlightIndex: number | null;
  values: {
    primary: number | null;
    primaryText: string;
    primaryPct: number;
    secondary: number | null;
    secondaryText: string;
    secondaryPct: number;
  }[];
}) {
  return (
    <article className="rounded-lg border border-border-subtle bg-bp-deep p-4">
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-[18px] font-semibold text-text-primary">
          {title}
        </h2>
        <div className="grid w-[48%] grid-cols-2 gap-4">
          <p className="font-data text-[10px] font-bold uppercase tracking-widest text-accent-alert">
            {labelLeft}
          </p>
          <p className="font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
            {labelRight}
          </p>
        </div>
      </header>
      <div className="flex flex-col gap-3">
        {builds.map((build, idx) => {
          const row = values[idx]!;
          const dimmed = highlightIndex !== null && highlightIndex !== idx;
          return (
            <div
              key={build.build_id}
              data-col={idx + 1}
              className="transition-opacity duration-normal"
              style={{ opacity: dimmed ? 0.25 : 1 }}
            >
              <div className="grid items-start gap-4 tablet:grid-cols-[minmax(0,1.4fr)_minmax(110px,0.8fr)_minmax(110px,0.8fr)]">
                <p className="truncate font-body text-small font-bold text-text-secondary">
                  {build.school_name}
                </p>
                <div>
                  <p className="mb-1 text-right font-data text-data-sm text-accent-alert">
                    <span className="sr-only">{labelLeft} </span>
                    {row.primaryText}
                  </p>
                  <div
                    className="h-2 rounded-full bg-accent-alert/10"
                    aria-label={`${build.school_name} ${labelLeft} ${row.primaryText}`}
                  >
                    <div
                      className="h-2 rounded-full bg-accent-alert/75"
                      style={{ width: `${clampPct(row.primaryPct)}%` }}
                    />
                  </div>
                </div>
                <div>
                  <p className="mb-1 text-right font-data text-data-sm text-text-primary">
                    <span className="sr-only">{labelRight} </span>
                    {row.secondaryText.replace("K", "k")}
                  </p>
                  <div
                    className="h-2 rounded-full bg-white/[0.05]"
                    aria-label={`${build.school_name} ${labelRight} ${row.secondaryText}`}
                  >
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${clampPct(row.secondaryPct)}%`,
                        background: buildColors[idx],
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function RiskMatrix({
  bosses,
  builds,
  buildColors,
  highlightIndex,
}: {
  bosses: CompareResult["bosses"];
  builds: CompareResult["builds"];
  buildColors: string[];
  highlightIndex: number | null;
}) {
  return (
    <article className="rounded-lg border border-border-subtle bg-bp-deep p-4">
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-[18px] font-semibold text-text-primary">
          Risk Exposure
        </h2>
        <p className="font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          Boss outcomes
        </p>
      </header>
      <div
        className="grid gap-2"
        style={{ gridTemplateColumns: `88px repeat(${builds.length}, minmax(0, 1fr))` }}
      >
        <div />
        {builds.map((build, idx) => (
          <div
            key={build.build_id}
            data-col={idx + 1}
            className="min-w-0 truncate text-center font-body text-[10px] font-bold uppercase text-text-muted"
            style={{ color: buildColors[idx] }}
          >
            {shortName(build.school_name, 12)}
          </div>
        ))}
        {bosses.map((boss) => (
          <FragmentRow
            key={boss.boss_id}
            label={boss.label}
            cells={builds.map((build, idx) => {
              const result = boss.values[idx] ?? "—";
              const dimmed = highlightIndex !== null && highlightIndex !== idx;
              return (
                <span
                  key={build.build_id}
                  data-col={idx + 1}
                  className={[
                    "rounded-md border px-2 py-1 text-center font-data text-[11px] font-bold",
                    BOSS_TONE[result] ?? "border-border-subtle bg-bp-void text-text-muted",
                    dimmed ? "opacity-25" : "opacity-100",
                  ].join(" ")}
                >
                  {result}
                </span>
              );
            })}
          />
        ))}
      </div>
    </article>
  );
}

function StatMatrix({
  result,
  buildColors,
  highlightIndex,
}: {
  result: CompareResult;
  buildColors: string[];
  highlightIndex: number | null;
}) {
  return (
    <article className="rounded-lg border border-border-subtle bg-bp-deep p-4">
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-[18px] font-semibold text-text-primary">
          Career Upside
        </h2>
        <p className="font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          Stat strength
        </p>
      </header>
      <div className="flex flex-col gap-3">
        {result.stats.filter((row) => STAT_LABELS[row.label]).map((row) => (
          <div key={row.label}>
            <div className="mb-1 flex items-center justify-between">
              <p className="font-body text-small text-text-secondary">
                {STAT_LABELS[row.label]}
              </p>
              <p className="font-data text-[10px] text-text-muted">{row.label}</p>
            </div>
            <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${result.builds.length}, 1fr)` }}>
              {result.builds.map((build, idx) => {
                const value = row.values[idx];
                const dimmed = highlightIndex !== null && highlightIndex !== idx;
                return (
                  <div
                    key={build.build_id}
                    data-col={idx + 1}
                    className="h-2 rounded-full bg-white/[0.05] transition-opacity duration-normal"
                    style={{ opacity: dimmed ? 0.25 : 1 }}
                    aria-label={`${build.school_name} ${row.label} ${value ?? "unavailable"}`}
                  >
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: value == null ? "0%" : `${clampPct((value / 10) * 100)}%`,
                        background: buildColors[idx],
                      }}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function FragmentRow({
  label,
  cells,
}: {
  label: string;
  cells: ReactNode[];
}) {
  return (
    <>
      <p className="self-center truncate font-body text-small text-text-secondary">
        {label}
      </p>
      {cells}
    </>
  );
}

export function CompareView({ buildIds, onBack }: CompareViewProps) {
  const navigate = useNavigate();
  const setBuild = useBuildStore((s) => s.setBuild);
  const t = useT();
  const [phase, setPhase] = useState<Phase>("loading");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [insights, setInsights] = useState<CompareInsights | null>(null);
  const [insightsSettled, setInsightsSettled] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState<number | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Compare-scope chip text per docs/specs/feature-ask-gemma.md §3.
  // School names truncated at 24 chars; N≥3 uses summary form.
  const compareChipText = useMemo(() => {
    if (!result?.builds || result.builds.length === 0) return "";
    const names = result.builds.map((b) =>
      b.school_name.length > 24
        ? b.school_name.slice(0, 23).trimEnd() + "…"
        : b.school_name,
    );
    if (names.length === 2) return `Comparing: ${names[0]} vs ${names[1]}`;
    return `Comparing ${names.length} builds`;
  }, [result?.builds]);

  const compareScope: AskScope | undefined = useMemo(() => {
    if (!buildIds || buildIds.length < 2) return undefined;
    return {
      kind: "compare",
      build_ids: buildIds,
    };
  }, [buildIds]);

  const handleMouseOver = useCallback((e: React.MouseEvent) => {
    let target = e.target as HTMLElement | null;
    while (target && target !== containerRef.current) {
      const col = target.getAttribute?.("data-col");
      if (col) {
        setHighlightIndex(parseInt(col, 10) - 1);
        return;
      }
      target = target.parentElement;
    }
    setHighlightIndex(null);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHighlightIndex(null);
  }, []);

  const handleOpenBuild = useCallback(async (buildId: string) => {
    try {
      const full = await getBuild(buildId);
      setBuild(full);
      navigate("/my-build");
    } catch {
      setError("Couldn't load that build.");
    }
  }, [navigate, setBuild]);

  useEffect(() => {
    if (buildIds.length === 0) {
      setError("No builds selected to compare.");
      setPhase("error");
      return;
    }
    let cancelled = false;
    setPhase("loading");
    setInsights(null);
    setInsightsSettled(false);

    const dataPromise = compareBuilds(buildIds);
    const insightsPromise = compareInsights(buildIds);

    (async () => {
      try {
        const data = await dataPromise;
        if (cancelled) return;
        setResult(data);
        setPhase("ready");
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to compare builds");
        setPhase("error");
        return;
      }

      try {
        const ins = await insightsPromise;
        if (!cancelled) setInsights(ins);
      } catch (e) {
        console.warn("Compare insights failed (non-blocking):", e);
      } finally {
        if (!cancelled) setInsightsSettled(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [buildIds]);

  if (phase === "loading") {
    return (
      <div
        data-testid="region-compare"
        className="flex flex-col items-center justify-center gap-4 py-16"
      >
        <motion.div
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
          className="w-16 h-16 rounded-full"
          style={{
            background:
              "radial-gradient(circle, var(--color-state-loading) 0%, transparent 70%)",
          }}
        />
        <p className="font-body text-body text-text-secondary">
          Loading comparison…
        </p>
      </div>
    );
  }

  if (phase === "error" || !result) {
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-center">
        <p className="font-display text-heading text-accent-alert">
          Couldn't load the comparison.
        </p>
        <p className="font-body text-body text-text-secondary">
          {error ?? "The comparison didn't load. Try again, or head back to your builds."}
        </p>
        <Button variant="ghost" onClick={onBack} data-testid="btn-back-builds">
          ← Back to builds
        </Button>
      </div>
    );
  }

  const buildCount = result.builds.length;
  const buildColors = BUILD_COLORS.slice(0, buildCount);
  const costValues = result.builds.map(costPressure);
  const upsideValues = result.builds.map((_, idx) =>
    averageStats(result, idx, ["ERN", "ROI", "GRW"]),
  );
  const resilienceValues = result.builds.map((_, idx) =>
    averageStats(result, idx, ["RES", "GRW", "AURA"]),
  );
  const lowestCostIndex = bestIndex(costValues, "low");
  const highestUpsideIndex = bestIndex(upsideValues, "high");
  const strongestResilienceIndex = bestIndex(resilienceValues, "high");
  const maxCost = Math.max(...costValues.filter((v): v is number => v !== null), 1);
  const maxSalary = Math.max(
    ...result.builds
      .map((build) => build.median_annual_wage ?? 0)
      .filter((value) => Number.isFinite(value)),
    1,
  );
  const fallbackHeroTradeoff = heroHeadline({
    builds: result.builds,
    lowestCostIndex,
    highestUpsideIndex,
    strongestResilienceIndex,
  });
  const gemmaHeroTradeoff = insights?.pivotal?.meta_tradeoff?.trim();
  const heroTradeoff = gemmaHeroTradeoff || (insightsSettled ? fallbackHeroTradeoff : null);

  return (
    <motion.article
      ref={containerRef}
      data-testid="region-compare"
      aria-label={`Comparison of ${buildCount} builds`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
      className="flex flex-col gap-0"
      onMouseOver={handleMouseOver}
      onMouseLeave={handleMouseLeave}
    >
      <section className="pt-6 pb-5">
        <div className="-mx-4 tablet:mx-0 mb-5 border-y tablet:border border-border-subtle bg-bp-void/75 tablet:rounded-lg shadow-md">
          <div
            className="grid gap-0 overflow-x-auto"
            style={{
              gridTemplateColumns: `repeat(${buildCount}, minmax(220px, 1fr))`,
            }}
          >
            {result.builds.map((build, idx) => {
              const dimmed = highlightIndex !== null && highlightIndex !== idx;
              return (
                <button
                  key={build.build_id}
                  type="button"
                  data-col={idx + 1}
                  onClick={() => setHighlightIndex(highlightIndex === idx ? null : idx)}
                  className={[
                    "min-w-0 border-r border-border-subtle last:border-r-0 px-4 py-3 text-left",
                    "transition-colors duration-normal hover:bg-white/[0.04]",
                    dimmed ? "opacity-45" : "opacity-100",
                  ].join(" ")}
                  style={{ borderTop: `3px solid ${buildColors[idx]}` }}
                >
                  <p className="font-body text-[10px] font-bold uppercase tracking-widest text-text-muted">
                    Path {idx + 1}
                  </p>
                  <p className="mt-1 truncate font-display text-[16px] font-semibold text-text-primary">
                    {build.school_name}
                  </p>
                  <p className="truncate font-body text-small text-text-secondary">
                    {build.career}
                  </p>
                  <TopRailStats result={result} buildIndex={idx} />
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid gap-5 desktop:grid-cols-[minmax(0,0.95fr)_minmax(460px,1.05fr)] desktop:items-stretch">
          <div className="rounded-lg border border-border-subtle bg-bp-deep p-5 tablet:p-6 shadow-lg">
            <p className="font-data text-[11px] font-bold uppercase tracking-widest text-accent-info">
              Big Choice
            </p>
            <div className="mt-3 min-h-[82px] tablet:min-h-[108px]">
              {heroTradeoff ? (
                <h1 className="font-display text-[32px] font-bold leading-tight text-text-primary tablet:text-[42px]">
                  {heroTradeoff}
                </h1>
              ) : (
                <BigChoiceLoading />
              )}
            </div>
            <div className="mt-6 grid grid-cols-1 gap-3 tablet:grid-cols-3 desktop:grid-cols-1">
              <SummaryCallout
                label="Lowest pressure"
                build={lowestCostIndex !== null ? result.builds[lowestCostIndex] ?? null : null}
                value={lowestCostIndex !== null ? formatMoney(costValues[lowestCostIndex] ?? null, true) : "n/a"}
                color={lowestCostIndex !== null ? buildColors[lowestCostIndex] : undefined}
              />
              <SummaryCallout
                label="Highest upside"
                build={highestUpsideIndex !== null ? result.builds[highestUpsideIndex] ?? null : null}
                value={highestUpsideIndex !== null && upsideValues[highestUpsideIndex] !== null ? `${upsideValues[highestUpsideIndex]!.toFixed(1)}/10` : "n/a"}
                color={highestUpsideIndex !== null ? buildColors[highestUpsideIndex] : undefined}
              />
              <SummaryCallout
                label="Most resilient"
                build={strongestResilienceIndex !== null ? result.builds[strongestResilienceIndex] ?? null : null}
                value={strongestResilienceIndex !== null && resilienceValues[strongestResilienceIndex] !== null ? `${resilienceValues[strongestResilienceIndex]!.toFixed(1)}/10` : "n/a"}
                color={strongestResilienceIndex !== null ? buildColors[strongestResilienceIndex] : undefined}
              />
            </div>
          </div>

          <TradeoffMap
            result={result}
            buildColors={buildColors}
            costValues={costValues}
            upsideValues={upsideValues}
            highlightIndex={highlightIndex}
            maxCost={maxCost}
          />
        </div>
      </section>

      <section className="mb-8 grid gap-4 desktop:grid-cols-3" aria-label="Decision rows">
        <DecisionRow
          title="Money Pressure"
          labelLeft="Cost"
          labelRight="Early pay"
          builds={result.builds}
          buildColors={buildColors}
          highlightIndex={highlightIndex}
          values={result.builds.map((build, idx) => ({
            primary: costValues[idx] ?? null,
            primaryText: formatMoney(costValues[idx] ?? null, true),
            primaryPct: costValues[idx] == null ? 0 : (costValues[idx]! / maxCost) * 100,
            secondary: build.median_annual_wage,
            secondaryText: formatMoney(build.median_annual_wage, true),
            secondaryPct: build.median_annual_wage == null ? 0 : (build.median_annual_wage / maxSalary) * 100,
          }))}
        />
        <RiskMatrix
          bosses={result.bosses}
          builds={result.builds}
          buildColors={buildColors}
          highlightIndex={highlightIndex}
        />
        <StatMatrix
          result={result}
          buildColors={buildColors}
          highlightIndex={highlightIndex}
        />
      </section>

      <section
        className="mb-8"
        data-testid="region-compare-winners"
        aria-label="Where they win — dimension comparison"
      >
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <p className="font-body text-[11px] font-bold uppercase tracking-widest text-text-muted">
            Where Each Path Wins
          </p>
          <p className="hidden tablet:block font-body text-small text-text-muted">
            Click a path in the rail to pin focus.
          </p>
        </div>
        <CompareWinners result={result} highlightIndex={highlightIndex} />
      </section>

      <section className="mb-8 grid gap-5 desktop:grid-cols-[360px_minmax(0,1fr)] desktop:items-start">
        <div>
          <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
            Builds
          </p>
          <motion.div
            className="grid grid-cols-1 gap-4"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: {},
              visible: { transition: { staggerChildren: stagger.normal } },
            }}
          >
            {result.builds.map((build, idx) => (
              <motion.div
                key={build.build_id}
                data-col={idx + 1}
                variants={{
                  hidden: { opacity: 0, y: 18, scale: 0.98 },
                  visible: { opacity: 1, y: 0, scale: 1, transition: springs.smooth },
                }}
              >
                <CharacterCard
                  build={build}
                  stats={result.stats}
                  buildIndex={idx}
                  highlighted={highlightIndex === null || highlightIndex === idx}
                  onOpen={() => handleOpenBuild(build.build_id)}
                  showStats={false}
                />
              </motion.div>
            ))}
          </motion.div>
        </div>

        <div className="flex flex-col gap-5">
          <section>
            <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
              Pentagon Detail
            </p>
            <div className="flex justify-center rounded-lg border border-border-subtle bg-bp-deep py-5">
              <PentagonOverlay result={result} highlightIndex={highlightIndex} size={320} />
            </div>
          </section>

          <section>
            <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
              Boss Gauntlet
            </p>
            <RiskHeadlineGrid
              bosses={result.bosses}
              builds={result.builds}
              buildColors={buildColors}
              highlightIndex={highlightIndex}
            />
          </section>

          <section>
            <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
              Early Salary
            </p>
            <MoneySection builds={result.builds} highlightIndex={highlightIndex} />
          </section>
        </div>
      </section>

      {/* Cost Breakdown accordion */}
      <section className="mb-8">
        <CompareAccordion
          title="Cost Breakdown"
          icon={<span aria-hidden className="font-data text-data-sm text-accent-caution">$</span>}
          testId="accordion-cost-breakdown"
          ariaLabel="Cost breakdown comparison"
        >
          <CompareCostBreakdown builds={result.builds} highlightIndex={highlightIndex} />
        </CompareAccordion>
      </section>

      {/* School Profile accordion */}
      <section className="mb-8">
        <CompareAccordion
          title="School Profile"
          icon={<span aria-hidden className="font-data text-data-sm text-accent-info">ID</span>}
          testId="accordion-school-profile"
          ariaLabel="School profile comparison"
        >
          <CompareSchoolProfile
            builds={result.builds}
            stats={result.stats}
            highlightIndex={highlightIndex}
          />
        </CompareAccordion>
      </section>

      {/* Branch Preview */}
      {result.branches.some((b) => b.destinations.length > 0) && (
        <section className="mb-16">
          <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
            Career Branches
          </p>
          <BranchPreview
            branches={result.branches}
            buildColors={buildColors}
            highlightIndex={highlightIndex}
          />
        </section>
      )}

      {/* Gemma's Take */}
      <section
        data-testid="region-gemma-compare"
        aria-label="Gemma's comparison analysis"
        className="border-t border-border-subtle pt-6"
      >
        <div className="flex items-center justify-center gap-2.5 mb-5">
          <span className="w-8 h-8 rounded-md bg-accent-info/15 flex items-center justify-center font-data text-data-sm font-bold text-accent-info">
            AI
          </span>
          <span className="font-display font-semibold text-xl text-text-primary">
            Gemma's Take
          </span>
        </div>

        <div className="max-w-[720px] mx-auto flex flex-col gap-5">
          {insights?.compare_summary ? (
            <p className="font-body text-[15px] text-text-secondary leading-relaxed text-center">
              {(() => {
                const trimmed = insights.compare_summary.trim();
                const sentenceMatch = trimmed.match(/^[^.!?]+[.!?]/);
                return sentenceMatch ? sentenceMatch[0] : trimmed;
              })()}
            </p>
          ) : (
            <motion.p
              animate={{ opacity: [0.4, 0.9, 0.4] }}
              transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
              className="font-body text-body text-text-muted text-center"
            >
              Reading the tradeoffs…
            </motion.p>
          )}

          {insights?.pivotal?.meta_tradeoff && (
            <div
              data-testid="pivotal-meta-tradeoff"
              className="self-center inline-flex flex-col items-center gap-1.5 px-5 py-3 rounded-full bg-bp-deep/60 border border-border-subtle"
            >
              <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted">
                Big Choice
              </p>
              <p className="font-display text-heading text-text-primary">
                {insights.pivotal.meta_tradeoff}
              </p>
              {insights.pivotal.meta_explanation && (
                <p className="font-body text-small text-text-secondary text-center max-w-[520px] leading-snug">
                  {insights.pivotal.meta_explanation}
                </p>
              )}
            </div>
          )}

          {insights?.pros_cons && insights.pros_cons.length > 0 && (
            <CompareProsCons
              builds={result.builds}
              prosCons={insights.pros_cons}
              highlightIndex={highlightIndex}
            />
          )}

          {insights?.pivotal?.decade_projection && (
            <article
              data-testid="pivotal-decade-projection"
              className="rounded-xl p-5 bg-bp-deep/60 border border-border-subtle relative"
            >
              <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-accent-info to-accent-info/20 rounded-l-xl" />
              <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted mb-2">
                In ten years
              </p>
              <p className="font-body text-[15px] text-text-primary leading-relaxed">
                {insights.pivotal.decade_projection}
              </p>
            </article>
          )}

          {insights?.pivotal?.pivot_question && (
            <article
              data-testid="pivotal-question"
              className="rounded-xl p-5 bg-gradient-to-br from-accent-thrive/10 to-accent-insight/10 border border-accent-thrive/30 relative"
            >
              <p className="font-data text-[11px] font-bold tracking-widest uppercase text-accent-thrive mb-2">
                Sit with this
              </p>
              <p className="font-display text-heading text-text-primary leading-snug">
                {insights.pivotal.pivot_question}
              </p>
            </article>
          )}
        </div>

        {insights?.compare_summary && compareScope && (
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            disabled={chatOpen}
            data-testid="btn-ask-compare"
            aria-label={t("chat.compareEntry")}
            className={[
              "w-full max-w-[420px] mx-auto mt-5 block",
              "inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-lg",
              "bg-accent-thrive text-text-inverse font-body text-cta",
              "hover:bg-[#6bc494]",
              "active:scale-[0.97]",
              "focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none",
              "disabled:bg-bp-surface disabled:text-text-muted disabled:cursor-not-allowed",
              "transition-colors duration-fast",
              "cursor-pointer",
            ].join(" ")}
          >
            <span aria-hidden className="text-text-inverse text-[16px] leading-none">
              AI
            </span>
            {t("chat.compareEntry")}
          </button>
        )}
      </section>

      <GemmaChat
        open={chatOpen}
        build={null}
        scope={compareScope}
        chipText={compareChipText}
        onClose={() => setChatOpen(false)}
      />
    </motion.article>
  );
}
