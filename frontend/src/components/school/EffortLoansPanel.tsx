import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { DiscreteSlider } from "@/components/ui/DiscreteSlider";
import type { SliderStop } from "@/components/ui/DiscreteSlider";
import type { EffortSelection, LoanSelection } from "@/types/buildInput";
import { useT } from "@/i18n/useT";

interface EffortLoansPanelProps {
  effort: EffortSelection;
  loans: LoanSelection;
  onEffortChange: (effort: EffortSelection) => void;
  onLoanChange: (loans: LoanSelection) => void;
  profileName?: string;
  onSubmit?: () => void;
  submitting?: boolean;
  /**
   * Institution-level net price per year (after grants/scholarships) sourced from
   * the College Scorecard institution-level pipeline. When provided, the loan
   * slider scales modeled debt (net_price × 4 × loan_pct) — this drives the
   * Student Loans Boss score, but NOT the ROI stat. ROI reflects cost of
   * attendance vs. earnings and is independent of financing. See plan
   * ~/.claude/plans/why-are-we-still-jaunty-curry.md.
   */
  netPriceAnnual?: number | null;
  /** Pulse each slider container with a thrive glow — used as a soft cue after career selection. */
  highlight?: boolean;
}

// Effort + Loan stop / desc keys live in `EFFORT_MAP` and `LOAN_STOPS`.
// `label` comes from `t(...)` at render time so the screen-reader
// `aria-valuetext` and visible chips switch with the active locale.
const EFFORT_MAP: Record<
  string,
  { percentile: 10 | 25 | 50 | 75 | 90; ernShift: -2 | -1 | 0 | 1 | 2; stopKey: string; descKey: string }
> = {
  working_hard: { percentile: 10, ernShift: -2, stopKey: "effortLoans.effort.stop.workingHard", descKey: "effortLoans.effort.desc.workingHard" },
  working: { percentile: 25, ernShift: -1, stopKey: "effortLoans.effort.stop.working", descKey: "effortLoans.effort.desc.working" },
  balanced: { percentile: 50, ernShift: 0, stopKey: "effortLoans.effort.stop.balanced", descKey: "effortLoans.effort.desc.balanced" },
  focused: { percentile: 75, ernShift: 1, stopKey: "effortLoans.effort.stop.focused", descKey: "effortLoans.effort.desc.focused" },
  all_in: { percentile: 90, ernShift: 2, stopKey: "effortLoans.effort.stop.allIn", descKey: "effortLoans.effort.desc.allIn" },
};

const LOAN_STOP_KEYS: { value: number; labelKey: string }[] = [
  { value: 0, labelKey: "effortLoans.loans.stop.none" },
  { value: 25, labelKey: "effortLoans.loans.stop.some" },
  { value: 50, labelKey: "effortLoans.loans.stop.half" },
  { value: 75, labelKey: "effortLoans.loans.stop.mostly" },
  { value: 100, labelKey: "effortLoans.loans.stop.all" },
];

// Copy describes the Student Loans Boss impact only — ROI is cost-based
// and does not change with loan coverage. See plan
// ~/.claude/plans/why-are-we-still-jaunty-curry.md
function loanImpactText(
  pct: number,
  netPriceAnnual: number | null | undefined,
  t: (key: string, vars?: Record<string, string | number>) => string,
): string {
  if (pct === 0) return t("effortLoans.loans.impact.none");
  const hasCost = typeof netPriceAnnual === "number" && netPriceAnnual > 0;
  const total = hasCost
    ? `$${(netPriceAnnual! * 4).toLocaleString()}`
    : t("effortLoans.loans.impact.fourYearCost");
  if (pct === 100) {
    return t("effortLoans.loans.impact.full", { total });
  }
  return t("effortLoans.loans.impact.partial", { pct, total });
}


