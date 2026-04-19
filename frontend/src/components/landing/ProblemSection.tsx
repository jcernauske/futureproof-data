/**
 * Section B — The Problem
 * Typography-only centered column. Two inline typographic receipts:
 *   `82% exposed to AI` (accent-insight) and `$400/hour counselor` (accent-alert).
 * See spec §3.5.
 *
 * NOTE: motion wrappers removed 2026-04-18 because Framer Motion's
 * `useReducedMotion()` returns `null` on first paint — components rendered
 * with `initial: { opacity: 0 }` get stuck invisible when the media-query
 * resolves to `true` after mount. Plain tags always paint; losing the
 * fade-in is a smaller bug than a blank page for reduced-motion users.
 */
export function ProblemSection() {
  return (
    <section
      id="landing-section-problem"
      className="relative px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div className="mx-auto max-w-[960px] text-center">
        <p className="font-data text-micro tracking-[0.2em] uppercase text-accent-alert mb-4">
          The gap
        </p>
        <h2 className="font-display font-bold text-heading tablet:text-title desktop:text-marketing-section text-text-primary leading-[1.15] tracking-tight">
          Your college probably isn't going to mention the ceiling.
        </h2>

        <div className="mt-10 tablet:mt-14 space-y-7 text-left mx-auto max-w-[62ch]">
          <p className="font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed">
            Admissions brochures tell you about the first job. They don't tell
            you what the tenth one pays, or which careers are{" "}
            <span className="font-data font-bold text-accent-insight">
              82% exposed to AI
            </span>
            , or whether your major survives the next decade of automation.
          </p>

          <p className="font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed">
            Your guidance counselor has 400 other students and a quarter-hour
            with you.
          </p>

          <p className="font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed">
            A private-school senior with a{" "}
            <span className="font-data font-bold text-accent-alert">
              $400/hour counselor
            </span>{" "}
            gets a different answer than a first-gen community-college student.
            That's the gap FutureProof closes.
          </p>
        </div>
      </div>
    </section>
  );
}
