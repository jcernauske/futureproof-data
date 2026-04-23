import { motion } from "framer-motion";
import { DiscreteSlider } from "@/components/ui/DiscreteSlider";
import type { SliderStop } from "@/components/ui/DiscreteSlider";
import { springs } from "@/styles/motion";

export type Residency = "in_state" | "out_of_state";

interface ControlDockProps {
  residency: Residency;
  onResidencyChange: (r: Residency) => void;
  loanPct: number;
  onLoanPctChange: (pct: number) => void;
  effort: string;
  onEffortChange: (level: string) => void;
}

const EFFORT_STOPS: SliderStop<string>[] = [
  { value: "working_hard", label: "Working two jobs" },
  { value: "working", label: "Working + school" },
  { value: "balanced", label: "Balanced" },
  { value: "focused", label: "Strong focus" },
  { value: "all_in", label: "All-in" },
];

const EFFORT_LABELS: Record<string, string> = {
  working_hard: "Very limited focus",
  working: "Limited focus",
  balanced: "Balanced focus",
  focused: "Strong academic focus",
  all_in: "Maximum focus",
};

const LOAN_STOPS: SliderStop<number>[] = [
  { value: 0, label: "No loans" },
  { value: 25, label: "Some" },
  { value: 50, label: "Half" },
  { value: 75, label: "Mostly" },
  { value: 100, label: "All loans" },
];

function loanColor(pct: number): string {
  if (pct <= 25) return "var(--color-accent-thrive)";
  if (pct <= 50) return "var(--color-accent-caution)";
  return "var(--color-accent-alert)";
}

export function ControlDock({
  residency,
  onResidencyChange,
  loanPct,
  onLoanPctChange,
  effort,
  onEffortChange,
}: ControlDockProps) {
  const isInState = residency === "in_state";

  return (
    <motion.div
      className="rounded-[20px] border border-border-subtle bg-bp-mid"
      style={{ padding: "24px 28px", marginTop: 24 }}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
    >
      <div
        className="font-data font-bold uppercase text-accent-info"
        style={{ fontSize: 11, letterSpacing: 2, marginBottom: 20 }}
      >
        Tune Your Build
      </div>

      <div
        className="control-dock-grid grid gap-8 items-end"
        style={{ gridTemplateColumns: "auto 1fr 1fr" }}
      >
        {/* Residency toggle */}
        <div>
          <span
            className="block font-body font-semibold text-text-secondary"
            style={{ fontSize: 13, marginBottom: 8 }}
          >
            Residency
          </span>
          <div
            className="relative flex rounded-full bg-bp-deep border border-border-subtle"
            style={{ padding: 3 }}
          >
            <motion.div
              className="absolute rounded-full bg-bp-surface"
              style={{
                top: 3,
                bottom: 3,
                width: "50%",
              }}
              animate={{ left: isInState ? 3 : "50%" }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            />
            <button
              className={`relative z-10 rounded-full font-body font-semibold whitespace-nowrap ${
                isInState ? "text-text-primary" : "text-text-muted"
              }`}
              style={{ padding: "8px 16px", fontSize: 13 }}
              onClick={() => onResidencyChange("in_state")}
            >
              In-State
            </button>
            <button
              className={`relative z-10 rounded-full font-body font-semibold whitespace-nowrap ${
                !isInState ? "text-text-primary" : "text-text-muted"
              }`}
              style={{ padding: "8px 16px", fontSize: 13 }}
              onClick={() => onResidencyChange("out_of_state")}
            >
              Out-of-State
            </button>
          </div>
        </div>

        {/* Loan slider */}
        <div>
          <div
            className="flex items-baseline justify-between"
            style={{ marginBottom: 8 }}
          >
            <span
              className="font-body font-semibold text-text-secondary"
              style={{ fontSize: 13 }}
            >
              Loan %
            </span>
            <motion.span
              className="font-data font-bold"
              style={{ fontSize: 20, color: loanColor(loanPct) }}
              key={loanPct}
              initial={{ scale: 1.15, opacity: 0.7 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
            >
              {loanPct}%
            </motion.span>
          </div>
          <DiscreteSlider
            stops={LOAN_STOPS}
            value={loanPct}
            onChange={onLoanPctChange}
            labelLeft="No loans"
            labelRight="All loans"
            fillGradient={`linear-gradient(90deg, var(--color-accent-thrive), ${loanColor(loanPct)})`}
            ariaLabel="Loan percentage"
          />
        </div>

        {/* Effort slider */}
        <div>
          <div
            className="flex items-baseline justify-between"
            style={{ marginBottom: 8 }}
          >
            <span
              className="font-body font-semibold text-text-secondary"
              style={{ fontSize: 13 }}
            >
              Effort
            </span>
            <span
              className="font-data font-bold text-accent-thrive"
              style={{ fontSize: 13 }}
            >
              {EFFORT_LABELS[effort] ?? "Balanced focus"}
            </span>
          </div>
          <DiscreteSlider
            stops={EFFORT_STOPS}
            value={effort}
            onChange={onEffortChange}
            labelLeft="Working"
            labelRight="All-in"
            fillGradient="linear-gradient(90deg, var(--color-accent-info), var(--color-accent-thrive))"
            ariaLabel="Effort level"
          />
        </div>
      </div>

      <style>{`
        @media (max-width: 599px) {
          .control-dock-grid {
            grid-template-columns: 1fr !important;
            gap: 20px !important;
          }
        }
      `}</style>
    </motion.div>
  );
}
