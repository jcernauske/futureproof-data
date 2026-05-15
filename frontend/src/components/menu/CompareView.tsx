import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { getBuild } from "@/api/build";
import { useBuildStore } from "@/store/buildStore";
import {
  compareBuilds,
  type AskScope,
  type CompareResult,
} from "@/api/menu";
import { PentagonOverlay } from "@/components/menu/PentagonOverlay";
import { RiskHeadlineGrid } from "@/components/menu/RiskHeadlineCard";
import { CharacterCard } from "@/components/menu/CharacterCard";
import { MoneySection } from "@/components/menu/MoneySection";
import { BranchPreview } from "@/components/menu/BranchPreview";
import { CompareWinners } from "@/components/menu/CompareWinners";
import { CompareAccordion } from "@/components/menu/CompareAccordion";
import { CompareCostBreakdown } from "@/components/menu/CompareCostBreakdown";
import { CompareSchoolProfile } from "@/components/menu/CompareSchoolProfile";
import { Button } from "@/components/ui/Button";
import { GemmaSpinner } from "@/components/ui/GemmaSpinner";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { useT } from "@/i18n/useT";
import { useProfileStore } from "@/store/profileStore";
import { exportComparisonPdf, downloadBlobAs } from "@/api/pdf";

interface CompareViewProps {
  buildIds: string[];
  onBack: () => void;
}

type Phase = "loading" | "ready" | "error";

const COMPARE_STARTER_KEYS = [
  "compare.starter.whichOne",
  "compare.starter.cheapestCatchUp",
  "compare.starter.realCost",
  "compare.starter.saferLongTerm",
];

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-caution)",
  "var(--color-accent-empathy)",
];

const STAT_LABEL_KEYS: Record<string, string> = {
  ERN: "compare.stat.ern",
  ROI: "compare.stat.roi",
  RES: "compare.stat.res",
  GRW: "compare.stat.grw",
  AURA: "compare.stat.aura",
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
  t,
}: {
  builds: CompareResult["builds"];
  lowestCostIndex: number | null;
  highestUpsideIndex: number | null;
  strongestResilienceIndex: number | null;
  t: (key: string, vars?: Record<string, string | number>) => string;
}): string {
  const cost = lowestCostIndex !== null ? builds[lowestCostIndex] : null;
  const upside = highestUpsideIndex !== null ? builds[highestUpsideIndex] : null;
  const resilience =
    strongestResilienceIndex !== null ? builds[strongestResilienceIndex] : null;

  if (cost && upside && cost.build_id !== upside.build_id) {
    return t("compare.hero.costVsUpside", {
      costSchool: cost.school_name,
      upsideSchool: upside.school_name,
    });
  }
  if (upside && resilience && upside.build_id !== resilience.build_id) {
    return t("compare.hero.upsideVsResilience", {
      upsideSchool: upside.school_name,
      resilienceSchool: resilience.school_name,
    });
  }
  if (upside) return t("compare.hero.upsideOnly", { upsideSchool: upside.school_name });
  return t("compare.hero.fallback");
}

