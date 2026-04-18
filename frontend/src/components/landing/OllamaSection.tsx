import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { springs } from "@/styles/motion";
import { TerminalSVG } from "./TerminalSVG";

/**
 * Section E — Run It Yourself (Gemma + Ollama)
 * 3-column: terminal / body / laptop illustration (fallback: terminal spans 8).
 * Ollama claim is scoped per §2 Decision 8 + §3.8 architect hand-off.
 * See spec §3.8.
 */
export function OllamaSection() {
  const prefersReducedMotion = useReducedMotion();
  const [laptopAvailable, setLaptopAvailable] = useState(true);

  useEffect(() => {
    const img = new Image();
    img.onerror = () => setLaptopAvailable(false);
    img.src = "/assets/plush-laptop.svg";
    return () => {
      img.onerror = null;
    };
  }, []);

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

  const laptopReveal = prefersReducedMotion
    ? { initial: false, animate: { opacity: 1, scale: 1 } }
    : {
        initial: { opacity: 0, scale: 0.95 },
        whileInView: { opacity: 1, scale: 1 },
        viewport: { once: true, margin: "-80px" },
        transition: { ...springs.smooth, delay: 0.4 },
      };

  return (
    <section
      id="landing-section-ollama"
      className="border-t border-border-subtle px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div className="mx-auto max-w-[1280px]">
        <motion.h2
          className="font-display font-bold text-heading tablet:text-title text-text-primary max-w-[760px] mb-12 tablet:mb-16"
          {...reveal(0)}
        >
          Any school can run this on their own hardware.
          <br />
          Forever. At zero cost.
        </motion.h2>

        <div className="grid grid-cols-1 desktop:grid-cols-12 gap-10 desktop:gap-12 items-start">
          <motion.div
            className={
              laptopAvailable ? "desktop:col-span-5" : "desktop:col-span-8"
            }
            {...terminalReveal}
          >
            <TerminalSVG />
          </motion.div>

          <motion.div
            className={`desktop:col-span-4 space-y-5 font-body text-body tablet:text-body-lg text-text-secondary leading-relaxed max-w-[62ch] ${
              laptopAvailable ? "" : "desktop:col-start-9 desktop:col-span-4"
            }`}
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

          {laptopAvailable && (
            <motion.div
              className="desktop:col-span-3 flex justify-center"
              {...laptopReveal}
            >
              <img
                id="landing-ollama-laptop"
                src="/assets/plush-laptop.svg"
                alt="Laptop displaying FutureProof's pentagon constellation."
                loading="lazy"
                decoding="async"
                className="w-full max-w-[280px] h-auto"
              />
            </motion.div>
          )}
        </div>
      </div>
    </section>
  );
}

