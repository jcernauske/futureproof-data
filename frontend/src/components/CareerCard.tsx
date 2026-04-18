import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { CareerOutcome } from "@/types/build";
import { STAT_MAP, type StatKey } from "@/data/statExplanations";
import { socEmoji } from "@/data/socEmoji";

interface CareerCardProps {
  career: CareerOutcome;
  selected: boolean;
  /** Primary card click — opens lineage in the bottom sheet. */
  onExplore: () => void;
  /** Inline "Pick this path" action — commits this career to buildStore. */
  onSelect: () => void;
}

const STAT_ORDER: StatKey[] = ["ern", "roi", "res", "grw", "hmn"];

export function CareerCard({
  career,
  selected,
  onExplore,
  onSelect,
}: CareerCardProps) {
  const wage = career.median_annual_wage;

  function handleCardClick(event: React.MouseEvent<HTMLButtonElement>) {
    // Ignore clicks bubbling from the inner "Pick this path" button — it
    // fires onSelect directly and must NOT also populate the sheet.
    const target = event.target as HTMLElement | null;
    if (target?.closest?.("[data-pick-button]")) return;
    onExplore();
  }

  return (
    <motion.button
      id={`career-${career.soc_code}`}
      type="button"
      role="button"
      aria-label={`Explore lineage for ${career.occupation_title}`}
      aria-pressed={selected}
      onClick={handleCardClick}
      className={`w-full text-left rounded-xl p-6 border cursor-pointer transition-colors duration-normal ${
        selected
          ? "bg-bp-surface border-accent-thrive shadow-glow-thrive"
          : "bg-bp-mid border-border-subtle hover:bg-bp-surface hover:border-border hover:shadow-lg hover:-translate-y-0.5"
      }`}
      whileTap={{ scale: 0.98 }}
      animate={selected ? { scale: [1, 1.02, 1] } : {}}
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
          <h3 className="font-body font-bold text-body-lg text-text-primary">
            {career.occupation_title}
          </h3>
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

      <div className="mt-4 flex items-center justify-end">
        <span
          data-pick-button
          role="radio"
          aria-checked={selected}
          aria-label={career.occupation_title}
          tabIndex={0}
          onClick={(event) => {
            event.stopPropagation();
            onSelect();
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              event.stopPropagation();
              onSelect();
            }
          }}
          className={`inline-flex items-center gap-2 h-9 px-3 rounded-full border font-body text-small font-semibold cursor-pointer transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] ${
            selected
              ? "bg-accent-thrive/20 border-accent-thrive text-accent-thrive"
              : "bg-transparent border-border-default text-text-secondary hover:text-text-primary hover:border-border-strong"
          }`}
        >
          {selected ? "Picked ✓" : "Pick this path"}
        </span>
      </div>
    </motion.button>
  );
}