function BigChoiceLoading() {
  const t = useT();
  return (
    <div className="flex items-center gap-3 py-2" role="status" aria-label={t("compare.loadingBigChoice")}>
      <GemmaSpinner size={34} className="shrink-0" />
      <span className="font-display text-[28px] font-bold leading-tight text-text-muted animate-gemma-shimmer-loop tablet:text-[36px]">
        {t("compare.readingTradeoffs")}
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
  const t = useT();
  return (
    <div
      className="rounded-md border border-border-subtle bg-bp-void/50 px-4 py-3"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <p className="font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
        {label}
      </p>
      <p className="mt-1 truncate font-display text-[18px] font-semibold text-text-primary">
        {build ? shortName(build.school_name, 24) : t("compare.callout.insufficient")}
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
  const t = useT();
  return (
    <div className="mt-3 flex flex-col gap-1.5" aria-label={t("compare.rail.statBars")}>
      {Object.keys(STAT_LABEL_KEYS).map((label) => {
        const raw = statValue(result, label, buildIndex);
        const isAbsent = raw == null;
        const value = isAbsent ? 0 : Math.max(0, Math.min(10, raw));
        const color = STAT_COLORS[label] ?? "var(--color-text-muted)";
        const tipValue = isAbsent ? t("compare.rail.statUnavailable") : String(value);
        return (
          <div
            key={label}
            className="grid min-w-0 items-center gap-2"
            style={{ gridTemplateColumns: "34px minmax(72px, 1fr) 22px" }}
            title={t("compare.rail.statTooltip", { label: t(STAT_LABEL_KEYS[label]!), value: tipValue })}
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
  const t = useT();
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
      upsideText: upsideValues[idx] == null
        ? t("compare.callout.na")
        : `${upsideValues[idx]!.toFixed(1)} ${t("compare.tradeoff.upSuffix")}`,
    };
  });

  return (
    <div className="rounded-lg border border-border-subtle bg-bp-deep p-5 tablet:p-6 shadow-lg">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="font-data text-[11px] font-bold uppercase tracking-widest text-text-muted">
            {t("compare.section.costUpsideMap")}
          </p>
          <h2 className="mt-1 font-display text-subheading font-semibold text-text-primary">
            {t("compare.tradeoff.subtitle")}
          </h2>
          <p className="mt-2 max-w-[620px] font-body text-small leading-relaxed text-text-secondary">
            {t("compare.tradeoff.body")}
          </p>
        </div>
        <div className="hidden tablet:flex items-center gap-2 font-data text-data-sm text-text-muted">
          <span>{t("compare.tradeoff.lowerCost")}</span>
          <span className="h-px w-8 bg-border" />
          <span>{t("compare.tradeoff.higherCost")}</span>
        </div>
      </div>

      <div className="relative h-[340px] overflow-hidden rounded-md border border-border-subtle bg-bp-void">
        <div className="absolute inset-x-6 top-1/2 h-px bg-border-subtle" />
        <div className="absolute inset-y-6 left-1/2 w-px bg-border-subtle" />
        <div className="absolute left-4 top-3 font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          {t("compare.tradeoff.higherUpside")}
        </div>
        <div className="absolute bottom-3 right-4 font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          {t("compare.tradeoff.higherPressure")}
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
                  {point.costText} {t("compare.tradeoff.legendPressureSuffix")} / {point.upsideText}
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
  const t = useT();
  return (
    <article className="rounded-lg border border-border-subtle bg-bp-deep p-4">
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-[18px] font-semibold text-text-primary">
          {t("compare.section.riskExposure")}
        </h2>
        <p className="font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          {t("compare.section.bossOutcomes")}
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
  const t = useT();
  return (
    <article className="rounded-lg border border-border-subtle bg-bp-deep p-4">
      <header className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-[18px] font-semibold text-text-primary">
          {t("compare.section.careerUpside")}
        </h2>
        <p className="font-data text-[10px] font-bold uppercase tracking-widest text-text-muted">
          {t("compare.section.statStrength")}
        </p>
      </header>
      <div className="flex flex-col gap-3">
        {result.stats.filter((row) => STAT_LABEL_KEYS[row.label]).map((row) => (
          <div key={row.label}>
            <div className="mb-1 flex items-center justify-between">
              <p className="font-body text-small text-text-secondary">
                {t(STAT_LABEL_KEYS[row.label]!)}
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
  const locale = useProfileStore((s) => s.locale);
  const [phase, setPhase] = useState<Phase>("loading");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [highlightIndex, setHighlightIndex] = useState<number | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [pdfState, setPdfState] = useState<"idle" | "loading" | "error">("idle");
  const [pdfErrorMsg, setPdfErrorMsg] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pentagonSectionRef = useRef<HTMLDivElement>(null);

  const handlePentagonMouseOver = useCallback((e: React.MouseEvent) => {
    let target = e.target as HTMLElement | null;
    while (target && target !== pentagonSectionRef.current) {
      const col = target.getAttribute?.("data-col");
      if (col) {
        setHighlightIndex(parseInt(col, 10) - 1);
        return;
      }
      target = target.parentElement;
    }
    setHighlightIndex(null);
  }, []);

  const handlePentagonMouseLeave = useCallback(() => {
    setHighlightIndex(null);
  }, []);

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


  // Export-PDF guard — only the build-count cap. Cross-major comparisons
  // are supported (the in-app CompareView already shows them; the PDF
  // matches that contract). The PDF title falls back to "Career
  // comparison" server-side when majors differ.
  const exportPdfDisabledReason = useMemo<string | null>(() => {
    const builds = result?.builds ?? [];
    if (builds.length < 2) return t("compare.exportPdfDisabledFew");
    if (builds.length > 4) return t("compare.exportPdfDisabledMany");
    return null;
  }, [result?.builds, t]);

  const handleExportPdf = useCallback(async () => {
    if (pdfState === "loading") return;
    if (exportPdfDisabledReason) return;
    setPdfState("loading");
    setPdfErrorMsg(null);
    try {
      const blob = await exportComparisonPdf(buildIds, { locale });
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const major = (result?.builds[0]?.major_text || "compare")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      const filename = `futureproof-compare-${major}-${buildIds.length}schools-${today}.pdf`;
      downloadBlobAs(blob, filename);
      setPdfState("idle");
    } catch (err) {
      console.warn("compare pdf export failed:", err);
      // Surface the backend's actual error detail (e.g. "Comparison PDF
      // requires the same major across schools..."). Fall back to the
      // generic toast string only when the error has no message.
      const detail = err instanceof Error ? err.message : "";
      setPdfErrorMsg(detail || t("build.exportPdfError"));
      setPdfState("error");
      setTimeout(() => {
        setPdfState("idle");
        setPdfErrorMsg(null);
      }, 8000);
    }
  }, [buildIds, exportPdfDisabledReason, pdfState, result?.builds, t]);

  const handleOpenBuild = useCallback(async (buildId: string) => {
    try {
      const full = await getBuild(buildId);
      setBuild(full);
      navigate("/my-build");
    } catch {
      setError(t("compare.errorBuild"));
    }
  }, [navigate, setBuild, t]);

  useEffect(() => {
    if (buildIds.length === 0) {
      setError(t("compare.errorNoBuildsSelected"));
      setPhase("error");
      return;
    }
    let cancelled = false;
    setPhase("loading");

    (async () => {
      try {
        const data = await compareBuilds(buildIds);
        if (cancelled) return;
        setResult(data);
        setPhase("ready");
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : t("compare.errorCompareFailed"));
        setPhase("error");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [buildIds, t]);

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
          {t("compare.loading")}
        </p>
      </div>
    );
  }

  if (phase === "error" || !result) {
    return (
      <div className="flex flex-col items-center gap-4 py-12 text-center">
        <p className="font-display text-heading text-accent-alert">
          {t("compare.errorTitle")}
        </p>
        <p className="font-body text-body text-text-secondary">
          {error ?? t("compare.errorDefault")}
        </p>
        <Button variant="ghost" onClick={onBack} data-testid="btn-back-builds">
          {t("compare.backToBuilds")}
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
    t,
  });
  const heroTradeoff = fallbackHeroTradeoff;

  return (
    <motion.article
      ref={containerRef}
      data-testid="region-compare"
      aria-label={t("compare.regionLabel", { n: buildCount })}
      initial={{ y: 12 }}
      animate={{ y: 0 }}
      transition={springs.smooth}
      className="flex flex-col gap-0"
    >
      <section className="pt-6 pb-5">
        <div className="flex items-center justify-end gap-3 mb-3">
          <button
            type="button"
            data-testid="btn-export-pdf-compare"
            aria-label={t("compare.exportPdfAriaLabel")}
            onClick={handleExportPdf}
            disabled={pdfState === "loading" || exportPdfDisabledReason !== null}
            title={exportPdfDisabledReason ?? undefined}
            className="font-body text-accent-info hover:underline hover:brightness-125 transition-colors duration-150 bg-transparent border-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ fontSize: 14 }}
          >
            {pdfState === "loading"
              ? t("build.exportingPdf")
              : t("compare.exportPdf")}
          </button>
          {pdfState === "error" && (
            <span
              role="alert"
              data-testid="alert-pdf-export-error"
              className="font-body text-accent-warn"
              style={{ fontSize: 13, maxWidth: 480 }}
            >
              {pdfErrorMsg ?? t("build.exportPdfError")}
            </span>
          )}
        </div>
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
                    {t("compare.rail.path", { n: idx + 1 })}
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
              {t("compare.section.bigChoice")}
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
                label={t("compare.callout.lowestPressure")}
                build={lowestCostIndex !== null ? result.builds[lowestCostIndex] ?? null : null}
                value={lowestCostIndex !== null ? formatMoney(costValues[lowestCostIndex] ?? null, true) : t("compare.callout.na")}
                color={lowestCostIndex !== null ? buildColors[lowestCostIndex] : undefined}
              />
              <SummaryCallout
                label={t("compare.callout.highestUpside")}
                build={highestUpsideIndex !== null ? result.builds[highestUpsideIndex] ?? null : null}
                value={highestUpsideIndex !== null && upsideValues[highestUpsideIndex] !== null ? t("compare.unitOf10", { value: upsideValues[highestUpsideIndex]!.toFixed(1) }) : t("compare.callout.na")}
                color={highestUpsideIndex !== null ? buildColors[highestUpsideIndex] : undefined}
              />
              <SummaryCallout
                label={t("compare.callout.mostResilient")}
                build={strongestResilienceIndex !== null ? result.builds[strongestResilienceIndex] ?? null : null}
                value={strongestResilienceIndex !== null && resilienceValues[strongestResilienceIndex] !== null ? t("compare.unitOf10", { value: resilienceValues[strongestResilienceIndex]!.toFixed(1) }) : t("compare.callout.na")}
                color={strongestResilienceIndex !== null ? buildColors[strongestResilienceIndex] : undefined}
              />
            </div>
          </div>

          <TradeoffMap
            result={result}
            buildColors={buildColors}
            costValues={costValues}
            upsideValues={upsideValues}
            highlightIndex={null}
            maxCost={maxCost}
          />
        </div>
      </section>

      <section className="mb-8 grid gap-4 desktop:grid-cols-3" aria-label={t("compare.section.moneyPressure")}>
        <DecisionRow
          title={t("compare.section.moneyPressure")}
          labelLeft={t("compare.section.cost")}
          labelRight={t("compare.section.earlyPay")}
          builds={result.builds}
          buildColors={buildColors}
          highlightIndex={null}
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
          highlightIndex={null}
        />
        <StatMatrix
          result={result}
          buildColors={buildColors}
          highlightIndex={null}
        />
      </section>

      <section
        className="mb-8"
        data-testid="region-compare-winners"
        aria-label={t("compare.winners.regionLabel")}
      >
        <div className="mb-3 flex items-baseline justify-between gap-3">
          <p className="font-body text-[11px] font-bold uppercase tracking-widest text-text-muted">
            {t("compare.section.whereEachWins")}
          </p>
          <p className="hidden tablet:block font-body text-small text-text-muted">
            {t("compare.winners.pinFocusHint")}
          </p>
        </div>
        <CompareWinners result={result} highlightIndex={null} />
      </section>

      <section
        ref={pentagonSectionRef}
        onMouseOver={handlePentagonMouseOver}
        onMouseLeave={handlePentagonMouseLeave}
        className="mb-8 grid gap-5 desktop:grid-cols-[360px_minmax(0,1fr)] desktop:items-start"
      >
        <div>
          <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
            {t("compare.section.builds")}
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
              {t("compare.section.pentagonDetail")}
            </p>
            <div className="flex justify-center rounded-lg border border-border-subtle bg-bp-deep py-5">
              <PentagonOverlay result={result} highlightIndex={highlightIndex} size={320} />
            </div>
          </section>

          <section>
            <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
              {t("compare.section.bossGauntlet")}
            </p>
            <RiskHeadlineGrid
              bosses={result.bosses}
              builds={result.builds}
              buildColors={buildColors}
              highlightIndex={null}
            />
          </section>

          <section>
            <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
              {t("compare.section.earlySalary")}
            </p>
            <MoneySection builds={result.builds} highlightIndex={null} />
          </section>
        </div>
      </section>

      {/* Cost Breakdown accordion */}
      <section className="mb-8">
        <CompareAccordion
          title={t("compare.accordion.costBreakdown")}
          icon={<span aria-hidden className="font-data text-data-sm text-accent-caution">$</span>}
          testId="accordion-cost-breakdown"
          ariaLabel={t("compare.accordion.costAriaLabel")}
        >
          <CompareCostBreakdown builds={result.builds} highlightIndex={null} />
        </CompareAccordion>
      </section>

      {/* School Profile accordion */}
      <section className="mb-8">
        <CompareAccordion
          title={t("compare.accordion.schoolProfile")}
          icon={<span aria-hidden className="font-data text-data-sm text-accent-info">ID</span>}
          testId="accordion-school-profile"
          ariaLabel={t("compare.accordion.schoolAriaLabel")}
        >
          <CompareSchoolProfile
            builds={result.builds}
            stats={result.stats}
            highlightIndex={null}
          />
        </CompareAccordion>
      </section>

      {/* Branch Preview */}
      {result.branches.some((b) => b.destinations.length > 0) && (
        <section className="mb-16">
          <p className="font-body text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3 pl-1">
            {t("compare.section.careerBranches")}
          </p>
          <BranchPreview
            branches={result.branches}
            buildColors={buildColors}
            highlightIndex={null}
          />
        </section>
      )}

      {/* ================================================================
       * Gemma's Verdict — editorial climax of the comparison.
       *
       * Visual hierarchy:
       *   1. Accent divider + GemmaStar header
       *   2. Summary lede (one-sentence read)
       *   3. Big Choice — thesis callout with insight accent bar
       *   4. Pros/Cons — editorial prose cards per build
       *   5. Decade Projection — "In ten years" with info accent bar
       *   6. Pivot Question — mic-drop moment with thrive glow
       *
       * Each element staggers in at 100ms (stagger.slow) for cinematic
       * pacing. The section breathes with generous vertical spacing so
       * the student can absorb each insight before the next arrives.
       * ================================================================ */}

      <AnimatePresence>
        {!chatOpen && compareScope && (
          <motion.button
            key="compare-fab"
            type="button"
            onClick={() => setChatOpen(true)}
            aria-label={t("chat.compareEntry")}
            data-testid="btn-ask-compare"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={springs.snappy}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.95 }}
            className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-accent-insight/15 text-accent-insight border border-accent-insight/40 px-5 py-3.5 font-body font-bold text-cta shadow-lg backdrop-blur-md hover:bg-accent-insight/25 hover:border-accent-insight/70 hover:shadow-glow-insight cursor-pointer"
            style={{ paddingBottom: "max(14px, calc(env(safe-area-inset-bottom) + 14px))" }}
          >
            <span aria-hidden className="font-display text-[18px] leading-none">
              ✦
            </span>
            {t("chat.compareEntry")}
          </motion.button>
        )}
      </AnimatePresence>

      <GemmaChat
        open={chatOpen}
        build={null}
        scope={compareScope}
        chipText={compareChipText}
        starters={COMPARE_STARTER_KEYS.map((k) => t(k))}
        onClose={() => setChatOpen(false)}
      />
    </motion.article>
  );
}
