import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiGet } from "@/api/client";
import { requestPrefetch } from "@/api/prefetch";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useSetYourCourse } from "@/hooks/useSetYourCourse";
import { SchoolSearch } from "@/components/school/SchoolSearch";
import { DemoChipsDrawer } from "@/components/setyourcourse/DemoChipsDrawer";
import type { DemoChip } from "@/data/demoChips";
import { EffortLoansPanel } from "@/components/school/EffortLoansPanel";
import { AskGemmaChip } from "@/components/school/AskGemmaChip";
import { CareerListSkeleton } from "@/components/school/CareerListSkeleton";
import { CareerTierSection } from "@/components/CareerTierSection";
import { CipPicker } from "@/components/school/CipPicker";
import { CommunitySuggestions } from "@/components/school/CommunitySuggestions";
import { Button } from "@/components/ui/Button";
import { GemmaStar } from "@/components/ui/GemmaStar";
import { GemmaSpinner } from "@/components/ui/GemmaSpinner";
import { PageContainer } from "@/components/ui/PageContainer";
import { SealedBuildContext } from "@/components/school/SealedBuildContext";
import { GemmaChat } from "@/components/menu/GemmaChat";
import { fireCheckpoint } from "@/lib/checkpoint";
import { useT } from "@/i18n/useT";
import type {
  ProgramResult,
  SchoolSelection,
} from "@/types/buildInput";
import type { CareerDescription, CareerOutcome } from "@/types/build";
import type { AskScope } from "@/api/menu";
import {
  getCachedCareerDescription,
  loadCareerDescription,
} from "@/store/careerDescriptionStore";

const isPostgrad = (c: CareerOutcome) =>
  c.education_level_name != null &&
  /doctoral|professional|master/i.test(c.education_level_name);

