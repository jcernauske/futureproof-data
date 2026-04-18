import { motion, useReducedMotion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";

/**
 * Section B — The Problem
 * Typography-only centered column. Two inline typographic receipts:
 *   `82% exposed to AI` (accent-insight) and `$400/hour counselor` (accent-alert).
 * See spec §3.5.
 */
export function ProblemSection() {
  const prefersReducedMotion = useReducedMotion();

  const reveal = (delay = 0) =>
    prefersReducedMotion
      ? { initial: false, animate: { opacity: 1, y: 0 } }
      : {
          initial: { opacity: 0, y: 32 },
          whileInView: { opacity: 1, y: 0 },
          viewport: { once: true, margin: "-80px" },
          transition: { ...springs.smooth, delay },
        };

  return (
    <section
      id="landing-section-problem"
      className="border-t border-border-subtle px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div className="mx-auto max-w-[960px] text-center">
        <motion.h2
          className="font-display font-bold text-heading tablet:text-title desktop:text-marketing-section text-text-primary leading-[1.15] tracking-tight"
          {...reveal(0)}
        >
          Your college probably isn't going to mention the ceiling.
        </motion.h2>

        <div className="mt-10 tablet:mt-14 space-y-7 text-left mx-auto max-w-[62ch]">
          <motion.p
            className="font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed"
            {...reveal(prefersReducedMotion ? 0 : stagger.slow)}
          >
            Admissions brochures tell you about the first job. They don't tell
            you what the tenth one pays, or which careers are{" "}
            <span className="font-data font-bold text-accent-insight">
              82% exposed to AI
            </span>
            , or whether your major survives the next decade of automation.
          </motion.p>

          <motion.p
            className="font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed"
            {...reveal(prefersReducedMotion ? 0 : stagger.slow * 2)}
          >
            Your guidance counselor has 400 other students and a quarter-hour
            with you.
          </motion.p>

          <motion.p
            className="font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed"
            {...reveal(prefersReducedMotion ? 0 : stagger.slow * 3)}
          >
            A private-school senior with a{" "}
            <span className="font-data font-bold text-accent-alert">
              $400/hour counselor
            </span>{" "}
            gets a different answer than a first-gen community-college student.
            That's the gap FutureProof closes.
          </motion.p>
        </div>
      </div>
    </section>
  );
}
