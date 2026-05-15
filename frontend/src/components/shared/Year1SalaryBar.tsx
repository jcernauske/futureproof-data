/**
 * Year1SalaryBar — single-row peer-band visualization with a program-median
 * pill on top.
 *
 * Renders College Scorecard year-1 earnings for one program in context of the
 * peer band for the same CIP family:
 *   - the **peer band** (`peerP25`–`peerP75`) is computed in the Gold zone as
 *     `PERCENTILE_CONT` over all schools' program medians within the same
 *     2-digit CIP family (`src/gold/college_scorecard_career_outcomes.py`
 *     §cip_bands). It's a cross-institution band, not a within-cohort range.
 *   - the **pill** is `programMedian` (this school's `earnings_1yr_median`).
 *     If null, falls back to `careerMedian` (`median_annual_wage`, the
 *     career-level OEWS mid-career wage) and tags the pill as a career-wage
 *     reference rather than a year-1 number.
 *
 * Used on /my-build (FinancesCard, single program) and /builds compare view
 * (MoneySection, multiple programs sharing one scale). Compare passes a
 * shared `scaleMin`/`scaleMax` so all bars align; single-build leaves them
 * undefined and the component picks a tight scale around its own values.
 */
import { useMemo } from "react";
import { useT } from "@/i18n/useT";

interface Year1SalaryBarProps {
  /** Optional caps over the bar (e.g. school name, "this program"). Single-
   * build callers usually omit it because the surrounding card already names
   * the program. */
  schoolName?: string;
  /** This program's year-1 median earnings (`earnings_1yr_median`). */
  programMedian: number | null;
  /** Career-level OEWS mid-career wage (`median_annual_wage`). Used only as
   * the pill fallback when programMedian is null. */
  careerMedian: number | null;
  /** Peer-band lower bound (`earnings_1yr_p25` — peer 25th of program medians
   * within the CIP family). */
  peerP25: number | null;
  /** Peer-band upper bound (`earnings_1yr_p75`). */
  peerP75: number | null;
  /** Optional shared scale. When omitted, the component fits to its own
   * values + small padding. The compare view passes a shared scale so the
   * bars across all builds align visually. */
  scaleMin?: number;
  scaleMax?: number;
  /** Compare view dims non-highlighted bars; default true. */
  highlighted?: boolean;
  /** Test id on the outer wrapper. */
  testId?: string;
}

function formatSalaryShort(val: number | null): string {
  if (val == null) return "n/a";
  return `$${Math.round(val / 1000)}K`;
}

export function Year1SalaryBar({
  schoolName,
  programMedian,
  careerMedian,
  peerP25,
  peerP75,
  scaleMin: scaleMinProp,
  scaleMax: scaleMaxProp,
  highlighted = true,
  testId,
}: Year1SalaryBarProps) {
  const t = useT();
  const hasRange = peerP25 != null && peerP75 != null;
  const markerValue = programMedian ?? careerMedian;
  const usingCareerFallback = programMedian == null && careerMedian != null;
  const peerBandPosition: "above" | "below" | "inside" | null =
    hasRange && programMedian != null
      ? programMedian > peerP75!
        ? "above"
        : programMedian < peerP25!
          ? "below"
          : "inside"
      : null;

  const { scaleMin, scaleMax } = useMemo(() => {
    if (scaleMinProp != null && scaleMaxProp != null) {
      return { scaleMin: scaleMinProp, scaleMax: scaleMaxProp };
    }
    const vals: number[] = [];
    if (peerP25 != null) vals.push(peerP25);
    if (peerP75 != null) vals.push(peerP75);
    if (markerValue != null) vals.push(markerValue);
    if (vals.length === 0) return { scaleMin: 0, scaleMax: 1 };
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const padding = (max - min) * 0.1 || max * 0.05 || 1000;
    return { scaleMin: min - padding, scaleMax: max + padding };
  }, [scaleMinProp, scaleMaxProp, peerP25, peerP75, markerValue]);

  const range = scaleMax - scaleMin || 1;
  const p25Pct = hasRange ? ((peerP25! - scaleMin) / range) * 100 : 0;
  const p75Pct = hasRange ? ((peerP75! - scaleMin) / range) * 100 : 100;
  const medianPct = markerValue != null ? ((markerValue - scaleMin) / range) * 100 : 50;

  return (
    <div
      data-testid={testId}
      className="transition-opacity duration-200"
      style={{ opacity: highlighted ? 1 : 0.2 }}
    >
      {schoolName && (
        <p className="font-body text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1.5">
          {schoolName}
        </p>
      )}

      {hasRange ? (
        <>
          <div
            className="relative h-9 w-full"
            aria-label={
              `Peer Year-1 band: ${formatSalaryShort(peerP25)} to ${formatSalaryShort(peerP75)}, ` +
              (programMedian != null
                ? `this program median ${formatSalaryShort(programMedian)}`
                : `career wage reference ${formatSalaryShort(markerValue)}`)
            }
          >
            <div className="absolute left-0 right-0 top-[15px] h-1 rounded-full bg-white/[0.08]" />
            {/* Peer band */}
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
                  ? "rgba(92, 80, 42, 1)"
                  : "rgba(45, 70, 90, 1)",
                borderColor: programMedian != null
                  ? "rgba(242, 212, 119, 0.9)"
                  : "rgba(123, 184, 224, 0.8)",
              }}
            >
              <span className="font-data text-[15px] font-bold text-stat-ern whitespace-nowrap">
                {formatSalaryShort(markerValue)}
              </span>
            </div>
          </div>
          <div
            className="flex justify-between mt-1"
            style={{ paddingLeft: `${p25Pct}%`, paddingRight: `${100 - p75Pct}%` }}
          >
            <span className="flex flex-col font-data text-data-sm text-text-secondary">
              <span className="text-[10px] uppercase tracking-widest text-text-muted">{t("salaryBar.peer25")}</span>
              <span>{formatSalaryShort(peerP25)}</span>
            </span>
            <span className="flex flex-col items-end font-data text-data-sm text-text-secondary">
              <span className="text-[10px] uppercase tracking-widest text-text-muted">{t("salaryBar.peer75")}</span>
              <span>{formatSalaryShort(peerP75)}</span>
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
                {t(
                  peerBandPosition === "above"
                    ? "salaryBar.standoutLabel"
                    : "salaryBar.cautionLabel",
                )}
              </p>
              <p className="mt-1 font-display text-[16px] font-semibold leading-snug text-text-primary">
                {t(
                  peerBandPosition === "above"
                    ? "salaryBar.standoutBody"
                    : "salaryBar.cautionBody",
                )}
              </p>
            </div>
          )}
          {usingCareerFallback && (
            <p className="mt-2 font-body text-small text-text-muted">
              {t("salaryBar.careerWageNote")}
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
