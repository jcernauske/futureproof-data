import { motion, useReducedMotion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
import { ScreenshotWithFallback } from "./ScreenshotWithFallback";

/**
 * Section C — How It Works
 * Three cards (stats / gauntlet / branches) with screenshot slots.
 * See spec §3.6.
 */

interface CardSpec {
  identifier: string;
  label: string;
  heading: string;
  body: string;
  screenshot: string; // relative path; base = /assets/screenshots/landing/{screenshot}
  alt: string;
}

const CARDS: CardSpec[] = [
  {
    identifier: "landing-how-stats-card",
    label: "STATS",
    heading: "You see the stats.",
    body: "Five numbers, one to ten. Every stat has a tappable receipt. No vibes, no admissions-brochure gloss — just where the number came from.",
    screenshot: "01-reveal",
    alt: "Stage 2 Reveal showing the pentagon of five career stats alongside Gemma's Take narrative.",
  },
  {
    identifier: "landing-how-gauntlet-card",
    label: "GAUNTLET",
    heading: "You fight the bosses.",
    body: "Fight AI, Student Loans, the Market, Burnout, the Ceiling. Each boss is a real career threat, scored from real data. Lose one? Reroll with a skill, see what changes.",
    screenshot: "02-gauntlet-reroll",
    alt: "Boss gauntlet mid-reroll showing a skill card equipped against Fight AI.",
  },
  {
    identifier: "landing-how-branches-card",
    label: "BRANCHES",
    heading: "You see the branches.",
    body: "A degree isn't one job — it's a starting position. Tap any career and the tree unfolds: the ten other careers your major actually leads to, with the stat deltas that come with each.",
    screenshot: "03-branch-tree",
    alt: "Branch Tree for a Marketing major showing every career path lit with endpoint glow.",
  },
];

export function HowItWorksSection() {
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

  const cardReveal = (index: number) =>
    prefersReducedMotion
      ? { initial: false, animate: { opacity: 1, scale: 1 } }
      : {
          initial: { opacity: 0, scale: 0.95 },
          whileInView: { opacity: 1, scale: 1 },
          viewport: { once: true, margin: "-80px" },
          transition: { ...springs.smooth, delay: index * stagger.slow },
        };

  return (
    <section
      id="landing-section-how"
      className="border-t border-border-subtle px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-32"
    >
      <div className="mx-auto max-w-[1280px]">
        <motion.h2
          className="font-display font-bold text-heading tablet:text-title text-text-primary text-center max-w-[720px] mx-auto mb-16 tablet:mb-20"
          {...reveal(0)}
        >
          Three things happen when you spec a build.
        </motion.h2>

        <div className="grid grid-cols-1 desktop:grid-cols-3 gap-8 tablet:gap-10">
          {CARDS.map((card, index) => (
            <motion.article
              key={card.identifier}
              id={card.identifier}
              className="group bg-bp-mid border border-border-subtle rounded-xl p-8 shadow-md transition-all duration-normal desktop:hover:bg-bp-surface desktop:hover:border-border desktop:hover:shadow-lg desktop:hover:-translate-y-[3px]"
              {...cardReveal(index)}
            >
              <ScreenshotWithFallback
                slug={card.screenshot}
                alt={card.alt}
                className="w-full aspect-[16/10] object-cover rounded-lg border border-border-subtle shadow-md transition-[filter] duration-normal desktop:group-hover:brightness-[1.02]"
              />
              <p className="mt-6 font-data font-bold text-[11px] tracking-[2px] uppercase text-accent-info">
                {card.label}
              </p>
              <h3 className="mt-2 font-display font-semibold text-heading text-text-primary">
                {card.heading}
              </h3>
              <p className="mt-3 font-body text-body text-text-secondary leading-normal">
                {card.body}
              </p>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
