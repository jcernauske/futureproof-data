import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import { StatBadge } from "@/components/ui/StatBadge";
import type { EffortSelection, LoanSelection } from "@/types/buildInput";
import type { Segment } from "@/components/ui/SegmentedControl";

interface EffortLoansPanelProps {
  effort: EffortSelection;
  loans: LoanSelection;
  onEffortChange: (effort: EffortSelection) => void;
  onLoanChange: (loans: LoanSelection) => void;
  profileName: string;
  onSubmit: () => void;
  submitting: boolean;
}

const EFFORT_SEGMENTS: Segment<string>[] = [
  {
    value: "working",
    label: "Working + school",
    shortLabel: "Work",
    subtext: "Limited time to focus",
  },
  {
    value: "balanced",
    label: "Balanced",
    shortLabel: "Bal",
    subtext: "Solid effort",
  },
  {
    value: "all_in",
    label: "All-in",
    shortLabel: "All",
    subtext: "Maximum focus",
  },
];

const EFFORT_MAP: Record<
  string,
  { percentile: 25 | 50 | 75; ernShift: -1 | 0 | 1 }
> = {
  working: { percentile: 25, ernShift: -1 },
  balanced: { percentile: 50, ernShift: 0 },
  all_in: { percentile: 75, ernShift: 1 },
};

const LOAN_SEGMENTS: Segment<number>[] = [
  { value: 0, label: "No loans", shortLabel: "0%" },
  { value: 25, label: "Some", shortLabel: "25%" },
  { value: 50, label: "Half", shortLabel: "50%" },
  { value: 75, label: "Mostly", shortLabel: "75%" },
  { value: 100, label: "All loans", shortLabel: "100%" },
];

const LOAN_LABELS: Record<number, string> = {
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
  const seg = LOAN_SEGMENTS.find((s) => s.value === pct);
  return seg?.label ?? "Half";
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

  return (
    <motion.div
      className="space-y-8"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      {/* Effort slider */}
      <div>
        <h2 className="font-display text-subheading font-semibold text-text-primary mb-1">
          How much time will you have to focus on school?
        </h2>
        <p className="text-sm text-text-muted mb-4">
          This isn't about intelligence — it's about circumstances.
        </p>
        <SegmentedControl
          segments={EFFORT_SEGMENTS}
          value={effort.level}
          onChange={handleEffortChange}
          ariaLabel="Effort level"
        />
        <p className="mt-2 text-sm">
          <span className="text-stat-ern font-data">
            ERN impact: {ernShiftDisplay(effort.ernShift)}
          </span>
        </p>
      </div>

      {/* Loan slider */}
      <div>
        <h2 className="font-display text-subheading font-semibold text-text-primary mb-1">
          How much of your school costs will you cover with loans?
        </h2>
        <p className="text-sm text-text-muted mb-4">
          Scholarships, savings, family help — anything that isn't borrowed
          money.
        </p>
        <SegmentedControl
          segments={LOAN_SEGMENTS}
          value={loans.percentage}
          onChange={handleLoanChange}
          warningValues={[75, 100]}
          ariaLabel="Loan percentage"
        />
        <p className="mt-2 text-sm">
          <span className="text-stat-roi font-data">
            ROI impact: {LOAN_LABELS[loans.percentage]}
          </span>
        </p>
      </div>

      {/* Live stat preview */}
      <motion.div
        className="bg-bp-raised rounded-md p-4 flex justify-center gap-8"
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
