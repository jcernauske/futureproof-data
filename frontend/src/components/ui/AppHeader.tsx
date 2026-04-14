import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";

interface ProfileResponse {
  profile_name: string;
  animal_emoji: string;
  animal_name: string;
}

export function AppHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const { profileName, animalEmoji, setProfile } = useProfileStore();
  const [starting, setStarting] = useState(false);

  const isLanding = location.pathname === "/";
  const isHub = location.pathname === "/menu";
  const isPostReveal = ["/build", "/branches", "/save", "/menu"].some((p) =>
    location.pathname.startsWith(p),
  );

  function handleBack() {
    navigate(-1);
  }

  function handleHome() {
    navigate("/menu");
  }

  return (
    <AnimatePresence>
      {(
        <motion.header
          key="app-header"
          className="fixed top-0 left-0 right-0 z-[100] h-14 px-8 flex items-center backdrop-blur-[12px] border-b border-border-subtle"
          style={{ background: "rgba(18, 19, 31, 0.92)" }}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ ...springs.smooth, delay: 0.3 }}
        >
          {/* Left zone: wordmark + back/home */}
          <div className="flex items-center gap-3 shrink-0">
            <span className="font-display font-bold text-body-sm text-accent-thrive">
              FutureProof
            </span>
            {!isLanding && (
              <button
                onClick={isHub ? handleHome : handleBack}
                className="text-text-muted text-body-lg px-3 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:text-text-primary hover:bg-bp-surface"
                aria-label={isHub ? "Go to menu" : "Go back"}
              >
                {isHub ? "\u2302" : "\u2190"}
              </button>
            )}
          </div>

          {/* Center zone: profile identity */}
          <div className="flex-1 text-center">
            {profileName && (
              <span
                className={`font-body text-small font-semibold transition-colors duration-slow ${
                  isPostReveal ? "text-text-secondary" : "text-text-muted"
                }`}
              >
                {profileName} {animalEmoji}
              </span>
            )}
          </div>

          {/* Right zone: contextual actions */}
          <div className="shrink-0 text-right">
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
            {isHub && (
              <motion.button
                className="font-body text-small font-semibold text-accent-info px-3.5 py-1.5 rounded-full cursor-pointer transition-all duration-normal hover:text-text-primary hover:bg-bp-surface"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...springs.smooth, delay: 0.5 }}
                onClick={() => navigate("/school")}
              >
                + New
              </motion.button>
            )}
          </div>
        </motion.header>
      )}
    </AnimatePresence>
  );
}
