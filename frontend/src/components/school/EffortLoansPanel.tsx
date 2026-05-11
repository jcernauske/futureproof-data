import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { DiscreteSlider } from "@/components/ui/DiscreteSlider";
import type { SliderStop } from "@/components/ui/DiscreteSlider";
import type { EffortSelection, LoanSelection } from "@/types/buildInput";

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

const EFFORT_STOPS: SliderStop<string>[] = [
  { value: "working_hard", label: "Working two jobs" },
  { value: "working", label: "Working + school" },
  { value: "balanced", label: "Balanced" },
  { value: "focused", label: "Strong focus" },
  { value: "all_in", label: "All-in" },
];

const EFFORT_MAP: Record<
  string,
  { percentile: 10 | 25 | 50 | 75 | 90; ernShift: -2 | -1 | 0 | 1 | 2; desc: string }
> = {
  working_hard: { percentile: 10, ernShift: -2, desc: "Very limited focus" },
  working: { percentile: 25, ernShift: -1, desc: "Limited focus" },
  balanced: { percentile: 50, ernShift: 0, desc: "Balanced focus" },
  focused: { percentile: 75, ernShift: 1, desc: "Strong academic focus" },
  all_in: { percentile: 90, ernShift: 2, desc: "Maximum focus" },
};

const LOAN_STOPS: SliderStop<number>[] = [
  { value: 0, label: "No loans" },
  { value: 25, label: "Some" },
  { value: 50, label: "Half" },
  { value: 75, label: "Mostly" },
  { value: 100, label: "All loans" },
];

// Copy describes the Student Loans Boss impact only — ROI is cost-based
// and does not change with loan coverage. See plan
// ~/.claude/plans/why-are-we-still-jaunty-curry.md
function loanImpactText(pct: number, netPriceAnnual?: number | null): string {
  if (pct === 0) return "no debt — Fight Student Loans auto-win";
  const hasCost = typeof netPriceAnnual === "number" && netPriceAnnual > 0;
  const total = hasCost
    ? `$${(netPriceAnnual! * 4).toLocaleString()}`
    : "4-year cost";
  if (pct === 100) {
    return `financing 100% of ${total} — Fight Student Loans at full difficulty`;
  }
  return `financing ${pct}% of ${total}`;
}


export function EffortLoansPanel({
  effort,
  loans,
  onEffortChange,
  onLoanChange,
  netPriceAnnual,
  highlight = false,
}: EffortLoansPanelProps) {
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
            How much time will you have to focus on school?
          </div>
          <DiscreteSlider
            stops={EFFORT_STOPS}
            value={effort.level}
            onChange={handleEffortChange}
            labelLeft="Working to support myself"
            labelRight="Full focus on school"
            fillGradient="linear-gradient(90deg, var(--color-accent-info), var(--color-accent-thrive))"
            ariaLabel="Effort level"
          />
          <div className="font-data text-[14px] font-bold text-accent-thrive text-center mt-5">
            {effortInfo!.desc}
          </div>
        </div>

        {/* Loan slider */}
        <div className={sliderCardClass}>
          <div className="font-display text-[20px] font-semibold text-text-primary text-center mb-6">
            How much of your costs will you cover with loans?
          </div>
          <DiscreteSlider
            stops={LOAN_STOPS}
            value={loans.percentage}
            onChange={handleLoanChange}
            labelLeft="No loans"
            labelRight="All loans"
            fillGradient="linear-gradient(90deg, var(--color-accent-thrive), var(--color-accent-alert))"
            ariaLabel="Loan percentage"
          />
          <div className="font-data text-[14px] font-bold text-accent-thrive text-center mt-5">
            {loanImpactText(loans.percentage, netPriceAnnual)}
          </div>
          {typeof netPriceAnnual === "number" && netPriceAnnual > 0 && (
            <div
              className="mt-3 text-center space-y-0.5"
              data-testid="loan-slider-cost-context"
            >
              <div className="font-data text-data-sm text-text-muted">
                ${netPriceAnnual.toLocaleString()}/yr × 4 years = $
                {(netPriceAnnual * 4).toLocaleString()} total
              </div>
              <div className="font-data text-data-sm text-text-secondary">
                At {loans.percentage}%: $
                {Math.round(
                  netPriceAnnual * 4 * (loans.percentage / 100),
                ).toLocaleString()}{" "}
                in loans
              </div>
            </div>
          )}
        </div>
      </div>

    </motion.div>
  );
}
