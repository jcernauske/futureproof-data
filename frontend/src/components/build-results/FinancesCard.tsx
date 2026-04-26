import { useT } from "@/i18n/useT";

interface FinancesCardProps {
  startingSalary: number | null;
  medianSalary: number | null;
  tuitionInState: number | null;
  tuitionOutOfState: number | null;
  netPriceAnnual: number | null;
  loanPct: number;
  isInState: boolean | null;
  institutionControl: string | null;
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
}

function Row({ label, value, muted, highlight, highlightLabel, subtitle }: RowProps) {
  return (
    <div
      className="flex items-center justify-between py-3"
      style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
    >
      <div>
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
        {subtitle && (
          <div className="font-body text-text-muted" style={{ fontSize: 11, marginTop: 1 }}>
            {subtitle}
          </div>
        )}
      </div>
      <span
        className={`font-data text-small font-bold ${muted ? "text-text-muted" : "text-text-primary"}`}
      >
        {value}
      </span>
    </div>
  );
}

export function FinancesCard({
  startingSalary,
  medianSalary,
  tuitionInState,
  tuitionOutOfState,
  netPriceAnnual,
  loanPct,
  isInState,
  institutionControl,
}: FinancesCardProps) {
  const t = useT();
  const isPrivate = institutionControl?.startsWith("Private") ?? false;
  const yoursLabel = t("build.yours");

  return (
    <div
      className="rounded-[20px] border border-border-subtle bg-bp-mid shadow-md p-6"
      role="region"
      aria-label={t("build.finances")}
    >
      <div
        className="font-data font-bold uppercase text-accent-info mb-4"
        style={{ fontSize: 11, letterSpacing: 2 }}
      >
        {t("build.finances")}
      </div>

      <Row label={t("build.startingSalary")} value={`${fmt(startingSalary)} / yr`} />
      <Row label={t("build.medianSalary")} value={`${fmt(medianSalary)} / yr`} />
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
      {netPriceAnnual != null && (
        <Row label={t("build.avgNetPrice")} value={fmt(netPriceAnnual, 4)} subtitle={t("build.afterGrants")} />
      )}
      <Row label={t("build.financing")} value={pct(loanPct)} muted={loanPct === 1} />
    </div>
  );
}
