import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { CareerOutcome } from "@/types/build";
import type { StatKey } from "@/data/statExplanations";

interface CareerCardProps {
  career: CareerOutcome;
  selected: boolean;
  onSelect: () => void;
}

const STAT_KEYS: { key: StatKey; color: string }[] = [
  { key: "ern", color: "var(--color-stat-ern)" },
  { key: "roi", color: "var(--color-stat-roi)" },
  { key: "res", color: "var(--color-stat-res)" },
  { key: "grw", color: "var(--color-stat-grw)" },
  { key: "hmn", color: "var(--color-stat-hmn)" },
];

export function CareerCard({ career, selected, onSelect }: CareerCardProps) {
  const wage = career.median_annual_wage;

  return (
    <motion.button
      id={`career-${career.soc_code}`}
      role="radio"
      aria-checked={selected}
      aria-label={career.occupation_title}
      onClick={onSelect}
      className={`w-full text-left rounded-xl p-6 border cursor-pointer transition-colors duration-normal ${
        selected
          ? "bg-bp-surface border-accent-thrive shadow-glow-thrive"
          : "bg-bp-mid border-border-subtle hover:bg-bp-surface hover:border-border hover:shadow-lg hover:-translate-y-0.5"
      }`}
      whileTap={{ scale: 0.98 }}
      animate={selected ? { scale: [1, 1.02, 1] } : {}}
      transition={springs.snappy}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-body font-bold text-body-lg text-text-primary">
          {career.occupation_title}
        </h3>
      </div>

      {wage !== null && (
        <p className="font-data text-data text-stat-ern mt-1">
          ${wage.toLocaleString()}/yr median
        </p>
      )}

      <div className="flex flex-wrap gap-1.5 mt-3">
        {STAT_KEYS.map(({ key, color }) => {
          const val = career.stats[key];
          return (
            <span
              key={key}
              className="inline-flex items-center gap-1 bg-bp-surface rounded-sm px-2 py-0.5"
            >
              <span className="font-data text-micro uppercase" style={{ color }}>
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
