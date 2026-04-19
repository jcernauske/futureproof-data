import type { ReactElement } from "react";
import { BossRowArt, BranchTreeArt, PentagonArt } from "./HowItWorksCardArt";

type CardArtKey = "pentagon" | "boss-row" | "branch-tree";
const CARD_ART: Record<CardArtKey, () => ReactElement> = {
  pentagon: PentagonArt,
  "boss-row": BossRowArt,
  "branch-tree": BranchTreeArt,
};

/**
 * Section C — How It Works
 * Three cards (stats / gauntlet / branches) with screenshot slots.
 * See spec §3.6.
 *
 * Motion wrappers removed 2026-04-18 — see ProblemSection for context.
 * The card hover elevation is a CSS transition, not a framer animation,
 * so reduced-motion users still get static cards that paint on first load.
 */

type CardTone = "thrive" | "alert" | "insight";

interface CardSpec {
  identifier: string;
  label: string;
  heading: string;
  body: string;
  art: CardArtKey;
  tone: CardTone;
}

const CARDS: CardSpec[] = [
  {
    identifier: "landing-how-stats-card",
    label: "STATS",
    heading: "You see the stats.",
    body: "Five numbers, one to ten. Every stat has a tappable receipt. No vibes, no admissions-brochure gloss — just where the number came from.",
    art: "pentagon",
    tone: "thrive",
  },
  {
    identifier: "landing-how-gauntlet-card",
    label: "GAUNTLET",
    heading: "You fight the bosses.",
    body: "Fight AI, Student Loans, the Market, Burnout, the Ceiling. Each boss is a real career threat, scored from real data. Lose one? Reroll with a skill, see what changes.",
    art: "boss-row",
    tone: "alert",
  },
  {
    identifier: "landing-how-branches-card",
    label: "BRANCHES",
    heading: "You see the branches.",
    body: "A degree isn't one job — it's a starting position. Tap any career and the tree unfolds: the ten other careers your major actually leads to, with the stat deltas that come with each.",
    art: "branch-tree",
    tone: "insight",
  },
];

export function HowItWorksSection() {
  return (
    <section
      id="landing-section-how"
      className="relative px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-24"
    >
      <div
        aria-hidden
        className="absolute left-1/2 top-0 h-[80px] w-px -translate-x-1/2 bg-gradient-to-b from-border-subtle to-transparent"
      />
      <div className="mx-auto max-w-[1280px]">
        <p className="font-data text-micro tracking-[0.2em] uppercase text-accent-info text-center mb-4">
          How it works
        </p>
        <h2 className="font-display font-bold text-heading tablet:text-title text-text-primary text-center max-w-[720px] mx-auto mb-16 tablet:mb-20">
          Three things happen when you spec a build.
        </h2>

        <div className="grid grid-cols-1 desktop:grid-cols-3 gap-8 tablet:gap-10">
          {CARDS.map((card) => {
            const Art = CARD_ART[card.art];
            return (
              <article
                key={card.identifier}
                id={card.identifier}
                className="group bg-bp-mid border border-border-subtle rounded-xl p-8 shadow-md transition-all duration-normal desktop:hover:bg-bp-surface desktop:hover:border-border desktop:hover:shadow-lg desktop:hover:-translate-y-[3px]"
              >
                <Art />
                <p className={`mt-6 font-data font-bold text-[11px] tracking-[2px] uppercase text-accent-${card.tone}`}>
                  {card.label}
                </p>
                <h3 className="mt-2 font-display font-semibold text-heading text-text-primary">
                  {card.heading}
                </h3>
                <p className="mt-3 font-body text-body text-text-secondary leading-normal">
                  {card.body}
                </p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
