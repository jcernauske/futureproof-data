import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { bossFight, springs, transitions } from "@/styles/motion";
import { BOSS_METADATA } from "@/data/bossMetadata";
import { ReceiptPanel } from "@/components/ReceiptPanel";
import { RerollFlow } from "./RerollFlow";
import { StructuralLoss } from "./StructuralLoss";
import { Button } from "@/components/ui/Button";
import type { BossFightResult, AppliedSkill, BossOutcome } from "@/types/build";
import type { FightPhase } from "@/store/gauntletStore";

interface BossFightCardProps {
  fight: BossFightResult;
  fightPhase: FightPhase;
  availableSkills: AppliedSkill[];
  selectedSkillIds: Set<string>;
  isRescoring: boolean;
  isLastFight: boolean;
  onPhaseChange: (phase: FightPhase) => void;
  onToggleSkill: (skillId: string) => void;
  onRescore: () => void;
  onAccept: () => void;
  onAdvance: () => void;
}

const RESULT_CONFIG: Record<
  BossOutcome,
  { label: string; pillClass: string }
> = {
  win: {
    label: "WIN \u2726",
    pillClass: "bg-accent-thrive/20 text-accent-thrive border-accent-thrive/30",
  },
  lose: {
    label: "LOSS",
    pillClass: "bg-accent-alert/20 text-accent-alert border-accent-alert/30",
  },
  draw: {
    label: "DRAW",
    pillClass: "bg-accent-caution/20 text-accent-caution border-accent-caution/30",
  },
  unknown: {
    label: "NO DATA",
    pillClass: "bg-accent-info/20 text-accent-info border-accent-info/30",
  },
};