export function EffortLoansPanel({
  effort,
  loans,
  onEffortChange,
  onLoanChange,
  netPriceAnnual,
  highlight = false,
}: EffortLoansPanelProps) {
  const t = useT();
  const sliderCardClass = [
    "bg-bp-mid border rounded-xl p-6 transition-all duration-500",
    highlight
      ? "border-accent-thrive/60 ring-2 ring-accent-thrive/60 shadow-glow-thrive"
      : "border-border-subtle ring-0 ring-transparent",
  ].join(" ");
  function handleEffortChange(level: string) {
    const mapped = EFFORT_MAP[level] ?? EFFORT_MAP.balanced!;
    onEffortChange({
      level: level as EffortSelection["level"],
      percentile: mapped!.percentile,
      ernShift: mapped!.ernShift,
    });
  }

  function handleLoanChange(pct: number) {
    onLoanChange({ percentage: pct as LoanSelection["percentage"] });
  }

  const effortInfo = EFFORT_MAP[effort.level] ?? EFFORT_MAP.balanced!;

  // Build localized slider-stop arrays at render time so they react to
  // locale changes from the profile store.
  const effortStops: SliderStop<string>[] = (
    ["working_hard", "working", "balanced", "focused", "all_in"] as const
  ).map((key) => ({ value: key, label: t(EFFORT_MAP[key]!.stopKey) }));
  const loanStops: SliderStop<number>[] = LOAN_STOP_KEYS.map(({ value, labelKey }) => ({
    value,
    label: t(labelKey),
  }));

  return (
    <motion.div
      className="space-y-5"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      {/* Row 1: effort (left) + loans (right) */}
      <div className="grid grid-cols-1 tablet:grid-cols-2 gap-5">
        {/* Effort slider */}
        <div className={sliderCardClass}>
          <div className="font-display text-[20px] font-semibold text-text-primary text-center mb-6">
            {t("effortLoans.effort.heading")}
          </div>
          <DiscreteSlider
            stops={effortStops}
            value={effort.level}
            onChange={handleEffortChange}
            labelLeft={t("effortLoans.effort.labelLeft")}
            labelRight={t("effortLoans.effort.labelRight")}
            fillGradient="linear-gradient(90deg, var(--color-accent-info), var(--color-accent-thrive))"
            ariaLabel={t("effortLoans.effort.aria")}
          />
          <div className="font-data text-[14px] font-bold text-accent-thrive text-center mt-5">
            {t(effortInfo!.descKey)}
          </div>
        </div>

        {/* Loan slider */}
        <div className={sliderCardClass}>
          <div className="font-display text-[20px] font-semibold text-text-primary text-center mb-6">
            {t("effortLoans.loans.heading")}
          </div>
          <DiscreteSlider
            stops={loanStops}
            value={loans.percentage}
            onChange={handleLoanChange}
            labelLeft={t("effortLoans.loans.labelLeft")}
            labelRight={t("effortLoans.loans.labelRight")}
            fillGradient="linear-gradient(90deg, var(--color-accent-thrive), var(--color-accent-alert))"
            ariaLabel={t("effortLoans.loans.aria")}
          />
          <div className="font-data text-[14px] font-bold text-accent-thrive text-center mt-5">
            {loanImpactText(loans.percentage, netPriceAnnual, t)}
          </div>
          {typeof netPriceAnnual === "number" && netPriceAnnual > 0 && (
            <div
              className="mt-3 text-center space-y-0.5"
              data-testid="loan-slider-cost-context"
            >
              <div className="font-data text-data-sm text-text-muted">
                {t("effortLoans.loans.cost.totalLine", {
                  annual: `$${netPriceAnnual.toLocaleString()}`,
                  total: `$${(netPriceAnnual * 4).toLocaleString()}`,
                })}
              </div>
              <div className="font-data text-data-sm text-text-secondary">
                {t("effortLoans.loans.cost.atPctLine", {
                  pct: loans.percentage,
                  amount: `$${Math.round(
                    netPriceAnnual * 4 * (loans.percentage / 100),
                  ).toLocaleString()}`,
                })}
              </div>
            </div>
          )}
        </div>
      </div>

    </motion.div>
  );
}
