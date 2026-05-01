import type { ReactElement } from "react";
import { BossRowArt, BranchTreeArt, PentagonArt } from "./HowItWorksCardArt";
import { useT } from "@/i18n/useT";

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
  labelKey: string;
  headingKey: string;
  bodyKey: string;
  art: CardArtKey;
  tone: CardTone;
}

const CARDS: CardSpec[] = [
  {
    identifier: "landing-how-stats-card",
    labelKey: "landing.howItWorks.statsLabel",
    headingKey: "landing.howItWorks.statsHeading",
    bodyKey: "landing.howItWorks.statsBody",
    art: "pentagon",
    tone: "thrive",
  },
  {
    identifier: "landing-how-gauntlet-card",
    labelKey: "landing.howItWorks.gauntletLabel",
    headingKey: "landing.howItWorks.gauntletHeading",
    bodyKey: "landing.howItWorks.gauntletBody",
    art: "boss-row",
    tone: "alert",
  },
  {
    identifier: "landing-how-branches-card",
    labelKey: "landing.howItWorks.branchesLabel",
    headingKey: "landing.howItWorks.branchesHeading",
    bodyKey: "landing.howItWorks.branchesBody",
    art: "branch-tree",
    tone: "insight",
  },
];

export function HowItWorksSection() {
  const t = useT();
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
          {t("landing.howItWorks.kicker")}
        </p>
        <h2 className="font-display font-bold text-heading tablet:text-title text-text-primary text-center max-w-[720px] mx-auto mb-16 tablet:mb-20">
          {t("landing.howItWorks.heading")}
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
                  {t(card.labelKey)}
                </p>
                <h3 className="mt-2 font-display font-semibold text-heading text-text-primary">
                  {t(card.headingKey)}
                </h3>
                <p className="mt-3 font-body text-body text-text-secondary leading-normal">
                  {t(card.bodyKey)}
                </p>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
