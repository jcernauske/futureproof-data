import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { DiscreteSlider } from "@/components/ui/DiscreteSlider";
import { StatBadge } from "@/components/ui/StatBadge";
import type { SliderStop } from "@/components/ui/DiscreteSlider";
import type { EffortSelection, LoanSelection } from "@/types/buildInput";

interface EffortLoansPanelProps {
  effort: EffortSelection;
  loans: LoanSelection;
  onEffortChange: (effort: EffortSelection) => void;
  onLoanChange: (loans: LoanSelection) => void;
  profileName: string;
  onSubmit: () => void;
  submitting: boolean;
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

const LOAN_IMPACT: Record<number, string> = {
  0: "best case — no debt",
  25: "scales debt-to-earnings to 25%",
  50: "scales debt-to-earnings to 50%",
  75: "scales debt-to-earnings to 75%",
  100: "full published debt load",
};

function ernShiftDisplay(shift: number): string {
  if (shift === 0) return "±0";
  return shift > 0 ? `+${shift}` : `${shift}`;
}

function loanLabel(pct: number): string {
  const stop = LOAN_STOPS.find((s) => s.value === pct);
  return stop?.label ?? "Half";
}

export function EffortLoansPanel({
  effort,
  loans,
  onEffortChange,
  onLoanChange,
  profileName,
  onSubmit,
  submitting,
}: EffortLoansPanelProps) {
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
      {/* Effort slider */}
      <div className="bg-bp-mid border border-border-subtle rounded-xl p-6">
        <div className="font-display text-[22px] font-semibold text-text-primary text-center mb-8">
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
        <div className="flex justify-center gap-10 mt-6">
          <div className="text-center">
            <div className="text-[12px] text-text-muted mb-1">ERN</div>
            <div
              className="font-data font-bold text-[28px]"
              style={{ color: "var(--color-stat-ern)" }}
            >
              {ernShiftDisplay(effort.ernShift)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[12px] text-text-muted mb-1">ROI</div>
            <div
              className="font-data font-bold text-[28px]"
              style={{ color: "var(--color-stat-roi)" }}
            >
              —
            </div>
          </div>
          <div className="text-center">
            <div className="text-[12px] text-text-muted mb-1">RES</div>
            <div
              className="font-data font-bold text-[28px]"
              style={{ color: "var(--color-stat-res)" }}
            >
              —
            </div>
          </div>
        </div>
      </div>

      {/* Loan slider */}
      <div className="bg-bp-mid border border-border-subtle rounded-xl p-6">
        <div className="font-display text-[22px] font-semibold text-text-primary text-center mb-8">
          How much will you cover with loans?
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
          {LOAN_IMPACT[loans.percentage]}
        </div>
      </div>

      {/* Live stat preview */}
      <motion.div
        className="bg-bp-mid border border-border-subtle rounded-xl p-6 flex justify-center gap-8"
        layout
        transition={springs.snappy}
      >
        <StatBadge
          stat="ERN"
          value={`▲ ${ernShiftDisplay(effort.ernShift)}`}
          label={`${effort.percentile}th percentile`}
          colorClass="text-stat-ern"
        />
        <div className="w-px bg-border-subtle" />
        <StatBadge
          stat="ROI"
          value={`● ${loans.percentage}%`}
          label={loanLabel(loans.percentage)}
          colorClass="text-stat-roi"
        />
      </motion.div>

      {/* CTA */}
      <motion.button
        onClick={onSubmit}
        disabled={submitting}
        className="w-full bg-accent-thrive text-text-inverse font-body font-bold text-cta h-12 rounded-lg cursor-pointer hover:bg-[#6bc494] hover:shadow-glow-thrive transition-all duration-normal disabled:opacity-60 disabled:cursor-not-allowed"
        whileTap={submitting ? undefined : { scale: 0.97 }}
        transition={springs.snappy}
      >
        {submitting ? `Specing ${profileName}...` : "Spec my build →"}
      </motion.button>
    </motion.div>
  );
}
