import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";

/**
 * Section H — Team / About
 * Centered single paragraph. No headshot. Restraint is the register.
 * See spec §3.11.
 */
export function TeamSection() {
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

  return (
    <section
      id="landing-section-team"
      className="border-t border-border-subtle px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div className="mx-auto max-w-[640px] text-center">
        <motion.h2
          className="font-display font-bold text-heading text-text-primary"
          {...reveal(0)}
        >
          Who built this.
        </motion.h2>
        <motion.p
          className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed max-w-[62ch] mx-auto"
          {...reveal(0.1)}
        >
          FutureProof was built for the Gemma 4 Good hackathon by a one-person
          team. The data pipeline runs on{" "}
          <a
            id="landing-team-brightsmith-link"
            href="https://github.com/jcernauske/brightsmith"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent-info hover:underline underline-offset-4"
          >
            Brightsmith
          </a>
          , an open-source framework for governed data products. The code is
          MIT-licensed and the public data is public.
        </motion.p>
      </div>
    </section>
  );
}