export function SetYourCourseScreen() {
  const navigate = useNavigate();
  const profileName = useProfileStore((s) => s.profileName);
  const homeState = useProfileStore((s) => s.homeState);
  const t = useT();
  const {
    school,
    effort,
    loans,
    setSchool,
    setPrograms,
    setEffort,
    setLoans,
    clearSchool,
    reset,
    initialResolution,
    currentResolution,
    programs,
  } = useBuildInputStore();
  const selectedCareer = useBuildStore((s) => s.selectedCareer);
  const setSelectedCareer = useBuildStore((s) => s.setSelectedCareer);

  const [majorText, setMajorText] = useState("");

  // Scope-aware Ask Gemma chat — opens from the per-career sparkle on
  // CareerCard with a "Describe in detail what this career does" opener
  // that fires automatically. No build_id yet (the student is picking).
  const [chatOpen, setChatOpen] = useState(false);
  const [chatScope, setChatScope] = useState<AskScope | null>(null);
  const [chatChipText, setChatChipText] = useState<string>("");
  const [chatOpenerPrompt, setChatOpenerPrompt] = useState<string | null>(null);

  // Career-description state passed into <GemmaChat>. null = not started,
  // "loading" = fetch in flight, "error" = fetch failed (panel falls back
  // to existing freeform chat opener), CareerDescription = populated.
  const [careerDescription, setCareerDescription] = useState<
    CareerDescription | "loading" | "error" | null
  >(null);

  const handleAskCareer = useCallback((career: CareerOutcome) => {
    setChatScope({
      kind: "career",
      build_ids: [],
      target_id: career.soc_code,
      target_label: career.occupation_title,
    });
    setChatChipText(
      t("build.askPrefix").replace("{label}", career.occupation_title),
    );
    // No opener prompt — the structured "About this career" card IS the
    // answer to "what does this career do." Auto-firing the freeform
    // describe-in-detail opener was producing a duplicate description
    // beneath the card. Chat starts empty; the student types their own
    // follow-up if they want to dig deeper.
    setChatOpenerPrompt(null);
    setChatOpen(true);

    // Cache-first: synchronous hit → render populated; miss → loading
    // sentinel + dispatch fetch through the single-flight store.
    const cached = getCachedCareerDescription(career.soc_code);
    if (cached !== null) {
      setCareerDescription(cached);
      return;
    }
    setCareerDescription("loading");
    loadCareerDescription(career.soc_code, career.occupation_title)
      .then((desc) => {
        // Guard against a stale resolution if the user has clicked
        // through to a different SOC while this fetch was in flight.
        setCareerDescription((prev) =>
          prev === "loading" || prev === null ? desc : prev,
        );
      })
      .catch(() => {
        setCareerDescription((prev) =>
          prev === "loading" ? "error" : prev,
        );
      });
  }, [t]);

  const closeChat = useCallback(() => {
    setChatOpen(false);
    setChatOpenerPrompt(null);
  }, []);

  const {
    resolve,
    onChip,
    commit,
    onPickAlternative,
    streaming,
    busy,
    streamingText,
    error,
    suggestions,
    setCommittedClick,
    lastClarifier,
    debugTrace,
    revealedTrace,
    revealDone,
    clarifierDiverged,
    suggestedMajor,
    socReveal,
    gradCredentialNotice,
  } = useSetYourCourse(majorText);

  const location = useLocation();
  const isAdjustMode = Boolean(
    (location.state as { adjustMode?: boolean } | null)?.adjustMode
      && school
      && currentResolution
      && selectedCareer,
  );

  const [confirmStartOver, setConfirmStartOver] = useState(false);
  const reducedMotion = useReducedMotion();
  const slidersRef = useRef<HTMLDivElement>(null);
  const [highlightSliders, setHighlightSliders] = useState(false);
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Holds a chip-selected major text until React has committed the
  // school + majorText state updates triggered by the chip click. The
  // effect below then fires `resolve` with a fresh closure that sees the
  // newly-set school. See handleDemoChipPick for the why.
  const pendingChipMajorRef = useRef<string | null>(null);

  useEffect(() => {
    if (!school || !majorText) return;
    if (pendingChipMajorRef.current !== majorText) return;
    pendingChipMajorRef.current = null;
    resolve(majorText);
  }, [school, majorText, resolve]);

  useEffect(() => {
    if (isAdjustMode) {
      const timer = setTimeout(() => {
        slidersRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isAdjustMode]);

  // Residency-aware 4-year published cost — full COA sticker, with the
  // OOS tuition gap added for out-of-state public-school applicants.
  // Mirrors stat_engine._published_cost_4yr exactly. Per the 2026-05-02
  // cost-anchor change, this is THE cost number every screen shows; the
  // legacy "average net price" is no longer surfaced because it's an
  // average across other students' aid that doesn't apply to anyone in
  // particular before they've applied.
  const publishedCost4yr = useMemo<number | null>(() => {
    const coa = school?.costOfAttendanceAnnual;
    if (!coa || coa <= 0) return null;
    // Private — single sticker, no residency adjustment.
    if (!school?.institutionControl?.startsWith("Public")) return coa * 4;
    // Public — adjust upward when student is out-of-state.
    if (!homeState || !school.stateAbbr) return coa * 4;
    if (homeState === school.stateAbbr) return coa * 4;
    const inState = school.tuitionInState;
    const outState = school.tuitionOutOfState;
    if (inState == null || outState == null) return coa * 4;
    const gap = outState - inState;
    if (gap <= 0) return coa * 4;
    return (coa + gap) * 4;
  }, [school, homeState]);

  // Legacy field name retained for the EffortLoansPanel prop wiring
  // below — both the panel and the mocked fallback expect a per-year
  // cost. We pass `publishedCost4yr / 4` so the loans-slider math
  // (cost × 4 × loan_pct) lands on the same total as the backend's
  // (published_cost_4yr × loan_pct).
  const effectivePerYearCost = useMemo<number | null>(() => {
    if (publishedCost4yr === null) return null;
    return publishedCost4yr / 4;
  }, [publishedCost4yr]);

  // Speculative prefetch: fire stat engine + branches + career description
  // as soon as the student has a school, resolution, and selected career.
  // Re-fires when sliders change so the build stream always finds a matching
  // cache entry with the final slider values.
  const prefetchAbortRef = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!school || !currentResolution || !selectedCareer) return;

    prefetchAbortRef.current?.abort();
    const controller = new AbortController();
    prefetchAbortRef.current = controller;

    const lookupCip = currentResolution.parent_cip || currentResolution.matched_cip;
    const studentCip = currentResolution.parent_cip ? currentResolution.matched_cip : null;

    requestPrefetch({
      unitid: school.unitid,
      cipcode: lookupCip,
      soc_code: selectedCareer.soc_code,
      occupation_title: selectedCareer.occupation_title,
      effort: effort.level,
      loan_pct: loans.percentage / 100,
      student_major: currentResolution.student_major_text ?? null,
      student_cip: studentCip,
      intent_keywords: currentResolution.intent_keywords ?? [],
      home_state: homeState ?? null,
    }, controller.signal);

    return () => { controller.abort(); };
  }, [
    school?.unitid,
    currentResolution?.matched_cip,
    currentResolution?.parent_cip,
    selectedCareer?.soc_code,
    effort.level,
    loans.percentage,
    homeState,
  ]);

  // Profile guard — bounce to /profile if the profile isn't set. Stash this
  // route so ProfileScreen returns here after onboarding.
  useEffect(() => {
    if (!profileName) {
      sessionStorage.setItem("fp-after-profile", "/set-your-course");
      navigate("/profile", { replace: true });
    }
  }, [profileName, navigate]);

  async function handleSchoolSelect(selected: SchoolSelection) {
    setSchool(selected);
    try {
      const progs = await apiGet<ProgramResult[]>(
        `/schools/${selected.unitid}/programs`,
      );
      setPrograms(progs);
    } catch {
      setPrograms([]);
    }
  }

  // Demo-chip handler — seeds school + major. We can't call `resolve`
  // here directly because `resolve` short-circuits on `if (!school)` and
  // it captures `school` via closure; the closure is from the render
  // before this chip click, so it still sees the prior null. Stash the
  // chip's major in a ref instead and let the effect below fire `resolve`
  // once school + majorText have both propagated to a fresh render.
  async function handleDemoChipPick(chip: DemoChip) {
    pendingChipMajorRef.current = chip.majorText;
    try {
      await handleSchoolSelect(chip.school);
      setMajorText(chip.majorText);
    } catch {
      pendingChipMajorRef.current = null;
    }
  }

  function handleMajorChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setMajorText(value);
    resolve(value);
  }

  const handleCareerSelect = useCallback(
    (career: CareerOutcome) => {
      setSelectedCareer(career);
      setCommittedClick({
        soc: career.soc_code,
        title: career.occupation_title,
        feasibility: null,
      });
      fireCheckpoint("/set-your-course");
      // Soft cue: scroll the effort/loans sliders into view and pulse a
      // glow so the student notices them before clicking Spec my build.
      // Defer one frame so layout settles after the selection state update.
      // Offset for the fixed action bar at the bottom so the sliders fully
      // clear it instead of hiding under the menu.
      requestAnimationFrame(() => {
        const el = slidersRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const actionBar = document.querySelector(
          '[data-testid="action-bar"]',
        ) as HTMLElement | null;
        const obstruction = actionBar?.offsetHeight ?? 96;
        const breathingRoom = 24;
        const visibleBottom = window.innerHeight - obstruction - breathingRoom;
        if (rect.bottom > visibleBottom) {
          window.scrollBy({ top: rect.bottom - visibleBottom, behavior: "smooth" });
        } else if (rect.top < 80) {
          el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
      setHighlightSliders(true);
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = setTimeout(() => setHighlightSliders(false), 1800);
    },
    [setSelectedCareer, setCommittedClick],
  );

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    };
  }, []);

  function handleStartOverRequest() {
    setConfirmStartOver(true);
  }

  function handleStartOverConfirm() {
    setMajorText("");
    setSelectedCareer(null);
    reset();
    setConfirmStartOver(false);
    if (isAdjustMode) {
      navigate("/set-your-course", { replace: true });
    }
  }

  // Bundle 4: softNudge also fires on medium confidence. Gemma's
  // narrowing_hint is most actionable for medium-confidence resolutions
  // (e.g. "money" → Mathematics with a hint suggesting economics/finance);
  // surfacing the nudge color + chip row at medium gives the student a
  // visible affordance to course-correct.
  const lowConfidence =
    currentResolution?.confidence === "low" ||
    currentResolution?.confidence === "medium";
  const softNudge = lowConfidence ? t("syc.softNudge") : null;

  const normalizedInput = useMemo(
    () => majorText.trim().toLowerCase().replace(/\s+/g, " "),
    [majorText],
  );

  // Taxonomy receipt — shows the CIP code + title the resolution
  // lives under, plus the specific field of study inside it when
  // Gemma substituted through a broader school-reported parent.
  // Overrides spec §Decision #12 "no taxonomy leakage" for this one
  // line at founder direction. Uses the §Decision #14 acronym-spell-
  // out convention ("Classification of Instructional Programs (CIP)").
  const taxonomyReceipt = useMemo<{
    code: string;
    title: string;
    fieldOfStudy: string | null;
  } | null>(() => {
    if (!currentResolution || !currentResolution.matched_cip) return null;
    const matched = currentResolution.matched_cip;
    const matched4 = matched.slice(0, 5);
    const parent4 = (currentResolution.parent_cip || "").trim();

    // Try to find the school's reported program that backs the parent
    // (or, absent substitution, the matched CIP itself). Match on both
    // raw cipcode and the 4-digit prefix to absorb 4-vs-6-digit
    // storage quirks in the programs list.
    const findProgramTitle = (fourDigit: string): string | null => {
      if (!fourDigit) return null;
      for (const p of programs) {
        const raw = String(p.cipcode || "").trim();
        if (!raw) continue;
        const canonical = raw.slice(0, 5);
        if (
          raw === fourDigit ||
          canonical === fourDigit ||
          raw === `${fourDigit}00` ||
          raw === `${fourDigit}0`
        ) {
          return p.program_name || null;
        }
      }
      return null;
    };

    if (parent4 && parent4 !== matched4) {
      const parentTitle =
        findProgramTitle(parent4) || "the school's reported program";
      return {
        code: matched,
        title: currentResolution.matched_title || "",
        fieldOfStudy: parentTitle,
      };
    }

    return {
      code: matched,
      title: currentResolution.matched_title || "",
      fieldOfStudy: null,
    };
  }, [currentResolution, programs]);

  const loadedOutcomes = socReveal.kind === "outcomes-loaded" ? socReveal.outcomes : [];

  // Dedupe by soc_code before partitioning into tiers. The gold table's
  // consumable.program_career_paths can carry multiple rows per
  // (unitid, cipcode, soc_code) — typically when the same SOC reaches
  // the school through more than one crosswalk source. Without this
  // dedupe, CareerTierSection renders <CareerCard key={career.soc_code}
  // ...> and React collapses the duplicates into the first, silently
  // dropping the second card while emitting a "Encountered two children
  // with the same key" console warning. Keep first occurrence because
  // upstream rows are already sorted by stats_available_count DESC, so
  // "first" is also "best-attested."
  const uniqueOutcomes = useMemo<CareerOutcome[]>(() => {
    const seen = new Set<string>();
    return loadedOutcomes.filter((c) => {
      if (seen.has(c.soc_code)) return false;
      seen.add(c.soc_code);
      return true;
    });
  }, [loadedOutcomes]);

  const careerPaths = useMemo<CareerOutcome[]>(
    () => uniqueOutcomes.filter((c) => !isPostgrad(c)),
    [uniqueOutcomes],
  );
  const postgradCareers = useMemo<CareerOutcome[]>(
    () => uniqueOutcomes.filter(isPostgrad),
    [uniqueOutcomes],
  );
  // Experience-based grouping (BLS OOH work_experience_code):
  //   3 → "Likely first jobs" (no related experience required)
  //   2 + null → "Early-career roles" (<5 years, or unknown)
  //   1 → "Where this can lead long-term" (5+ years required)
  // Within each section the existing stats_available_count DESC ordering
  // from the upstream loadedOutcomes carries through. Empty sections are
  // hidden by CareerTierSection's own length-0 guard.
  const firstJobsCareers = useMemo<CareerOutcome[]>(
    () => careerPaths.filter((c) => c.work_experience_code === 3),
    [careerPaths],
  );
  const earlyCareerCareers = useMemo<CareerOutcome[]>(
    () =>
      careerPaths.filter(
        (c) => c.work_experience_code === 2 || c.work_experience_code == null,
      ),
    [careerPaths],
  );
  const longTermCareers = useMemo<CareerOutcome[]>(
    () => careerPaths.filter((c) => c.work_experience_code === 1),
    [careerPaths],
  );

  const hasOutcomes = careerPaths.length > 0 || postgradCareers.length > 0;

  if (!profileName) return null;

  return (
    <div className="min-h-screen relative pt-14 pb-32">
      <PageContainer variant="centered" className="py-10">
        <div className="flex flex-col gap-8">
          <header className="max-w-[560px]">
            <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info mb-2">
              {t("syc.kicker")}
            </p>
            <h1 className="font-display text-heading font-semibold text-text-primary leading-tight">
              {isAdjustMode ? t("syc.headingAdjust") : t("syc.heading")}
            </h1>
            <p className="font-body text-body text-text-secondary mt-3 max-w-[44ch]">
              {isAdjustMode ? t("syc.subtitleAdjust") : t("syc.subtitle")}
            </p>
          </header>

          {/* Sealed context badges (adjust mode) */}
          {isAdjustMode && (
            <SealedBuildContext
              school={school!}
              resolvedTitle={currentResolution!.matched_title}
              cipCode={currentResolution!.matched_cip}
              career={selectedCareer!}
              onStartOver={handleStartOverRequest}
            />
          )}

          {/* ROW 1 — School/major inputs (left) + Gemma conversation (right) */}
          {!isAdjustMode && <div className="grid grid-cols-1 desktop:grid-cols-2 gap-6 desktop:gap-8 items-start">
            <section aria-label={t("syc.aria.yourInputs")} className="flex flex-col gap-6">
              <DemoChipsDrawer
                disabled={streaming || busy}
                onPick={handleDemoChipPick}
              />
              <div>
                <label className="block font-body text-small font-bold text-text-secondary tracking-wide mb-2">
                  {t("syc.schoolLabel")}
                </label>
                <SchoolSearch
                  selected={school}
                  onSelect={handleSchoolSelect}
                  onClear={() => {
                    clearSchool();
                    setMajorText("");
                    // If the user clears the school WHILE a chip-driven
                    // resolve is still pending (the effect hasn't fired
                    // yet because school was just nulled), drop the
                    // pending major. Otherwise the next school they pick
                    // would silently trigger an unrelated chip's resolve.
                    pendingChipMajorRef.current = null;
                  }}
                />
              </div>

              <AnimatePresence>
                {school && (
                  <motion.div
                    key="major-input"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={springs.smooth}
                  >
                    <label
                      htmlFor="set-your-course-major"
                      className="block font-body text-small font-bold text-text-secondary tracking-wide mb-2"
                    >
                      {t("syc.majorLabel")}
                    </label>
                    <input
                      id="set-your-course-major"
                      type="text"
                      value={majorText}
                      onChange={handleMajorChange}
                      placeholder={t("syc.majorPlaceholder")}
                      autoComplete="off"
                      maxLength={200}
                      data-testid="major-input"
                      className="w-full h-14 bg-bp-deep text-text-primary font-body text-body rounded-lg border border-border px-5 focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-all duration-normal placeholder:text-text-muted placeholder:italic"
                    />
                  </motion.div>
                )}
              </AnimatePresence>

              {/* "Not what I expected?" — appears after results load */}
              {hasOutcomes && currentResolution && !streaming && (
                <AskGemmaChip
                  onChip={(id, clarifier) => onChip(id, clarifier)}
                  busy={busy}
                  softNudge={lowConfidence}
                />
              )}
            </section>

            <section aria-label={t("syc.aria.gemmaConversation")} className="flex flex-col">
              {/* Single AnimatePresence with mode="wait" ensures the streaming
                  card fully exits before the resolution header enters — no
                  overlap, no layout shift. */}
              <AnimatePresence mode="wait">
                {/* Streaming readout */}
                {streaming && (
                  <motion.div
                    key="streaming"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={springs.smooth}
                    className="relative rounded-xl bg-bp-mid/60 border border-border-subtle border-l-[3px] border-l-accent-insight p-5 shadow-md"
                    data-testid="gemma-streaming"
                  >
                    <div className="flex items-center gap-3 mb-3">
                      <GemmaSpinner size={20} />
                      <span className="font-body text-small text-text-secondary">
                        {t("syc.gemmaThinking")}
                      </span>
                    </div>
                    <p className="font-body text-body text-text-primary leading-relaxed whitespace-pre-wrap animate-gemma-shimmer-loop">
                      {streamingText || t("syc.gemmaReading")}
                      <span
                        aria-hidden="true"
                        className="inline-block w-2 h-[1.1em] bg-accent-insight align-text-bottom ml-[2px] animate-terminal-cursor"
                      />
                    </p>
                  </motion.div>
                )}

                {/* Resolution header */}
                {currentResolution && !streaming && (
                  <motion.div
                    key="resolved"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={springs.smooth}
                    className="flex flex-col gap-1"
                    data-testid="current-resolution-summary"
                  >
                    <div className="flex items-center gap-[6px] font-body text-small text-text-muted">
                      <GemmaStar size={18} />
                      <span>{t("syc.gemmaMatched")}</span>
                      <span
                        className={`font-bold ${lowConfidence ? "text-accent-caution" : "text-accent-insight"}`}
                      >
                        &ldquo;{majorText || currentResolution.matched_title}&rdquo;
                      </span>
                      {currentResolution.matched_cip && (
                        <>
                          <span>{t("syc.toCip")}</span>
                          <span className="font-data font-semibold text-text-secondary">
                            {currentResolution.matched_cip}
                          </span>
                        </>
                      )}
                    </div>
                    <div className="flex items-baseline gap-3 pl-[22px] min-h-[3.5em]">
                      <span
                        className={`font-display text-subheading font-semibold ${lowConfidence ? "text-accent-caution" : "text-accent-insight"}`}
                      >
                        {currentResolution.matched_title}
                      </span>
                      {currentResolution.confirmed_focus ? (
                        <span className="font-body text-small text-text-secondary">
                          · {currentResolution.confirmed_focus}
                        </span>
                      ) : null}
                    </div>
                    {taxonomyReceipt?.fieldOfStudy && (
                      <p
                        className="pl-[22px] mt-2 font-body text-small text-text-muted leading-relaxed"
                        data-testid="taxonomy-receipt"
                      >
                        <span>{t("syc.reportedAs")} </span>
                        <span className="font-semibold text-accent-insight">
                          {taxonomyReceipt.fieldOfStudy}
                        </span>
                        <span>.</span>
                      </p>
                    )}
                    {initialResolution?.alternatives && initialResolution.alternatives.length > 0 && (
                      <CipPicker
                        initial={initialResolution}
                        current={currentResolution}
                        onPick={onPickAlternative}
                      />
                    )}
                    {/* Bundle 4: render Gemma's narrowing_hint inline when
                        there are NO alternatives (otherwise CipPicker shows
                        it). Common for medium-confidence one-word inputs
                        like "money" → Mathematics with a real suggestion
                        the student should see. */}
                    {currentResolution.narrowing_hint &&
                      (!initialResolution?.alternatives ||
                        initialResolution.alternatives.length === 0) && (
                        <p
                          className="pl-[22px] mt-2 font-body text-small text-text-secondary leading-relaxed"
                          data-testid="narrowing-hint-inline"
                        >
                          {currentResolution.narrowing_hint}
                        </p>
                      )}
                  </motion.div>
                )}
              </AnimatePresence>

              {error && (
                <p
                  role="alert"
                  className="font-body text-small text-accent-alert mt-2"
                  data-testid="set-your-course-error"
                >
                  {error}
                </p>
              )}

              {/* Reasoning card */}
              <AnimatePresence mode="wait">
                {(busy || debugTrace) && (
                  <motion.div
                    key={debugTrace ?? "pending"}
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={springs.smooth}
                    className="mt-4 rounded-xl bg-bp-mid/60 border border-border-subtle border-l-[3px] border-l-accent-insight p-5 shadow-md"
                    data-testid="reasoning-card"
                  >
                    <div className="flex items-start gap-3">
                      <GemmaSpinner
                        size={20}
                        className={busy ? "" : "opacity-40"}
                      />
                      <div className="flex-1 min-w-0">
                        {lastClarifier && (
                          <p className="font-data text-micro text-text-muted mb-2">
                            &ldquo;{lastClarifier}&rdquo;
                            {!busy && debugTrace && currentResolution && (
                              <span className="ml-2 text-text-muted/70">
                                → {currentResolution.matched_title}
                              </span>
                            )}
                          </p>
                        )}
                        <p
                          className={[
                            "font-body text-body text-text-primary leading-relaxed whitespace-pre-wrap",
                            busy ? "animate-gemma-shimmer-loop" : "",
                          ].join(" ")}
                        >
                          {busy
                            ? t("syc.gemmaReasoning")
                            : revealedTrace}
                          {(busy || !revealDone) && (
                            <span
                              aria-hidden="true"
                              className="inline-block w-2 h-[1.1em] bg-accent-insight align-text-bottom ml-[2px] animate-terminal-cursor"
                            />
                          )}
                        </p>

                        {!busy &&
                          revealDone &&
                          clarifierDiverged &&
                          lastClarifier && (
                            <div className="mt-5 pt-4 border-t border-white/5 flex flex-wrap items-center gap-x-4 gap-y-2">
                              <button
                                type="button"
                                onClick={() => {
                                  const next = suggestedMajor || lastClarifier;
                                  setMajorText(next);
                                  resolve(next);
                                }}
                                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-insight/15 hover:bg-accent-insight/25 text-accent-insight font-display font-medium text-small ring-1 ring-accent-insight/30 hover:ring-accent-insight/50 transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]"
                                data-testid="btn-try-clarifier"
                              >
                                <span className="opacity-60">→</span>
                                Try &ldquo;{suggestedMajor || lastClarifier}&rdquo; {t("syc.tryAs")}
                              </button>
                              <span
                                aria-disabled="true"
                                title={t("syc.comingSoon")}
                                className="cursor-not-allowed inline-flex items-center gap-2 font-body text-small text-text-muted/70"
                                data-testid="btn-search-schools"
                              >
                                {t("syc.searchSchools")}
                                <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/5 text-text-muted/60">
                                  {t("syc.soon")}
                                </span>
                              </span>
                            </div>
                          )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </section>
          </div>}

          {/* Program not offered at this school */}
          {!isAdjustMode && currentResolution?.program_not_at_school && !streaming && school && (
            <motion.section
              key="not-offered"
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reducedMotion ? { duration: 0 } : springs.smooth}
              className="flex flex-col gap-4"
              data-testid="program-not-at-school"
            >
              <p className="font-body text-body text-text-secondary">
                {t("syc.notOfferedAtSchool")
                  .replace("{school}", school.name)
                  .replace("{program}", currentResolution.matched_title || majorText)}
              </p>
              {programs.length > 0 && (
                <div>
                  <p className="font-body text-small text-text-muted mb-3">
                    {t("syc.tryInstead").replace("{school}", school.name)}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {programs.map((p) => (
                      <button
                        key={p.cipcode}
                        type="button"
                        onClick={() => {
                          setMajorText(p.program_name);
                          resolve(p.program_name);
                        }}
                        className="px-3 py-1.5 rounded-full bg-white/5 hover:bg-white/10 text-text-secondary hover:text-text-primary font-body text-small ring-1 ring-white/10 hover:ring-white/20 transition-colors duration-normal"
                      >
                        {p.program_name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </motion.section>
          )}

          {/* ROW 2 — Career cards (full width) */}
          {!isAdjustMode && currentResolution && !currentResolution.program_not_at_school && !streaming && !clarifierDiverged && (
            <motion.section
              key={currentResolution.matched_cip}
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reducedMotion ? { duration: 0 } : springs.smooth}
              aria-label={t("syc.aria.careerPaths")}
              className="flex flex-col gap-6"
            >
              {currentResolution.matched_cip ? (
                <p className="font-body text-small italic text-text-muted">
                  {t("syc.showingSoc")} {currentResolution.matched_cip.slice(0, 5)}.
                </p>
              ) : (
                // No-match path: Gemma resolved but the matched_cip was
                // not a real CIP at this school (coerced to "" in
                // useSetYourCourse). Give the student a concrete next
                // step instead of leaving the page blank.
                <div
                  data-testid="syc-no-match-hint"
                  role="status"
                  className={[
                    "rounded-xl",
                    "border border-border-subtle",
                    "border-l-[3px] border-l-accent-caution",
                    "bg-bp-mid/60 p-4",
                  ].join(" ")}
                >
                  <p className="font-body text-small text-text-secondary leading-relaxed">
                    {t("syc.noMatch.body", {
                      majorText: majorText || "",
                      schoolName: school?.name ?? "",
                    })}
                  </p>
                </div>
              )}
              {/* GradCredentialNotice render slot — fires when chip dispatch
                  or pre-flag short-circuit detects a grad-school requirement.
                  The GradCredentialNotice component will be wired here once
                  the design visionary builds it. */}
              {gradCredentialNotice && (
                <div
                  data-testid="grad-credential-notice-slot"
                  className="rounded-xl border border-border-default bg-surface-elevated p-4"
                >
                  <p className="font-body text-small text-text-secondary">
                    <span className="font-semibold text-text-primary">&ldquo;{gradCredentialNotice.target_career_title}&rdquo;</span>{" "}
                    requires a{" "}
                    <strong>{gradCredentialNotice.credential_name_full}</strong>{" "}
                    ({gradCredentialNotice.credential_acronym}), so the careers
                    below reflect what you can do with the undergraduate degree
                    most students pursue on that path.
                  </p>
                </div>
              )}
              {socReveal.kind === "outcomes-loading" && <CareerListSkeleton />}
              {socReveal.kind === "error" && (
                <p className="font-body text-small text-accent-alert">
                  {socReveal.message}
                </p>
              )}
              {/* Experience-based grouping (work_experience_code).
                  Each section renders only when non-empty so empty
                  buckets don't take screen space. Order matters:
                  first jobs → early-career → long-term. */}
              {firstJobsCareers.length > 0 && (
                <CareerTierSection
                  id="tier-first-jobs"
                  label={t("syc.firstJobs")}
                  description={t("syc.firstJobsDesc")}
                  accent="common"
                  careers={firstJobsCareers}
                  pickedSoc={selectedCareer?.soc_code ?? null}
                  onSelect={handleCareerSelect}
                  ernShift={effort.ernShift}
                  onAskGemma={handleAskCareer}
                />
              )}
              {earlyCareerCareers.length > 0 && (
                <CareerTierSection
                  id="tier-early-career"
                  label={t("syc.earlyCareer")}
                  description={t("syc.earlyCareerDesc")}
                  accent="common"
                  careers={earlyCareerCareers}
                  pickedSoc={selectedCareer?.soc_code ?? null}
                  onSelect={handleCareerSelect}
                  ernShift={effort.ernShift}
                  onAskGemma={handleAskCareer}
                />
              )}
              {longTermCareers.length > 0 && (
                <CareerTierSection
                  id="tier-long-term"
                  label={t("syc.longTerm")}
                  description={t("syc.longTermDesc")}
                  accent="common"
                  careers={longTermCareers}
                  pickedSoc={selectedCareer?.soc_code ?? null}
                  onSelect={handleCareerSelect}
                  ernShift={effort.ernShift}
                  onAskGemma={handleAskCareer}
                />
              )}
              {postgradCareers.length > 0 && (
                <CareerTierSection
                  id="tier-postgrad"
                  label={t("syc.postgradLabel")}
                  description={t("syc.postgradDesc")}
                  accent="postgrad"
                  careers={postgradCareers}
                  pickedSoc={selectedCareer?.soc_code ?? null}
                  onSelect={handleCareerSelect}
                  ernShift={effort.ernShift}
                  onAskGemma={handleAskCareer}
                />
              )}
            </motion.section>
          )}

          {/* Community Suggestions */}
          {!isAdjustMode && school && suggestions.length > 0 && (
            <CommunitySuggestions
              suggestions={suggestions}
              inputText={majorText}
              schoolName={school.name}
              onSelect={(s) => {
                setCommittedClick({
                  soc: s.clicked_soc,
                  title: s.clicked_career_title,
                  feasibility: null,
                });
              }}
            />
          )}

          {/* ROW 3 — Effort/loans sliders */}
          <AnimatePresence>
            {(isAdjustMode || (hasOutcomes && currentResolution && !streaming && !clarifierDiverged)) && (
              <motion.section
                ref={slidersRef}
                key="effort-commit"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={springs.smooth}
                aria-label={t("syc.aria.effortLoans")}
                data-testid="effort-commit-section"
              >
                <EffortLoansPanel
                  effort={effort}
                  loans={loans}
                  onEffortChange={setEffort}
                  onLoanChange={setLoans}
                  profileName={profileName}
                  onSubmit={() => void commit()}
                  submitting={busy}
                  netPriceAnnual={effectivePerYearCost}
                  highlight={highlightSliders}
                />
                {softNudge && (
                  <p
                    className="mt-3 text-center italic font-body text-small text-text-muted"
                    data-testid="soft-nudge"
                  >
                    {softNudge}
                  </p>
                )}
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </PageContainer>

      {/* Sticky bottom action bar — sibling of PageContainer so framer transforms
          on inner sections don't promote it into a transformed containing block
          and break `position: fixed`. */}
      <AnimatePresence>
        {(isAdjustMode || (hasOutcomes && currentResolution && !streaming && !clarifierDiverged)) && (
          <motion.div
            key="action-bar"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 24 }}
            transition={springs.smooth}
            className="fixed inset-x-0 bottom-0 z-40 bg-bp-deep/85 backdrop-blur-lg"
            style={{
              boxShadow:
                "inset 0 1px 0 0 rgba(245, 240, 232, 0.06), 0 -12px 32px -8px rgba(0, 0, 0, 0.45), 0 -1px 0 0 rgba(0, 0, 0, 0.4)",
            }}
            data-testid="action-bar"
          >
            <PageContainer variant="centered" className="py-4">
              <div
                className="grid grid-cols-[1fr_2fr] gap-4"
                style={{ paddingBottom: "max(0px, env(safe-area-inset-bottom))" }}
              >
                <Button
                  variant="ghost"
                  onClick={handleStartOverRequest}
                  disabled={busy}
                  data-testid="btn-start-over"
                  className="w-full h-12"
                >
                  {t("syc.startOver")}
                </Button>
                <motion.button
                  onClick={() => void commit()}
                  disabled={busy || !selectedCareer}
                  title={!selectedCareer ? t("syc.pickCareerFirst") : undefined}
                  className="w-full bg-accent-thrive text-text-inverse font-body font-bold text-cta h-12 rounded-lg cursor-pointer hover:bg-[#6bc494] hover:shadow-glow-thrive transition-all duration-normal disabled:opacity-60 disabled:cursor-not-allowed"
                  whileTap={busy || !selectedCareer ? undefined : { scale: 0.97 }}
                  transition={springs.snappy}
                  data-testid="btn-spec-build-bottom"
                >
                  {busy
                    ? t("syc.specing").replace("{profileName}", profileName ?? "")
                    : selectedCareer
                      ? t("syc.specBuild")
                      : t("syc.chooseCareer")}
                </motion.button>
              </div>
            </PageContainer>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Start-over confirm dialog. */}
      <AnimatePresence>
        {confirmStartOver && (
          <motion.div
            key="confirm-overlay"
            className="fixed inset-0 z-50 bg-bp-void/70 backdrop-blur-sm flex items-center justify-center px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            role="dialog"
            aria-modal="true"
            aria-label={t("syc.aria.confirmStartOver")}
          >
            <motion.div
              className="bg-bp-mid border border-border rounded-xl p-6 max-w-sm w-full space-y-4"
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={springs.smooth}
              data-testid="confirm-start-over"
            >
              <p className="font-display text-subheading text-text-primary">
                {t("syc.confirmClear")}
              </p>
              <p className="font-body text-small text-text-secondary">
                {t("syc.confirmClearBody")}
              </p>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  variant="ghost"
                  onClick={() => setConfirmStartOver(false)}
                  data-testid="btn-keep-going"
                >
                  {t("syc.keepGoing")}
                </Button>
                <Button
                  variant="primary"
                  onClick={handleStartOverConfirm}
                  data-testid="btn-confirm-start-over"
                >
                  {t("syc.yesStartOver")}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <span className="sr-only" data-testid="normalized-input">
        {normalizedInput}
      </span>

      {/* Scope-aware Ask Gemma slide-in. Build is null because no build
          exists yet at this stage; the chat opens with a "career" scope
          plus the auto-fired opener prompt set by handleAskCareer. */}
      <GemmaChat
        open={chatOpen}
        build={null}
        scope={chatScope ?? undefined}
        chipText={chatChipText}
        openerPrompt={chatOpenerPrompt ?? undefined}
        careerDescription={careerDescription}
        starters={[]}
        onClose={closeChat}
      />
    </div>
  );
}
