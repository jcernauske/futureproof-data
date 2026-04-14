import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { springs, staggerContainer, staggerItem, stagger } from "@/styles/motion";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { getOutcomes, getTieredCareers } from "@/api/build";
import { CareerTierSection } from "@/components/CareerTierSection";
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

  // Navigation guard
  useEffect(() => {
    if (!school || !major) {
      navigate("/school", { replace: true });
    }
  }, [school, major, navigate]);

  // Fetch tiered careers on mount
  useEffect(() => {
    if (tieredCareers || !school || !major) return;

    let cancelled = false;
    async function fetchCareers() {
      setLoading(true);
      setError(null);
      try {
        const outcomes = await getOutcomes(
          school!.unitid,
          major!.cipCode,
          effort.level,
          loans.percentage / 100,
          major!.rawText,
        );
        if (cancelled) return;
        const tiers = await getTieredCareers(
          outcomes,
          school!.name,
          major!.cipTitle,
          major!.cipCode,
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
  }, [school, major, effort, loans, tieredCareers, setTieredCareers]);

  function handleSelect(career: CareerOutcome) {
    setSelectedCareer(career);
  }

  function handleBuild() {
    if (!selectedCareer) return;
    navigate("/reveal");
  }

  if (!school || !major) return null;

  return (
    <div className="min-h-screen bg-bp-deep pt-14">
      <div className="max-w-[720px] mx-auto px-6 py-10 pb-32">
        {/* Step indicator */}
        <motion.p
          className="font-data text-[11px] text-text-muted tracking-[2px] uppercase mb-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          CHOOSE YOUR PATH
        </motion.p>

        {/* Title */}
        <motion.h1
          className="font-display font-bold text-display text-text-primary mb-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springs.smooth, delay: 0.15 }}
        >
          Where could this degree take you?
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          className="font-body text-body-lg text-text-secondary mb-10"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springs.smooth, delay: 0.25 }}
        >
          Gemma analyzed your program and grouped career paths by how common they
          are for graduates like you.
        </motion.p>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="font-body text-body text-text-muted animate-pulse">
              Analyzing career paths...
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="text-center py-20">
            <p className="font-body text-body text-accent-alert mb-4">{error}</p>
            <button
              onClick={() => {
                setTieredCareers(null as unknown as import("@/types/build").TieredCareers);
              }}
              className="font-body font-semibold text-body px-6 py-3 rounded-lg bg-bp-surface border border-border-subtle text-text-primary cursor-pointer hover:bg-bp-raised transition-colors duration-normal"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Tier sections */}
        {tieredCareers && (
          <motion.div
            className="space-y-10"
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
      </div>

      {/* CTA */}
      {tieredCareers && (
        <div className="fixed bottom-0 left-0 right-0 bg-bp-deep/90 backdrop-blur-sm border-t border-border-subtle p-4 desktop:static desktop:border-0 desktop:bg-transparent desktop:p-0">
          <div className="max-w-[720px] mx-auto text-center">
            <motion.button
              id="btn-build-career"
              aria-label="Build your career path"
              disabled={!selectedCareer}
              onClick={handleBuild}
              className={`w-full desktop:w-auto font-display font-semibold text-cta px-8 py-3.5 rounded-lg transition-all duration-normal ${
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
            <p className="font-body text-[13px] text-text-muted mt-2">
              You can always come back and pick a different path.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
