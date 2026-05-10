import { useMemo } from "react";
import type { CompareBuild } from "@/api/menu";
import { Year1SalaryBar } from "@/components/shared/Year1SalaryBar";

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
            <div key={build.build_id} data-col={idx + 1}>
              <Year1SalaryBar
                schoolName={build.school_name}
                programMedian={build.earnings_1yr_median}
                careerMedian={build.median_annual_wage}
                peerP25={build.earnings_1yr_p25}
                peerP75={build.earnings_1yr_p75}
                scaleMin={scaleMin}
                scaleMax={scaleMax}
                highlighted={highlightIndex === null || highlightIndex === idx}
                testId={`salary-${build.build_id}`}
              />
            </div>
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
