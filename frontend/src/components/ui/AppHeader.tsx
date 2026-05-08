import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useGauntletStore } from "@/store/gauntletStore";
import { useBuildsCountStore } from "@/store/buildsCountStore";
import { Wordmark } from "@/components/ui/Wordmark";
import { InferenceBadge } from "@/components/ui/InferenceBadge";
import { Toast } from "@/components/ui/Toast";
import { useT } from "@/i18n/useT";

function getPhaseAccent(pathname: string): string {
  if (pathname.startsWith("/set-your-course"))
    return "bg-accent-info";
  if (pathname.startsWith("/my-build"))
    return "bg-accent-thrive";
  if (pathname.startsWith("/gauntlet") || pathname.startsWith("/bosses"))
    return "bg-accent-alert";
  if (pathname.startsWith("/future"))
    return "bg-accent-insight";
  if (pathname.startsWith("/save"))
    return "bg-accent-empathy";
  if (pathname.startsWith("/builds"))
    return "bg-accent-info";
  return "";
}

export function AppHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const t = useT();
  const { clearProfile } = useProfileStore();
  const { school, major, resetInputs } = useBuildInputStore();
  const selectedCareer = useBuildStore((s) => s.selectedCareer);
  const buildsCount = useBuildsCountStore((s) => s.count);
  const buildsCountLoading = useBuildsCountStore((s) => s.loading);
  const refreshBuildsCount = useBuildsCountStore((s) => s.refresh);
  const gauntletPhase = useGauntletStore((s) => s.phase);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  // Re-entrancy guard for the New Build / Try Another button. Resets on
  // every navigation so the next screen can use the button again.
  const navLockRef = useRef(false);
  useEffect(() => {
    navLockRef.current = false;
  }, [location.pathname]);

  const isMarketing = false;
  const isGauntlet = location.pathname === "/gauntlet";
  // Active-fight tunnel-vision rule: hide right-zone CTAs only while a fight
  // is mid-animation. The header bar itself stays at 0.55 opacity for the
  // entire /gauntlet route per the existing rule.
  const isGauntletFight =
    isGauntlet &&
    (gauntletPhase === "fighting" || gauntletPhase === "final_boss");
  const phaseAccent = getPhaseAccent(location.pathname);
  const hasContext = Boolean(school || major || selectedCareer);

  // Refresh saved-build count once on first in-app render so the badge is
  // accurate when AppHeader mounts. Bail when a fetch is already in flight
  // (e.g., MenuScreen mounting concurrently on direct-nav to /builds) so we
  // don't double-fetch and stomp the response with a stale one.
  useEffect(() => {
    if (isMarketing) return;
    if (buildsCount === null && !buildsCountLoading) {
      refreshBuildsCount();
    }
  }, [isMarketing, buildsCount, buildsCountLoading, refreshBuildsCount]);

  function buildSavedLabel(): string {
    if (school && major) return `${school.name} · ${major.cipTitle}`;
    if (school) return school.name;
    if (major) return major.cipTitle;
    if (selectedCareer) return selectedCareer.occupation_title;
    return "";
  }

  function handleNewBuildClick(fireToast: boolean) {
    if (navLockRef.current) return;
    navLockRef.current = true;
    if (fireToast) {
      const label = buildSavedLabel();
      if (label) {
        setToastMessage(t("header.toastSavedTemplate").replace("{label}", label));
      }
    }
    clearProfile();
    resetInputs();
    useBuildStore.getState().resetBuild();
    navigate("/profile");
  }

  if (isMarketing) return null;

  const showMyBuilds = !isGauntletFight;
  const showCompare = !isGauntletFight;
  const showNewBuild = !isGauntletFight;
  const compareDisabled = (buildsCount ?? 0) < 2;

  const myBuildsAriaLabel =
    buildsCount === null || buildsCount === 0
      ? t("header.myBuildsAriaEmpty")
      : buildsCount > 9
        ? t("header.myBuildsAriaMany")
        : t("header.myBuildsAriaSingular").replace("{count}", String(buildsCount));

  return (
    <AnimatePresence>
      <motion.header
        key="app-header"
        className="fixed top-0 left-0 right-0 z-[100] flex flex-col"
        initial={false}
        animate={{ opacity: isGauntlet ? 0.55 : 1, y: 0 }}
        transition={springs.smooth}
      >
        <div
          className="h-14 px-8 flex items-center backdrop-blur-[12px] border-b border-border-subtle"
          style={{ background: "rgba(18, 19, 31, 0.92)" }}
        >
          {/* Left zone: wordmark (tappable home) + inference backend badge */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => navigate("/")}
              className="cursor-pointer hover:opacity-80 transition-opacity duration-normal"
              aria-label={t("header.goLandingAria")}
            >
              <Wordmark size="sm" />
            </button>
            <InferenceBadge />
          </div>

          {/* Center zone: intentionally empty — the build context pill
              (school · major · career) lived here but was removed per
              user feedback. Keep the flex spacer so the wordmark stays
              left-aligned and the action cluster stays right-aligned. */}
          <div className="flex-1" />

          {/* Right zone: persistent actions — icon+label on desktop, icon-only below */}
          <div className="shrink-0 flex items-center gap-2">
            {showMyBuilds && (
              <motion.button
                data-testid="header-my-builds"
                className="font-body text-small text-text-muted px-3 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:text-text-primary hover:bg-bp-surface inline-flex items-center gap-1.5"
                initial={false}
                onClick={() => navigate("/builds")}
                aria-label={myBuildsAriaLabel}
                title={myBuildsAriaLabel}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="block shrink-0">
                  <rect x="1" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <rect x="8" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <rect x="1" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <rect x="8" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                <span className="hidden desktop:inline">
                  {t("header.myBuildsLabel")}
                </span>
                {buildsCount !== null && buildsCount >= 1 && (
                  <span
                    data-testid="header-builds-count"
                    aria-hidden="true"
                    className="min-w-[18px] h-[18px] px-1 rounded-full bg-accent-thrive text-text-inverse font-body text-micro font-semibold inline-flex items-center justify-center shadow-glow-thrive pointer-events-none"
                  >
                    {buildsCount > 9 ? "9+" : buildsCount}
                  </span>
                )}
              </motion.button>
            )}
            {showCompare && (
              <motion.button
                data-testid="header-compare"
                className="font-body text-small text-text-muted px-3 py-1.5 rounded-full transition-all duration-normal enabled:cursor-pointer enabled:hover:text-text-primary enabled:hover:bg-bp-surface disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
                initial={false}
                onClick={() => navigate("/builds?select=1")}
                disabled={compareDisabled}
                aria-label={
                  compareDisabled
                    ? t("header.compareAriaDisabled")
                    : t("header.compareAria")
                }
                title={
                  compareDisabled
                    ? t("header.compareAriaDisabled")
                    : t("header.compareLabel")
                }
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="block shrink-0">
                  <rect x="1" y="2.5" width="6.5" height="9" rx="1.25" stroke="currentColor" strokeWidth="1.5" />
                  <rect x="6.5" y="2.5" width="6.5" height="9" rx="1.25" stroke="currentColor" strokeWidth="1.5" fill="var(--color-bg-void)" />
                </svg>
                <span className="hidden desktop:inline">
                  {t("header.compareLabel")}
                </span>
              </motion.button>
            )}
            {showNewBuild && (
              <motion.button
                data-testid="header-new-build"
                className="font-body text-small font-semibold text-text-inverse bg-accent-thrive px-3.5 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:shadow-glow-thrive hover:brightness-105 active:scale-[0.97] inline-flex items-center gap-1.5"
                initial={false}
                onClick={() => handleNewBuildClick(hasContext)}
                aria-label={t("header.newBuildAria")}
                title={t("header.newBuildAria")}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="block shrink-0">
                  <path d="M7 1.5 L7 12.5 M1.5 7 L12.5 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M3.2 3.2 L4.6 4.6 M9.4 9.4 L10.8 10.8 M3.2 10.8 L4.6 9.4 M9.4 4.6 L10.8 3.2" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" opacity="0.55" />
                </svg>
                <span className="hidden desktop:inline">
                  {t("header.newBuildLabel")}
                </span>
              </motion.button>
            )}
          </div>
        </div>

        {/* Phase accent line — wipes outward from horizontal center on mount.
            No layoutId: it caused Framer to animate the line from an
            uninitialized layout origin (visually, a sweep up from mid-screen). */}
        {phaseAccent && (
          <motion.div
            className={`h-[2px] ${phaseAccent} opacity-40`}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={springs.smooth}
            style={{ transformOrigin: "center" }}
          />
        )}
      </motion.header>
      <Toast
        open={toastMessage !== null}
        message={toastMessage ?? ""}
        onClose={() => setToastMessage(null)}
      />
    </AnimatePresence>
  );
}
