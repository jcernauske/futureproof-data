import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useId, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { springs, staggerContainer, staggerItem, stagger } from "@/styles/motion";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useProfileStore } from "@/store/profileStore";
import { getOutcomes, getTieredCareers } from "@/api/build";
import { askCareerPickChip, getCareerPickChips } from "@/api/careerPick";
import { AskGemmaChipRow } from "@/components/AskGemmaChipRow";
import { AskGemmaResponseCard } from "@/components/AskGemmaResponseCard";
import {
  CareerLineageSheet,
  type SheetDetent,
} from "@/components/CareerLineageSheet";
import { CareerTierSection } from "@/components/CareerTierSection";
import { PageContainer } from "@/components/ui/PageContainer";
import { GemmaThinking } from "@/components/ui/GemmaThinking";
import type { CareerOutcome } from "@/types/build";
import { useT } from "@/i18n/useT";
import type { CareerPickChip } from "@/types/careerPick";

export function CareerPickScreen() {
  const navigate = useNavigate();
  const { school, major, effort, loans } = useBuildInputStore();
  const locale = useProfileStore((s) => s.locale);
  const { tieredCareers, selectedCareer, setTieredCareers, setSelectedCareer } =
    useBuildStore();
  const t = useT();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);

  // Sheet-local UI state: which SOC populates the sheet + current detent +
  // the chip set fetched on mount.
  const [lineageCareer, setLineageCareer] = useState<CareerOutcome | null>(null);
  const [detent, setDetent] = useState<SheetDetent>("compact");
  const [chips, setChips] = useState<CareerPickChip[]>([]);
  const [activeChipId, setActiveChipId] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [answerLoading, setAnswerLoading] = useState(false);
  const askElevationHintId = useId();

  // Navigation guard — school/major are session-scoped and not persisted.
  useEffect(() => {
    if (!school || !major) {
      sessionStorage.setItem("fp-nav-hint", "session-expired");
      navigate("/set-your-course", { replace: true });
    }
  }, [school, major, navigate]);

  // Fetch tiered careers on mount.
  useEffect(() => {
    if (tieredCareers || !school || !major) return;

    const currentSchool = school;
    const currentMajor = major;
    const currentEffortLevel = effort.level;
    const currentLoanPct = loans.percentage / 100;
    // The backend's substitution path keys on the school's reported
    // broad cip, not the intent-matched leaf. When parentCip is set
    // (e.g. IU reports 52.01 for Kelley but the student typed "marketing"
    // → matched 52.14), send the parent so _handle_get_career_paths
    // fires its broad-cip substitution branch instead of falling into
    // the family-broaden fallback that returns every 52.* career.
    const lookupCip = currentMajor.parentCip || currentMajor.cipCode;

    let cancelled = false;
    async function fetchCareers() {
      setLoading(true);
      setError(null);
      try {
        const outcomes = await getOutcomes(
          currentSchool.unitid,
          lookupCip,
          currentEffortLevel,
          currentLoanPct,
          currentMajor.rawText,
        );
        if (cancelled) return;
        const tiers = await getTieredCareers(
          outcomes,
          currentSchool.name,
          currentMajor.cipTitle,
          lookupCip,
          currentMajor.studentMajorText,
          currentMajor.intentKeywords,
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

  const socCodes = useMemo(() => {
    if (!tieredCareers) return [];
    return [
      ...tieredCareers.common,
      ...tieredCareers.less_common,
      ...tieredCareers.stretch,
    ].map((c) => c.soc_code);
  }, [tieredCareers]);
  const displayedChips = useMemo(
    () =>
      chips.map((chip) => {
        const key = `careerPick.chip.${chip.id}`;
        const label = t(key);
        return { ...chip, label: label === key ? chip.label : label };
      }),
    [chips, t],
  );

  // Prefetch the chip set once the tier response lands, so the chips are
  // ready by the time the student clicks a card.
  useEffect(() => {
    if (!major || !tieredCareers || socCodes.length === 0) return;
    let cancelled = false;
    // Same lookup-cip rule as the outcomes/tier calls above — the chips
    // endpoint reads the school row to build the Ask-Gemma context, and
    // needs the reported broad cip to land on actual program data.
    getCareerPickChips({
      cipcode: major.parentCip || major.cipCode,
      majorText: major.rawText,
      socCodes,
    })
      .then((result) => {
        if (cancelled) return;
        setChips(result);
      })
      .catch(() => {
        if (cancelled) return;
        // Chips are non-critical — fall back to empty row.
        setChips([]);
      });
    return () => {
      cancelled = true;
    };
  }, [major, tieredCareers, socCodes]);

  // Proposal A redesign: the card is a pure "explore" gesture — click
  // populates the lineage sheet. The student commits (and then moves
  // forward) from inside the sheet's primary CTA. Previous behavior had
  // a separate pill inside the card that few real users discovered.
  function handleExplore(career: CareerOutcome) {
    setLineageCareer(career);
  }

  // Commit the lineage-displayed career as the pick. Sheet auto-promotes
  // to medium so the "See my build" state is visible above the fold.
  function handlePick(career: CareerOutcome) {
    setSelectedCareer(career);
  }

  // Clear the pick (used by the persistent "You picked" chip's × glyph).
  function handleUnpick() {
    setSelectedCareer(null);
  }

  function handleGo() {
    if (!selectedCareer) return;
    navigate("/reveal");
  }

  function handleAskGemma(chip: CareerPickChip) {
    if (!major) return;
    setActiveChipId(chip.id);
    setAnswer(null);
    setAnswerLoading(true);

    askCareerPickChip({
      chipId: chip.id,
      cipcode: major.parentCip || major.cipCode,
      majorText: major.rawText,
      socCodes,
      selectedSoc: selectedCareer?.soc_code ?? lineageCareer?.soc_code ?? null,
      terminalTitle: chip.terminal_title,
      locale,
    })
      .then((response) => {
        setAnswer(response.answer);
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : "Gemma couldn't answer.";
        setAnswer(message);
      })
      .finally(() => {
        setAnswerLoading(false);
      });
  }

  function handleRegenerateAskGemma() {
    if (!activeChipId) return;
    const chip = displayedChips.find((candidate) => candidate.id === activeChipId);
    if (!chip) return;
    handleAskGemma(chip);
  }

  function handleCloseAskGemma() {
    setActiveChipId(null);
    setAnswer(null);
    setAnswerLoading(false);
  }

  if (!school || !major) return null;

  return (
    <div className="min-h-screen pt-14">
      <PageContainer
        variant="grid"
        className="py-10 pb-[calc(45vh+var(--space-6))] tablet:pb-[calc(33vh+var(--space-6))]"
      >
        {/* Header block — spans full grid width */}
        <div className="col-span-12 desktop:col-span-8 desktop:col-start-3 mb-10">
          <motion.p
            className="font-data text-micro text-text-muted tracking-[2px] uppercase mb-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            {t("careerPick.kicker")}
          </motion.p>
          <motion.h1
            className="font-display font-bold text-display text-text-primary mb-3"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 0.15 }}
          >
            {t("careerPick.heading")}
          </motion.h1>
          <motion.p
            className="font-body text-body-lg text-text-secondary"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springs.smooth, delay: 0.25 }}
          >
            {t("careerPick.subtitle")}
          </motion.p>
          {/* Persistent "You picked" chip — visible from anywhere on the page
              so the student never loses sight of their current commitment.
              Positioned in document flow (not global chrome) to keep the
              app header pattern intact per DESIGN.md §Application Header. */}
          {selectedCareer ? (
            <motion.div
              className="mt-4 flex items-center"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...springs.smooth, delay: 0.05 }}
            >
              <div className="inline-flex items-center gap-2 bg-accent-thrive/15 border border-accent-thrive/40 rounded-full pl-3 pr-1 py-1">
                <span className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-thrive">
                  {t("careerPick.picked")}
                </span>
                <span className="font-body text-small font-semibold text-text-primary">
                  {selectedCareer.occupation_title}
                </span>
                <button
                  type="button"
                  aria-label={t("careerPick.clearPick")}
                  onClick={handleUnpick}
                  className="ml-1 w-6 h-6 rounded-full inline-flex items-center justify-center text-accent-thrive hover:bg-accent-thrive/20 cursor-pointer transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]"
                >
                  <svg
                    viewBox="0 0 24 24"
                    width="12"
                    height="12"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <line x1="6" y1="6" x2="18" y2="18" />
                    <line x1="18" y1="6" x2="6" y2="18" />
                  </svg>
                </button>
              </div>
            </motion.div>
          ) : null}
        </div>

        {/* Loading state */}
        {loading && (
          <div className="col-span-12 flex items-center justify-center py-20">
            <GemmaThinking message={t("careerPick.analyzing")} />
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
              {t("careerPick.tryAgain")}
            </button>
          </div>
        )}

        {/* Tier sections — always stacked vertically (outer grid-cols-1) */}
        {tieredCareers && (
          <motion.div
            className="col-span-12 grid grid-cols-1 gap-10"
            variants={staggerContainer(0.3, stagger.normal)}
            initial="hidden"
            animate="visible"
          >
            {displayedChips.length > 0 ? (
              <motion.section
                aria-labelledby="career-pick-ask-gemma-title"
                className="
                  bg-bp-mid/70 border border-border-subtle rounded-xl
                  p-4 tablet:p-5 shadow-md
                "
                variants={staggerItem}
              >
                <div className="flex flex-col gap-3 tablet:flex-row tablet:items-center tablet:justify-between">
                  <div>
                    <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-insight mb-1">
                      {t("careerPick.askGemma")}
                    </p>
                    <h2
                      id="career-pick-ask-gemma-title"
                      className="font-display font-semibold text-subheading text-text-primary"
                    >
                      {t("careerPick.makeSense")}
                    </h2>
                  </div>
                  <AskGemmaChipRow
                    chips={displayedChips}
                    activeChipId={activeChipId}
                    onChipClick={handleAskGemma}
                    elevationHintId={askElevationHintId}
                    ariaLabel="Ask Gemma about these career paths"
                    className="py-1"
                  />
                </div>
                <span id={askElevationHintId} className="sr-only">
                  Gemma thinks this question might be relevant based on your
                  program and career results.
                </span>
                <AnimatePresence initial={false}>
                  {activeChipId !== null ? (
                    <AskGemmaResponseCard
                      key={activeChipId}
                      loading={answerLoading}
                      answer={answer}
                      onRegenerate={handleRegenerateAskGemma}
                      onClose={handleCloseAskGemma}
                    />
                  ) : null}
                </AnimatePresence>
              </motion.section>
            ) : null}
            <motion.div variants={staggerItem}>
              <CareerTierSection
                id="section-tier-common"
                label={t("careerPick.common")}
                description={t("careerPick.commonDesc")}
                accent="common"
                careers={tieredCareers.common}
                pickedSoc={selectedCareer?.soc_code ?? null}
                onSelect={handleExplore}
              />
            </motion.div>
            <motion.div variants={staggerItem}>
              <CareerTierSection
                id="section-tier-less-common"
                label={t("careerPick.lessCommon")}
                description={t("careerPick.lessCommonDesc")}
                accent="uncommon"
                careers={tieredCareers.less_common}
                pickedSoc={selectedCareer?.soc_code ?? null}
                onSelect={handleExplore}
              />
            </motion.div>
            <motion.div variants={staggerItem}>
              <CareerTierSection
                id="section-tier-stretch"
                label={t("careerPick.stretch")}
                description={t("careerPick.stretchDesc")}
                accent="uncommon"
                careers={tieredCareers.stretch}
                pickedSoc={selectedCareer?.soc_code ?? null}
                onSelect={handleExplore}
              />
            </motion.div>
          </motion.div>
        )}
      </PageContainer>

      {/* Bottom lineage sheet — always mounted after tiers resolve.
          Proposal A: the sheet now owns the commit + forward-nav CTAs
          (Pick this path → / See my build ✦). The document-bottom
          "See my build" CTA was removed because it was discoverable
          below the fold behind the sheet — see design visionary's
          diagnosis. */}
      {tieredCareers && (
        <CareerLineageSheet
          soc={lineageCareer?.soc_code ?? null}
          career={lineageCareer}
          detent={detent}
          onDetentChange={setDetent}
          chips={chips}
          askContext={{
            cipcode: major.parentCip || major.cipCode,
            majorText: major.rawText,
            socCodes,
          }}
          pickedSoc={selectedCareer?.soc_code ?? null}
          onPick={handlePick}
          onGo={handleGo}
        />
      )}
    </div>
  );
}
