import type { CareerOutcome } from "@/types/build";
import { ReceiptPanel } from "@/components/ReceiptPanel";

interface CareerDetailProps {
  career: CareerOutcome;
  loanPct: number;
}

function roiColor(dte: number | null): string {
  if (dte === null) return "var(--color-text-muted)";
  if (dte <= 0.5) return "var(--color-accent-thrive)";
  if (dte <= 1.0) return "var(--color-accent-caution)";
  return "var(--color-accent-alert)";
}

function roiLabel(dte: number | null): string {
  if (dte === null) return "Insufficient data";
  if (dte <= 0.5) return "Strong ROI";
  if (dte <= 1.0) return "Moderate ROI";
  return "Challenging ROI";
}

export function CareerDetail({ career, loanPct }: CareerDetailProps) {
  const activities = career.top_5_activities
    .map((a) => (typeof a.activity === "string" ? a.activity : String(a.activity ?? "")))
    .filter(Boolean);

  const resScore = career.stats.res;

  return (
    <div className="bg-bp-mid border border-border-subtle rounded-xl p-6 space-y-5">
      {/* Salary range */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <h3 className="font-body font-bold text-body text-text-primary">
            Salary Range
          </h3>
          <ReceiptPanel id="salary" label="Salary Range">
            <p>Source: College Scorecard (program-level) + BLS OOH</p>
            <p className="mt-1">Earnings at 1 year post-graduation, adjusted by effort level.</p>
          </ReceiptPanel>
        </div>
        <div className="flex items-baseline gap-4 font-data">
          <span className="text-data-sm text-text-muted">
            25th: ${(career.earnings_1yr_p25 ?? 0).toLocaleString()}
          </span>
          <span className="text-data-lg text-stat-ern font-bold">
            ${(career.median_annual_wage ?? 0).toLocaleString()}
          </span>
          <span className="text-data-sm text-text-muted">
            75th: ${(career.earnings_1yr_p75 ?? 0).toLocaleString()}
          </span>
        </div>
      </div>

      {/* ROI */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <h3 className="font-body font-bold text-body text-text-primary">
            Return on Investment
          </h3>
          <ReceiptPanel id="roi" label="ROI">
            <p>Debt-to-earnings ratio at {Math.round(loanPct * 100)}% loan coverage.</p>
            <p className="mt-1">DTE: {career.debt_to_earnings_annual?.toFixed(2) ?? "N/A"}</p>
          </ReceiptPanel>
        </div>
        <span
          className="font-data text-data font-bold"
          style={{ color: roiColor(career.debt_to_earnings_annual) }}
        >
          {roiLabel(career.debt_to_earnings_annual)}
        </span>
      </div>

      {/* Top Activities */}
      {activities.length > 0 && (
        <div>
          <h3 className="font-body font-bold text-body text-text-primary mb-2">
            Top Activities
          </h3>
          <ul className="space-y-1">
            {activities.map((act, i) => (
              <li key={i} className="font-body text-small text-text-secondary flex items-start gap-2">
                <span className="text-text-muted mt-0.5">•</span>
                {act}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* AI Exposure */}
      {resScore !== null && (
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-body font-bold text-body text-text-primary">
              AI Exposure
            </h3>
            <ReceiptPanel id="ai-exposure" label="AI Exposure">
              <p>Source: Karpathy AI Exposure Scores + O*NET task analysis</p>
              <p className="mt-1">RES stat: {resScore}/10</p>
            </ReceiptPanel>
          </div>
          <p className="font-body text-small text-text-secondary">
            This career has{" "}
            <span className="text-accent-insight font-semibold">
              {resScore >= 7 ? "low" : resScore >= 4 ? "moderate" : "high"} AI exposure
            </span>
          </p>
        </div>
      )}

      {/* Substitution notice */}
      {career.substitution_applied && (
        <div
          className="bg-bp-surface rounded-md p-3 text-small text-text-secondary font-body"
          style={{ borderLeft: "3px solid var(--color-accent-info)" }}
        >
          <strong className="text-accent-info">Note:</strong> Broad CIP data was used for
          this career because program-level data wasn't available. Results are still
          meaningful but may be less precise.
        </div>
      )}
    </div>
  );
}
