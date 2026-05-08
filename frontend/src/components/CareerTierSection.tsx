import { motion } from "framer-motion";
import { staggerItem } from "@/styles/motion";
import { CareerCard } from "@/components/CareerCard";
import type { CareerOutcome } from "@/types/build";

type TierAccent = "common" | "uncommon" | "postgrad";

const TIER_STYLES: Record<TierAccent, string> = {
  common: "text-accent-thrive",
  uncommon: "text-accent-info",
  postgrad: "text-accent-caution",
};

interface CareerTierSectionProps {
  id: string;
  label: string;
  description: string;
  accent: TierAccent;
  careers: CareerOutcome[];
  pickedSoc: string | null;
  onSelect: (career: CareerOutcome) => void;
  ernShift?: number;
  onAskGemma?: (career: CareerOutcome) => void;
}

export function CareerTierSection({
  id,
  label,
  description,
  accent,
  careers,
  pickedSoc,
  onSelect,
  ernShift = 0,
  onAskGemma,
}: CareerTierSectionProps) {
  if (careers.length === 0) return null;

  return (
    <section id={id} role="region" aria-label={`${label} career paths`}>
      <div className="mb-3">
        <div className="flex items-center gap-3">
          <h2
            className={`font-display font-semibold text-subheading ${TIER_STYLES[accent]}`}
          >
            {label}
          </h2>
          <span className="bg-bp-surface rounded-full px-2.5 py-0.5 font-data text-data-sm text-text-muted">
            {careers.length} {careers.length === 1 ? "path" : "paths"}
          </span>
        </div>
        <p className="font-body text-small text-text-secondary mt-1">
          {description}
        </p>
      </div>
      <motion.div
        className="grid grid-cols-1 tablet:grid-cols-2 desktop:grid-cols-3 gap-3"
        variants={{
          hidden: { opacity: 0 },
          visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
        }}
        initial="hidden"
        animate="visible"
      >
        {careers.map((career) => (
          <motion.div key={career.soc_code} variants={staggerItem} className="h-full">
            <CareerCard
              career={career}
              picked={pickedSoc === career.soc_code}
              onSelect={() => onSelect(career)}
              ernShift={ernShift}
              onAskGemma={onAskGemma}
            />
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
