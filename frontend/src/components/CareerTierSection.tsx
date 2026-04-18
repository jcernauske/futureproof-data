import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { springs, staggerItem } from "@/styles/motion";
import { CareerCard } from "@/components/CareerCard";
import type { CareerOutcome } from "@/types/build";

interface CareerTierSectionProps {
  id: string;
  label: string;
  description: string;
  careers: CareerOutcome[];
  selectedSoc: string | null;
  onSelect: (career: CareerOutcome) => void;
  /**
   * Primary card click — populate the lineage sheet with this career.
   * Distinct from ``onSelect`` which commits the pick to buildStore.
   */
  onExplore: (career: CareerOutcome) => void;
  /** All tiers expanded by default; student can collapse. */
  defaultExpanded?: boolean;
}

export function CareerTierSection({
  id,
  label,
  description,
  careers,
  selectedSoc,
  onSelect,
  onExplore,
  defaultExpanded = true,
}: CareerTierSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (careers.length === 0) return null;

  const contentId = `${id}-careers`;

  return (
    <section id={id} role="region" aria-label={`${label} career paths`}>
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={contentId}
        onClick={() => setExpanded((prev) => !prev)}
        className="w-full text-left mb-2 cursor-pointer group"
      >
        <div className="flex items-center gap-3">
          <motion.span
            aria-hidden="true"
            animate={{ rotate: expanded ? 90 : 0 }}
            transition={springs.snappy}
            className="font-data text-data text-text-muted group-hover:text-text-secondary transition-colors duration-normal"
          >
            ▸
          </motion.span>
          <h2 className="font-display font-semibold text-heading text-text-primary">
            {label}
          </h2>
          <span className="bg-bp-surface rounded-full px-2.5 py-0.5 font-data text-data-sm text-text-muted">
            ({careers.length} {careers.length === 1 ? "path" : "paths"})
          </span>
        </div>
        <p className="font-body text-small text-text-secondary mt-1 ml-7">
          {description}
        </p>
      </button>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={contentId}
            key="tier-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={springs.smooth}
            className="overflow-hidden"
          >
            <motion.div
              className="grid grid-cols-1 tablet:grid-cols-2 gap-3 pt-2"
              role="radiogroup"
              aria-label="Career path options"
              variants={{
                hidden: { opacity: 0 },
                visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
              }}
              initial="hidden"
              animate="visible"
            >
              {careers.map((career) => (
                <motion.div key={career.soc_code} variants={staggerItem}>
                  <CareerCard
                    career={career}
                    selected={selectedSoc === career.soc_code}
                    onSelect={() => onSelect(career)}
                    onExplore={() => onExplore(career)}
                  />
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
