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
import { CipPicker } from "@/components/school/CipPicker";
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

const isPostgrad = (c: CareerOutcome) =>
  c.education_level_name != null &&
  /doctoral|professional|master/i.test(c.education_level_name);

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
    initialResolution,
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
  } = useSetYourCourse(majorText);

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

  const careerPaths = useMemo<CareerOutcome[]>(
    () => loadedOutcomes.filter((c) => !isPostgrad(c)),
    [loadedOutcomes],
  );
  const postgradCareers = useMemo<CareerOutcome[]>(
    () => loadedOutcomes.filter(isPostgrad),
    [loadedOutcomes],
  );

  const hasOutcomes = careerPaths.length > 0 || postgradCareers.length > 0;

  if (!profileName) return null;

  return (
    <div className="min-h-screen relative pt-14 pb-10">
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

          {/* ROW 1 — School/major inputs (left) + Gemma conversation (right) */}
          <div className="grid grid-cols-1 desktop:grid-cols-2 gap-6 desktop:gap-8 items-start">
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

              {/* "Not what I expected?" — appears after results load */}
              {hasOutcomes && currentResolution && !streaming && (
                <AskGemmaChip
                  onChip={(id, clarifier) => onChip(id, clarifier)}
                  busy={busy}
                  softNudge={lowConfidence}
                />
              )}
            </section>

            <section aria-label="Gemma conversation" className="flex flex-col min-h-[340px]">
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
                        Gemma is thinking
                      </span>
                    </div>
                    <p className="font-body text-body text-text-primary leading-relaxed whitespace-pre-wrap animate-gemma-shimmer-loop">
                      {streamingText || "Reading your input..."}
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
                      <span>Gemma matched</span>
                      <span
                        className={`font-bold ${lowConfidence ? "text-accent-caution" : "text-accent-insight"}`}
                      >
                        &ldquo;{majorText || currentResolution.matched_title}&rdquo;
                      </span>
                      {currentResolution.matched_cip && (
                        <>
                          <span>to CIP</span>
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
                        <span>Reported by the school as </span>
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
                            ? "Gemma is reasoning about your clarifier…"
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
            </section>
          </div>

          {/* ROW 2 — Career cards (full width) */}
          {currentResolution && !streaming && !clarifierDiverged && (
            <motion.section
              key={currentResolution.matched_cip}
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reducedMotion ? { duration: 0 } : springs.smooth}
              aria-label="Career paths"
              className="flex flex-col gap-6"
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
              {careerPaths.length > 0 && (
                <CareerTierSection
                  id="tier-careers"
                  label="Where this leads"
                  description="Career paths graduates from this program pursue."
                  accent="common"
                  careers={careerPaths}
                  pickedSoc={selectedCareer?.soc_code ?? null}
                  onSelect={handleCareerSelect}
                  ernShift={effort.ernShift}
                />
              )}
              {postgradCareers.length > 0 && (
                <CareerTierSection
                  id="tier-postgrad"
                  label="Requires postgraduate education"
                  description="These paths typically need a master's or doctoral degree."
                  accent="postgrad"
                  careers={postgradCareers}
                  pickedSoc={selectedCareer?.soc_code ?? null}
                  onSelect={handleCareerSelect}
                  ernShift={effort.ernShift}
                />
              )}
            </motion.section>
          )}

          {/* Community Suggestions */}
          {school && suggestions.length > 0 && (
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

          {/* ROW 3 — Effort/loans sliders + actions (two-column) */}
          <AnimatePresence>
            {hasOutcomes && currentResolution && !streaming && !clarifierDiverged && (
              <motion.section
                key="effort-commit"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={springs.smooth}
                aria-label="Effort, loans, and next step"
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
                  netPriceAnnual={school?.netPriceAnnual}
                />
                {softNudge && (
                  <p
                    className="mt-3 text-center italic font-body text-small text-text-muted"
                    data-testid="soft-nudge"
                  >
                    {softNudge}
                  </p>
                )}
                <div className="mt-4 grid grid-cols-[1fr_2fr] gap-4">
                  <Button
                    variant="ghost"
                    onClick={handleStartOverRequest}
                    disabled={busy}
                    data-testid="btn-start-over"
                    className="w-full h-12"
                  >
                    Start over
                  </Button>
                  <motion.button
                    onClick={() => void commit()}
                    disabled={busy}
                    className="w-full bg-accent-thrive text-text-inverse font-body font-bold text-cta h-12 rounded-lg cursor-pointer hover:bg-[#6bc494] hover:shadow-glow-thrive transition-all duration-normal disabled:opacity-60 disabled:cursor-not-allowed"
                    whileTap={busy ? undefined : { scale: 0.97 }}
                    transition={springs.snappy}
                    data-testid="btn-spec-build-bottom"
                  >
                    {busy ? `Specing ${profileName}...` : "Spec my build →"}
                  </motion.button>
                </div>
              </motion.section>
            )}
          </AnimatePresence>
        </div>
      </PageContainer>

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
