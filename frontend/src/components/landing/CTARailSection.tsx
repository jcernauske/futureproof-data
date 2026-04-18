import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";

/**
 * Section F — Live Demo / CTA Rail
 * Shortest section on the page. Mirrors hero CTA DNA intentionally.
 * See spec §3.9.
 */
export function CTARailSection() {
  const prefersReducedMotion = useReducedMotion();

  const reveal = (delay = 0) =>
    prefersReducedMotion
      ? { initial: false, animate: { opacity: 1, y: 0 } }
      : {
          initial: { opacity: 0, y: 24 },
          whileInView: { opacity: 1, y: 0 },
          viewport: { once: true, margin: "-80px" },
          transition: { ...springs.smooth, delay },
        };

  const ctaReveal = prefersReducedMotion
    ? { initial: false, animate: { opacity: 1, scale: 1 } }
    : {
        initial: { opacity: 0, scale: 0.92 },
        whileInView: { opacity: 1, scale: 1 },
        viewport: { once: true, margin: "-80px" },
        transition: { ...springs.smooth, delay: 0.25 },
      };

  return (
    <section
      id="landing-section-cta-rail"
      className="border-t border-border-subtle px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div className="mx-auto max-w-[640px] text-center">
        <motion.h2
          className="font-display font-bold text-heading tablet:text-title text-text-primary"
          {...reveal(0)}
        >
          Spec your first build.
        </motion.h2>
        <motion.p
          className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary leading-normal"
          {...reveal(0.1)}
        >
          Takes about two minutes. No signup, no email. You'll get a
          three-word name and emoji — that's your identity.
        </motion.p>
        <motion.div className="mt-10 flex justify-center" {...ctaReveal}>
          <a
            id="landing-cta-rail"
            href="/app"
            aria-label="Start your first FutureProof build"
            className="inline-flex items-center justify-center gap-2 font-body font-bold text-cta bg-accent-thrive text-text-inverse rounded-lg h-14 px-8 transition-all duration-normal hover:brightness-95 hover:shadow-glow-thrive active:scale-[0.97]"
          >
            Start <span className="opacity-70">✦</span>
          </a>
        </motion.div>
      </div>
    </section>
  );
}
