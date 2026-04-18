import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { PentagonGlow } from "./PentagonGlow";

/**
 * Section A — Above the Fold (Hero)
 * Planetarium-before-the-show. Dark indigo, PentagonGlow at 320px with a 7s
 * vertical drift, one headline, one subhead, one CTA + secondary demo link,
 * data footer at the bottom. See spec §3.4.
 */
export function HeroSection() {
  const prefersReducedMotion = useReducedMotion();

  const fadeInUp = (delay: number) => ({
    initial: { opacity: 0, y: 24 },
    animate: { opacity: 1, y: 0 },
    transition: prefersReducedMotion
      ? { duration: 0 }
      : { ...springs.smooth, delay },
  });

  return (
    <section
      id="landing-section-hero"
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <motion.div
        className="mb-10 tablet:mb-12"
        animate={
          prefersReducedMotion
            ? undefined
            : { y: [0, -10, 0] as number[] }
        }
        transition={
          prefersReducedMotion
            ? undefined
            : { duration: 7, ease: "easeInOut", repeat: Infinity }
        }
      >
        <PentagonGlow size={320} />
      </motion.div>

      <motion.h1
        className="font-display font-bold text-hero tablet:text-marketing-section desktop:text-marketing-hero text-text-primary text-center max-w-[900px] leading-[1.05] tracking-tight"
        {...fadeInUp(0.2)}
      >
        A college degree isn't a destination.
        <br />
        It's a starting position.
      </motion.h1>

      <motion.p
        className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary text-center max-w-[560px] leading-normal"
        {...fadeInUp(0.35)}
      >
        See where your degree actually leads. 700K rows of public data, zero
        admissions brochure.
      </motion.p>

      <motion.div
        className="mt-10 flex justify-center"
        {...fadeInUp(0.5)}
      >
        <a
          id="landing-hero-cta"
          href="/app"
          aria-label="Start your first FutureProof build"
          className="inline-flex items-center justify-center gap-2 font-body font-bold text-cta bg-accent-thrive text-text-inverse rounded-lg h-14 px-8 transition-all duration-normal hover:brightness-95 hover:shadow-glow-thrive active:scale-[0.97]"
        >
          Start <span className="opacity-70">✦</span>
        </a>
      </motion.div>

      <motion.p
        className="absolute bottom-16 font-data text-micro text-text-muted text-center tracking-widest opacity-45 leading-relaxed px-4"
        {...fadeInUp(0.7)}
      >
        700K rows · 280 DQ rules · 7 public datasets
        <br />
        Every number has a receipt.
      </motion.p>

      <motion.div
        className="absolute bottom-6 w-px h-8 bg-gradient-to-b from-border-subtle to-transparent"
        initial={{ opacity: 0 }}
        animate={{ opacity: prefersReducedMotion ? 0.3 : [0.15, 0.3, 0.15] as number[] }}
        transition={
          prefersReducedMotion
            ? { duration: 0 }
            : { duration: 2, delay: 1.5, ease: "easeInOut", repeat: Infinity }
        }
        aria-hidden
      />
    </section>
  );
}
