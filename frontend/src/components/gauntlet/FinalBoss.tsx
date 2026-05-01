import { motion } from "framer-motion";
import { bossFight, springs, staggerContainer, staggerItem, stagger } from "@/styles/motion";
import { BOSS_METADATA, BOSS_ORDER, getVerdictColor } from "@/data/bossMetadata";
import { Button } from "@/components/ui/Button";
import type { GauntletResult, AppliedSkill, BossOutcome } from "@/types/build";
import { useState } from "react";
import { useT } from "@/i18n/useT";

// `gauntlet.verdict` may be either:
//   - an i18n key emitted by the frontend reroll path (deriveVerdict in
//     GauntletScreen); or
//   - an English string emitted by the backend (boss_fights._final_verdict).
// When it's a key we translate; otherwise we display as-is so backend-
// originated English verdicts still render until the backend speaks keys.
function renderVerdict(verdict: string, t: (k: string) => string): string {
  if (verdict.startsWith("gauntlet.verdict.")) {
    const translated = t(verdict);
    // getString returns the raw key when the lookup fails — fall back to
    // a sensible English string in that case so we never show a key path.
    return translated === verdict ? "" : translated;
  }
  return verdict;
}

interface FinalBossProps {
  gauntlet: GauntletResult;
  skillsCrafted: AppliedSkill[];
  onNextSteps: () => void;
}

const RESULT_PILL: Record<BossOutcome, { label: string; cls: string }> = {
  win: { label: "WIN", cls: "bg-accent-thrive/20 text-accent-thrive" },
  lose: { label: "LOSE", cls: "bg-accent-alert/20 text-accent-alert" },
  draw: { label: "DRAW", cls: "bg-accent-caution/20 text-accent-caution" },
  unknown: { label: "N/A", cls: "bg-accent-info/20 text-accent-info" },
};

export function FinalBoss({ gauntlet, skillsCrafted, onNextSteps }: FinalBossProps) {
  const t = useT();
  const verdictText = renderVerdict(gauntlet.verdict, t);
  const verdictColor = getVerdictColor(verdictText || gauntlet.verdict);
  const [skillsExpanded, setSkillsExpanded] = useState(false);

  return (
    <motion.article
      id="region-final-boss"
      aria-label={`Fight the Future: ${verdictText || gauntlet.verdict}`}
      className="flex flex-col items-center text-center"
    >
      {/* Progress circles converge animation */}
      <motion.div
        className="flex items-center gap-2 mb-8"
        variants={staggerContainer(0, 0.1)}
        initial="hidden"
        animate="visible"
      >
        {BOSS_ORDER.map((bossId) => {
          const fight = gauntlet.fights.find((f) => f.boss === bossId);
          const result = fight?.result ?? "unknown";
          return (
            <motion.div
              key={bossId}
              className={`w-3 h-3 rounded-full bg-${result === "win" ? "accent-thrive" : result === "lose" ? "accent-alert" : result === "draw" ? "accent-caution" : "accent-info"}`}
              variants={staggerItem}
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ delay: 0.5, duration: 0.4 }}
            />
          );
        })}
      </motion.div>

      {/* Final Boss emoji with cycling glow */}
      <motion.div
        className="relative text-[100px] leading-none"
        {...bossFight.bossEntrance}
      >
        <div
          className="absolute inset-0 w-48 h-48 rounded-full blur-3xl opacity-20 -z-10 -translate-x-1/4 -translate-y-1/4"
          style={{
            background:
              "conic-gradient(var(--color-boss-ai), var(--color-boss-loans), var(--color-boss-market), var(--color-boss-burnout), var(--color-boss-ceiling), var(--color-boss-ai))",
            animation: "spin 8s linear infinite",
          }}
        />
        {"\u2694\uFE0F"}
      </motion.div>

      {/* Boss name */}
      <motion.h2
        className="font-display font-bold text-display text-text-primary mt-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.3 }}
      >
        Fight the Future
      </motion.h2>

      {/* Verdict */}
      <motion.p
        className={`font-display font-semibold text-heading ${verdictColor} mt-4`}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.smooth, delay: 0.7 }}
      >
        {verdictText || gauntlet.verdict}
      </motion.p>

      {/* Scorecard */}
      <motion.div
        id="region-scorecard"
        role="list"
        aria-label="Boss fight scorecard"
        className="grid grid-cols-2 tablet:grid-cols-5 gap-3 mt-8 w-full max-w-lg"
        variants={staggerContainer(1, stagger.normal)}
        initial="hidden"
        animate="visible"
      >
        {BOSS_ORDER.map((bossId) => {
          const fight = gauntlet.fights.find((f) => f.boss === bossId);
          const boss = BOSS_METADATA[bossId];
          const result = fight?.result ?? "unknown";
          const pill = RESULT_PILL[result];

          return (
            <motion.div
              key={bossId}
              role="listitem"
              className="flex flex-col items-center gap-1.5 p-3 rounded-lg"
              style={{ backgroundColor: boss.bgWash }}
              variants={staggerItem}
            >
              <span className="text-[24px]">{boss.emoji}</span>
              <span className="font-body font-semibold text-small text-text-primary">
                {boss.label.replace("Fight ", "")}
              </span>
              <span
                className={`px-2 py-0.5 rounded-full font-data text-data-sm ${pill.cls}`}
              >
                {pill.label}
              </span>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Tally */}
      <motion.p
        className="font-data font-bold text-data text-text-secondary mt-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
      >
        {gauntlet.wins} win{gauntlet.wins !== 1 ? "s" : ""} {"\u00B7"}{" "}
        {gauntlet.draws} draw{gauntlet.draws !== 1 ? "s" : ""} {"\u00B7"}{" "}
        {gauntlet.losses} loss{gauntlet.losses !== 1 ? "es" : ""}
      </motion.p>

      {/* Skills crafted summary */}
      {skillsCrafted.length > 0 && (
        <motion.div
          className="mt-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.8 }}
        >
          <button
            onClick={() => setSkillsExpanded(!skillsExpanded)}
            className="font-body text-small text-text-secondary hover:text-text-primary cursor-pointer transition-colors duration-normal"
          >
            Skills equipped: {skillsCrafted.length}{" "}
            {skillsExpanded ? "\u25B2" : "\u25BC"}
          </button>
          {skillsExpanded && (
            <div className="mt-2 space-y-2">
              {skillsCrafted.map((skill) => (
                <div
                  key={skill.id}
                  className="text-left bg-bp-surface rounded-lg p-3"
                >
                  <span className="font-body font-semibold text-small text-text-primary">
                    {skill.title}
                  </span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}

      {/* CTA */}
      <motion.div
        className="mt-10"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.smooth, delay: 2 }}
      >
        <Button
          id="btn-next-steps"
          variant="primary"
          onClick={onNextSteps}
          aria-label="Generate your next steps"
        >
          Your Next Steps {"\u2726"}
        </Button>
      </motion.div>
    </motion.article>
  );
}
