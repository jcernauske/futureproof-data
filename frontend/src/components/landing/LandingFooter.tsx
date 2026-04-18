import { motion, useReducedMotion } from "framer-motion";

/**
 * Section I — Footer
 * Wordmark + primary nav (Live app only, pre-launch) + disclaimer + data-line.
 *
 * **Scope reduction per @faang-staff-engineer Finding 1 (2026-04-17):** the
 * Kaggle, GitHub, Video, Brightsmith, Voice-guide, and Disclaimers links were
 * removed because their destinations 404 or have no in-page anchors. See §6
 * Deviations + §11 Follow-ups — they come back when the destinations exist.
 * See spec §3.12.
 */
export function LandingFooter() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.footer
      id="landing-footer"
      className="bg-bp-deep border-t border-border-subtle py-16 px-6 tablet:px-10"
      initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={
        prefersReducedMotion
          ? { duration: 0 }
          : { duration: 0.3, ease: "easeOut" }
      }
    >
      <div className="mx-auto max-w-[1280px] space-y-8">
        <div className="flex flex-col tablet:flex-row tablet:items-start tablet:justify-between gap-6">
          <span className="font-display font-bold text-heading text-text-primary">
            FutureProof
          </span>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <a
              id="landing-footer-live-app"
              href="/app"
              className="font-body text-body text-text-secondary hover:text-text-primary hover:underline underline-offset-4"
            >
              Live app
            </a>
          </div>
        </div>

        <p className="font-body text-small text-text-muted max-w-[720px]">
          AI-estimated. Not a substitute for professional career counseling.
        </p>

        <p className="font-data text-micro text-text-muted tracking-widest opacity-40 leading-relaxed">
          700K rows · 280 DQ rules · 7 public datasets · Every number has a
          receipt.
        </p>
      </div>
    </motion.footer>
  );
}
