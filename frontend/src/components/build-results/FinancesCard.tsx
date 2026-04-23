interface FinancesCardProps {
  startingSalary: number | null;
  medianSalary: number | null;
  tuitionInState: number | null;
  tuitionOutOfState: number | null;
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
}

function Row({ label, value, muted, highlight }: RowProps) {
  return (
    <div
      className="flex items-center justify-between py-3"
      style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
    >
      <span
        className={`font-body text-small ${highlight ? "text-text-primary font-semibold" : "text-text-secondary"}`}
      >
        {label}
        {highlight && (
          <span className="text-accent-thrive ml-1 text-micro">
            ← yours
          </span>
        )}
      </span>
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
  loanPct,
  isInState,
  institutionControl,
}: FinancesCardProps) {
  const isPrivate = institutionControl?.startsWith("Private") ?? false;

  return (
    <div
      className="rounded-[20px] border border-border-subtle bg-bp-mid shadow-md p-6"
      role="region"
      aria-label="Finances"
    >
      <div
        className="font-data font-bold uppercase text-accent-info mb-4"
        style={{ fontSize: 11, letterSpacing: 2 }}
      >
        Finances
      </div>

      <Row label="Starting salary" value={`${fmt(startingSalary)} / yr`} />
      <Row label="Median salary" value={`${fmt(medianSalary)} / yr`} />
      {isPrivate ? (
        <Row label="Tuition (4 yr)" value={fmt(tuitionInState, 4)} />
      ) : (
        <>
          <Row
            label="In-state tuition (4 yr)"
            value={fmt(tuitionInState, 4)}
            highlight={isInState === true}
          />
          <Row
            label="Out-of-state tuition (4 yr)"
            value={fmt(tuitionOutOfState, 4)}
            highlight={isInState === false}
          />
        </>
      )}
      <Row label="Financing" value={pct(loanPct)} muted={loanPct === 1} />
    </div>
  );
}
