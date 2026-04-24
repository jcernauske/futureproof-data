import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { createBuild } from "@/api/build";
import { clearSession } from "@/api/session";
import { PentagonChart } from "@/components/PentagonChart";
import { Button } from "@/components/ui/Button";
import { CampusHeroBanner } from "@/components/build-results/CampusHeroBanner";
import { HeroIdentity } from "@/components/build-results/HeroIdentity";
import { PathCard } from "@/components/build-results/PathCard";
import { FinancesCard } from "@/components/build-results/FinancesCard";
import { InstitutionCard } from "@/components/build-results/InstitutionCard";
import { StatInfoPopover } from "@/components/build-results/StatInfoPopover";
import { BossBand } from "@/components/build-results/BossBand";
import { VerdictBadge } from "@/components/build-results/VerdictBadge";
import { STAT_COLORS } from "@/components/build-results/bossData";
import type { StatKey } from "@/data/statExplanations";
import { STAT_EXPLANATIONS } from "@/data/statExplanations";
import { fireCheckpoint } from "@/lib/checkpoint";
import type { BossFightResult } from "@/types/build";

const STAT_KEYS: StatKey[] = ["ern", "roi", "res", "grw", "hmn"];

export function BuildResultsScreen() {
  const navigate = useNavigate();
  const { school, major, effort, loans } = useBuildInputStore();
  const { profileName, animalEmoji, homeState } = useProfileStore();
  const { selectedCareer, build, setBuild, isBuilding, setIsBuilding } = useBuildStore();

  const [error, setError] = useState<string | null>(null);
  const [openPopover, setOpenPopover] = useState<string | null>(null);
  const [highlightStat, setHighlightStat] = useState<StatKey | null>(null);
  const [fights, setFights] = useState<BossFightResult[]>([]);
  const [consumedSkillIds, setConsumedSkillIds] = useState<Set<string>>(new Set());

  const cancelledRef = useRef(false);

  // Boss band reveal state
  const [revealedBands, setRevealedBands] = useState<Set<string>>(new Set());
  const [vsActiveBands, setVsActiveBands] = useState<Set<string>>(new Set());
  const [vsDoneBands, setVsDoneBands] = useState<Set<string>>(new Set());
  const [visibleBands, setVisibleBands] = useState<Set<string>>(new Set());
  const bandRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const animatingRef = useRef<string | null>(null);
  const pendingQueueRef = useRef<string[]>([]);
  // Refs mirroring state for observer callbacks (avoids observer recreation)
  const revealedBandsRef = useRef(revealedBands);
  revealedBandsRef.current = revealedBands;
  const vsActiveBandsRef = useRef(vsActiveBands);
  vsActiveBandsRef.current = vsActiveBands;
  const timeoutsRef = useRef<Map<string, number[]>>(new Map());

  // Nav guard — skip when a build is already loaded (e.g. from /builds menu)
  useEffect(() => {
    if (build) return;
    if (!selectedCareer || !school || !major) {
      sessionStorage.setItem("fp-nav-hint", "session-expired");
      navigate("/set-your-course", { replace: true });
    }
  }, [build, selectedCareer, school, major, navigate]);

  // Build trigger
  useEffect(() => {
    cancelledRef.current = false;
    return () => { cancelledRef.current = true; };
  }, []);

  const runBuild = useCallback(async () => {
    if (!selectedCareer || !school || !major || !profileName) return;
    setIsBuilding(true);
    setError(null);

    const minDisplayTime = new Promise<void>((r) => setTimeout(r, 1000));
    try {
      const lookupCip = major.parentCip || major.cipCode;
      const studentCip = major.parentCip ? major.cipCode : undefined;
      const [result] = await Promise.all([
        createBuild(
          profileName,
          school.name,
          school.unitid,
          lookupCip,
          major.cipTitle,
          major.rawText,
          effort.level,
          loans.percentage / 100,
          selectedCareer.soc_code,
          selectedCareer.occupation_title,
          major.rawText,
          studentCip,
          homeState ?? undefined,
          school.stateAbbr ?? undefined,
          animalEmoji ?? undefined,
        ),
        minDisplayTime,
      ]);
      if (cancelledRef.current) return;
      setBuild(result);
      setFights(result.gauntlet.fights);
      setIsBuilding(false);
      fireCheckpoint("/my-build");
    } catch (err) {
      if (cancelledRef.current) return;
      setError(err instanceof Error ? err.message : "Build failed");
      setIsBuilding(false);
    }
  }, [selectedCareer, school, major, profileName, effort, loans, homeState, setBuild, setIsBuilding]);

  useEffect(() => {
    if (!build && !isBuilding && selectedCareer) {
      runBuild();
    } else if (build) {
      setFights(build.gauntlet.fights);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Reveal queue system
  const clearBandTimeouts = useCallback((bossId: string) => {
    const ids = timeoutsRef.current.get(bossId);
    if (ids) {
      ids.forEach((id) => window.clearTimeout(id));
      timeoutsRef.current.delete(bossId);
    }
  }, []);

  const skipToRevealed = useCallback((bossId: string) => {
    clearBandTimeouts(bossId);
    setVsActiveBands((p) => { const n = new Set(p); n.delete(bossId); return n; });
    setVsDoneBands((p) => new Set(p).add(bossId));
    setRevealedBands((p) => new Set(p).add(bossId));
    if (animatingRef.current === bossId) {
      animatingRef.current = null;
    }
  }, [clearBandTimeouts]);

  const processNext = useCallback(() => {
    if (animatingRef.current) return;
    const next = pendingQueueRef.current.shift();
    if (!next) return;
    animatingRef.current = next;

    const ids: number[] = [];

    // Phase 1: VS active
    ids.push(window.setTimeout(() => {
      setVsActiveBands((p) => new Set(p).add(next));
    }, 200));

    // Phase 2: VS done
    ids.push(window.setTimeout(() => {
      setVsDoneBands((p) => new Set(p).add(next));
    }, 1200));

    // Phase 3: Reveal
    ids.push(window.setTimeout(() => {
      setVsActiveBands((p) => { const n = new Set(p); n.delete(next); return n; });
      setRevealedBands((p) => new Set(p).add(next));
      animatingRef.current = null;
      processNext();
    }, 1350));

    timeoutsRef.current.set(next, ids);
  }, []);

  const triggerReveal = useCallback((bossId: string) => {
    if (revealedBandsRef.current.has(bossId) || vsActiveBandsRef.current.has(bossId)) return;
    if (pendingQueueRef.current.includes(bossId)) return;

    pendingQueueRef.current.push(bossId);
    if (!animatingRef.current) {
      processNext();
    }
  }, [processNext]);

  // IntersectionObserver setup
  useEffect(() => {
    if (!build || fights.length === 0) return;

    const visibilityObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const bossId = (entry.target as HTMLElement).dataset.boss;
          if (!bossId) return;
          if (entry.isIntersecting) {
            setVisibleBands((p) => new Set(p).add(bossId));
          }
        });
      },
      { threshold: 0.1 },
    );

    const centerObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const bossId = (entry.target as HTMLElement).dataset.boss;
          if (!bossId) return;
          if (entry.isIntersecting) {
            triggerReveal(bossId);
          } else if (!entry.isIntersecting) {
            // Fast-scroll skip — read refs to avoid stale closures
            if (
              (vsActiveBandsRef.current.has(bossId) || pendingQueueRef.current.includes(bossId)) &&
              !revealedBandsRef.current.has(bossId)
            ) {
              skipToRevealed(bossId);
              const idx = pendingQueueRef.current.indexOf(bossId);
              if (idx !== -1) pendingQueueRef.current.splice(idx, 1);
            }
          }
        });
      },
      { threshold: 0.15, rootMargin: "-20% 0px -20% 0px" },
    );

    bandRefs.current.forEach((el) => {
      visibilityObserver.observe(el);
      centerObserver.observe(el);
    });

    return () => {
      visibilityObserver.disconnect();
      centerObserver.disconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [build, fights, triggerReveal, skipToRevealed]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach((ids) => ids.forEach((id) => window.clearTimeout(id)));
    };
  }, []);

  // Reroll handlers
  const handleRerollComplete = useCallback((updated: BossFightResult) => {
    setFights((prev) =>
      prev.map((f) => (f.boss === updated.boss ? updated : f)),
    );
  }, []);

  const handleSkillsConsumed = useCallback((usedIds: string[]) => {
    setConsumedSkillIds((prev) => {
      const next = new Set(prev);
      usedIds.forEach((id) => next.add(id));
      return next;
    });
  }, []);

  // Derived state
  const availableSkillPool = useMemo(() => {
    if (!build) return [];
    return build.skill_pool.filter((s) => !consumedSkillIds.has(s.id));
  }, [build, consumedSkillIds]);

  const verdictCounts = useMemo(() => {
    let rawWins = 0;
    let equippedWins = 0;
    let losses = 0;
    let draws = 0;
    let unknowns = 0;
    fights.forEach((f) => {
      if (f.result === "win") {
        if (f.rerolled) equippedWins++;
        else rawWins++;
      } else if (f.result === "lose") {
        losses++;
      } else if (f.result === "draw") {
        draws++;
      } else if (f.result === "unknown") {
        unknowns++;
      }
    });
    return { rawWins, equippedWins, losses, draws, unknowns };
  }, [fights]);

  // Guards
  if (!build && (!selectedCareer || !school || !major)) return null;

  // Loading state
  if (isBuilding || !build) {
    return (
      <div className="min-h-screen pt-14">
        <div
          className="w-full bg-bp-surface"
          style={{
            height: 280,
            backgroundImage: "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.03) 50%, transparent 100%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.5s ease-in-out infinite",
          }}
        />
        <div className="flex flex-col items-center justify-center py-16">
          <span style={{ fontSize: 56, animation: "emojiFloat 2s ease-in-out infinite", marginTop: -40 }}>
            {animalEmoji ?? "🐻"}
          </span>
          <p className="font-body text-text-secondary mt-4" style={{ fontSize: 16 }}>
            Gemma is analyzing your build...
          </p>
          <div
            className="mt-4 rounded-full"
            style={{
              width: 32,
              height: 32,
              border: "3px solid var(--color-bg-surface)",
              borderTopColor: "var(--color-accent-insight)",
              animation: "spin 1s linear infinite",
            }}
          />
          {error && (
            <div className="mt-8 bg-bp-mid rounded-xl p-8 border border-border-subtle max-w-md mx-auto text-center">
              <div className="text-accent-alert" style={{ fontSize: 48 }}>⚠</div>
              <p className="font-body text-text-secondary mt-4" style={{ fontSize: 16, lineHeight: 1.5 }}>
                {error}
              </p>
              <div className="flex gap-3 justify-center mt-6">
                <Button variant="primary" onClick={runBuild}>
                  Try Again
                </Button>
                <Button variant="ghost" onClick={() => navigate("/set-your-course")}>
                  Go Back
                </Button>
              </div>
            </div>
          )}
        </div>
        <style>{`
          @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
          }
          @keyframes emojiFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
          }
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Error state (no build, not loading)
  if (error && !build) {
    return (
      <div className="min-h-screen pt-14 flex items-start justify-center" style={{ marginTop: 80 }}>
        <div className="bg-bp-mid rounded-xl p-8 border border-border-subtle max-w-md mx-auto text-center">
          <div className="text-accent-alert" style={{ fontSize: 48 }}>⚠</div>
          <p className="font-body text-text-secondary mt-4" style={{ fontSize: 16, lineHeight: 1.5 }}>
            {error}
          </p>
          <div className="flex gap-3 justify-center mt-6">
            <Button variant="primary" onClick={runBuild}>
              Try Again
            </Button>
            <Button variant="ghost" onClick={() => navigate("/set-your-course")}>
              Go Back
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const career = build.career;

  return (
    <div className="min-h-screen pt-14">
      {/* Section 1: Campus Hero Banner */}
      <CampusHeroBanner />

      {/* Hero Identity */}
      <HeroIdentity
        profileName={build.profile_name || profileName || "Adventurer"}
        animalEmoji={build.animal_emoji || animalEmoji || "🐻"}
        schoolName={school?.name ?? build.school_name}
        programName={major?.cipTitle ?? build.program_name}
      />

      {/* Content column */}
      <div className="max-w-[1280px] mx-auto px-4 tablet:px-6 desktop:px-8">

        {/* Adjust / Start over links */}
        <div className="flex justify-end gap-4" style={{ marginTop: 16 }}>
          <button
            type="button"
            className="font-body text-text-muted hover:text-text-secondary hover:underline transition-colors duration-150 bg-transparent border-none cursor-pointer"
            style={{ fontSize: 14 }}
            onClick={() => {
              clearSession().catch(console.warn);
              useBuildInputStore.getState().reset();
              useBuildStore.setState({ build: null, selectedCareer: null });
              navigate("/set-your-course");
            }}
          >
            Start over
          </button>
          <button
            type="button"
            className="font-body text-accent-info hover:underline hover:brightness-125 transition-colors duration-150 bg-transparent border-none cursor-pointer"
            style={{ fontSize: 14 }}
            onClick={() => {
              useBuildStore.setState({ build: null });
              navigate("/set-your-course", { state: { adjustMode: true } });
            }}
          >
            ← Adjust effort & loans
          </button>
        </div>

        {/* Section 2: Path + Institution grid */}
        <div
          className="path-institution-grid grid gap-6 items-stretch"
          style={{
            gridTemplateColumns: "1fr 1.6fr",
            marginTop: 32,
            animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.2s both",
          }}
        >
          <div className="flex flex-col gap-6">
            <PathCard
              programName={career.program_name || major?.cipTitle || build.program_name}
              cipCode={career.cipcode}
              careerName={career.occupation_title}
              socCode={career.soc_code}
              stats={career.stats}
            />
            <FinancesCard
              startingSalary={career.earnings_1yr_median}
              medianSalary={career.median_annual_wage}
              tuitionInState={career.tuition_in_state}
              tuitionOutOfState={career.tuition_out_of_state}
              netPriceAnnual={career.net_price_annual}
              loanPct={career.loan_pct}
              isInState={homeState && school?.stateAbbr ? homeState === school.stateAbbr : null}
              institutionControl={career.institution_control ?? null}
            />
          </div>
          <InstitutionCard
            schoolName={build.school_name}
            narrative={build.guidance}
          />
        </div>

        {/* Section 3: Build Stats (Pentagon + Legend) */}
        <div style={{ marginTop: 48, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.4s both" }}>
          <h2 className="font-display font-bold text-text-primary" style={{ fontSize: 32 }}>
            Build Stats
          </h2>

          <div
            className="rounded-[20px] border border-border-subtle bg-bp-mid mt-4"
            style={{ padding: 32 }}
          >
            <div className="flex gap-12 items-center flex-wrap">
              <div>
                <PentagonChart
                  stats={career.stats}
                  size={320}
                  animated
                  delay={0.3}
                  highlightStat={highlightStat}
                />
              </div>

              {/* Stat legend */}
              <div className="flex-1" style={{ minWidth: 240 }}>
                {STAT_KEYS.map((key) => {
                  const stat = STAT_EXPLANATIONS.find((s) => s.key === key)!;
                  const colors = STAT_COLORS[key];
                  const value = career.stats[key];

                  return (
                    <div key={key}>
                      <div
                        className="flex items-center gap-3 cursor-pointer transition-colors duration-150"
                        style={{
                          padding: "14px 0",
                          borderBottom: "1px solid rgba(255,255,255,0.06)",
                        }}
                        onMouseEnter={() => setHighlightStat(key)}
                        onMouseLeave={() => setHighlightStat(null)}
                      >
                        {/* Dot */}
                        <div
                          className="flex-shrink-0 rounded-full"
                          style={{ width: 12, height: 12, background: colors?.text }}
                        />
                        {/* Abbreviation */}
                        <span className="font-data text-text-muted" style={{ fontSize: 12, width: 32 }}>
                          {stat.abbreviation}
                        </span>
                        {/* Name + explanation */}
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-display font-semibold text-text-primary" style={{ fontSize: 15 }}>
                              {stat.name}
                            </span>
                            {/* Info trigger */}
                            <button
                              type="button"
                              className="flex-shrink-0 rounded-full flex items-center justify-center font-body font-bold transition-all duration-150"
                              style={{
                                width: 18,
                                height: 18,
                                fontSize: 11,
                                border: openPopover === key
                                  ? `1.5px solid var(--color-accent-info)`
                                  : "1.5px solid var(--color-border-default)",
                                color: openPopover === key ? "var(--color-accent-info)" : undefined,
                                background: openPopover === key ? "rgba(123,184,224,0.08)" : undefined,
                                opacity: openPopover === key ? 1 : 0.6,
                              }}
                              aria-expanded={openPopover === key}
                              aria-controls={`info-${key}`}
                              aria-label={`What is ${stat.name}?`}
                              onClick={() => setOpenPopover(openPopover === key ? null : key)}
                            >
                              ?
                            </button>
                          </div>
                          <p className="font-body text-text-secondary" style={{ fontSize: 13, lineHeight: 1.5, marginTop: 4 }}>
                            {stat.explanation}
                          </p>
                        </div>
                        {/* Score */}
                        <div className="flex-shrink-0 text-right">
                          <span className="font-data font-bold" style={{ fontSize: 18, color: colors?.text }}>
                            {value ?? "—"}
                          </span>
                          <span className="font-data" style={{ fontSize: 13, fontWeight: 400, opacity: 0.45, color: colors?.text }}>
                            /10
                          </span>
                        </div>
                      </div>

                      {/* Popover */}
                      <StatInfoPopover
                        stat={key}
                        isOpen={openPopover === key}
                        onClose={() => setOpenPopover(null)}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Boss Fight Results (The Gauntlet) */}
        <div style={{ marginTop: 48, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.6s both" }}>
          <h2 className="font-display font-bold text-text-primary" style={{ fontSize: 32 }}>
            The Gauntlet
          </h2>
          <p className="font-body text-text-secondary" style={{ fontSize: 16, marginTop: 4 }}>
            5 fights. Your stats vs. real-world threats.
          </p>

          <div
            className="flex flex-col gap-12 mt-6"
            style={{ scrollSnapType: "y proximity" }}
          >
            {fights.map((fight) => (
              <div
                key={fight.boss}
                ref={(el) => {
                  if (el) bandRefs.current.set(fight.boss, el);
                  else bandRefs.current.delete(fight.boss);
                }}
                data-boss={fight.boss}
              >
                <BossBand
                  fight={fight}
                  buildId={build.build_id}
                  playerEmoji={animalEmoji ?? "🐻"}
                  playerName={profileName ?? "Adventurer"}
                  skillPool={availableSkillPool}
                  onRerollComplete={handleRerollComplete}
                  onSkillsConsumed={handleSkillsConsumed}
                  isRevealed={revealedBands.has(fight.boss)}
                  isSealed={!revealedBands.has(fight.boss)}
                  isVsActive={vsActiveBands.has(fight.boss)}
                  isVsDone={vsDoneBands.has(fight.boss)}
                  isSealedVisible={visibleBands.has(fight.boss)}
                  onReveal={() => triggerReveal(fight.boss)}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Section 5: Verdict */}
        <div style={{ marginTop: 48, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 0.8s both" }}>
          <VerdictBadge
            rawWins={verdictCounts.rawWins}
            equippedWins={verdictCounts.equippedWins}
            losses={verdictCounts.losses}
            draws={verdictCounts.draws}
            unknowns={verdictCounts.unknowns}
          />
        </div>

        {/* Section 6: Save CTA */}
        <div
          className="text-center"
          style={{ marginTop: 48, marginBottom: 64, animation: "sectionFadeIn 0.5s cubic-bezier(0.25, 1, 0.5, 1) 1.2s both" }}
        >
          <Button
            variant="primary"
            className="w-full font-bold"
            style={{ maxWidth: 480, height: 48, fontSize: 17 }}
            onClick={() => navigate("/save")}
          >
            Save This Build
          </Button>
          <div style={{ marginTop: 14 }}>
            <button
              type="button"
              className="font-body text-accent-info hover:underline hover:brightness-125 transition-colors duration-150 bg-transparent border-none cursor-pointer"
              style={{ fontSize: 14 }}
              onClick={() => navigate("/branches")}
            >
              Want to explore career branches? See the Branch Tree →
            </button>
          </div>
        </div>
      </div>

      {/* Responsive overrides + shared keyframes */}
      <style>{`
        @keyframes sectionFadeIn {
          from { opacity: 0; transform: translateY(24px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 899px) {
          .path-institution-grid { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 767px) {
          .pentagon-flex { flex-direction: column !important; }
          .pentagon-sticky { position: static !important; }
          .section-gaps { margin-top: 32px !important; }
          .save-section { margin-top: 32px !important; margin-bottom: 48px !important; }
        }
      `}</style>
    </div>
  );
}
