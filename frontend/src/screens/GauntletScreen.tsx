import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useBuildStore } from "@/store/buildStore";
import { useGauntletStore } from "@/store/gauntletStore";
import { useProfileStore } from "@/store/profileStore";
import { BOSS_ORDER } from "@/data/bossMetadata";
import { rerollFight, getNextSteps } from "@/api/gauntlet";
import { GauntletIntro } from "@/components/gauntlet/GauntletIntro";
import { BossFightCard } from "@/components/gauntlet/BossFightCard";
import { FightProgress } from "@/components/gauntlet/FightProgress";
import { FinalBoss } from "@/components/gauntlet/FinalBoss";
import { NextSteps } from "@/components/gauntlet/NextSteps";
import type { Build, BossFightResult, BossId, AppliedSkill } from "@/types/build";
import type { FightPhase } from "@/store/gauntletStore";

// Defense-in-depth client-side cap. Backend should also enforce.
// A student who rerolls this many times and still isn't winning has a
// structural gap, not a tactical one — the gauntlet surfaces that.
const MAX_REROLLS = 3;

function deriveVerdict(
  wins: number,
  losses: number,
  draws: number,
  _unknown: number,
): string {
  const scored = wins + losses + draws;
  if (scored === 0) return "Insufficient data to score the gauntlet.";
  if (losses === 0 && wins >= 3)
    return "DOMINANT BUILD \u2014 strong across the board.";
  if (wins > losses) {
    if (losses === 0) return "SOLID BUILD with minor soft spots.";
    return "SOLID BUILD with a gap.";
  }
  if (wins === losses)
    return "MIXED BUILD \u2014 wins and losses cancel out; play to strengths.";
  return "VULNERABLE BUILD \u2014 losses outweigh wins; active mitigation required.";
}

function applyRerollResult(
  build: Build,
  bossId: BossId,
  newFight: BossFightResult,
  craftedSkillIds: string[],
): Build {
  const updatedFights = build.gauntlet.fights.map((f) =>
    f.boss === bossId ? newFight : f,
  );

  const craftedSkills = build.skill_pool.filter((s) =>
    craftedSkillIds.includes(s.id),
  );
  const remainingPool = build.skill_pool.filter(
    (s) => !craftedSkillIds.includes(s.id),
  );

  const wins = updatedFights.filter((f) => f.result === "win").length;
  const losses = updatedFights.filter((f) => f.result === "lose").length;
  const draws = updatedFights.filter((f) => f.result === "draw").length;
  const unknown = updatedFights.filter((f) => f.result === "unknown").length;

  return {
    ...build,
    gauntlet: {
      ...build.gauntlet,
      fights: updatedFights,
      wins,
      losses,
      draws,
      unknown,
      verdict: deriveVerdict(wins, losses, draws, unknown),
    },
    skill_pool: remainingPool,
    skills_crafted: [...build.skills_crafted, ...craftedSkills],
  };
}

function getAvailableSkills(
  skillPool: AppliedSkill[],
  skillsCrafted: AppliedSkill[],
  bossId: BossId,
): AppliedSkill[] {
  const craftedIds = new Set(skillsCrafted.map((s) => s.id));
  return skillPool.filter(
    (s) => s.targets.includes(bossId) && !craftedIds.has(s.id),
  );
}

