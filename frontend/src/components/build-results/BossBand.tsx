import { useState, useCallback, useRef, useEffect } from "react";
import type { BossFightResult, AppliedSkill, BossOutcome, BossId } from "@/types/build";
import { rerollFight, getFightWrapup } from "@/api/gauntlet";
import { Button } from "@/components/ui/Button";
import { BOSS_META, RESULT_COLORS } from "./bossData";
import { SealedOverlay } from "./SealedOverlay";
import { VSOverlay } from "./VSOverlay";
import { SkillStatBadge } from "./SkillStatBadge";
import { NarrativeTimeline } from "./NarrativeTimeline";
import type { NarrativeEntry } from "./NarrativeTimeline";
import { useT } from "@/i18n/useT";
import { useProfileStore } from "@/store/profileStore";
import { localizeProfileName } from "@/i18n/profileName";

const MAX_REROLLS = 3;
const RESULT_WORD_KEYS: Record<BossOutcome, string> = {
  win: "build.resultVictory",
  lose: "build.resultDefeated",
  draw: "build.resultStandoff",
  unknown: "build.resultUnknown",
};
const RESULT_FLAVOR_KEYS: Record<BossOutcome, string> = {
  win: "build.flavorWin",
  lose: "build.flavorLose",
  draw: "build.flavorDraw",
  unknown: "",
};

// Voice-contract-clean i18n keys for the per-boss "Ask why" button.
// See docs/specs/feature-ask-gemma.md §3 entry point #2.
const ASK_BOSS_LABEL_KEYS: Record<BossOutcome, string> = {
  win: "boss.askWhy.passed",
  lose: "boss.askWhy.didntPass",
  draw: "boss.askWhy.borderline",
  unknown: "boss.askWhy.borderline",
};
const ASK_BOSS_ARIA_KEYS: Record<BossOutcome, string> = {
  win: "boss.askWhy.aria.passed",
  lose: "boss.askWhy.aria.didntPass",
  draw: "boss.askWhy.aria.borderline",
  unknown: "boss.askWhy.aria.borderline",
};
// Result-aware border tint (8% alpha — reads as warmth, not signal).
// Uses the existing --shadow-glow-* RGB triplets from DESIGN.md.
const RESULT_BORDER_TINT: Record<BossOutcome, string> = {
  win: "rgba(125, 212, 163, 0.08)",
  lose: "rgba(244, 169, 126, 0.08)",
  draw: "rgba(242, 212, 119, 0.08)",
  unknown: "rgba(255, 255, 255, 0.08)",
};

interface BossBandProps {
  fight: BossFightResult;
  buildId: string;
  playerEmoji: string;
  playerName: string;
  skillPool: AppliedSkill[];
  onRerollComplete: (updatedFight: BossFightResult) => void;
  onSkillsConsumed: (usedSkillIds: string[]) => void;
  isRevealed: boolean;
  isSealed: boolean;
  isVsActive: boolean;
  isVsDone: boolean;
  isSealedVisible: boolean;
  onReveal?: () => void;
  /** When set, renders the per-boss "Ask why" button in the result
   * column and the per-skill ask icon-buttons in the reroll grid. */
  onAskBoss?: (bossId: BossId) => void;
  onAskSkill?: (skillId: string) => void;
  /** When the chat is already open, ask buttons are disabled
   * (opacity reduced) to prevent double-fire. */
  chatOpen?: boolean;
}

const STAT_DELTAS: { key: string; field: keyof AppliedSkill; signMultiplier?: number }[] = [
  { key: "ern", field: "delta_ern" },
  { key: "roi", field: "delta_roi" },
  { key: "res", field: "delta_res" },
  { key: "grw", field: "delta_grw" },
  { key: "hmn", field: "delta_hmn" },
  { key: "brn", field: "delta_burnout_raw", signMultiplier: -1 },
  { key: "ceil", field: "delta_ceiling_raw" },
];

