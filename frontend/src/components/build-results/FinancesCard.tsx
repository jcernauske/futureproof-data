import { useT } from "@/i18n/useT";
import type { CareerOutcome } from "@/types/build";
import { ReceiptPanel } from "@/components/ReceiptPanel";
import { fmtMoney, roiColorClass } from "@/lib/format";

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

function roiLabelKey(dte: number | null): string {
  if (dte === null) return "build.roi.insufficientData";
  if (dte <= 0.5) return "build.roi.strong";
  if (dte <= 1.0) return "build.roi.moderate";
  return "build.roi.challenging";
}

function fill(template: string, values: Record<string, string>): string {
  let out = template;
  for (const [key, value] of Object.entries(values)) {
    out = out.replace(`{${key}}`, value);
  }
  return out;
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

interface RoiReceiptProps {
  career: CareerOutcome;
  loanPct: number;
  t: (key: string) => string;
}

/**
 * Migrated from the deprecated CareerDetail.tsx (RoiReceipt). Cost-basis
 * receipt body — ROI is a property of the program's cost of attendance vs
 * earnings and is NOT sensitive to loan_pct. Loan coverage still affects
 * the Student Loans Boss (modeled_total_debt), so we surface both angles
 * here while keeping the ROI math visibly separate from financing math.
 */
function RoiReceipt({ career, loanPct, t }: RoiReceiptProps) {
  const basis = career.roi_cost_basis ?? null;
  const fourYearCost =
    typeof career.net_price_annual === "number" && career.net_price_annual > 0
      ? career.net_price_annual * 4
      : null;
  const medianRef = career.debt_median_reference ?? career.debt_median ?? null;
  const modeled = career.modeled_total_debt ?? null;

  return (
    <div data-testid="roi-receipt" className="space-y-1">
      {career.institution_control && (
        <p>{fill(t("build.roi.schoolControl"), { value: career.institution_control })}</p>
      )}

      {basis === "cost_of_attendance" && fourYearCost !== null ? (
        <>
          <p>
            {fill(t("build.roi.netPriceYear"), { value: fmtMoney(career.net_price_annual) })}
          </p>
          {career.cost_of_attendance_annual !== null && (
            <p>
              {fill(t("build.roi.costOfAttendanceYear"), {
                value: fmtMoney(career.cost_of_attendance_annual),
              })}
            </p>
          )}
          <p>{fill(t("build.roi.costOfAttendance4yr"), { value: fmtMoney(fourYearCost) })}</p>
        </>
      ) : basis === "debt_median" && medianRef !== null ? (
        <p>
          {fill(t("build.roi.costBasisMedianFallback"), { value: fmtMoney(medianRef) })}
        </p>
      ) : (
        <p>{t("build.roi.costBasisUnavailable")}</p>
      )}

      {career.earnings_1yr_median !== null && (
        <p>
          {fill(t("build.roi.earnings1yr"), { value: fmtMoney(career.earnings_1yr_median) })}
        </p>
      )}
      {career.debt_to_earnings_annual !== null && (
        <p>
          {fill(t("build.roi.dte"), {
            dte: career.debt_to_earnings_annual.toFixed(2),
            roi: career.stats.roi !== null ? String(career.stats.roi) : "—",
          })}
        </p>
      )}

      {modeled !== null && (
        <p className="pt-1">
          {fill(t("build.roi.loanCoverage"), {
            pct: String(Math.round(loanPct * 100)),
            value: fmtMoney(modeled),
          })}
        </p>
      )}
      {career.financed_dte !== null && career.financed_dte !== undefined && (
        <p>{fill(t("build.roi.financedDte"), { dte: career.financed_dte.toFixed(2) })}</p>
      )}
      {basis === "cost_of_attendance" && medianRef !== null && (
        <p>{fill(t("build.roi.medianGradDebt"), { value: fmtMoney(medianRef) })}</p>
      )}
      {career.tuition_in_state !== null && career.tuition_in_state !== undefined && (
        <p>{fill(t("build.roi.inStateTuition"), { value: fmtMoney(career.tuition_in_state) })}</p>
      )}
      {career.tuition_out_of_state !== null && career.tuition_out_of_state !== undefined && (
        <p>
          {fill(t("build.roi.outStateTuition"), { value: fmtMoney(career.tuition_out_of_state) })}
        </p>
      )}
      {career.room_board_on_campus !== null && career.room_board_on_campus !== undefined && (
        <p>{fill(t("build.roi.roomBoard"), { value: fmtMoney(career.room_board_on_campus) })}</p>
      )}

      <p className="mt-1">
        {basis === "cost_of_attendance"
          ? t("build.roi.sourcesInstitution")
          : t("build.roi.sourcesProgram")}
      </p>
    </div>
  );
}

/**
 * Migrated from the deprecated CareerDetail.tsx. Subtle caution/thrive
 * indicator comparing modeled debt to program median. Renders nothing
 * when either input is missing or non-positive — we don't want to imply
 * a comparison we can't actually make.
 */
function DebtVsMedianIndicator({
  modeled,
  median,
  t,
}: {
  modeled: number | null | undefined;
  median: number | null | undefined;
  t: (key: string) => string;
}) {
  if (
    typeof modeled !== "number" ||
    typeof median !== "number" ||
    modeled <= 0 ||
    median <= 0
  ) {
    return null;
  }

  if (modeled > median * 1.2) {
    return (
      <p
        data-testid="debt-indicator-caution"
        role="note"
        className="font-data text-data-sm text-accent-caution mt-1"
      >
        {t("build.debtIndicator.caution")}
      </p>
    );
  }

  if (modeled < median * 0.8) {
    return (
      <p
        data-testid="debt-indicator-thrive"
        role="note"
        className="font-data text-data-sm text-accent-thrive mt-1"
      >
        {t("build.debtIndicator.thrive")}
      </p>
    );
  }

  return null;
}

export function FinancesCard({ career, loanPct, isInState }: FinancesCardProps) {
  const t = useT();
  const isPrivate = career.institution_control?.startsWith("Private") ?? false;
  const yoursLabel = t("build.yours");

  const startingSalary = career.earnings_1yr_median;
  const medianSalary = career.median_annual_wage;
  const tuitionInState = career.tuition_in_state;
  const tuitionOutOfState = career.tuition_out_of_state;
  const netPriceAnnual = career.net_price_annual;

  const p25 = career.earnings_1yr_p25;
  const p75 = career.earnings_1yr_p75;
  const salarySubtitle =
    typeof p25 === "number" && typeof p75 === "number"
      ? `25th: ${fmtMoney(p25)} · 75th: ${fmtMoney(p75)}`
      : undefined;

  const modeledDebt = career.modeled_total_debt;
  const medianRef = career.debt_median_reference ?? career.debt_median ?? null;

  return (
    <div
      className="rounded-[20px] border border-border-subtle bg-bp-mid shadow-md p-6"
      role="region"
      aria-label={t("build.finances")}
    >
      <div className="font-data font-bold uppercase text-micro text-accent-info tracking-[2px] mb-4">
        {t("build.finances")}
      </div>

      <Row label={t("build.startingSalary")} value={`${fmt(startingSalary)} / yr`} />
      <Row
        label={t("build.medianSalary")}
        value={`${fmt(medianSalary)} / yr`}
        subtitle={salarySubtitle}
      />
      {isPrivate ? (
        <Row label={t("build.tuition4yr")} value={fmt(tuitionInState, 4)} />
      ) : (
        <>
          <Row
            label={t("build.inStateTuition")}
            value={fmt(tuitionInState, 4)}
            highlight={isInState === true}
            highlightLabel={yoursLabel}
          />
          <Row
            label={t("build.outStateTuition")}
            value={fmt(tuitionOutOfState, 4)}
            highlight={isInState === false}
            highlightLabel={yoursLabel}
          />
        </>
      )}
      {netPriceAnnual !== null && netPriceAnnual > 0 && (
        <Row
          label={t("build.avgNetPrice")}
          value={fmt(netPriceAnnual, 4)}
          subtitle={t("build.afterGrants")}
        />
      )}
      <Row label={t("build.financing")} value={pct(loanPct)} muted={loanPct === 1} />

      {modeledDebt !== null && modeledDebt !== undefined && (
        <Row label={t("build.modeledDebt")} value={fmtMoney(modeledDebt)} />
      )}
      <DebtVsMedianIndicator modeled={modeledDebt} median={medianRef} t={t} />

      <div className="flex items-center gap-2 mt-3">
        <span
          className={`font-data text-small font-bold ${roiColorClass(career.debt_to_earnings_annual)}`}
        >
          {t("build.roi.label")}: {t(roiLabelKey(career.debt_to_earnings_annual))}
        </span>
        <ReceiptPanel id="roi" label={t("build.roi.label")}>
          <RoiReceipt career={career} loanPct={loanPct} t={t} />
        </ReceiptPanel>
      </div>
    </div>
  );
}
