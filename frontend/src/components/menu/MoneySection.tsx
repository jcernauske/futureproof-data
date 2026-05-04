import { useMemo } from "react";
import type { CompareBuild } from "@/api/menu";

interface MoneySectionProps {
  builds: CompareBuild[];
  highlightIndex?: number | null;
}

function formatSalaryShort(val: number | null): string {
  if (val == null) return "n/a";
  return `$${Math.round(val / 1000)}K`;
}

export function MoneySection({ builds, highlightIndex = null }: MoneySectionProps) {
  const hasAnyRange = builds.some(
    (b) => b.earnings_1yr_p25 != null && b.earnings_1yr_p75 != null,
  );

  const { scaleMin, scaleMax } = useMemo(() => {
    if (!hasAnyRange) return { scaleMin: 0, scaleMax: 1 };
    const p25s = builds.map((b) => b.earnings_1yr_p25).filter((v): v is number => v != null);
    const p75s = builds.map((b) => b.earnings_1yr_p75).filter((v): v is number => v != null);
    const medians = builds.map((b) => b.median_annual_wage).filter((v): v is number => v != null);
    const allVals = [...p25s, ...p75s, ...medians];
    if (allVals.length === 0) return { scaleMin: 0, scaleMax: 1 };
    const min = Math.min(...allVals);
    const max = Math.max(...allVals);
    const padding = (max - min) * 0.05;
    return { scaleMin: min - padding, scaleMax: max + padding };
  }, [builds, hasAnyRange]);

  return (
    <div
      className="bg-bp-deep border border-border-subtle rounded-[20px] p-5"
      data-testid="money-section"
    >
      <div className="mb-5 flex flex-col gap-2 tablet:flex-row tablet:items-start tablet:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full shrink-0 bg-stat-ern" />
            <span className="font-display font-medium text-sm text-text-primary">
              Early Salary
            </span>
          </div>
          <p className="mt-1 font-body text-small text-text-secondary">
            Band shows the middle 50% of peer programs in this field. The pill marks this school/program's reported early-earnings median when available.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3 font-data text-[11px] text-text-muted">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-7 rounded-full bg-stat-ern/35" />
            Peer 25th-75th
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-4 w-4 rounded-full border border-stat-ern bg-stat-ern/25" />
            This program median
          </span>
        </div>
      </div>

      {hasAnyRange ? (
        <div className="flex flex-col gap-4">
          {builds.map((build, idx) => (
            <SalaryBar
              key={build.build_id}
              build={build}
              buildIndex={idx}
              scaleMin={scaleMin}
              scaleMax={scaleMax}
              highlighted={highlightIndex === null || highlightIndex === idx}
            />
          ))}
        </div>
      ) : (
        <div
          className="grid items-center"
          style={{ gridTemplateColumns: `repeat(${builds.length}, 1fr)` }}
        >
          {builds.map((build, idx) => (
            <div
              key={build.build_id}
              data-col={idx + 1}
              data-testid={`salary-${build.build_id}`}
              className="flex flex-col items-center transition-opacity duration-200"
              style={{
                opacity: highlightIndex !== null && highlightIndex !== idx ? 0.2 : 1,
              }}
            >
              <p className="font-body text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1.5">
                {build.school_name}
              </p>
              <span className="font-data text-[22px] font-bold text-stat-ern">
                {formatSalaryShort(build.median_annual_wage)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface SalaryBarProps {
  build: CompareBuild;
  buildIndex: number;
  scaleMin: number;
  scaleMax: number;
  highlighted: boolean;
}

function SalaryBar({ build, buildIndex, scaleMin, scaleMax, highlighted }: SalaryBarProps) {
  const range = scaleMax - scaleMin || 1;
  const hasRange = build.earnings_1yr_p25 != null && build.earnings_1yr_p75 != null;
  const programMedian = build.earnings_1yr_median;
  const careerMedian = build.median_annual_wage;
  const markerValue = programMedian ?? careerMedian;
  const markerLabel = programMedian != null
    ? "This program median"
    : "Career wage reference";
  const peerBandPosition =
    hasRange && programMedian != null
      ? programMedian > build.earnings_1yr_p75!
        ? "above"
        : programMedian < build.earnings_1yr_p25!
          ? "below"
          : "inside"
      : null;

  const p25Pct = hasRange ? ((build.earnings_1yr_p25! - scaleMin) / range) * 100 : 0;
  const p75Pct = hasRange ? ((build.earnings_1yr_p75! - scaleMin) / range) * 100 : 100;
  const medianPct = markerValue != null ? ((markerValue - scaleMin) / range) * 100 : 50;

  return (
    <div
      data-col={buildIndex + 1}
      data-testid={`salary-${build.build_id}`}
      className="transition-opacity duration-200"
      style={{ opacity: highlighted ? 1 : 0.2 }}
    >
      <p className="font-body text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1.5">
        {build.school_name}
      </p>

      {hasRange ? (
        <>
          <div className="relative h-9 w-full" aria-label={`Salary range: ${formatSalaryShort(build.earnings_1yr_p25)} to ${formatSalaryShort(build.earnings_1yr_p75)}, ${markerLabel.toLowerCase()} ${formatSalaryShort(markerValue)}`}>
            <div className="absolute left-0 right-0 top-[15px] h-1 rounded-full bg-white/[0.08]" />
            {/* Range band */}
            <div
              className="absolute top-[10px] h-3.5 rounded-full border border-stat-ern/20"
              style={{
                left: `${p25Pct}%`,
                width: `${p75Pct - p25Pct}%`,
                background: "rgba(242, 212, 119, 0.34)",
              }}
            />
            {/* Median pill */}
            <div
              className="absolute top-[3px] h-7 flex items-center justify-center rounded-full px-3 border shadow-sm"
              style={{
                left: `${Math.max(Math.min(medianPct - 4, 94), 0)}%`,
                minWidth: "64px",
                background: programMedian != null
                  ? "rgba(242, 212, 119, 0.30)"
                  : "rgba(123, 184, 224, 0.18)",
                borderColor: programMedian != null
                  ? "rgba(242, 212, 119, 0.70)"
                  : "rgba(123, 184, 224, 0.65)",
              }}
            >
              <span className="font-data text-[15px] font-bold text-stat-ern whitespace-nowrap">
                {formatSalaryShort(markerValue)}
              </span>
            </div>
          </div>
          {/* Range labels */}
          <div
            className="flex justify-between mt-1"
            style={{ paddingLeft: `${p25Pct}%`, paddingRight: `${100 - p75Pct}%` }}
          >
            <span className="flex flex-col font-data text-data-sm text-text-secondary">
              <span className="text-[10px] uppercase tracking-widest text-text-muted">Peer 25th</span>
              <span>{formatSalaryShort(build.earnings_1yr_p25)}</span>
            </span>
            <span className="flex flex-col items-end font-data text-data-sm text-text-secondary">
              <span className="text-[10px] uppercase tracking-widest text-text-muted">Peer 75th</span>
              <span>{formatSalaryShort(build.earnings_1yr_p75)}</span>
            </span>
          </div>
          {peerBandPosition && peerBandPosition !== "inside" && (
            <div
              className={[
                "mt-3 rounded-lg border bg-bp-mid/45 px-4 py-3",
                peerBandPosition === "above"
                  ? "border-accent-thrive/25 shadow-glow-thrive"
                  : "border-accent-alert/25 shadow-glow-alert",
              ].join(" ")}
              style={{
                borderLeftWidth: 3,
                borderLeftColor:
                  peerBandPosition === "above"
                    ? "var(--color-accent-thrive)"
                    : "var(--color-accent-alert)",
              }}
            >
              <p
                className={[
                  "font-data text-[10px] font-bold uppercase tracking-widest",
                  peerBandPosition === "above"
                    ? "text-accent-thrive"
                    : "text-accent-alert",
                ].join(" ")}
              >
                {peerBandPosition === "above" ? "Standout earnings" : "Earnings caution"}
              </p>
              <p className="mt-1 font-display text-[16px] font-semibold leading-snug text-text-primary">
                {peerBandPosition === "above"
                  ? "This program beats the peer-program 75th percentile for this field."
                  : "This program sits below the peer-program 25th percentile for this field."}
              </p>
            </div>
          )}
          {programMedian == null && markerValue != null && (
            <p className="mt-2 font-body text-small text-text-muted">
              Pill is a career wage reference because program median earnings are unavailable.
            </p>
          )}
        </>
      ) : (
          <div className="flex justify-center py-1">
            <span className="font-data text-[22px] font-bold text-stat-ern">
              {formatSalaryShort(markerValue)}
            </span>
          </div>
      )}
    </div>
  );
}
