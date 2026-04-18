import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { CareerOutcome } from "@/types/build";
import { STAT_MAP, type StatKey } from "@/data/statExplanations";
import { socEmoji } from "@/data/socEmoji";

interface CareerCardProps {
  career: CareerOutcome;
  /**
   * True when this card's SOC is the student's currently-committed pick.
   * Styled with the thrive-glow accent to signal commitment. The actual
   * commit button lives inside the lineage sheet (see Proposal A redesign
   * — click a card to preview lineage, confirm inside the sheet).
   */
  picked: boolean;
  /** Card click — populates the bottom lineage sheet with this career. */
  onExplore: () => void;
}

const STAT_ORDER: StatKey[] = ["ern", "roi", "res", "grw", "hmn"];

export function CareerCard({ career, picked, onExplore }: CareerCardProps) {
  const wage = career.median_annual_wage;
  const reducedMotion = useReducedMotion() ?? false;

  return (
    <motion.button
      type="button"
      id={`career-${career.soc_code}`}
      aria-label={`Explore lineage for ${career.occupation_title}${
        picked ? " (currently picked)" : ""
      }`}
      aria-pressed={picked}
      onClick={onExplore}
      className={`w-full text-left rounded-xl p-6 border cursor-pointer transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] ${
        picked
          ? "bg-bp-surface border-accent-thrive border-l-[3px] shadow-glow-thrive"
          : "bg-bp-mid border-border-subtle hover:bg-bp-surface hover:border-border hover:shadow-lg hover:-translate-y-0.5"
      }`}
      whileTap={reducedMotion ? undefined : { scale: 0.98 }}
      animate={picked && !reducedMotion ? { scale: [1, 1.02, 1] } : {}}
      transition={springs.snappy}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="text-[32px] leading-none select-none flex-shrink-0"
        >
          {socEmoji(career.soc_code)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-body font-bold text-body-lg text-text-primary">
              {career.occupation_title}
            </h3>
            {picked ? (
              <span
                aria-hidden="true"
                className="shrink-0 inline-flex items-center gap-1 bg-accent-thrive/15 text-accent-thrive font-data text-micro font-bold uppercase tracking-[2px] rounded-full px-2 py-0.5"
              >
                Picked
              </span>
            ) : null}
          </div>
          {wage !== null && (
            <p className="font-data text-data text-stat-ern mt-1">
              ${wage.toLocaleString()}/yr median
            </p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mt-3">
        {STAT_ORDER.map((key) => {
          const val = career.stats[key];
          const stat = STAT_MAP[key];
          return (
            <span
              key={key}
              className="inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5"
            >
              <span className={`font-data text-micro uppercase ${stat.textClass}`}>
                {key.toUpperCase()}
              </span>
              <span className="font-data text-micro text-text-secondary">
                {val ?? "—"}
              </span>
            </span>
          );
        })}
      </div>
    </motion.button>
  );
}
