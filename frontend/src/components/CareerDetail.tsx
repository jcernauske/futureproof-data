import type { CareerOutcome } from "@/types/build";
import { ReceiptPanel } from "@/components/ReceiptPanel";

interface CareerDetailProps {
  career: CareerOutcome;
  loanPct: number;
}

function roiColorClass(dte: number | null): string {
  if (dte === null) return "text-text-muted";
  if (dte <= 0.5) return "text-accent-thrive";
  if (dte <= 1.0) return "text-accent-caution";
  return "text-accent-alert";
}

function roiLabel(dte: number | null): string {
  if (dte === null) return "Insufficient data";
  if (dte <= 0.5) return "Strong ROI";
  if (dte <= 1.0) return "Moderate ROI";
  return "Challenging ROI";
}

function fmtMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `$${Math.round(value).toLocaleString()}`;
}

/**
 * ROI receipt body — cost-based, one-path rendering.
 *
 * ROI is a property of the program's **cost of attendance vs earnings**
 * and is NOT sensitive to loan_pct. Loan coverage still affects the
 * Student Loans Boss (and its modeled_total_debt), so we surface both
 * angles in this receipt — but we keep the ROI math visibly separate
 * from the financing math.
 *
 * Plan: ~/.claude/plans/why-are-we-still-jaunty-curry.md
 */
function RoiReceipt({
  career,
  loanPct,
}: {
  career: CareerOutcome;
  loanPct: number;
}) {
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
        <p>
          School control:{" "}
          <span className="text-text-secondary">{career.institution_control}</span>
        </p>
      )}

      {/* Cost basis block — the numerator behind stat_roi. */}
      {basis === "cost_of_attendance" && fourYearCost !== null ? (
        <>
          <p>
            Net price per year: {fmtMoney(career.net_price_annual)} (after
            grants/scholarships)
          </p>
          {career.cost_of_attendance_annual !== null && (
            <p>
              Cost of attendance per year:{" "}
              {fmtMoney(career.cost_of_attendance_annual)} (sticker price)
            </p>
          )}
          <p>
            4-year cost of attendance:{" "}
            <span className="text-text-secondary">{fmtMoney(fourYearCost)}</span>{" "}
            (net price × 4)
          </p>
        </>
      ) : basis === "debt_median" && medianRef !== null ? (
        <p>
          Cost basis: median graduate debt {fmtMoney(medianRef)} —
          institution-level cost data is not available for this program, so
          the median stands in as an approximation.
        </p>
      ) : (
        <p>
          Cost basis: unavailable (no institution-level net price or program-level
          median debt for this row).
        </p>
      )}

      {/* Earnings + ROI DTE — the ratio that drives stat_roi. */}
      {career.earnings_1yr_median !== null && (
        <p>1-year post-grad earnings: {fmtMoney(career.earnings_1yr_median)}</p>
      )}
      {career.debt_to_earnings_annual !== null && (
        <p>
          ROI DTE (cost ÷ earnings):{" "}
          <span className="text-text-secondary">
            {career.debt_to_earnings_annual.toFixed(2)}
          </span>{" "}
          → ROI {career.stats.roi ?? "—"}/10
        </p>
      )}

      {/* Financing block — drives the Student Loans Boss, NOT ROI. */}
      {modeled !== null && (
        <p className="pt-1">
          Loan coverage: {Math.round(loanPct * 100)}% → modeled debt{" "}
          <span className="text-text-secondary">{fmtMoney(modeled)}</span>
        </p>
      )}
      {career.financed_dte !== null && career.financed_dte !== undefined && (
        <p>
          Financed DTE (loans boss input):{" "}
          {career.financed_dte.toFixed(2)}
        </p>
      )}
      {basis === "cost_of_attendance" && medianRef !== null && (
        <p>Median debt of graduates from this program: {fmtMoney(medianRef)}</p>
      )}
      {career.tuition_in_state !== null &&
        career.tuition_in_state !== undefined && (
          <p>In-state tuition: {fmtMoney(career.tuition_in_state)}</p>
        )}
      {career.tuition_out_of_state !== null &&
        career.tuition_out_of_state !== undefined && (
          <p>Out-of-state tuition: {fmtMoney(career.tuition_out_of_state)}</p>
        )}
      {career.room_board_on_campus !== null &&
        career.room_board_on_campus !== undefined && (
          <p>Room &amp; board (on campus): {fmtMoney(career.room_board_on_campus)}</p>
        )}

      <p className="mt-1">
        Sources: College Scorecard
        {basis === "cost_of_attendance"
          ? " (Field of Study + Institution Level)"
          : " (Field of Study)"}
      </p>
    </div>
  );
}

/**
 * Subtle caution/thrive indicator comparing modeled debt to program median.
 * Renders nothing when either input is missing or non-positive — we don't want
 * to imply a comparison we can't actually make.
 *
 * Color tokens (existing Brightpath palette only):
 *   - thrive: text-accent-thrive (green) — modeled debt is well below median
 *   - caution: text-accent-caution (yellow) — modeled debt is significantly above
 */
function DebtVsMedianIndicator({
  modeled,
  median,
}: {
  modeled: number | null | undefined;
  median: number | null | undefined;
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
        Your modeled debt is significantly above the program median.
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
        Your modeled debt is well below the program median.
      </p>
    );
  }

  return null;
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
            <RoiReceipt career={career} loanPct={loanPct} />
          </ReceiptPanel>
        </div>
        <span className={`font-data text-data font-bold ${roiColorClass(career.debt_to_earnings_annual)}`}>
          {roiLabel(career.debt_to_earnings_annual)}
        </span>
        <DebtVsMedianIndicator
          modeled={career.modeled_total_debt}
          median={career.debt_median_reference ?? career.debt_median}
        />
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
        <div className="bg-bp-surface rounded-md p-3 text-small text-text-secondary font-body border-l-[3px] border-accent-info">
          <strong className="text-accent-info">Note:</strong> Broad CIP data was used for
          this career because program-level data wasn't available. Results are still
          meaningful but may be less precise.
        </div>
      )}
    </div>
  );
}