export function GauntletScreen() {
  const navigate = useNavigate();
  const { build, setBuild } = useBuildStore();
  const { animalEmoji } = useProfileStore();
  const {
    phase,
    currentFightIndex,
    fightPhase,
    selectedSkillIds,
    isRescoring,
    nextStepsContent,
    nextStepsError,
    setPhase,
    setFightPhase,
    advanceFight,
    toggleSkill,
    clearSelectedSkills,
    setIsRescoring,
    setNextStepsContent,
    setNextStepsError,
    resetGauntlet,
  } = useGauntletStore();

  // Nav guard
  useEffect(() => {
    if (!build?.gauntlet?.fights?.length) {
      navigate("/reveal", { replace: true });
    }
  }, [build, navigate]);

  // Reset gauntlet state on mount
  useEffect(() => {
    resetGauntlet();
  }, [resetGauntlet]);

  if (!build) return null;

  const currentBossId = BOSS_ORDER[currentFightIndex];
  const currentFight = build.gauntlet.fights.find(
    (f) => f.boss === currentBossId,
  );
  const availableSkills = currentBossId
    ? getAvailableSkills(build.skill_pool, build.skills_crafted, currentBossId)
    : [];

  const handleIntroComplete = useCallback(() => {
    setPhase("fighting");
    setFightPhase("entrance");
  }, [setPhase, setFightPhase]);

  const handlePhaseChange = useCallback(
    (newPhase: FightPhase) => {
      setFightPhase(newPhase);
    },
    [setFightPhase],
  );

  const [rescoreError, setRescoreError] = useState<string | null>(null);

  const handleRescore = useCallback(async () => {
    // Double-click guard: check isRescoring from Zustand's getState, not render state
    if (useGauntletStore.getState().isRescoring) return;
    if (!currentBossId) return;

    // Read build from store at call time, not from render closure
    const currentBuild = useBuildStore.getState().build;
    if (!currentBuild) return;

    // Cap rerolls per-fight — after MAX_REROLLS failed attempts the gap
    // is structural, not tactical. Route to the structural_loss screen.
    const existingFight = currentBuild.gauntlet.fights.find(
      (f) => f.boss === currentBossId,
    );
    if ((existingFight?.reroll_count ?? 0) >= MAX_REROLLS) {
      setFightPhase("structural_loss");
      return;
    }

    setRescoreError(null);
    setIsRescoring(true);
    try {
      const skillIds = Array.from(useGauntletStore.getState().selectedSkillIds);

      const newFight = await rerollFight(
        currentBuild.build_id,
        currentBossId,
        skillIds,
      );
      const updatedBuild = applyRerollResult(
        currentBuild,
        currentBossId,
        newFight,
        skillIds,
      );
      setBuild(updatedBuild);
      clearSelectedSkills();

      // Check if more skills available or structural loss
      const remainingSkills = getAvailableSkills(
        updatedBuild.skill_pool,
        updatedBuild.skills_crafted,
        currentBossId,
      );

      if (
        (newFight.result === "lose" || newFight.result === "draw") &&
        remainingSkills.length === 0
      ) {
        setFightPhase("structural_loss");
      } else if (newFight.result === "win") {
        setFightPhase("resolved");
      } else {
        // Stay in reroll — can try again with remaining skills
        setFightPhase("reroll");
      }
    } catch (err) {
      setRescoreError(
        err instanceof Error ? err.message : "Rescore failed. Try again.",
      );
    } finally {
      setIsRescoring(false);
    }
  }, [
    currentBossId,
    setBuild,
    clearSelectedSkills,
    setIsRescoring,
    setFightPhase,
  ]);

  const handleAccept = useCallback(() => {
    setFightPhase("resolved");
    clearSelectedSkills();
  }, [setFightPhase, clearSelectedSkills]);

  const handleAdvance = useCallback(() => {
    advanceFight();
  }, [advanceFight]);

  const handleNextSteps = useCallback(async () => {
    setPhase("next_steps_loading");
    try {
      const content = await getNextSteps(build.build_id);
      setNextStepsContent(content);
      setPhase("next_steps");
    } catch {
      setNextStepsError(true);
      setPhase("next_steps");
    }
  }, [build.build_id, setPhase, setNextStepsContent, setNextStepsError]);

  const handleBranches = useCallback(() => {
    navigate("/branches");
  }, [navigate]);

  const handleSave = useCallback(() => {
    navigate("/save");
  }, [navigate]);

  const handleBackToBuild = useCallback(() => {
    navigate("/reveal");
  }, [navigate]);

  return (
    <div className="min-h-screen bg-bp-void pt-14">
      <div className="max-w-[640px] mx-auto px-6 py-8">
        {/* Fight progress — shown during fighting and final_boss */}
        {(phase === "fighting" || phase === "final_boss") && (
          <div className="mb-8">
            <FightProgress
              fights={build.gauntlet.fights}
              currentFightIndex={currentFightIndex}
              isGauntletActive={phase === "fighting"}
            />
          </div>
        )}

        <AnimatePresence mode="wait">
          {/* Intro */}
          {phase === "intro" && (
            <motion.div
              key="intro"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <GauntletIntro onComplete={handleIntroComplete} />
            </motion.div>
          )}

          {/* Fighting */}
          {phase === "fighting" && currentFight && (
            <motion.div
              key={`fight-${currentBossId}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <BossFightCard
                fight={currentFight}
                fightPhase={fightPhase}
                availableSkills={availableSkills}
                selectedSkillIds={selectedSkillIds}
                isRescoring={isRescoring}
                isLastFight={currentFightIndex === 4}
                rerollCount={currentFight.reroll_count}
                maxRerolls={MAX_REROLLS}
                onPhaseChange={handlePhaseChange}
                onToggleSkill={toggleSkill}
                onRescore={handleRescore}
                onAccept={handleAccept}
                onAdvance={handleAdvance}
              />
              {rescoreError && (
                <p className="mt-3 text-center font-body text-small text-accent-alert">
                  {rescoreError}
                </p>
              )}
            </motion.div>
          )}

          {/* Final Boss */}
          {phase === "final_boss" && (
            <motion.div
              key="final-boss"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <FinalBoss
                gauntlet={build.gauntlet}
                skillsCrafted={build.skills_crafted}
                onNextSteps={handleNextSteps}
              />
            </motion.div>
          )}

          {/* Next Steps (loading + content + error) */}
          {(phase === "next_steps_loading" || phase === "next_steps") && (
            <motion.div
              key="next-steps"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <NextSteps
                content={nextStepsContent}
                error={nextStepsError}
                loading={phase === "next_steps_loading"}
                profileEmoji={animalEmoji ?? ""}
                onRetry={handleNextSteps}
                onBranches={handleBranches}
                onSave={handleSave}
                onBackToBuild={handleBackToBuild}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
