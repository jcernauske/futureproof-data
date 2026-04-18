import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { springs, staggerContainer, staggerItem, stagger } from "@/styles/motion";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { getOutcomes, getTieredCareers } from "@/api/build";
import { CareerTierSection } from "@/components/CareerTierSection";
import { PageContainer } from "@/components/ui/PageContainer";
import type { CareerOutcome } from "@/types/build";

const TIER_DESCRIPTIONS = {
  common: "Where most graduates from this program end up.",
  less_common: "Realistic paths that take more intention.",
  stretch: "Possible but atypical — these take extra work to reach.",
} as const;

export function CareerPickScreen() {
  const navigate = useNavigate();
  const { school, major, effort, loans } = useBuildInputStore();
  const { tieredCareers, selectedCareer, setTieredCareers, setSelectedCareer } =
    useBuildStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Bumping this triggers the fetch effect to re-run even when tieredCareers is
  // already null (the Try-Again case after a failed tier call).
  const [retryKey, setRetryKey] = useState(0);

  // Navigation guard — school/major are session-scoped and not persisted,
  // so refresh on /career-pick will kick back to /school. Hint the destination
  // so it can surface a "session expired" banner.
  useEffect(() => {
    if (!school || !major) {
      sessionStorage.setItem("fp-nav-hint", "session-expired");
      navigate("/school", { replace: true });
    }
  }, [school, major, navigate]);

  // Fetch tiered careers on mount
  useEffect(() => {
    if (tieredCareers || !school || !major) return;

    const currentSchool = school;
    const currentMajor = major;
    const currentEffortLevel = effort.level;
    const currentLoanPct = loans.percentage / 100;

    let cancelled = false;
    async function fetchCareers() {
      setLoading(true);
      setError(null);
      try {
        const outcomes = await getOutcomes(
          currentSchool.unitid,
          currentMajor.cipCode,
          currentEffortLevel,
          currentLoanPct,
          currentMajor.rawText,
        );
        if (cancelled) return;
        const tiers = await getTieredCareers(
          outcomes,
          currentSchool.name,
          currentMajor.cipTitle,
          currentMajor.cipCode,
        );
        if (cancelled) return;
        setTieredCareers(tiers);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load careers");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchCareers();
    return () => {
      cancelled = true;
    };
  }, [school, major, effort, loans, tieredCareers, setTieredCareers, retryKey]);

  function handleSelect(career: CareerOutcome) {
    setSelectedCareer(career);
  }

  function handleBuild() {
    if (!selectedCareer) return;
    navigate("/reveal");
  }

  if (!school || !major) return null;

  return (
    <div className="min-h-screen pt-14">
      <PageContainer variant="grid" className="py-10 pb-32">
        {/* Header block — spans full grid width */}
        <div className="col-span-12 desktop:col-span-8 desktop:col-start-3 mb-10">
          <motion.p
            className="font-data text-micro text-text-muted tracking-[2px] uppercase mb-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            CHOOSE YOUR PATH
          </motion.p>
          <motion.h1
            className="font-display font-bold text-display text-text-primary mb-3"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 0.15 }}
          >
            Where could this degree take you?
          </motion.h1>
          <motion.p
            className="font-body text-body-lg text-text-secondary"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 0.25 }}
          >
            Gemma analyzed your program and grouped career paths by how common
            they are for graduates like you.
          </motion.p>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="col-span-12 flex items-center justify-center py-20">
            <div className="font-body text-body text-text-muted animate-pulse">
              Analyzing career paths...
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="col-span-12 text-center py-20">
            <p className="font-body text-body text-accent-alert mb-4">{error}</p>
            <button
              onClick={() => {
                setError(null);
                setTieredCareers(null);
                setRetryKey((k) => k + 1);
              }}
              className="font-body font-semibold text-body px-6 py-3 rounded-lg bg-bp-surface border border-border-subtle text-text-primary cursor-pointer hover:bg-bp-raised transition-colors duration-normal"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Tier sections — stack on mobile/tablet, 3-up on desktop */}
        {tieredCareers && (
          <motion.div
            className="col-span-12 grid grid-cols-1 desktop:grid-cols-3 gap-10"
            variants={staggerContainer(0.3, stagger.normal)}
            initial="hidden"
            animate="visible"
          >
            <motion.div variants={staggerItem}>
              <CareerTierSection
                id="section-tier-common"
                label="Common"
                description={TIER_DESCRIPTIONS.common}
                careers={tieredCareers.common}
                selectedSoc={selectedCareer?.soc_code ?? null}
                onSelect={handleSelect}
              />
            </motion.div>
            <motion.div variants={staggerItem}>
              <CareerTierSection
                id="section-tier-less-common"
                label="Less Common"
                description={TIER_DESCRIPTIONS.less_common}
                careers={tieredCareers.less_common}
                selectedSoc={selectedCareer?.soc_code ?? null}
                onSelect={handleSelect}
              />
            </motion.div>
            <motion.div variants={staggerItem}>
              <CareerTierSection
                id="section-tier-stretch"
                label="Stretch"
                description={TIER_DESCRIPTIONS.stretch}
                careers={tieredCareers.stretch}
                selectedSoc={selectedCareer?.soc_code ?? null}
                onSelect={handleSelect}
              />
            </motion.div>
          </motion.div>
        )}
      </PageContainer>

      {/* CTA — sticky on mobile, inline on desktop */}
      {tieredCareers && (
        <div className="fixed bottom-0 left-0 right-0 bg-bp-deep/90 backdrop-blur-sm border-t border-border-subtle p-4 desktop:static desktop:border-0 desktop:bg-transparent desktop:p-0">
          <PageContainer variant="centered">
            <div className="text-center">
              <motion.button
                id="btn-build-career"
                aria-label="Build your career path"
                disabled={!selectedCareer}
                onClick={handleBuild}
                className={`w-full desktop:w-auto font-display font-semibold text-cta h-12 px-7 rounded-lg transition-all duration-normal ${
                  selectedCareer
                    ? "bg-accent-thrive text-text-inverse cursor-pointer hover:brightness-110 shadow-glow-thrive"
                    : "bg-bp-surface text-text-muted cursor-not-allowed opacity-60"
                }`}
                whileTap={selectedCareer ? { scale: 0.97 } : undefined}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springs.smooth, delay: 0.5 }}
              >
                See my build ✦
              </motion.button>
              <p className="font-body text-small text-text-muted mt-2">
                You can always come back and pick a different path.
              </p>
            </div>
          </PageContainer>
        </div>
      )}
    </div>
  );
}
