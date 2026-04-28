import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ambient, springs, stage2Reveal } from "@/styles/motion";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { createBuild, createBuildStream } from "@/api/build";
import type { BuildParams, BuildStreamEvent } from "@/api/build";
import type { Build } from "@/types/build";
import { LoadingScreen } from "@/components/LoadingScreen";
import { PentagonChart } from "@/components/PentagonChart";
import { StatTutorial } from "@/components/StatTutorial";
import { GemmaTake } from "@/components/GemmaTake";
import { StatDetailCard } from "@/components/StatDetailCard";
import { CareerDetail } from "@/components/CareerDetail";
import { PageContainer } from "@/components/ui/PageContainer";
import { useT } from "@/i18n/useT";
import type { StatKey } from "@/data/statExplanations";

const STAT_KEYS: StatKey[] = ["ern", "roi", "res", "grw", "hmn"];

function mergeBossNarrative(build: Build, bossId: string, narrative: string): Build {
  return {
    ...build,
    gauntlet: {
      ...build.gauntlet,
      fights: build.gauntlet.fights.map((f) =>
        f.boss === bossId ? { ...f, narrative } : f,
      ),
    },
  };
}

export function RevealScreen() {
  const navigate = useNavigate();
  const { school, major, effort, loans } = useBuildInputStore();
  const { profileName, animalEmoji, homeState, locale } = useProfileStore();
  const t = useT();
  const {
    selectedCareer,
    build,
    setBuild,
    updateBuild,
    isBuilding,
    setIsBuilding,
    hasSeenStatTutorial,
    setHasSeenStatTutorial,
  } = useBuildStore();

  const [error, setError] = useState<string | null>(null);
  const [showTutorial, setShowTutorial] = useState(false);
  const [revealReady, setRevealReady] = useState(false);

  const cancelledRef = useRef(false);
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
      if (revealTimerRef.current !== null) {
        clearTimeout(revealTimerRef.current);
        revealTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (build) return;
    if (!selectedCareer || !school || !major) {
      sessionStorage.setItem("fp-nav-hint", "session-expired");
      navigate("/career-pick", { replace: true });
    }
  }, [build, selectedCareer, school, major, navigate]);

  // Trigger build
  const runBuild = useCallback(async () => {
    if (!selectedCareer || !school || !major || !profileName) return;
    setIsBuilding(true);
    setError(null);

    const lookupCip = major.parentCip || major.cipCode;
    const studentCip = major.parentCip ? major.cipCode : undefined;

    const params: BuildParams = {
      profile_name: profileName,
      school_name: school.name,
      unitid: school.unitid,
      cipcode: lookupCip,
      cip_title: major.cipTitle,
      major_text: major.rawText,
      effort: effort.level,
      loan_pct: loans.percentage / 100,
      selected_soc: selectedCareer.soc_code,
      selected_title: selectedCareer.occupation_title,
      student_major: major.rawText,
      student_cip: studentCip ?? null,
      home_state: homeState ?? null,
      school_state: school.stateAbbr ?? null,
      animal_emoji: animalEmoji ?? null,
      locale: locale ?? "en",
    };

    const t0 = performance.now();
    const onEvent = (event: BuildStreamEvent) => {
      if (cancelledRef.current) return;
      console.log(`[stream] ${event.type} +${Math.round(performance.now() - t0)}ms`);
      switch (event.type) {
        case "skeleton":
          setBuild(event.build);
          setIsBuilding(false);
          navigate("/my-build");
          break;
        case "boss_narrative":
          updateBuild((prev) => mergeBossNarrative(prev, event.boss_id, event.narrative));
          break;
        case "skill_recs":
          updateBuild((prev) => ({ ...prev, skill_recs: event.recs }));
          break;
        case "skill_pool":
          updateBuild((prev) => ({ ...prev, skill_pool: event.pool }));
          break;
        case "guidance":
          updateBuild((prev) => ({ ...prev, guidance: event.narrative }));
          break;
        case "done":
          break;
      }
    };

    try {
      await createBuildStream(params, onEvent);
    } catch {
      if (cancelledRef.current) return;
      // SSE failed — fall back to blocking build
      try {
        const minDisplayTime = new Promise<void>((r) => setTimeout(r, 1000));
        const [result] = await Promise.all([
          createBuild(
            profileName, school.name, school.unitid, lookupCip,
            major.cipTitle, major.rawText, effort.level,
            loans.percentage / 100, selectedCareer.soc_code,
            selectedCareer.occupation_title, major.rawText, studentCip,
            homeState ?? undefined, school.stateAbbr ?? undefined,
            animalEmoji ?? undefined, locale,
          ),
          minDisplayTime,
        ]);
        if (cancelledRef.current) return;
        setBuild(result);
        setIsBuilding(false);
        navigate("/my-build");
      } catch (fallbackErr) {
        if (cancelledRef.current) return;
        setError(fallbackErr instanceof Error ? fallbackErr.message : "Build failed");
        setIsBuilding(false);
      }
    }
  }, [selectedCareer, school, major, profileName, effort, loans, homeState, locale, animalEmoji, navigate, setBuild, updateBuild, setIsBuilding]);

  useEffect(() => {
    if (!build && !isBuilding && selectedCareer) {
      runBuild();
    } else if (build) {
      setRevealReady(true);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Show tutorial after reveal animation completes
  useEffect(() => {
    if (!revealReady || !build || hasSeenStatTutorial) return;
    const timer = setTimeout(() => setShowTutorial(true), 3000);
    return () => clearTimeout(timer);
  }, [revealReady, build, hasSeenStatTutorial]);

  function handleTutorialComplete() {
    setShowTutorial(false);
    setHasSeenStatTutorial(true);
  }

  if (!build && (!selectedCareer || !school || !major)) return null;

  // Loading state
  if (isBuilding || (!build && !error)) {
    return (
      <LoadingScreen
        profileName={profileName ?? ""}
        emoji={animalEmoji ?? "🐻"}
        error={error}
        onRetry={runBuild}
      />
    );
  }

  // Error state (build failed after loading dismissed)
  if (error && !build) {
    return (
      <LoadingScreen
        profileName={profileName ?? ""}
        emoji={animalEmoji ?? "🐻"}
        error={error}
        onRetry={runBuild}
      />
    );
  }

  if (!build) return null;

  const career = build.career;

  return (
    <div className="min-h-screen pt-14">
      {/* Ambient glow */}
      <motion.div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background:
            "radial-gradient(circle at 50% 30%, rgba(125,212,163,0.15) 0%, transparent 50%)",
        }}
        animate={{ opacity: [0, 0.3, 0.15] as number[] }}
        transition={stage2Reveal.glowPulse.transition}
      />

      <div className="relative z-10">
      <PageContainer variant="grid" className="py-10 pb-20">
        {/* Character emoji — full width */}
        {revealReady && (
          <motion.div
            className="col-span-12 text-center mb-6"
            {...stage2Reveal.bearReveal}
          >
            <motion.div
              className="text-[120px] inline-block"
              animate={ambient.emojiFloat.animate}
              transition={ambient.emojiFloat.transition}
            >
              {animalEmoji ?? "🐻"}
            </motion.div>
          </motion.div>
        )}

        {/* Career title + salary — full width */}
        {revealReady && (
          <motion.div
            className="col-span-12 text-center mb-10"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 1.5 }}
          >
            <h1 className="font-display font-bold text-display text-text-primary">
              {career.occupation_title}
            </h1>
            <p className="font-body text-body text-text-secondary mt-1">
              {t("reveal.at")} {build.school_name}
            </p>
            {career.median_annual_wage !== null && (
              <p className="font-data font-bold text-data-lg text-stat-ern mt-3">
                ${career.median_annual_wage.toLocaleString()}/yr {t("reveal.median")}
              </p>
            )}
          </motion.div>
        )}

        {/* Pentagon — col-span-12 on mobile, col-span-7 on desktop */}
        {revealReady && (
          <div className="col-span-12 desktop:col-span-7 flex justify-center items-center mb-10 desktop:mb-0">
            <PentagonChart
              stats={career.stats}
              size={280}
              animated
              delay={2.0}
            />
          </div>
        )}

        {/* Stat detail cards — col-span-12 on mobile, col-span-5 on desktop */}
        {revealReady && (
          <motion.div
            className="col-span-12 desktop:col-span-5 grid grid-cols-1 gap-3 mb-10 desktop:mb-0"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 2.8 }}
          >
            {STAT_KEYS.map((key) => (
              <StatDetailCard
                key={key}
                statKey={key}
                value={career.stats[key]}
              />
            ))}
          </motion.div>
        )}

        {/* Gemma's Take — full width, below pentagon/stats */}
        {revealReady && (
          <div className="col-span-12 mt-10">
            <GemmaTake narrative={build.guidance} delay={3.0} />
          </div>
        )}

        {/* Career detail — full width */}
        {revealReady && (
          <motion.div
            className="col-span-12 mt-10"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 3.3 }}
          >
            <CareerDetail career={career} loanPct={build.loan_pct} />
          </motion.div>
        )}

        {/* Fight bosses CTA — full width */}
        {revealReady && (
          <motion.div
            className="col-span-12 text-center mt-10"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 3.7 }}
          >
            <button
              id="btn-fight-bosses"
              aria-label="Fight the Bosses"
              onClick={() => navigate("/gauntlet")}
              className="font-display font-semibold text-cta h-12 px-7 rounded-lg bg-accent-thrive text-text-inverse cursor-pointer hover:brightness-110 shadow-glow-thrive transition-all duration-normal"
            >
              {t("reveal.fightBosses")}
            </button>
            <p className="font-body text-small text-text-muted mt-3">
              {t("reveal.fiveStand")}
            </p>
          </motion.div>
        )}
      </PageContainer>
      </div>

      {/* Stat tutorial overlay */}
      <AnimatePresence>
        {showTutorial && (
          <StatTutorial
            stats={career.stats}
            onComplete={handleTutorialComplete}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
