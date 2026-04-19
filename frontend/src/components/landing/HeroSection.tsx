import { motion, useReducedMotion } from "framer-motion";
import { PentagonGlow } from "./PentagonGlow";

/**
 * Section A — Above the Fold (Hero)
 *
 * Planetarium-before-the-show. Pentagon + headline + subhead + CTA +
 * demo-link placeholder + data footer + scroll cue. See spec §3.4.
 *
 * Motion wrappers on critical content were removed 2026-04-18 —
 * `useReducedMotion()` returns `null` on first paint, and Framer Motion
 * leaves elements pinned at their `initial` state after the media query
 * resolves (headless browsers + users with OS-level reduced motion would
 * see an invisible hero). Only the decorative scroll cue stays motion.
 */
export function HeroSection() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <section
      id="landing-section-hero"
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      {/* Pentagon + labeled stats legend — turns the atmospheric pentagon
          into a product demo by pairing it with a sample build's actual
          values. Mirrors v3 mockup's Stats section. PentagonGlow owns its
          own drift + breathe internally — do NOT wrap in a second motion.div
          or the two animations compound. Responsive: pentagon left + legend
          right on desktop, stacked on mobile. */}
      <div className="mb-10 tablet:mb-12 flex flex-col desktop:flex-row items-center justify-center gap-10 desktop:gap-24">
        <div className="scale-[0.68] tablet:scale-[0.82] desktop:scale-100 origin-center">
          <PentagonGlow size={440} />
        </div>
        <div className="w-full max-w-[320px] desktop:max-w-[280px]">
          <p className="font-data text-micro tracking-[0.2em] uppercase text-text-muted mb-4">
            Example build
          </p>
          <ul className="space-y-3">
            {[
              { abbr: "ERN", label: "Earning Power", value: 78, color: "var(--color-stat-ern)" },
              { abbr: "ROI", label: "Return on Investment", value: 82, color: "var(--color-stat-roi)" },
              { abbr: "RES", label: "AI Resilience", value: 65, color: "var(--color-stat-res)" },
              { abbr: "GRW", label: "Growth Potential", value: 71, color: "var(--color-stat-grw)" },
              { abbr: "HMN", label: "Human Edge", value: 59, color: "var(--color-stat-hmn)" },
            ].map((s) => (
              <li
                key={s.abbr}
                className="flex items-center gap-3 pb-3 border-b border-border-subtle/40 last:border-b-0 last:pb-0"
              >
                <span
                  aria-hidden
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ background: s.color }}
                />
                <span
                  className="font-data text-micro tracking-[0.15em] uppercase shrink-0 w-9"
                  style={{ color: s.color }}
                >
                  {s.abbr}
                </span>
                <span className="flex-1 font-body text-small text-text-secondary">
                  {s.label}
                </span>
                <span
                  className="font-display font-bold text-body tabular-nums"
                  style={{ color: s.color }}
                >
                  {s.value}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/*
        Critical hero content is intentionally NOT wrapped in `motion.*`.
        Framer Motion's `useReducedMotion()` hook pins animated elements
        at their `initial` state when the OS (or headless browsers) report
        `prefers-reduced-motion: reduce`. We tried the `initial={false}`
        collapse but Framer's global reduce mode still suppressed the
        final paint for headless + some user machines, so the hero copy
        disappeared entirely. Keeping these as plain tags guarantees the
        headline, subhead, CTA, and data footer ALWAYS render — the
        decorative scroll cue below stays motion because missing it is
        harmless.
      */}
      <h1 className="font-display font-bold text-title tablet:text-marketing-section desktop:text-[80px] text-text-primary text-center max-w-[1040px] leading-[1.05] tracking-[-0.025em]">
        A college degree isn't a destination.
        <br />
        It's a starting position.
      </h1>

      <p className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary text-center max-w-[560px] leading-normal">
        See where your degree actually leads. 700K rows of public data, zero
        admissions brochure.
      </p>

      <div className="mt-10 flex flex-col tablet:flex-row items-center justify-center gap-6">
        <a
          id="landing-hero-cta"
          href="/app"
          aria-label="Start your first FutureProof build"
          className="inline-flex items-center justify-center gap-2 font-body font-bold text-cta bg-accent-thrive text-text-inverse rounded-lg h-14 px-8 transition-all duration-normal hover:brightness-95 hover:shadow-glow-thrive active:scale-[0.97]"
        >
          Start <span className="opacity-70">✦</span>
        </a>
        <span
          id="landing-hero-demo-link"
          aria-label="Watch the 3-minute demo — coming soon"
          aria-disabled="true"
          className="font-body text-body text-text-muted opacity-60 cursor-not-allowed select-none"
          title="Demo video ships week 3 — see §11 Follow-ups"
        >
          Watch the 3-min demo →
        </span>
      </div>

      <p className="absolute bottom-16 font-data text-micro text-text-muted text-center tracking-widest opacity-45 leading-relaxed px-4">
        700K rows · 280 DQ rules · 7 public datasets
        <br />
        Every number has a receipt.
      </p>

      <motion.div
        className="absolute bottom-6 w-px h-8 bg-gradient-to-b from-border-subtle to-transparent"
        initial={prefersReducedMotion ? false : { opacity: 0 }}
        animate={{
          opacity: prefersReducedMotion ? 0.3 : ([0.15, 0.3, 0.15] as number[]),
        }}
        transition={
          prefersReducedMotion
            ? undefined
            : { duration: 2, delay: 1.5, ease: "easeInOut", repeat: Infinity }
        }
        aria-hidden
      />
    </section>
  );
}
