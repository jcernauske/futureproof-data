import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { springs, stage2Reveal } from "@/styles/motion";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { createBuild } from "@/api/build";
import { LoadingScreen } from "@/components/LoadingScreen";
import { PentagonChart } from "@/components/PentagonChart";
import { StatTutorial } from "@/components/StatTutorial";
import { GemmaTake } from "@/components/GemmaTake";
import { StatDetailCard } from "@/components/StatDetailCard";
import { CareerDetail } from "@/components/CareerDetail";
import type { StatKey } from "@/data/statExplanations";

const STAT_KEYS: StatKey[] = ["ern", "roi", "res", "grw", "hmn"];

export function RevealScreen() {
  const navigate = useNavigate();
  const { school, major, effort, loans } = useBuildInputStore();
  const { profileName, animalEmoji } = useProfileStore();
  const {
    selectedCareer,
    build,
    setBuild,
    isBuilding,
    setIsBuilding,
    hasSeenStatTutorial,
    setHasSeenStatTutorial,
  } = useBuildStore();

  const [error, setError] = useState<string | null>(null);
  const [showTutorial, setShowTutorial] = useState(false);
  const [revealReady, setRevealReady] = useState(false);

  // Navigation guard
  useEffect(() => {
    if (!selectedCareer || !school || !major) {
      navigate("/career-pick", { replace: true });
    }
  }, [selectedCareer, school, major, navigate]);

  // Trigger build
  const runBuild = useCallback(async () => {
    if (!selectedCareer || !school || !major || !profileName) return;
    setIsBuilding(true);
    setError(null);

    const minDisplayTime = new Promise<void>((r) => setTimeout(r, 2000));

    try {
      const [result] = await Promise.all([
        createBuild(
          profileName,
          school.name,
          school.unitid,
          major.cipCode,
          major.cipTitle,
          major.rawText,
          effort.level,
          loans.percentage / 100,
          selectedCareer.soc_code,
          selectedCareer.occupation_title,
          major.rawText,
        ),
        minDisplayTime,
      ]);
      setBuild(result);
      setIsBuilding(false);
      // Brief pause before reveal starts
      setTimeout(() => setRevealReady(true), 400);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Build failed");
      setIsBuilding(false);
    }
  }, [selectedCareer, school, major, profileName, effort, loans, setBuild, setIsBuilding]);

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

  if (!selectedCareer || !school || !major) return null;

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
    <div className="min-h-screen bg-bp-deep pt-14">
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

      <div className="relative z-10 max-w-[800px] mx-auto px-6 py-10 pb-20">
        {/* Character emoji */}
        {revealReady && (
          <motion.div
            className="text-center mb-6"
            {...stage2Reveal.bearReveal}
          >
            <motion.div
              className="text-[120px] inline-block"
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 4, ease: "easeInOut", repeat: Infinity, delay: 1.5 }}
            >
              {animalEmoji ?? "🐻"}
            </motion.div>
          </motion.div>
        )}

        {/* Career title + salary */}
        {revealReady && (
          <motion.div
            className="text-center mb-10"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 0.9 }}
          >
            <h1 className="font-display font-bold text-display text-text-primary">
              {career.occupation_title}
            </h1>
            <p className="font-body text-body text-text-secondary mt-1">
              at {build.school_name}
            </p>
            {career.median_annual_wage !== null && (
              <p className="font-data font-bold text-data-lg text-stat-ern mt-3">
                ${career.median_annual_wage.toLocaleString()}/yr median
              </p>
            )}
          </motion.div>
        )}

        {/* Pentagon */}
        {revealReady && (
          <div className="flex justify-center mb-10">
            <PentagonChart
              stats={career.stats}
              size={280}
              animated
              delay={1.4}
            />
          </div>
        )}

        {/* Gemma's Take */}
        {revealReady && (
          <div className="mb-10">
            <GemmaTake narrative={build.guidance} delay={2.2} />
          </div>
        )}

        {/* Stat detail cards */}
        {revealReady && (
          <motion.div
            className="grid grid-cols-1 desktop:grid-cols-5 gap-3 mb-10"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 2.6 }}
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

        {/* Career detail */}
        {revealReady && (
          <motion.div
            className="mb-10"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 3.0 }}
          >
            <CareerDetail career={career} loanPct={build.loan_pct} />
          </motion.div>
        )}

        {/* Fight bosses CTA */}
        {revealReady && (
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 3.4 }}
          >
            <button
              id="btn-fight-bosses"
              aria-label="Fight the Bosses"
              onClick={() => navigate("/bosses")}
              className="font-display font-semibold text-cta px-8 py-3.5 rounded-lg bg-accent-thrive text-text-inverse cursor-pointer hover:brightness-110 shadow-glow-thrive transition-all duration-normal"
            >
              Fight the Bosses →
            </button>
            <p className="font-body text-[13px] text-text-muted mt-3">
              5 bosses stand between you and your future.
            </p>
          </motion.div>
        )}
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
