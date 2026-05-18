/**
 * DemoChipsDrawer — collapsible drawer of demo paths. Two sections:
 *
 *   1. Single picks — 10 verified (school, major) combos that return
 *      fully populated pentagons.
 *
 *   2. Same major, different cost — 3 pairs of schools where everything
 *      is equal except the price tag. Each pair surfaces a "Better ROI"
 *      chip alongside a "Higher cost" chip so judges can click both and
 *      see the contrast play out on the pentagon.
 *
 * Click behavior is identical across both sections: seed school + major,
 * fire live Gemma intent stream. Verified slate in src/data/demoChips.ts.
 */

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";

import {
  DEMO_CHIPS,
  DEMO_COMPARISONS,
  type DemoChip,
} from "@/data/demoChips";
import { useT } from "@/i18n/useT";
import { springs } from "@/styles/motion";

interface DemoChipsDrawerProps {
  disabled?: boolean;
  onPick: (chip: DemoChip) => void;
}

const CHIP_BASE = [
  "inline-flex items-center px-4 py-2 rounded-full",
  "font-body text-small font-semibold whitespace-nowrap",
  "transition-colors duration-normal",
  "border",
  "disabled:opacity-50 disabled:cursor-not-allowed",
  "focus-visible:outline-none focus-visible:ring-2",
  "focus-visible:ring-[color:var(--color-focus-ring)]",
].join(" ");

const CHIP_NEUTRAL =
  "border-border-subtle bg-bp-surface text-text-secondary " +
  "hover:bg-bp-raised hover:text-text-primary";

function chipTestId(chip: DemoChip, section: "single" | "compare"): string {
  return `demo-chip-${section}-${chip.school.unitid}-${chip.majorText
    .replace(/\s+/g, "-")
    .toLowerCase()}`;
}

export function DemoChipsDrawer({
  disabled = false,
  onPick,
}: DemoChipsDrawerProps) {
  const t = useT();
  const reducedMotion = useReducedMotion();
  const [expanded, setExpanded] = useState(false);

  // Collapse the drawer after a chip is picked so the school/major inputs
  // the chip just populated come back into view. The intent stream + build
  // play out on the right panel; keeping the drawer open just buries the
  // confirmed selection under a tall list of unchosen options.
  const handleChipClick = (chip: DemoChip) => {
    onPick(chip);
    setExpanded(false);
  };

  return (
    <section
      aria-labelledby="demo-chips-trigger"
      data-testid="demo-chips-drawer"
      className="rounded-xl border border-border-subtle bg-bp-mid/40"
    >
      <button
        type="button"
        id="demo-chips-trigger"
        data-testid="demo-chips-trigger"
        aria-expanded={expanded}
        aria-controls="demo-chips-panel"
        onClick={() => setExpanded((v) => !v)}
        className={[
          "w-full flex items-center justify-between gap-3",
          "px-4 py-3 text-left",
          "font-body text-small font-semibold text-text-secondary",
          "hover:text-text-primary transition-colors duration-normal",
          "focus-visible:outline-none focus-visible:ring-2",
          "focus-visible:ring-[color:var(--color-focus-ring)] rounded-xl",
        ].join(" ")}
      >
        <span className="inline-flex items-center gap-2">
          <span
            aria-hidden="true"
            className="inline-flex items-center justify-center w-5 h-5 text-accent-thrive"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M3 8 L13 8 M8 3 L13 8 L8 13"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          {t("syc.demoDrawer.trigger")}
        </span>
        <motion.span
          aria-hidden="true"
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={reducedMotion ? { duration: 0 } : springs.smooth}
          className="inline-flex items-center justify-center w-5 h-5 text-text-muted"
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M3 4.5 L6 7.5 L9 4.5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id="demo-chips-panel"
            key="demo-chips-panel"
            data-testid="demo-chips-panel"
            initial={reducedMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
            animate={reducedMotion ? { opacity: 1 } : { opacity: 1, height: "auto" }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={springs.smooth}
            className="overflow-hidden border-t border-border-subtle"
          >
            {/* Section 1 — single picks */}
            <div className="p-4">
              <h4
                data-testid="demo-section-single"
                className="font-body text-micro font-bold tracking-widest uppercase text-text-muted mb-3"
              >
                {t("syc.demoDrawer.singlePicks")}
              </h4>
              <div className="flex flex-wrap gap-2">
                {DEMO_CHIPS.map((chip) => (
                  <button
                    key={chipTestId(chip, "single")}
                    type="button"
                    data-testid={chipTestId(chip, "single")}
                    disabled={disabled}
                    onClick={() => handleChipClick(chip)}
                    className={`${CHIP_BASE} ${CHIP_NEUTRAL}`}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Section 2 — cost comparisons */}
            <div className="p-4 border-t border-border-subtle">
              <h4
                data-testid="demo-section-comparisons"
                className="font-body text-micro font-bold tracking-widest uppercase text-text-muted mb-1"
              >
                {t("syc.demoDrawer.comparisons")}
              </h4>
              <p className="font-body text-small text-text-muted mb-3">
                {t("syc.demoDrawer.comparisonsSubtitle")}
              </p>
              <div className="flex flex-col gap-3">
                {DEMO_COMPARISONS.map((pair) => (
                  <div
                    key={pair.major}
                    data-testid={`demo-comparison-${pair.major.replace(/\s+/g, "-").toLowerCase()}`}
                    className="flex flex-col gap-2"
                  >
                    <div className="font-body text-small font-semibold text-text-secondary">
                      {pair.major}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        data-testid={chipTestId(pair.better, "compare")}
                        disabled={disabled}
                        onClick={() => handleChipClick(pair.better)}
                        className={`${CHIP_BASE} ${CHIP_NEUTRAL}`}
                      >
                        {pair.better.label}
                      </button>
                      <button
                        type="button"
                        data-testid={chipTestId(pair.worse, "compare")}
                        disabled={disabled}
                        onClick={() => handleChipClick(pair.worse)}
                        className={`${CHIP_BASE} ${CHIP_NEUTRAL}`}
                      >
                        {pair.worse.label}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
