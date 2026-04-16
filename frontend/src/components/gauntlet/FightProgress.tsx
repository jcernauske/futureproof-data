import { motion } from "framer-motion";
import { BOSS_ORDER, BOSS_METADATA, RESULT_COLORS } from "@/data/bossMetadata";
import type { BossFightResult } from "@/types/build";

interface FightProgressProps {
  fights: BossFightResult[];
  currentFightIndex: number;
  isGauntletActive: boolean;
}

export function FightProgress({
  fights,
  currentFightIndex,
  isGauntletActive,
}: FightProgressProps) {
  return (
    <nav
      id="nav-fight-progress"
      aria-label={`Boss fight progress: ${currentFightIndex + 1} of 5`}
      className="flex items-center justify-center gap-2"
    >
      {BOSS_ORDER.map((bossId, i) => {
        const fight = fights.find((f) => f.boss === bossId);
        const isCurrent = isGauntletActive && i === currentFightIndex;
        const isResolved = i < currentFightIndex || !isGauntletActive;
        const resultColor =
          isResolved && fight
            ? `bg-${RESULT_COLORS[fight.result]}`
            : "bg-bp-surface";
        const bossMeta = BOSS_METADATA[bossId];

        return (
          <motion.div
            key={bossId}
            className={`w-3 h-3 rounded-full ${isCurrent ? "" : resultColor}`}
            style={
              isCurrent
                ? { backgroundColor: `var(--color-boss-${bossId})` }
                : undefined
            }
            animate={
              isCurrent
                ? { scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }
                : undefined
            }
            transition={
              isCurrent
                ? { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
                : undefined
            }
            aria-label={`${bossMeta.label}: ${isResolved && fight ? fight.result : isCurrent ? "current" : "upcoming"}`}
          />
        );
      })}
    </nav>
  );
}
