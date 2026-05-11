import { useT } from "@/i18n/useT";
import type { CareerOutcome } from "@/types/build";
import { fmtMoney } from "@/lib/format";

interface FinancesCardProps {
  career: CareerOutcome;
  loanPct: number;
  isInState: boolean | null;
}

function fmt(value: number | null, multiply?: number): string {
  if (value === null) return "—";
  const total = multiply ? value * multiply : value;
  return `$${Math.round(total).toLocaleString()}`;
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

interface RowProps {
  label: string;
  value: string;
  muted?: boolean;
  highlight?: boolean;
  highlightLabel?: string;
  subtitle?: string;
  trailing?: React.ReactNode;
}

function Row({ label, value, muted, highlight, highlightLabel, subtitle, trailing }: RowProps) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border-subtle">
      <div className="flex items-center gap-2">
        <span
          className={`font-body text-small ${highlight ? "text-text-primary font-semibold" : "text-text-secondary"}`}
        >
          {label}
          {highlight && highlightLabel && (
            <span className="text-accent-thrive ml-1 text-micro">
              {highlightLabel}
            </span>
          )}
        </span>
        {trailing}
      </div>
      <div className="text-right">
        <span
          className={`font-data text-small font-bold ${muted ? "text-text-muted" : "text-text-primary"}`}
        >
          {value}
        </span>
        {subtitle && (
          <div className="font-body text-micro text-text-muted mt-px">
            {subtitle}
          </div>
        )}
      </div>
    </div>
  );
}

export function FinancesCard({ career, loanPct, isInState }: FinancesCardProps) {
  const t = useT();

  const midCareerSalary = career.median_annual_wage;
  const publishedCost4yr = career.published_cost_4yr;

  const modeledDebt = career.modeled_total_debt;
  const medianRef = career.debt_median_reference ?? career.debt_median ?? null;
  const netPriceAnnual = career.net_price_annual;

  return (
    <div
      className="rounded-[20px] border border-border-subtle bg-bp-mid shadow-md p-6"
      role="region"
      aria-label={t("build.finances")}
    >
      <div className="font-data font-bold uppercase text-micro text-accent-info tracking-[2px] mb-4">
        {t("build.finances")}
      </div>

      <Row
        label={t("build.midCareerSalary")}
        value={`${fmt(midCareerSalary)} / yr`}
      />
      {/* OEWS national career-level wage distribution
          (spec ingest-bls-oews-wage-percentiles.md §Zone 4),
          experience-aware: entry-accessible careers (work_experience_code
          2, 3, or null) show p10–p25 as the "starting range"; long-term
          careers (code 1, 5+ yrs required) show p25–p75 as the "typical
          range". This avoids implying that a year-one student will earn
          the median of currently-working incumbents in roles that
          structurally exclude entrants.
          Distinct from the Scorecard "Year-one" row below:
          OEWS = what THIS career pays nationally;
          Year-one = what graduates of THIS program earn year one. */}
      {(() => {
        const isEntryAccessible =
          career.work_experience_code === 2 ||
          career.work_experience_code === 3 ||
          career.work_experience_code == null;
        const hasStarting =
          isEntryAccessible &&
          career.wage_p10 != null &&
          career.wage_p25 != null;
        const hasTypical =
          !isEntryAccessible &&
          career.wage_p25 != null &&
          career.wage_p75 != null;
        if (hasStarting) {
          return (
            <Row
              label={t("build.careerStartingRange")}
              value={`${fmtMoney(career.wage_p10)} – ${fmtMoney(career.wage_p25)}`}
              subtitle={career.occupation_title}
            />
          );
        }
        if (hasTypical) {
          return (
            <Row
              label={t("build.careerSalaryRange")}
              value={`${fmtMoney(career.wage_p25)} – ${fmtMoney(career.wage_p75)}`}
              subtitle={career.occupation_title}
            />
          );
        }
        return null;
      })()}
      {publishedCost4yr !== null && publishedCost4yr !== undefined && (
        <Row
          label={t("build.publishedCost4yr")}
          value={fmtMoney(publishedCost4yr)}
          highlight
          highlightLabel={isInState === false ? t("build.outOfStateApplied") : undefined}
        />
      )}
      {typeof netPriceAnnual === "number" && netPriceAnnual > 0 && (
        <Row
          label={t("build.avgNetPrice")}
          value={fmtMoney(netPriceAnnual * 4)}
          muted
          subtitle={t("build.afterAidContext")}
        />
      )}
      <Row label={t("build.financing")} value={pct(loanPct)} muted={loanPct === 1} />

      {modeledDebt !== null && modeledDebt !== undefined && (
        <Row label={t("build.modeledDebt")} value={fmtMoney(modeledDebt)} />
      )}
      {typeof medianRef === "number" && medianRef > 0 && (
        <Row
          label={t("build.programMedianDebt")}
          value={fmtMoney(medianRef)}
          muted
        />
      )}
    </div>
  );
}
