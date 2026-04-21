import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiGet } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useSetYourCourse } from "@/hooks/useSetYourCourse";
import { SchoolSearch } from "@/components/school/SchoolSearch";
import { EffortLoansPanel } from "@/components/school/EffortLoansPanel";
import { AskGemmaChip } from "@/components/school/AskGemmaChip";
import { CareerListSkeleton } from "@/components/school/CareerListSkeleton";
import { CareerTierSection } from "@/components/CareerTierSection";
import { CommunitySuggestions } from "@/components/school/CommunitySuggestions";
import { Button } from "@/components/ui/Button";
import { GemmaStar } from "@/components/ui/GemmaStar";
import { GemmaSpinner } from "@/components/ui/GemmaSpinner";
import { PageContainer } from "@/components/ui/PageContainer";
import type {
  ProgramResult,
  SchoolSelection,
} from "@/types/buildInput";
import type { CareerOutcome } from "@/types/build";

export function SetYourCourseScreen() {
  const navigate = useNavigate();
  const profileName = useProfileStore((s) => s.profileName);
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
    currentResolution,
    programs,
  } = useBuildInputStore();
  const selectedCareer = useBuildStore((s) => s.selectedCareer);
  const setSelectedCareer = useBuildStore((s) => s.setSelectedCareer);

  const [majorText, setMajorText] = useState("");

  const {
    resolve,
    onChip,
    commit,
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
  } = useSetYourCourse(majorText);

  const [effortExpanded, setEffortExpanded] = useState(false);
  const [confirmStartOver, setConfirmStartOver] = useState(false);
  const reducedMotion = useReducedMotion();

  // Profile guard — bounce to /app if the profile isn't set. Stash this
  // route so ProfileScreen returns here after onboarding.
  useEffect(() => {
    if (!profileName) {
      sessionStorage.setItem("fp-after-profile", "/set-your-course");
      navigate("/app", { replace: true });
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
    },
    [setSelectedCareer, setCommittedClick],
  );

  function handleStartOverRequest() {
    setConfirmStartOver(true);
  }

  function handleStartOverConfirm() {
    setMajorText("");
    setSelectedCareer(null);
    reset();
    setConfirmStartOver(false);
  }

  const canCommit =
    Boolean(currentResolution) &&
    Boolean(school) &&
    !streaming &&
    !busy;

  const lowConfidence = currentResolution?.confidence === "low";
  const softNudge = lowConfidence
    ? "Gemma wasn't sure on this one. Worth a sanity check?"
    : null;

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
      // Substitution applies — surface the school's broader program
      // as the CIP receipt, and the matched leaf as the field of study.
      const parentTitle =
        findProgramTitle(parent4) || "the school's reported program";
      return {
        code: parent4,
        title: parentTitle,
        fieldOfStudy: currentResolution.matched_title || null,
      };
    }

    // No substitution — show the matched code + title directly.
    return {
      code: matched4,
      title: currentResolution.matched_title || "",
      fieldOfStudy: null,
    };
  }, [currentResolution, programs]);

  const tieredCareers = socReveal.kind === "tiered" ? socReveal.tiers : null;

  const isPostgrad = (c: CareerOutcome) =>
    c.education_level_name != null &&
    /doctoral|professional|master/i.test(c.education_level_name);

  const commonCareers = useMemo<CareerOutcome[]>(
    () => (tieredCareers ? tieredCareers.common.filter((c) => !isPostgrad(c)).slice(0, 6) : []),
    [tieredCareers],
  );
  const uncommonCareers = useMemo<CareerOutcome[]>(
    () =>
      tieredCareers
        ? [...tieredCareers.less_common, ...tieredCareers.stretch].filter((c) => !isPostgrad(c))
        : [],
    [tieredCareers],
  );
  const postgradCareers = useMemo<CareerOutcome[]>(
    () =>
      tieredCareers
        ? [
            ...tieredCareers.common,
            ...tieredCareers.less_common,
            ...tieredCareers.stretch,
          ].filter(isPostgrad)
        : [],
    [tieredCareers],
  );

  const outcomesForIntermediate = useMemo<CareerOutcome[]>(
    () =>
      socReveal.kind === "outcomes-loaded-tiering"
        ? socReveal.outcomes.filter((c) => !isPostgrad(c)).slice(0, 6)
        : [],
    [socReveal],
  );
  const postgradIntermediate = useMemo<CareerOutcome[]>(
    () =>
      socReveal.kind === "outcomes-loaded-tiering"
        ? socReveal.outcomes.filter(isPostgrad)
        : [],
    [socReveal],
  );

  if (!profileName) return null;

  return (
    <div className="min-h-screen relative pt-14 pb-[calc(var(--space-6)+96px)] tablet:pb-10">
      <PageContainer variant="centered" className="py-10">
        <div className="flex flex-col gap-8">
          <header className="max-w-[560px]">
            <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info mb-2">
              Set your course
            </p>
            <h1 className="font-display text-heading font-semibold text-text-primary leading-tight">
              Where does this take you?
            </h1>
            <p className="font-body text-body text-text-secondary mt-3 max-w-[44ch]">
              Pick a school and a field of study. The careers follow.
            </p>
          </header>

          <div className="grid grid-cols-1 desktop:grid-cols-[4fr_8fr] gap-6 desktop:gap-8 items-start">
            {/* LEFT — inputs + effort/loans disclosure */}
            <section aria-label="Your inputs" className="flex flex-col gap-6">
              <div>
                <label className="block font-body text-small font-bold text-text-secondary tracking-wide mb-2">
                  Your school
                </label>
                <SchoolSearch
                  selected={school}
                  onSelect={handleSchoolSelect}
                  onClear={() => {
                    clearSchool();
                    setMajorText("");
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
                      Your field of study
                    </label>
                    <input
                      id="set-your-course-major"
                      type="text"
                      value={majorText}
                      onChange={handleMajorChange}
                      placeholder="What are you studying?"
                      autoComplete="off"
                      data-testid="major-input"
                      className="w-full h-14 bg-bp-deep text-text-primary font-body text-body rounded-lg border border-border px-5 focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-all duration-normal placeholder:text-text-muted placeholder:italic"
                    />
                  </motion.div>
                )}
              </AnimatePresence>

              {school && (
                <div>
                  <button
                    type="button"
                    onClick={() => setEffortExpanded((v) => !v)}
                    aria-expanded={effortExpanded}
                    data-testid="effort-disclosure"
                    className="inline-flex items-center gap-2 py-2 font-body text-small text-text-muted hover:text-text-secondary cursor-pointer transition-colors duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] rounded"
                  >
                    <span className="font-data text-data-sm">
                      {effortExpanded ? "▾" : "▸"}
                    </span>
                    {effortExpanded ? "Hide" : "Show"} effort &amp; loans
                  </button>
                  <AnimatePresence initial={false}>
                    {effortExpanded && (
                      <motion.div
                        key="effort-panel"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={springs.smooth}
                        className="overflow-hidden mt-3"
                      >
                        <EffortLoansPanel
                          effort={effort}
                          loans={loans}
                          onEffortChange={setEffort}
                          onLoanChange={setLoans}
                          profileName={profileName}
                          onSubmit={() => void commit()}
                          submitting={busy}
                          netPriceAnnual={school.netPriceAnnual}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </section>

            {/* RIGHT — preview + chips */}
            <section aria-label="Career preview" className="flex flex-col">
              {/* Empty state — before any resolution */}
              {!streaming && !currentResolution && (
                <div
                  className="min-h-[340px] rounded-xl border border-dashed border-border-subtle flex flex-col items-center justify-center gap-5 p-10 text-center"
                  data-testid="preview-empty"
                >
                  <div className="flex gap-4" aria-hidden="true">
                    <span className="w-1 h-1 rounded-full bg-bp-raised/40" />
                    <span className="w-1 h-1 rounded-full bg-bp-raised/40" />
                    <span className="w-1 h-1 rounded-full bg-bp-raised/40" />
                  </div>
                  <p className="font-body text-body italic text-text-muted max-w-[30ch]">
                    The careers will show up here as you type.
                  </p>
                  <div className="flex gap-4" aria-hidden="true">
                    <span className="w-1 h-1 rounded-full bg-bp-raised/40" />
                    <span className="w-1 h-1 rounded-full bg-bp-raised/40" />
                    <span className="w-1 h-1 rounded-full bg-bp-raised/40" />
                  </div>
                </div>
              )}

              {/* Streaming readout — morphs into the resolution header
                  when the stream completes. Card has a breathing glow
                  and an insight-colored rule on the left. The spinning
                  GemmaSpinner sits inline next to the "thinking" label;
                  when no prose has arrived yet, the label itself shimmers
                  via the looping .animate-gemma-shimmer-loop utility. */}
              <AnimatePresence mode="wait">
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
                        Gemma is thinking
                      </span>
                    </div>
                    {/* Arriving prose block — shimmer wipes across the
                        text, cursor-square blinks at the tail. Matches
                        mockup scenario 02's .reasoning-card .arriving. */}
                    <p className="font-body text-body text-text-primary leading-relaxed whitespace-pre-wrap animate-gemma-shimmer-loop">
                      {streamingText || "Reading your input…"}
                      <span
                        aria-hidden="true"
                        className="inline-block w-2 h-[1.1em] bg-accent-insight align-text-bottom ml-[2px] animate-terminal-cursor"
                      />
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Resolution header — compact "Gemma matched" row + big
                  resolved title, insight-colored (caution when low conf). */}
              {currentResolution && !streaming && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={springs.smooth}
                  className="flex flex-col gap-1 mb-6"
                  data-testid="current-resolution-summary"
                >
                  <div className="flex items-center gap-[6px] font-body text-small text-text-muted">
                    <GemmaStar size={18} />
                    <span>Gemma matched</span>
                    <span
                      className={`font-bold ${lowConfidence ? "text-accent-caution" : "text-accent-insight"}`}
                    >
                      &ldquo;{majorText || currentResolution.matched_title}&rdquo;
                    </span>
                  </div>
                  <div className="flex items-baseline gap-3 pl-[22px]">
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
                  {taxonomyReceipt && (
                    <p
                      className="pl-[22px] mt-2 font-body text-small text-text-muted leading-relaxed"
                      data-testid="taxonomy-receipt"
                    >
                      <span>Classification of Instructional Programs (CIP) code is </span>
                      <span className="font-data font-semibold text-text-secondary">
                        {taxonomyReceipt.code}
                      </span>
                      <span> — {taxonomyReceipt.title}</span>
                      {taxonomyReceipt.fieldOfStudy && (
                        <>
                          <span>, field of study is </span>
                          <span className="font-semibold text-accent-insight">
                            {taxonomyReceipt.fieldOfStudy}
                          </span>
                        </>
                      )}
                      <span>.</span>
                    </p>
                  )}
                </motion.div>
              )}

              {error && (
                <p
                  role="alert"
                  className="font-body text-small text-accent-alert mt-2"
                  data-testid="set-your-course-error"
                >
                  {error}
                </p>
              )}

              {/* Reasoning card — fills the gap between "Ask Gemma"
                  submit and the debug-trace response arriving. Shows a
                  shimmering spinner + pending copy while the dispatch
                  is in flight; flips to an echo of the clarifier + a
                  character-by-character reveal of Gemma's prose once
                  the response lands. If the resolution didn't change,
                  the "(unchanged)" tag makes the non-change explicit. */}
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
                            ? "Gemma is reasoning about your clarifier…"
                            : revealedTrace}
                          {(busy || !revealDone) && (
                            <span
                              aria-hidden="true"
                              className="inline-block w-2 h-[1.1em] bg-accent-insight align-text-bottom ml-[2px] animate-terminal-cursor"
                            />
                          )}
                        </p>

                        {/* Follow-up offers — Gemma's hand-off.
                            Rendered only when the clarifier diverged
                            from the current resolution and the reveal
                            has caught up. Pill = insight-voiced offer
                            (not a thrive CTA); secondary link with a
                            "soon" chip for the future school-search. */}
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
                                Try &ldquo;{suggestedMajor || lastClarifier}&rdquo; as the field of study
                              </button>
                              <span
                                aria-disabled="true"
                                title="Coming soon"
                                className="cursor-not-allowed inline-flex items-center gap-2 font-body text-small text-text-muted/70"
                                data-testid="btn-search-schools"
                              >
                                Search schools that offer this program
                                <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/5 text-text-muted/60">
                                  Soon
                                </span>
                              </span>
                            </div>
                          )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Career tier cards — always-open sections, no chapter book */}
              {currentResolution && !streaming && !clarifierDiverged && (
                <motion.div
                  key={currentResolution.matched_cip}
                  initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={reducedMotion ? { duration: 0 } : springs.smooth}
                  className="mt-6 flex flex-col gap-6"
                >
                  <p className="font-body text-small italic text-text-muted">
                    Showing Standard Occupational Classification (SOC) codes related to CIP {currentResolution.matched_cip.slice(0, 5)}.
                  </p>
                  {socReveal.kind === "outcomes-loading" && <CareerListSkeleton />}
                  {socReveal.kind === "error" && (
                    <p className="font-body text-small text-accent-alert">
                      {socReveal.message}
                    </p>
                  )}
                  {socReveal.kind === "outcomes-loaded-tiering" && (
                    <>
                      <p
                        aria-live="polite"
                        data-testid="tier-section-loading"
                        className="font-data text-micro font-bold uppercase tracking-[2px] text-text-secondary animate-gemma-shimmer-loop py-2"
                      >
                        Organizing your paths…
                      </p>
                      <CareerTierSection
                        id="tier-common"
                        label="Career paths"
                        description="Where most graduates from this program end up."
                        accent="common"
                        careers={outcomesForIntermediate}
                        pickedSoc={selectedCareer?.soc_code ?? null}
                        onSelect={handleCareerSelect}
                      />
                      {postgradIntermediate.length > 0 && (
                        <CareerTierSection
                          id="tier-postgrad-int"
                          label="Requires postgraduate education"
                          description="These paths typically need a master's or doctoral degree."
                          accent="postgrad"
                          careers={postgradIntermediate}
                          pickedSoc={selectedCareer?.soc_code ?? null}
                          onSelect={handleCareerSelect}
                        />
                      )}
                    </>
                  )}
                  {tieredCareers && (
                    <>
                      <CareerTierSection
                        id="tier-common"
                        label="Where this commonly leads"
                        description="Where most graduates from this program end up."
                        accent="common"
                        careers={commonCareers}
                        pickedSoc={selectedCareer?.soc_code ?? null}
                        onSelect={handleCareerSelect}
                      />
                      <CareerTierSection
                        id="tier-uncommon"
                        label="Uncommon paths"
                        description="Realistic paths that take more intention to reach."
                        accent="uncommon"
                        careers={uncommonCareers}
                        pickedSoc={selectedCareer?.soc_code ?? null}
                        onSelect={handleCareerSelect}
                      />
                      <CareerTierSection
                        id="tier-postgrad"
                        label="Requires postgraduate education"
                        description="These paths typically need a master's or doctoral degree."
                        accent="postgrad"
                        careers={postgradCareers}
                        pickedSoc={selectedCareer?.soc_code ?? null}
                        onSelect={handleCareerSelect}
                      />
                    </>
                  )}
                </motion.div>
              )}


              {/* Community Suggestions — absent when cold. */}
              {school && suggestions.length > 0 && (
                <div className="mt-8">
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
                </div>
              )}
            </section>
          </div>

          {/* Commit region — desktop. "Not what I expected" sits inline
              next to "Yes, continue" as a peer action. Tapping it opens
              a modal with the clarifier form; the career preview above
              stays in view. */}
          <div className="hidden tablet:block mt-4" data-testid="commit-bar">
            <div className="flex items-center justify-between gap-4 rounded-xl border border-border-subtle bg-bp-deep px-6 py-5">
              <Button
                variant="ghost"
                onClick={handleStartOverRequest}
                disabled={busy}
                data-testid="btn-start-over"
              >
                Start over
              </Button>
              {softNudge ? (
                <p
                  className="flex-1 text-center italic font-body text-small text-text-muted"
                  data-testid="soft-nudge"
                >
                  {softNudge}
                </p>
              ) : (
                <span className="flex-1" />
              )}
              <div className="flex items-center gap-3">
                {currentResolution && !streaming && (
                  <AskGemmaChip
                    onChip={(id, clarifier) => onChip(id, clarifier)}
                    busy={busy}
                    softNudge={lowConfidence}
                  />
                )}
                <Button
                  variant="primary"
                  onClick={() => void commit()}
                  disabled={!canCommit}
                  data-testid="btn-commit"
                >
                  Yes, continue
                </Button>
              </div>
            </div>
          </div>
        </div>
      </PageContainer>

      {/* Sticky mobile commit bar. Chip sits inline between Start over
          and Yes, continue — same peer relationship as desktop. The
          clarifier modal is the same overlay component on both. */}
      <div
        className="fixed bottom-0 left-0 right-0 z-40 tablet:hidden bg-bp-mid/95 backdrop-blur border-t border-border-subtle px-4 py-3 flex flex-col gap-2"
        data-testid="mobile-commit-bar"
      >
        {softNudge && (
          <p className="font-body text-micro italic text-text-muted text-center">
            {softNudge}
          </p>
        )}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="ghost"
            onClick={handleStartOverRequest}
            disabled={busy}
            className="flex-none"
          >
            Start over
          </Button>
          {currentResolution && !streaming && (
            <AskGemmaChip
              onChip={(id, clarifier) => onChip(id, clarifier)}
              busy={busy}
              softNudge={lowConfidence}
            />
          )}
          <Button
            variant="primary"
            onClick={() => void commit()}
            disabled={!canCommit}
            className="flex-1"
            data-testid="btn-commit-mobile"
          >
            Yes, continue
          </Button>
        </div>
      </div>

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
            aria-label="Confirm start over"
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
                This clears your progress. Sure?
              </p>
              <p className="font-body text-small text-text-secondary">
                Your school, field of study, and any chip corrections will reset.
                Effort and loans go back to defaults.
              </p>
              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  variant="ghost"
                  onClick={() => setConfirmStartOver(false)}
                  data-testid="btn-keep-going"
                >
                  Keep going
                </Button>
                <Button
                  variant="primary"
                  onClick={handleStartOverConfirm}
                  data-testid="btn-confirm-start-over"
                >
                  Yes, start over
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <span className="sr-only" data-testid="normalized-input">
        {normalizedInput}
      </span>
    </div>
  );
}
