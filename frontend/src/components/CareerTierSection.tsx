import { motion } from "framer-motion";
import { staggerItem } from "@/styles/motion";
import { CareerCard } from "@/components/CareerCard";
import type { CareerOutcome } from "@/types/build";

interface CareerTierSectionProps {
  id: string;
  label: string;
  description: string;
  careers: CareerOutcome[];
  selectedSoc: string | null;
  onSelect: (career: CareerOutcome) => void;
}

export function CareerTierSection({
  id,
  label,
  description,
  careers,
  selectedSoc,
  onSelect,
}: CareerTierSectionProps) {
  if (careers.length === 0) return null;

  return (
    <section id={id} role="region" aria-label={`${label} career paths`}>
      <div className="flex items-center gap-3 mb-2">
        <h2 className="font-display font-semibold text-heading text-text-primary">
          {label}
        </h2>
        <span className="bg-bp-surface rounded-full px-2.5 py-0.5 font-data text-data-sm text-text-muted">
          ({careers.length} {careers.length === 1 ? "path" : "paths"})
        </span>
      </div>
      <p className="font-body text-small text-text-secondary mb-4">
        {description}
      </p>
      <motion.div
        className="grid grid-cols-1 tablet:grid-cols-2 gap-3"
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
            />
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