export function BossBand({
  fight,
  buildId,
  playerEmoji,
  playerName,
  skillPool,
  onRerollComplete,
  onSkillsConsumed,
  isRevealed,
  isSealed,
  isVsActive,
  isVsDone,
  isSealedVisible,
  onReveal,
  onAskBoss,
  onAskSkill,
  chatOpen = false,
}: BossBandProps) {
  const t = useT();
  const locale = useProfileStore((s) => s.locale);
  const localizedPlayerName = localizeProfileName(playerName, locale);
  const boss = BOSS_META[fight.boss];
  const localizedBossName = t(boss.shortNameKey);
  const [localResult, setLocalResult] = useState<BossOutcome>(fight.result);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());
  const [isRescoring, setIsRescoring] = useState(false);
  const [rescored, setRescored] = useState(fight.rerolled);
  const [rerollCount, setRerollCount] = useState(fight.reroll_count);
  const [showReroll, setShowReroll] = useState(true);
  const [rerollError, setRerollError] = useState<string | null>(null);
  const bandRef = useRef<HTMLDivElement>(null);

  const [narrativeEntries, setNarrativeEntries] = useState<NarrativeEntry[]>([
    {
      id: `${fight.boss}-initial`,
      trigger: "initial",
      narrative: fight.narrative,
      result: fight.result,
    },
  ]);

  const availableSkills = skillPool.filter((s) => s.targets.includes(fight.boss));
  const canReroll = localResult !== "win" && availableSkills.length > 0 && rerollCount < MAX_REROLLS;
  const resultColors = RESULT_COLORS[localResult] ?? RESULT_COLORS.unknown;
  const firstName = localizedPlayerName.split(" ")[0] ?? localizedPlayerName;

  // Only reset when a completely different fight mounts (boss change),
  // NOT when the parent updates fight props from a reroll — we manage
  // our own accumulated state after that.
  useEffect(() => {
    setLocalResult(fight.result);
    setNarrativeEntries([
      {
        id: `${fight.boss}-initial`,
        trigger: "initial",
        narrative: fight.narrative,
        result: fight.result,
      },
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fight.boss]);

  // Pick up streaming narrative when it arrives (empty → non-empty).
  // Only fires when the initial entry has no narrative and no rerolls
  // have happened, so it's safe against reroll state.
  useEffect(() => {
    if (!fight.narrative) return;
    setNarrativeEntries((prev) => {
      const first = prev[0];
      if (prev.length !== 1 || !first || first.narrative) return prev;
      return [{
        id: first.id,
        trigger: first.trigger,
        narrative: fight.narrative,
        result: first.result,
        previousResult: first.previousResult,
      }];
    });
  }, [fight.narrative, fight.boss]);

  const toggleSkill = useCallback((skillId: string) => {
    setSelectedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skillId)) next.delete(skillId);
      else next.add(skillId);
      return next;
    });
  }, []);

  const handleRescore = useCallback(async () => {
    if (selectedSkills.size === 0 || isRescoring) return;
    setIsRescoring(true);
    setRerollError(null);

    const prevResult = localResult;

    try {
      const skillIds = Array.from(selectedSkills);
      const selectedSkillNames = skillIds
        .map((id) => skillPool.find((s) => s.id === id)?.title)
        .filter(Boolean)
        .join(" + ");

      const selectedSkillObjects = skillIds
        .map((id) => skillPool.find((s) => s.id === id))
        .filter(Boolean) as AppliedSkill[];
      const aggregatedDeltas = STAT_DELTAS
        .map(({ key, field, signMultiplier }) => ({
          stat: key,
          delta: selectedSkillObjects.reduce((sum, s) => sum + (s[field] as number), 0) * (signMultiplier ?? 1),
        }))
        .filter((d) => d.delta !== 0);

      const updated = await rerollFight(buildId, fight.boss, skillIds);

      const skillEntry: NarrativeEntry = {
        id: `${fight.boss}-reroll-${updated.reroll_count}`,
        trigger: "skill",
        skillName: selectedSkillNames,
        skillDeltas: aggregatedDeltas,
        narrative: updated.narrative,
        result: updated.result,
        previousResult: prevResult,
      };

      setLocalResult(updated.result);
      setRerollCount(updated.reroll_count);

      const remainingSkills = availableSkills.filter(
        (s) => !skillIds.includes(s.id),
      );
      const noMoreSkills = remainingSkills.length === 0;
      const maxedRerolls = updated.reroll_count >= MAX_REROLLS;
      const isWon = updated.result === "win";
      const shouldWrapup = noMoreSkills || maxedRerolls || isWon;

      if (shouldWrapup) {
        setNarrativeEntries((prev) => [...prev, skillEntry]);
        setIsRescoring(false);

        // Collect all skill titles and narratives for the wrapup
        const allEntries = [...narrativeEntries, skillEntry];
        const allSkillTitles = allEntries
          .filter((e) => e.trigger === "skill" && e.skillName)
          .map((e) => e.skillName!);
        const allNarratives = allEntries.map((e) => e.narrative);

        setIsRescoring(true);
        try {
          const wrapupNarrative = await getFightWrapup(
            buildId,
            fight.boss,
            allSkillTitles,
            allNarratives,
          );
          if (wrapupNarrative) {
            const wrapupEntry: NarrativeEntry = {
              id: `${fight.boss}-wrapup`,
              trigger: "wrapup",
              narrative: wrapupNarrative,
              result: updated.result,
              previousResult: narrativeEntries[0]?.result,
            };
            setNarrativeEntries((prev) => [...prev, wrapupEntry]);
          }
        } catch {
          // Wrapup is optional — fail silently
        }
        setIsRescoring(false);

        if (isWon) {
          setRescored(true);
        }
        setShowReroll(false);
      } else {
        setNarrativeEntries((prev) => [...prev, skillEntry]);
      }

      onRerollComplete(updated);
      onSkillsConsumed(skillIds);
      setSelectedSkills(new Set());
    } catch (err) {
      setRerollError(err instanceof Error ? err.message : t("build.rescoreFailed"));
    } finally {
      setIsRescoring(false);
    }
  }, [selectedSkills, isRescoring, buildId, fight.boss, onRerollComplete, onSkillsConsumed, localResult, skillPool, availableSkills, narrativeEntries]);

  const handleAccept = useCallback(() => {
    setShowReroll(false);
  }, []);

  const resultColorCss =
    localResult === "win" ? "var(--color-accent-thrive)" :
    localResult === "lose" ? "var(--color-accent-alert)" :
    localResult === "draw" ? "var(--color-accent-caution)" :
    "var(--color-text-muted)";

  const resultAnimation =
    localResult === "win" ? "winPulse 0.6s ease-in-out" :
    localResult === "lose" ? "loseShake 0.4s ease-in-out" :
    localResult === "draw" ? "drawWobble 0.4s ease-in-out" :
    undefined;

  return (
    <div
      ref={bandRef}
      className="relative rounded-[20px] overflow-hidden bg-bp-mid"
      style={{
        padding: "24px",
        minHeight: 140,
        scrollSnapAlign: "center",
        border: isRevealed ? `1px solid ${resultColors.border}` : "1px solid rgba(255,255,255,0.06)",
        transition: "border-color 0.3s, box-shadow 0.3s",
      }}
      data-boss={fight.boss}
      data-result={localResult}
      data-rescored={rescored ? "true" : undefined}
      role="region"
      aria-label={`${localizedBossName}: ${t(RESULT_WORD_KEYS[localResult])}`}
    >
      {/* Dual edge stripes */}
      {isRevealed && (
        <>
          <div
            className="absolute left-0 top-0 bottom-0 rounded-l-[20px]"
            style={{
              width: 4,
              background: `linear-gradient(to bottom, ${boss.color} 0%, rgba(${localResult === "win" ? "125,212,163" : localResult === "lose" ? "244,169,126" : "242,212,119"},0.15) 100%)`,
              opacity: 1,
            }}
          />
          <div
            className="absolute right-0 top-0 bottom-0 rounded-r-[20px]"
            style={{
              width: 4,
              background: `linear-gradient(to bottom, ${resultColorCss} 0%, ${resultColorCss}22 100%)`,
              boxShadow: `inset 8px 0 24px ${resultColors.glow}`,
            }}
          />
        </>
      )}

      {/* Sealed overlay */}
      {isSealed && (
        <SealedOverlay
          bossId={fight.boss}
          isVisible={isSealedVisible}
          isTriggered={isVsActive || isVsDone}
          onReveal={onReveal}
        />
      )}

      {/* VS overlay */}
      <VSOverlay
        playerEmoji={playerEmoji}
        playerName={firstName}
        bossEmoji={boss.emoji}
        bossShortName={localizedBossName}
        bossId={fight.boss}
        isActive={isVsActive}
        isDone={isVsDone}
      />

      {/* Revealed content */}
      <div
        style={{
          opacity: isRevealed ? 1 : 0,
          transform: isRevealed ? "translateY(0)" : "translateY(12px)",
          transition: "opacity 0.4s ease-out, transform 0.4s ease-out",
        }}
      >
        {/* Boss header */}
        <div className="flex items-center gap-4 relative z-[1]">
          <div
            className="flex-shrink-0 rounded-[14px] flex items-center justify-center"
            style={{
              width: 64,
              height: 64,
              background: boss.gradient,
              border: `1px solid ${boss.color}`,
              boxShadow: `0 0 20px ${boss.color}33`,
            }}
          >
            <span style={{ fontSize: 36 }}>{boss.emoji}</span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="font-display font-semibold" style={{ fontSize: 20, color: boss.color }}>
              <bdi>{firstName}</bdi> {t("build.bossBand.vs")} <bdi>{localizedBossName}</bdi>
            </div>
            <div className="font-body text-text-muted" style={{ fontSize: 14, marginTop: 2 }}>
              {t(boss.subtitleKey)}
            </div>
            {canReroll && showReroll && (
              <span
                className="inline-block font-data font-bold rounded-full mt-2"
                style={{
                  fontSize: 11,
                  color: "var(--color-accent-thrive)",
                  background: "rgba(125,212,163,0.12)",
                  padding: "2px 10px",
                }}
              >
                {t("build.skillsAvailable").replace("{count}", String(availableSkills.length)).replace("{s}", availableSkills.length !== 1 ? "s" : "")}
              </span>
            )}
          </div>

          {/* Result zone */}
          <div className="flex-shrink-0 flex flex-col items-end gap-1.5 text-right">
            <div
              className="font-display font-bold uppercase"
              style={{
                fontSize: 22,
                letterSpacing: 1,
                color: resultColorCss,
                textShadow: `0 0 20px ${resultColors.glow}`,
                animation: isRevealed ? resultAnimation : undefined,
              }}
            >
              {t(RESULT_WORD_KEYS[localResult])}
            </div>
            <div className="font-body text-text-muted" style={{ fontSize: 12, marginTop: 2 }}>
              {RESULT_FLAVOR_KEYS[localResult] ? t(RESULT_FLAVOR_KEYS[localResult]) : ""}
            </div>
            {isRevealed && onAskBoss && (
              <button
                type="button"
                onClick={() => onAskBoss(fight.boss)}
                disabled={chatOpen}
                data-testid={`btn-ask-boss-${fight.boss}`}
                aria-label={t(ASK_BOSS_ARIA_KEYS[localResult])}
                className={[
                  "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full",
                  "bg-bp-raised/60 border font-body text-small font-semibold text-text-secondary",
                  "hover:bg-bp-surface hover:border-border hover:text-text-primary",
                  "active:scale-[0.97]",
                  "focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none",
                  "disabled:opacity-40 disabled:cursor-not-allowed",
                  "transition-all duration-fast",
                  "cursor-pointer",
                ].join(" ")}
                style={{ borderColor: RESULT_BORDER_TINT[localResult] }}
              >
                <span aria-hidden className="text-accent-insight">✦</span>
                {t(ASK_BOSS_LABEL_KEYS[localResult])}
              </button>
            )}
          </div>
        </div>

        {/* Narrative Timeline (or streaming placeholder) */}
        {narrativeEntries[0]?.narrative ? (
          <NarrativeTimeline
            entries={narrativeEntries}
            bossColor={boss.color}
            isLoading={isRescoring}
          />
        ) : (
          <div
            data-testid={`boss-narrative-loading-${fight.boss}`}
            aria-label={t("build.bossBand.loadingAnalysisAria").replace("{bossName}", localizedBossName)}
            className="mt-3"
            style={{ padding: "12px 0" }}
          >
            <div className="flex items-center gap-2">
              <div
                className="rounded-full flex-shrink-0"
                style={{
                  width: 14,
                  height: 14,
                  border: `2px solid rgba(255,255,255,0.08)`,
                  borderTopColor: boss.color,
                  animation: "narrativeSpin 0.8s linear infinite",
                }}
              />
              <span
                className="font-body text-text-muted"
                style={{ fontSize: 13, animation: "narrativePulse 2s ease-in-out infinite" }}
              >
                Gemma is analyzing...
              </span>
            </div>
          </div>
        )}

        {/* Reroll section */}
        {canReroll && showReroll && (
          <div
            className="rounded-[14px] border border-border-subtle mt-4"
            style={{ padding: 16, background: "rgba(45,48,96,0.35)" }}
          >
            <div className="font-display font-semibold text-text-secondary" style={{ fontSize: 15, marginBottom: 12 }}>
              {t("build.equipSkills")}
            </div>

            {/* Skill grid */}
            <div
              className="skill-grid-responsive grid gap-2.5"
              style={{ gridTemplateColumns: `repeat(${Math.min(availableSkills.length, 3)}, 1fr)` }}
            >
              {availableSkills.map((skill) => {
                const isSelected = selectedSkills.has(skill.id);
                // The skill card is the selection target. We use a
                // div role=button (instead of <button>) so we can nest
                // a real ask icon-button inside without violating
                // button-in-button HTML semantics. Keyboard activation
                // (Enter/Space → toggleSkill) is wired explicitly.
                return (
                  <div
                    key={skill.id}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    className="relative text-left rounded-[14px] border cursor-pointer select-none transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                    style={{
                      padding: "12px 14px",
                      minHeight: 72,
                      background: isSelected ? "rgba(125,212,163,0.06)" : "var(--color-bg-mid)",
                      borderColor: isSelected ? "rgba(125,212,163,0.5)" : "var(--color-border-default)",
                      boxShadow: isSelected
                        ? "0 0 16px rgba(125,212,163,0.12), inset 0 0 12px rgba(125,212,163,0.04)"
                        : undefined,
                    }}
                    onClick={() => toggleSkill(skill.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        toggleSkill(skill.id);
                      }
                    }}
                  >
                    <div className="font-display font-semibold text-text-primary pr-16" style={{ fontSize: 14 }}>
                      {skill.title}
                    </div>
                    <div className="font-body text-text-secondary mt-1" style={{ fontSize: 13, lineHeight: 1.5 }}>
                      {skill.rationale}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {STAT_DELTAS.map(({ key, field, signMultiplier }) => {
                        const val = (skill[field] as number) * (signMultiplier ?? 1);
                        return val !== 0 ? <SkillStatBadge key={key} stat={key} delta={val} /> : null;
                      })}
                    </div>
                    {onAskSkill && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onAskSkill(skill.id);
                        }}
                        disabled={chatOpen}
                        data-testid={`btn-ask-skill-${skill.id}`}
                        aria-label={`Ask Gemma about ${skill.title}`}
                        className={[
                          "absolute top-3 right-10 -m-2 p-2",
                          "w-6 h-6 box-content flex items-center justify-center rounded-full",
                          "bg-bp-deep/80 border border-border-subtle",
                          "hover:bg-state-loading hover:border-accent-insight/40 hover:scale-110",
                          "active:scale-100",
                          "focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none",
                          "disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100",
                          "transition-all duration-fast",
                          "cursor-pointer",
                        ].join(" ")}
                      >
                        <span aria-hidden className="text-accent-insight text-[12px]">✦</span>
                      </button>
                    )}
                    <div
                      className="absolute top-3 right-3 flex-shrink-0 rounded-full flex items-center justify-center"
                      style={{
                        width: 24,
                        height: 24,
                        border: isSelected ? "2px solid var(--color-accent-thrive)" : "2px solid rgba(255,255,255,0.15)",
                        background: isSelected ? "var(--color-accent-thrive)" : "transparent",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {isSelected && (
                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                          <path d="M2 6L5 9L10 3" stroke="var(--color-bg-deep)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Actions */}
            <div className="flex items-stretch justify-between mt-3.5 gap-3">
              <Button variant="ghost" onClick={handleAccept}>
                {t("build.acceptResult")}
              </Button>
              <Button
                variant="primary"
                onClick={handleRescore}
                disabled={selectedSkills.size === 0}
                loading={isRescoring}
                aria-label="Rematch with equipped skills"
              >
                {t("build.rematch")}
                {selectedSkills.size > 0 && !isRescoring && (
                  <span className="ml-1.5" style={{ fontSize: 12, opacity: 0.7 }}>
                    {t("build.equipped").replace("{count}", String(selectedSkills.size)).replace("{s}", selectedSkills.size !== 1 ? "s" : "")}
                  </span>
                )}
              </Button>
            </div>
            {rerollError && (
              <div className="font-body text-accent-alert mt-2" style={{ fontSize: 13 }}>
                {rerollError}
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        @keyframes narrativePulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.7; }
        }
        @keyframes narrativeSpin {
          to { transform: rotate(360deg); }
        }
        @keyframes winPulse {
          0% { box-shadow: 0 0 0 transparent; }
          50% { box-shadow: 0 0 32px rgba(125,212,163,0.25); }
          100% { box-shadow: 0 0 0 transparent; }
        }
        @keyframes loseShake {
          0% { transform: translateX(0); }
          16% { transform: translateX(-3px); }
          33% { transform: translateX(3px); }
          50% { transform: translateX(-2px); }
          66% { transform: translateX(1px); }
          100% { transform: translateX(0); }
        }
        @keyframes drawWobble {
          0% { transform: rotate(0); }
          25% { transform: rotate(1.5deg); }
          75% { transform: rotate(-1.5deg); }
          100% { transform: rotate(0); }
        }
        @media (max-width: 767px) {
          .boss-band-card { padding: 18px !important; }
          .boss-band-card .boss-portrait { width: 52px !important; height: 52px !important; }
        }
        @media (max-width: 679px) {
          .skill-grid-responsive { grid-template-columns: repeat(2, 1fr) !important; }
        }
        @media (max-width: 439px) {
          .skill-grid-responsive { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