export function BossFightCard({
  fight,
  fightPhase,
  availableSkills,
  selectedSkillIds,
  isRescoring,
  isLastFight,
  onPhaseChange,
  onToggleSkill,
  onRescore,
  onAccept,
  onAdvance,
}: BossFightCardProps) {
  const boss = BOSS_METADATA[fight.boss];
  const resultConfig = RESULT_CONFIG[fight.result];
  const [showResult, setShowResult] = useState(false);
  const [showNarrative, setShowNarrative] = useState(false);
  const [prevResult, setPrevResult] = useState<BossOutcome | null>(null);
  const [scoreImproved, setScoreImproved] = useState(false);

  // Reset local state when fight changes (guard against stale state if not unmounted)
  useEffect(() => {
    setShowResult(false);
    setShowNarrative(false);
    setPrevResult(null);
    setScoreImproved(false);
  }, [fight.boss]);

  // Entrance → result reveal timing
  useEffect(() => {
    if (fightPhase === "entrance") {
      const resultTimer = setTimeout(() => {
        setShowResult(true);
        onPhaseChange("result");
      }, 1300);
      return () => clearTimeout(resultTimer);
    }
  }, [fightPhase, onPhaseChange]);

  // Show narrative after result
  useEffect(() => {
    if (showResult) {
      const narrativeTimer = setTimeout(() => setShowNarrative(true), 400);
      return () => clearTimeout(narrativeTimer);
    }
  }, [showResult]);

  // Detect result changes from reroll
  useEffect(() => {
    if (fight.rerolled && fight.original_result) {
      if (fight.result !== fight.original_result) {
        setPrevResult(fight.original_result);
        setScoreImproved(true);
        const timer = setTimeout(() => setScoreImproved(false), 2000);
        return () => clearTimeout(timer);
      }
    }
  }, [fight.result, fight.rerolled, fight.original_result]);

  const canReroll =
    (fight.result === "lose" || fight.result === "draw") &&
    fightPhase === "result";
  const showReroll = fightPhase === "reroll";
  const showStructuralLoss = fightPhase === "structural_loss";
  const showAdvance =
    fightPhase === "resolved" ||
    fight.result === "win" ||
    fight.result === "unknown";

  // Auto-transition to reroll or resolved based on result
  useEffect(() => {
    if (fightPhase !== "result") return;
    if (fight.result === "win" || fight.result === "unknown") {
      const timer = setTimeout(() => onPhaseChange("resolved"), 800);
      return () => clearTimeout(timer);
    }
  }, [fightPhase, fight.result, onPhaseChange]);

  return (
    <motion.article
      id={`region-fight-${fight.boss}`}
      aria-label={`${boss.label}: ${fight.result}`}
      className="relative flex flex-col items-center"
    >
      {/* Vignette overlay */}
      <motion.div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background: `radial-gradient(circle at center, transparent 30%, rgba(18, 19, 31, 0.7) 100%)`,
        }}
        {...bossFight.vignette}
      />

      {/* Boss entrance */}
      <div className="relative z-10 flex flex-col items-center text-center">
        {/* Ambient glow */}
        <div
          className="absolute w-40 h-40 rounded-full blur-3xl opacity-15 -z-10"
          style={{
            backgroundColor: `var(--color-boss-${fight.boss})`,
            animation: "pulse 4s ease-in-out infinite",
          }}
        />

        {/* Boss emoji */}
        <motion.div
          className="text-[80px] leading-none"
          {...bossFight.bossEntrance}
        >
          {boss.emoji}
        </motion.div>

        {/* Boss name */}
        <motion.h2
          className={`font-display font-bold text-display ${boss.colorToken} mt-4`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.3 }}
        >
          {boss.label}
        </motion.h2>

        {/* Boss subtitle */}
        <motion.p
          className="font-body text-body text-text-secondary mt-2 max-w-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.3 }}
        >
          {boss.subtitle}
        </motion.p>

        {/* Result reveal */}
        <AnimatePresence mode="wait">
          {showResult && (
            <motion.div className="mt-6 flex flex-col items-center" key={`result-${fight.result}`}>
              {/* Win burst animation on emoji */}
              {fight.result === "win" && (
                <motion.div
                  className="absolute top-0"
                  animate={{ scale: [1, 1.15, 1], opacity: [1, 0.8, 1] }}
                  transition={bossFight.winBurst.transition}
                />
              )}

              {/* Lose shake on card */}
              {fight.result === "lose" && !fight.rerolled && (
                <motion.div
                  animate={{ x: [0, -3, 3, -3, 3, 0] }}
                  transition={bossFight.loseShake.transition}
                />
              )}

              {/* Result pill */}
              <motion.span
                id={`badge-result-${fight.boss}`}
                role="status"
                aria-label={`${fight.result} \u2014 score ${fight.raw_score}`}
                className={`inline-block px-4 py-1.5 rounded-full font-data font-bold text-data-sm border ${resultConfig.pillClass}`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={springs.bouncy}
              >
                {resultConfig.label}
              </motion.span>

              {/* Score improvement indicator */}
              {scoreImproved && prevResult && (
                <motion.span
                  className="font-data text-data-sm text-accent-thrive mt-2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  {"\u2191"} {prevResult.toUpperCase()} {"\u2192"}{" "}
                  {fight.result.toUpperCase()}
                </motion.span>
              )}

              {/* Score context */}
              <motion.div
                className="flex items-center gap-2 mt-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                <span className="font-data text-data-sm text-text-muted">
                  Score: {fight.raw_score ?? "N/A"} (win {"\u2265"}{" "}
                  {fight.threshold_win}, draw {"\u2265"} {fight.threshold_draw})
                </span>
                <ReceiptPanel
                  id={`fight-${fight.boss}`}
                  label={boss.label}
                >
                  <div className="space-y-1">
                    <div>Raw score: {fight.raw_score ?? "N/A"}</div>
                    <div>Win threshold: {"\u2265"} {fight.threshold_win}</div>
                    <div>Draw threshold: {"\u2265"} {fight.threshold_draw}</div>
                    <div>Reason: {fight.reason}</div>
                    {fight.rerolled && (
                      <>
                        <div>Original result: {fight.original_result}</div>
                        <div>Original score: {fight.original_raw_score}</div>
                        <div>Reroll count: {fight.reroll_count}</div>
                      </>
                    )}
                  </div>
                </ReceiptPanel>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Coaching narrative */}
        <AnimatePresence>
          {showNarrative && (
            <motion.div
              id={`region-narrative-${fight.boss}`}
              role="article"
              aria-label={`Coach's analysis of ${boss.label}`}
              className="mt-6 bg-bp-mid border border-border-subtle rounded-lg p-4 max-w-md text-left"
              style={{ borderLeftWidth: "3px", borderLeftColor: `var(--color-boss-${fight.boss})` }}
              {...transitions.fadeInUp}
              transition={{ ...springs.smooth, delay: 0.3 }}
            >
              <p className="font-body text-body text-text-primary leading-relaxed">
                {fight.narrative}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Reroll CTA for loss/draw */}
        {canReroll && showNarrative && !showReroll && !showStructuralLoss && (
          <motion.div
            className="mt-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            <Button
              variant="secondary"
              onClick={() => onPhaseChange("reroll")}
            >
              Equip skills to fight again
            </Button>
          </motion.div>
        )}

        {/* Reroll flow */}
        <AnimatePresence>
          {showReroll && (
            <div className="w-full max-w-md mt-4">
              <RerollFlow
                bossId={fight.boss}
                availableSkills={availableSkills}
                selectedSkillIds={selectedSkillIds}
                isRescoring={isRescoring}
                onToggleSkill={onToggleSkill}
                onRescore={onRescore}
                onAccept={onAccept}
              />
            </div>
          )}
        </AnimatePresence>

        {/* Structural loss */}
        <AnimatePresence>
          {showStructuralLoss && (
            <div className="w-full max-w-md mt-4">
              <StructuralLoss bossId={fight.boss} onContinue={onAdvance} />
            </div>
          )}
        </AnimatePresence>

        {/* Advance button */}
        {showAdvance && fightPhase === "resolved" && (
          <motion.div
            className="mt-8"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Button variant="primary" id="btn-next-fight" onClick={onAdvance}>
              {isLastFight ? "See the Verdict \u2192" : "Next Fight \u2192"}
            </Button>
          </motion.div>
        )}
      </div>
    </motion.article>
  );
}
