import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";
import { Button } from "@/components/ui/Button";
import { TextInput } from "@/components/ui/TextInput";
import { PageContainer } from "@/components/ui/PageContainer";

interface ProfileResponse {
  profile_name: string;
  animal_emoji: string;
  animal_name: string;
}

interface LookupResponse {
  found: boolean;
  profile_name?: string;
  animal_emoji?: string;
  animal_name?: string;
  suggestion?: string;
}

const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: springs.smooth,
  },
};

export function ProfileScreen() {
  const navigate = useNavigate();
  const { profileName, animalEmoji, setProfile } = useProfileStore();

  const [rerolling, setRerolling] = useState(false);
  const [rerollError, setRerollError] = useState<string | null>(null);
  const [showLookup, setShowLookup] = useState(false);
  const [lookupQuery, setLookupQuery] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [nameKey, setNameKey] = useState(0);

  async function handleReroll() {
    if (!profileName) return;
    setRerolling(true);
    setRerollError(null);
    try {
      const res = await apiPost<ProfileResponse>("/profile/reroll", {
        current_name: profileName,
      });
      setProfile(res.profile_name, res.animal_emoji, res.animal_name);
      setNameKey((k) => k + 1);
    } catch {
      setRerollError("Couldn't generate a new name. Try again.");
    } finally {
      setRerolling(false);
    }
  }

  async function handleLookup() {
    if (!lookupQuery.trim()) return;
    setLookupLoading(true);
    setLookupError(null);
    setSuggestion(null);
    try {
      const res = await apiPost<LookupResponse>("/profile/lookup", {
        name_query: lookupQuery,
      });
      if (res.found && res.profile_name && res.animal_emoji && res.animal_name) {
        setProfile(res.profile_name, res.animal_emoji, res.animal_name);
        navigate("/school");
      } else if (res.suggestion) {
        setSuggestion(res.suggestion);
      } else {
        setLookupError("No profile found with that name.");
      }
    } catch {
      setLookupError("Something went wrong. Try again.");
    } finally {
      setLookupLoading(false);
    }
  }

  async function handleConfirmSuggestion() {
    if (!suggestion) return;
    setLookupLoading(true);
    try {
      const res = await apiPost<LookupResponse>("/profile/lookup", {
        name_query: suggestion,
      });
      if (res.found && res.profile_name && res.animal_emoji && res.animal_name) {
        setProfile(res.profile_name, res.animal_emoji, res.animal_name);
        navigate("/school");
      }
    } catch {
      setLookupError("Something went wrong. Try again.");
    } finally {
      setLookupLoading(false);
    }
  }

  useEffect(() => {
    if (!profileName) navigate("/app");
  }, [profileName, navigate]);

  if (!profileName) return null;

  return (
    <div className="min-h-screen relative overflow-hidden pt-14">
      <PageContainer variant="centered">
      <motion.div
        className="min-h-[calc(100vh-56px)] flex flex-col items-center justify-center relative"
        variants={staggerContainer}
        initial="hidden"
        animate="show"
      >
        <motion.p
          className="font-body text-subheading text-text-secondary"
          variants={staggerItem}
        >
          We'll call you
        </motion.p>

        <div className="relative mt-4">
          <div
            className="absolute inset-0 rounded-full pointer-events-none"
            style={{
              width: 300,
              height: 300,
              left: "50%",
              top: "50%",
              transform: "translate(-50%, -50%)",
              background:
                "radial-gradient(circle, var(--color-state-active) 0%, transparent 70%)",
              animation: "ambient-breathe 4s ease-in-out infinite",
            }}
          />

          <AnimatePresence mode="wait">
            <motion.div
              key={nameKey}
              className="text-center relative"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
            >
              <motion.p
                className="text-5xl tablet:text-6xl mb-2"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ ...springs.bouncy, delay: 0.3 }}
              >
                {animalEmoji}
              </motion.p>
              <motion.h1
                className="font-display text-display tablet:text-hero text-text-primary leading-tight"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ ...springs.bouncy, delay: 0.5 }}
              >
                {profileName?.replace(animalEmoji ?? "", "").trim()}
              </motion.h1>
            </motion.div>
          </AnimatePresence>
        </div>

        <motion.p
          className="font-body text-small text-text-muted mt-3"
          variants={staggerItem}
        >
          No accounts. No passwords. Just you.
        </motion.p>

        <motion.button
          className="mt-6 flex items-center gap-2 text-accent-info font-body text-small h-[44px] px-6 rounded-lg cursor-pointer border border-accent-info bg-transparent hover:bg-accent-info/10 transition-all duration-normal disabled:opacity-60 disabled:cursor-not-allowed"
          onClick={handleReroll}
          disabled={rerolling}
          aria-label="Generate a new profile name"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          transition={springs.snappy}
        >
          <motion.span
            animate={rerolling ? { rotate: 180 } : { rotate: 0 }}
            transition={springs.bouncy}
          >
            🎲
          </motion.span>
          New name
        </motion.button>

        {rerollError && (
          <p className="font-body text-small text-accent-alert mt-2">{rerollError}</p>
        )}

        <div className="mt-10 w-full max-w-xs border-t border-border-subtle" />

        <motion.div
          className="mt-10 flex flex-col items-center gap-3 w-full max-w-xs"
          variants={staggerItem}
        >
          <Button
            onClick={() => navigate("/school")}
            aria-label="Continue to school selection"
            className="w-full"
          >
            Let's go →
          </Button>

          <button
            className="font-body text-small text-text-muted mt-2 cursor-pointer hover:text-text-secondary transition-colors duration-normal"
            onClick={() => setShowLookup((v) => !v)}
          >
            Already have a name?
          </button>
        </motion.div>

        <AnimatePresence>
          {showLookup && (
            <motion.div
              className="mt-4 w-full max-w-xs flex flex-col gap-3"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <div className="flex gap-2">
                <TextInput
                  value={lookupQuery}
                  onChange={(e) => setLookupQuery(e.target.value)}
                  placeholder="Type your name..."
                  label="Enter your existing profile name"
                  className="flex-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleLookup();
                  }}
                />
                <Button
                  variant="secondary"
                  onClick={handleLookup}
                  loading={lookupLoading}
                  aria-label="Look up profile"
                >
                  Look up
                </Button>
              </div>

              {suggestion && (
                <div className="rounded-lg p-4 border bg-accent-caution/[0.08] border-accent-caution/[0.15]">
                  <p className="font-body text-small text-text-secondary text-center">
                    Did you mean{" "}
                    <strong className="text-text-primary">{suggestion}</strong>?
                  </p>
                  <div className="flex justify-center mt-2">
                    <Button
                      variant="secondary"
                      onClick={handleConfirmSuggestion}
                      loading={lookupLoading}
                    >
                      Yes, that's me
                    </Button>
                  </div>
                </div>
              )}

              {lookupError && (
                <div className="rounded-lg p-4 border bg-accent-alert/[0.08] border-accent-alert/[0.15]">
                  <p className="font-body text-small text-accent-alert text-center">
                    {lookupError}
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
      </PageContainer>
    </div>
  );
}
