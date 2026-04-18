import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { TerminalSVG } from "./TerminalSVG";

/**
 * Section E — Run It Yourself (Gemma + Ollama)
 *
 * Three columns: terminal / body copy / hardware-spec callout. The plush
 * laptop SVG called for in spec §3.8 wasn't produced this cycle, so per
 * visual critique §3 item 15 (fallback option b) the third column now
 * ships a receipt-styled "Works on..." callout instead of an empty slot.
 *
 * The Ollama data-residency claim is scoped per §2 Decision 8 — the full
 * "When a school runs FutureProof on Ollama, no student data leaves the
 * building" clause always ships together.
 */
export function OllamaSection() {
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

  const terminalReveal = prefersReducedMotion
    ? { initial: false, animate: { opacity: 1, scale: 1 } }
    : {
        initial: { opacity: 0, scale: 0.92 },
        whileInView: { opacity: 1, scale: 1 },
        viewport: { once: true, margin: "-80px" },
        transition: { ...springs.smooth, delay: 0.15 },
      };

  const calloutReveal = prefersReducedMotion
    ? { initial: false, animate: { opacity: 1, y: 0 } }
    : {
        initial: { opacity: 0, y: 16 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: "-80px" },
        transition: { ...springs.smooth, delay: 0.4 },
      };

  return (
    <section
      id="landing-section-ollama"
      className="relative border-t border-border-subtle px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32 overflow-hidden"
    >
      {/* Tier-2 thrive-tinted top glow — Ollama section owns the
          thrive-green tone (local inference = thrive) per §3 item 22. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[120px]"
        style={{
          background:
            "radial-gradient(ellipse 60% 100% at 50% 0%, rgba(125, 212, 163, 0.18) 0%, transparent 65%)",
        }}
      />
      {/* Section-specific scanline atmosphere — faint CRT read on the
          terminal environment per §3 item 14. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.55]"
        style={{
          background:
            "repeating-linear-gradient(transparent, transparent 3px, rgba(125, 212, 163, 0.025) 3px, rgba(125, 212, 163, 0.025) 4px)",
        }}
      />
      <div className="relative mx-auto max-w-[1280px]">
        <motion.h2
          className="font-display font-bold text-heading tablet:text-title text-text-primary max-w-[760px] mb-12 tablet:mb-16"
          {...reveal(0)}
        >
          Any school can run this on their own hardware.
          <br />
          Forever. At zero cost.
        </motion.h2>

        <div className="grid grid-cols-1 desktop:grid-cols-12 gap-10 desktop:gap-12 items-start">
          <motion.div className="desktop:col-span-5" {...terminalReveal}>
            <TerminalSVG />
          </motion.div>

          <motion.div
            className="desktop:col-span-4 space-y-5 font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed max-w-[62ch]"
            {...reveal(prefersReducedMotion ? 0 : 0.2)}
          >
            <p>
              FutureProof runs on Gemma 4 through Ollama. Flip one environment
              variable and the whole stack — stats, fights, Gemma's coaching,
              the branch tree — works on a school's own server.
            </p>
            <p>
              When a school runs FutureProof on Ollama, no student data leaves
              the building. No cloud bill. No ongoing cost.
            </p>
          </motion.div>

          {/* Hardware-spec callout — receipt-styled, ships in place of the
              plush-laptop illustration per visual critique §3 item 15. */}
          <motion.aside
            id="landing-ollama-specs"
            className="desktop:col-span-3 bg-bp-mid border border-border-subtle rounded-xl p-6 shadow-md"
            {...calloutReveal}
          >
            <p className="font-data font-bold text-[11px] tracking-[2px] uppercase text-accent-thrive">
              Runs locally on
            </p>
            <dl className="mt-5 space-y-4">
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Apple Silicon
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  M1 · M2 · M3 · M4
                </dd>
              </div>
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Memory
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  8&nbsp;GB minimum, 16&nbsp;GB recommended
                </dd>
              </div>
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Model
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  gemma4:e4b (4.1&nbsp;GB download)
                </dd>
              </div>
              <div>
                <dt className="font-body font-semibold text-body-sm text-text-primary">
                  Cold start
                </dt>
                <dd className="font-data text-small text-text-muted mt-0.5">
                  ~8&nbsp;s on M2, ~12&nbsp;s on M1
                </dd>
              </div>
            </dl>
            <p className="mt-6 pt-4 border-t border-border-subtle font-body text-small text-text-secondary leading-relaxed">
              One env var: <code className="font-data text-small text-accent-thrive">INFERENCE_BACKEND=ollama</code>.
              The rest of the stack doesn't change.
            </p>
          </motion.aside>
        </div>
      </div>
    </section>
  );
}
