import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiGet } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { SchoolSearch } from "@/components/school/SchoolSearch";
import { MajorInput } from "@/components/school/MajorInput";
import { EffortLoansPanel } from "@/components/school/EffortLoansPanel";
import { BuildSummaryBar } from "@/components/ui/BuildSummaryBar";
import type {
  MajorSelection,
  ProgramResult,
  SchoolSelection,
} from "@/types/buildInput";

export function SchoolMajorScreen() {
  const navigate = useNavigate();
  const profileName = useProfileStore((s) => s.profileName);
  const {
    phase,
    school,
    programs,
    major,
    effort,
    loans,
    setSchool,
    setPrograms,
    setMajor,
    setEffort,
    setLoans,
    clearSchool,
  } = useBuildInputStore();
  const tieredCareers = useBuildStore((s) => s.tieredCareers);
  const selectedCareer = useBuildStore((s) => s.selectedCareer);

  // net_price_annual is school-level — every CareerOutcome at the same UNITID
  // carries the same value. If the user already touched /career-pick we'll have
  // a tier'd or selected career to pull from; on first visit it's null and the
  // slider falls back to the existing copy.
  const netPriceAnnual = useMemo<number | null>(() => {
    const fromSelected = selectedCareer?.net_price_annual ?? null;
    if (fromSelected !== null) return fromSelected;
    const sample =
      tieredCareers?.common[0] ??
      tieredCareers?.less_common[0] ??
      tieredCareers?.stretch[0] ??
      null;
    return sample?.net_price_annual ?? null;
  }, [selectedCareer, tieredCareers]);

  const submitting = false;
  const [showSessionExpired, setShowSessionExpired] = useState(false);

  useEffect(() => {
    if (!profileName) navigate("/");
  }, [profileName, navigate]);

  useEffect(() => {
    if (sessionStorage.getItem("fp-nav-hint") === "session-expired") {
      sessionStorage.removeItem("fp-nav-hint");
      setShowSessionExpired(true);
      const t = setTimeout(() => setShowSessionExpired(false), 6000);
      return () => clearTimeout(t);
    }
  }, []);



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

  function handleMajorConfirm(majorSelection: MajorSelection) {
    setMajor(majorSelection);
  }

  function handleSubmit() {
    if (!school || !major || !profileName) return;
    navigate("/career-pick", {
      state: {
        school,
        major,
        effort,
        loans,
        profileName,
      },
    });
  }

  if (!profileName) return null;

  return (
    <div className="min-h-screen bg-bp-deep relative overflow-hidden pt-14">
      <div className="noise-overlay" />

      <div className="min-h-[calc(100vh-56px)] flex flex-col items-center px-6 py-12 relative">
        <div className="w-full max-w-lg space-y-6">
          {/* Session-expired banner — shown once when redirected from a downstream screen after state was lost. */}
          <AnimatePresence>
            {showSessionExpired && (
              <motion.div
                role="status"
                aria-live="polite"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={springs.smooth}
                className="rounded-lg border border-accent-caution/40 bg-accent-caution/10 px-4 py-3 text-small text-accent-caution"
              >
                Your session reset. Pick your school and major again to continue.
              </motion.div>
            )}
          </AnimatePresence>

          {/* Summary bar when in sliders phase */}
          <AnimatePresence>
            {phase === "sliders" && school && major && (
              <BuildSummaryBar
                schoolName={school.name}
                majorTitle={major.cipTitle}
              />
            )}
          </AnimatePresence>

          {/* Screen 3: School + Major */}
          {phase !== "sliders" && (
            <motion.div
              className="space-y-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={springs.smooth}
            >
              {/* School search */}
              <div>
                <h2 className="font-display text-subheading font-bold text-text-primary mb-4">
                  Where are you headed?
                </h2>
                <SchoolSearch
                  selected={school}
                  onSelect={handleSchoolSelect}
                  onClear={clearSchool}
                />
              </div>

              {/* Major input — revealed after school is selected */}
              <AnimatePresence>
                {school && phase === "major" && (
                  <MajorInput
                    school={school}
                    programs={programs}
                    onConfirm={handleMajorConfirm}
                  />
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* Screen 4: Effort + Loans */}
          <AnimatePresence>
            {phase === "sliders" && (
              <EffortLoansPanel
                effort={effort}
                loans={loans}
                onEffortChange={setEffort}
                onLoanChange={setLoans}
                profileName={profileName}
                onSubmit={handleSubmit}
                submitting={submitting}
                netPriceAnnual={netPriceAnnual}
              />
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
