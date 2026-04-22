import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { IntentResult } from "@/types/buildInput";

interface CipOption {
  cip: string;
  title: string;
  why: string;
  parent_cip?: string;
}

interface CipPickerProps {
  /** The initial resolution from Gemma (stable source of all options). */
  initial: IntentResult;
  /** The current resolution (determines which option is selected). */
  current: IntentResult;
  onPick: (index: number) => void;
}

export function CipPicker({ initial, current, onPick }: CipPickerProps) {
  const reducedMotion = useReducedMotion();

  const alts = initial.alternatives;
  if (!alts || alts.length === 0) return null;

  const remaining = initial.remaining_count ?? 0;
  const hint = initial.narrowing_hint || "try a more specific search";

  const options: CipOption[] = [
    {
      cip: initial.matched_cip,
      title: initial.matched_title,
      why: initial.reasoning ?? "",
      parent_cip: initial.parent_cip,
    },
    ...alts,
  ];

  return (
    <div
      role="group"
      aria-label="Program options"
      className="pl-[22px] mt-4"
      data-testid="cip-picker"
    >
      <p
        className="font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info mb-2"
        aria-hidden="true"
        data-testid="cip-picker-label"
      >
        Also matches
      </p>

      <div className="flex flex-col gap-1">
        {options.map((opt, i) => {
          const isSelected = opt.cip === current.matched_cip;
          const testId = i === 0 ? "cip-option-primary" : `cip-option-alt-${i - 1}`;

          if (isSelected) {
            return (
              <motion.div
                key={opt.cip}
                layout={!reducedMotion}
                transition={reducedMotion ? { duration: 0 } : springs.snappy}
                className="flex items-start gap-2.5 px-3 py-2.5 rounded-md"
                aria-current="true"
                data-testid={testId}
              >
                <span
                  className="mt-[7px] w-1.5 h-1.5 rounded-full bg-accent-thrive flex-none transition-colors duration-fast"
                  aria-hidden="true"
                />
                <div className="min-w-0">
                  <p className="font-body text-body-sm font-semibold text-text-primary">
                    {opt.title}
                  </p>
                  <p className="font-body text-small text-text-muted truncate max-w-[48ch]">
                    {opt.why}
                  </p>
                </div>
              </motion.div>
            );
          }

          return (
            <motion.button
              key={opt.cip}
              layout={!reducedMotion}
              type="button"
              onClick={() => onPick(i)}
              whileTap={reducedMotion ? undefined : { scale: 0.98 }}
              transition={reducedMotion ? { duration: 0 } : springs.snappy}
              className="w-full flex items-start gap-2.5 px-3 py-2.5 rounded-md
                         cursor-pointer transition-colors duration-fast
                         hover:bg-bp-surface group
                         focus-visible:outline-none focus-visible:ring-[3px]
                         focus-visible:ring-[color:var(--color-focus-ring)]
                         focus-visible:ring-offset-2"
              aria-label={`Select program: ${opt.title}`}
              data-testid={testId}
            >
              <span
                className="mt-[7px] w-1.5 h-1.5 rounded-full border-[1.5px] border-border
                           group-hover:border-accent-info flex-none transition-colors duration-fast"
                aria-hidden="true"
              />
              <div className="min-w-0 text-left">
                <p className="font-body text-body-sm font-semibold text-text-secondary
                              group-hover:text-text-primary transition-colors duration-fast">
                  {opt.title}
                </p>
                <p className="font-body text-small text-text-muted truncate max-w-[48ch]">
                  {opt.why}
                </p>
              </div>
            </motion.button>
          );
        })}
      </div>

      {remaining > 0 && (
        <p
          className="pl-[22px] mt-2 font-body text-small italic text-text-muted"
          data-testid="cip-remaining-hint"
          aria-label={`${remaining} more programs match`}
        >
          {remaining} more program{remaining === 1 ? "" : "s"} match{" "}
          {"—"} {hint}
        </p>
      )}
    </div>
  );
}
