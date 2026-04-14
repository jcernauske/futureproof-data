import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { springs } from "@/styles/motion";
import { STAT_EXPLANATIONS, type StatKey } from "@/data/statExplanations";
import type { PentagonStats } from "@/types/build";
import { PentagonChart } from "@/components/PentagonChart";

interface StatTutorialProps {
  stats: PentagonStats;
  onComplete: () => void;
}

export function StatTutorial({ stats, onComplete }: StatTutorialProps) {
  const [step, setStep] = useState(0);
  const current = STAT_EXPLANATIONS[step]!;
  const isLast = step === STAT_EXPLANATIONS.length - 1;

  function handleNext() {
    if (isLast) {
      onComplete();
    } else {
      setStep((prev) => prev + 1);
    }
  }

  return (
    <motion.div
      id="dialog-stat-tutorial"
      role="dialog"
      aria-label="Learn about your stats"
      className="fixed inset-0 z-[200] flex flex-col items-center justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0"
        style={{
          backgroundColor: "rgba(18, 19, 31, 0.85)",
          backdropFilter: "blur(8px)",
        }}
      />

      {/* Skip */}
      <button
        id="btn-tutorial-skip"
        aria-label="Skip tutorial"
        onClick={onComplete}
        className="absolute top-6 right-6 z-10 font-body text-small text-text-muted cursor-pointer hover:text-text-secondary transition-colors duration-normal"
      >
        Skip tutorial
      </button>

      {/* Pentagon with spotlight */}
      <div className="relative z-10 mb-8">
        <PentagonChart
          stats={stats}
          size={240}
          animated={false}
          highlightStat={current.key as StatKey}
          dimOpacity={0.2}
        />
      </div>

      {/* Tooltip card */}
      <div className="relative z-10 w-full max-w-[320px] px-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            className="bg-bp-raised rounded-lg p-4 shadow-lg"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={springs.smooth}
          >
            <p
              className="font-display font-semibold text-heading"
              style={{ color: current.color }}
            >
              {current.name}
            </p>
            <p className="font-data text-data-sm text-text-muted mt-0.5">
              ({current.abbreviation})
            </p>
            <p className="font-body text-body-sm text-text-primary mt-3">
              {current.explanation}
            </p>
            <p className="font-data text-micro text-text-muted mt-2">
              Source: {current.source}
            </p>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-4">
              {/* Step dots */}
              <div className="flex gap-1.5">
                {STAT_EXPLANATIONS.map((_, i) => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full transition-colors duration-normal"
                    style={{
                      backgroundColor:
                        i === step
                          ? current.color
                          : "var(--color-bg-surface)",
                    }}
                  />
                ))}
              </div>

              {/* Next / Got it */}
              {isLast ? (
                <button
                  id="btn-tutorial-next"
                  aria-label="Got it"
                  onClick={handleNext}
                  className="font-body font-semibold text-body-sm px-4 py-2 rounded-lg bg-accent-thrive text-text-inverse cursor-pointer hover:brightness-110 transition-all duration-normal"
                >
                  Got it ✦
                </button>
              ) : (
                <button
                  id="btn-tutorial-next"
                  aria-label="Next stat"
                  onClick={handleNext}
                  className="font-body font-semibold text-body-sm text-accent-info cursor-pointer hover:text-text-primary transition-colors duration-normal"
                >
                  Next →
                </button>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
