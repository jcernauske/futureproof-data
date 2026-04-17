import { motion } from "framer-motion";
import { staggerContainer, staggerItem, stagger } from "@/styles/motion";
import { SkillCard } from "./SkillCard";
import { Button } from "@/components/ui/Button";
import type { AppliedSkill, BossId } from "@/types/build";

interface RerollFlowProps {
  bossId: BossId;
  availableSkills: AppliedSkill[];
  selectedSkillIds: Set<string>;
  isRescoring: boolean;
  rerollCount?: number;
  maxRerolls?: number;
  onToggleSkill: (skillId: string) => void;
  onRescore: () => void;
  onAccept: () => void;
}

export function RerollFlow({
  bossId,
  availableSkills,
  selectedSkillIds,
  isRescoring,
  rerollCount = 0,
  maxRerolls = 3,
  onToggleSkill,
  onRescore,
  onAccept,
}: RerollFlowProps) {
  const hasSelection = selectedSkillIds.size > 0;
  const attemptNumber = rerollCount + 1;
  const attemptsLeft = maxRerolls - rerollCount;

  return (
    <motion.div
      className="bg-bp-mid border border-border-subtle rounded-xl p-6 mt-4"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.3 }}
    >
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-display font-semibold text-heading text-text-primary">
          Equip skills to fight again
        </h3>
        {maxRerolls > 0 && (
          <span
            className="font-data text-small text-text-muted whitespace-nowrap"
            aria-label={`Attempt ${attemptNumber} of ${maxRerolls}`}
          >
            Attempt {attemptNumber}/{maxRerolls}
          </span>
        )}
      </div>
      <p className="font-body text-small text-text-secondary mt-1">
        Pick skills that boost your stats, then rescore the fight.
        {attemptsLeft <= 1 && maxRerolls > 0 && (
          <span className="text-accent-alert"> Last attempt.</span>
        )}
      </p>

      <motion.div
        id={`group-skills-${bossId}`}
        role="group"
        aria-label={`Available skills for ${bossId}`}
        className="flex flex-col gap-3 mt-4"
        variants={staggerContainer(0.1, stagger.normal)}
        initial="hidden"
        animate="visible"
      >
        {availableSkills.map((skill) => (
          <motion.div key={skill.id} variants={staggerItem}>
            <SkillCard
              skill={skill}
              selected={selectedSkillIds.has(skill.id)}
              onToggle={() => onToggleSkill(skill.id)}
            />
          </motion.div>
        ))}
      </motion.div>

      <div className="flex items-center justify-between mt-6 gap-4">
        <Button
          id={`btn-accept-${bossId}`}
          variant="ghost"
          onClick={onAccept}
          aria-label="Accept result and continue"
        >
          Accept result
        </Button>
        <Button
          id={`btn-rescore-${bossId}`}
          variant="primary"
          disabled={!hasSelection}
          loading={isRescoring}
          onClick={onRescore}
          aria-label="Rescore fight with equipped skills"
        >
          {isRescoring ? "Rescoring..." : "Rescore Fight \u2726"}
          {hasSelection && !isRescoring && (
            <span className="ml-1.5 text-micro text-text-inverse/70">
              ({selectedSkillIds.size} equipped)
            </span>
          )}
        </Button>
      </div>
    </motion.div>
  );
}
