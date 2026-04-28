import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { Wordmark } from "@/components/ui/Wordmark";

interface ProfileResponse {
  profile_name: string;
  animal_emoji: string;
  animal_name: string;
}

function getPhaseAccent(pathname: string): string {
  if (pathname.startsWith("/set-your-course"))
    return "bg-accent-info";
  if (pathname.startsWith("/career-pick") || pathname.startsWith("/reveal") || pathname.startsWith("/my-build"))
    return "bg-accent-thrive";
  if (pathname.startsWith("/gauntlet") || pathname.startsWith("/bosses"))
    return "bg-accent-alert";
  if (pathname.startsWith("/branches"))
    return "bg-accent-insight";
  if (pathname.startsWith("/save"))
    return "bg-accent-empathy";
  if (pathname.startsWith("/builds"))
    return "bg-accent-info";
  return "";
}

function truncateSchoolName(name: string, maxLen = 24): string {
  if (name.length <= maxLen) return name;
  const common: Record<string, string> = {
    "University": "U",
    "Institute of Technology": "IT",
    "State University": "State",
  };
  let short = name;
  for (const [full, abbr] of Object.entries(common)) {
    short = short.replace(full, abbr);
  }
  if (short.length <= maxLen) return short;
  return short.slice(0, maxLen - 1) + "…";
}

export function AppHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const { profileName, animalEmoji, setProfile, clearProfile } = useProfileStore();
  const [starting, setStarting] = useState(false);
  const { school, major, resetInputs } = useBuildInputStore();
  const selectedCareer = useBuildStore((s) => s.selectedCareer);

  // TODO (spec §11 post-hackathon): replace this pathname-based marketing gate
  // with an InAppLayout wrapper route once a second marketing route lands
  // (e.g., /privacy, /about). The current "/"-only check does not scale past
  // one marketing surface. Tracked under `landing-page-and-design-polish.md`
  // §11 Follow-ups + staff-engineer Finding 5.
  const isMarketing = location.pathname === "/";
  const isLanding = location.pathname === "/app";
  const isHubList = location.pathname === "/builds" && !location.search.includes("view=compare");
  const isGauntlet = location.pathname === "/gauntlet";
  const showBack = !isLanding && !isHubList;
  const phaseAccent = getPhaseAccent(location.pathname);
  const hasContext = school || major || selectedCareer;

  function handleBack() {
    navigate(-1);
  }

  if (isMarketing) return null;

  return (
    <AnimatePresence>
      <motion.header
        key="app-header"
        className="fixed top-0 left-0 right-0 z-[100] flex flex-col"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: isGauntlet ? 0.55 : 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={springs.smooth}
      >
        <div
          className="h-14 px-8 flex items-center backdrop-blur-[12px] border-b border-border-subtle"
          style={{ background: "rgba(18, 19, 31, 0.92)" }}
        >
          {/* Left zone: wordmark (tappable home) + back chevron */}
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => navigate("/")}
              className="cursor-pointer hover:opacity-80 transition-opacity duration-normal"
              aria-label="Go to landing page"
            >
              <Wordmark size="sm" />
            </button>
            <AnimatePresence mode="wait">
              {showBack && (
                <motion.button
                  key="back"
                  onClick={handleBack}
                  className="text-text-muted px-2 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:text-text-primary hover:bg-bp-surface"
                  aria-label="Go back"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={springs.snappy}
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="block">
                    <path d="M10 3L5 8L10 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </motion.button>
              )}
            </AnimatePresence>
          </div>

          {/* Center zone: build context pill */}
          <div className="flex-1 flex justify-center">
            <AnimatePresence mode="wait">
              {hasContext && !isGauntlet ? (
                <motion.div
                  key="context-pill"
                  className="flex items-center gap-0 px-4 py-1 rounded-full max-w-[360px]"
                  style={{ background: "rgba(255, 255, 255, 0.05)" }}
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.92 }}
                  transition={springs.snappy}
                  layout
                >
                  {school && (
                    <motion.span
                      className="font-body text-small font-semibold text-text-primary truncate"
                      layout
                    >
                      {truncateSchoolName(school.name)}
                    </motion.span>
                  )}
                  {major && (
                    <>
                      <span className="text-text-muted opacity-50 mx-2 text-small">·</span>
                      <motion.span
                        className="font-body text-small text-text-secondary truncate"
                        initial={{ opacity: 0, x: -4 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={springs.snappy}
                        layout
                      >
                        {major.cipTitle}
                      </motion.span>
                    </>
                  )}
                  {selectedCareer && (
                    <>
                      <span className="text-text-muted opacity-50 mx-2 text-small">·</span>
                      <motion.span
                        className="font-body text-small text-accent-thrive truncate"
                        initial={{ opacity: 0, x: -4 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={springs.snappy}
                        layout
                      >
                        {selectedCareer.occupation_title}
                      </motion.span>
                    </>
                  )}
                </motion.div>
              ) : isHubList && profileName ? (
                <motion.span
                  key="profile-hub"
                  className="font-body text-small font-semibold text-text-muted"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={springs.smooth}
                >
                  {profileName} {animalEmoji}
                </motion.span>
              ) : null}
            </AnimatePresence>
          </div>

          {/* Right zone: contextual actions */}
          <div className="shrink-0 flex items-center gap-2">
            {!isHubList && !isGauntlet && (
              <motion.button
                className="font-body text-small text-text-muted px-3 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:text-text-primary hover:bg-bp-surface flex items-center gap-1.5"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...springs.smooth, delay: 0.3 }}
                onClick={() => navigate("/builds")}
                aria-label="Go to builds"
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="block">
                  <rect x="1" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <rect x="8" y="1" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <rect x="1" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <rect x="8" y="8" width="5" height="5" rx="1" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                Builds
              </motion.button>
            )}
            {isLanding && (
              <motion.button
                className="font-body text-small font-semibold text-accent-thrive px-3.5 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:text-text-primary hover:bg-bp-surface"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...springs.smooth, delay: 0.8 }}
                disabled={starting}
                onClick={async () => {
                  setStarting(true);
                  try {
                    const res = await apiPost<ProfileResponse>("/profile");
                    setProfile(res.profile_name, res.animal_emoji, res.animal_name);
                    navigate("/profile");
                  } catch {
                    // Fall through — user can use the main CTA
                  } finally {
                    setStarting(false);
                  }
                }}
              >
                Start ✦
              </motion.button>
            )}
            {location.pathname === "/builds" && (
              <motion.button
                className="font-body text-small font-semibold text-accent-info px-3.5 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:text-text-primary hover:bg-bp-surface"
                style={{ background: "rgba(123, 184, 224, 0.08)" }}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...springs.smooth, delay: 0.5 }}
                onClick={() => { clearProfile(); resetInputs(); navigate("/profile"); }}
              >
                + New Build
              </motion.button>
            )}
          </div>
        </div>

        {/* Phase accent line */}
        {phaseAccent && (
          <motion.div
            className={`h-[2px] ${phaseAccent} opacity-40`}
            layoutId="phase-accent"
            transition={springs.smooth}
          />
        )}
      </motion.header>
    </AnimatePresence>
  );
}
