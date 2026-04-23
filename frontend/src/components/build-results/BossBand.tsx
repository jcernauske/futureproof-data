import { useState, useCallback, useRef, useEffect } from "react";
import type { BossFightResult, AppliedSkill, BossOutcome } from "@/types/build";
import { rerollFight, getFightWrapup } from "@/api/gauntlet";
import { Button } from "@/components/ui/Button";
import { BOSS_META, RESULT_COLORS } from "./bossData";
import { SealedOverlay } from "./SealedOverlay";
import { VSOverlay } from "./VSOverlay";
import { SkillStatBadge } from "./SkillStatBadge";
import { NarrativeTimeline } from "./NarrativeTimeline";
import type { NarrativeEntry } from "./NarrativeTimeline";

const MAX_REROLLS = 3;
const RESULT_WORDS: Record<BossOutcome, string> = {
  win: "VICTORY",
  lose: "DEFEATED",
  draw: "STANDOFF",
  unknown: "UNKNOWN",
};
const RESULT_FLAVOR: Record<BossOutcome, string> = {
  win: "Your stats held strong",
  lose: "This one got you",
  draw: "A narrow escape",
  unknown: "",
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
}

const STAT_DELTAS: { key: string; field: keyof AppliedSkill }[] = [
  { key: "ern", field: "delta_ern" },
  { key: "roi", field: "delta_roi" },
  { key: "res", field: "delta_res" },
  { key: "grw", field: "delta_grw" },
  { key: "hmn", field: "delta_hmn" },
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
}: BossBandProps) {
  const boss = BOSS_META[fight.boss];
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
  const firstName = playerName.split(" ")[0] ?? playerName;

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

      const updated = await rerollFight(buildId, fight.boss, skillIds);

      const skillEntry: NarrativeEntry = {
        id: `${fight.boss}-reroll-${updated.reroll_count}`,
        trigger: "skill",
        skillName: selectedSkillNames,
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
      setRerollError(err instanceof Error ? err.message : "Rescore failed — try again");
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
      aria-label={`${boss.shortName}: ${RESULT_WORDS[localResult]}`}
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
        />
      )}

      {/* VS overlay */}
      <VSOverlay
        playerEmoji={playerEmoji}
        playerName={firstName}
        bossEmoji={boss.emoji}
        bossShortName={boss.shortName}
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
              {firstName} vs. {boss.shortName}
            </div>
            <div className="font-body text-text-muted" style={{ fontSize: 14, marginTop: 2 }}>
              {boss.subtitle}
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
                {availableSkills.length} skill{availableSkills.length !== 1 ? "s" : ""} available
              </span>
            )}
          </div>

          {/* Result zone */}
          <div className="flex-shrink-0 text-right">
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
              {RESULT_WORDS[localResult]}
            </div>
            <div className="font-body text-text-muted" style={{ fontSize: 12, marginTop: 2 }}>
              {RESULT_FLAVOR[localResult]}
            </div>
          </div>
        </div>

        {/* Narrative Timeline */}
        <NarrativeTimeline
          entries={narrativeEntries}
          bossColor={boss.color}
          isLoading={isRescoring}
        />

        {/* Reroll section */}
        {canReroll && showReroll && (
          <div
            className="rounded-[14px] border border-border-subtle mt-4"
            style={{ padding: 16, background: "rgba(45,48,96,0.35)" }}
          >
            <div className="font-display font-semibold text-text-secondary" style={{ fontSize: 15, marginBottom: 12 }}>
              Equip Skills
            </div>

            {/* Skill grid */}
            <div
              className="skill-grid-responsive grid gap-2.5"
              style={{ gridTemplateColumns: `repeat(${Math.min(availableSkills.length, 3)}, 1fr)` }}
            >
              {availableSkills.map((skill) => {
                const isSelected = selectedSkills.has(skill.id);
                return (
                  <button
                    key={skill.id}
                    type="button"
                    className="relative text-left rounded-[14px] border cursor-pointer select-none transition-all duration-150"
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
                  >
                    <div className="font-display font-semibold text-text-primary pr-16" style={{ fontSize: 14 }}>
                      {skill.title}
                    </div>
                    <div className="font-body text-text-secondary mt-1" style={{ fontSize: 13, lineHeight: 1.5 }}>
                      {skill.rationale}
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {STAT_DELTAS.map(({ key, field }) => {
                        const val = skill[field] as number;
                        return val !== 0 ? <SkillStatBadge key={key} stat={key} delta={val} /> : null;
                      })}
                    </div>
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
                  </button>
                );
              })}
            </div>

            {/* Actions */}
            <div className="flex items-stretch justify-between mt-3.5 gap-3">
              <Button variant="ghost" onClick={handleAccept}>
                Accept Result
              </Button>
              <Button
                variant="primary"
                onClick={handleRescore}
                disabled={selectedSkills.size === 0}
                loading={isRescoring}
                aria-label="Rescore fight with equipped skills"
              >
                Rescore Fight ✦
                {selectedSkills.size > 0 && !isRescoring && (
                  <span className="ml-1.5" style={{ fontSize: 12, opacity: 0.7 }}>
                    ({selectedSkills.size} equipped)
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
