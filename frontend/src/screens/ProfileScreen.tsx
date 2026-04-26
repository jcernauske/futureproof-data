import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/ui/PageContainer";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import type { Segment } from "@/components/ui/SegmentedControl";
import type { AppLocale } from "@/i18n/locales";
import { localizeProfileName } from "@/i18n/profileName";
import { useT } from "@/i18n/useT";
import { fireCheckpoint } from "@/lib/checkpoint";

const US_STATES = [
  { abbr: "AL", name: "Alabama" }, { abbr: "AK", name: "Alaska" },
  { abbr: "AZ", name: "Arizona" }, { abbr: "AR", name: "Arkansas" },
  { abbr: "CA", name: "California" }, { abbr: "CO", name: "Colorado" },
  { abbr: "CT", name: "Connecticut" }, { abbr: "DE", name: "Delaware" },
  { abbr: "FL", name: "Florida" }, { abbr: "GA", name: "Georgia" },
  { abbr: "HI", name: "Hawaii" }, { abbr: "ID", name: "Idaho" },
  { abbr: "IL", name: "Illinois" }, { abbr: "IN", name: "Indiana" },
  { abbr: "IA", name: "Iowa" }, { abbr: "KS", name: "Kansas" },
  { abbr: "KY", name: "Kentucky" }, { abbr: "LA", name: "Louisiana" },
  { abbr: "ME", name: "Maine" }, { abbr: "MD", name: "Maryland" },
  { abbr: "MA", name: "Massachusetts" }, { abbr: "MI", name: "Michigan" },
  { abbr: "MN", name: "Minnesota" }, { abbr: "MS", name: "Mississippi" },
  { abbr: "MO", name: "Missouri" }, { abbr: "MT", name: "Montana" },
  { abbr: "NE", name: "Nebraska" }, { abbr: "NV", name: "Nevada" },
  { abbr: "NH", name: "New Hampshire" }, { abbr: "NJ", name: "New Jersey" },
  { abbr: "NM", name: "New Mexico" }, { abbr: "NY", name: "New York" },
  { abbr: "NC", name: "North Carolina" }, { abbr: "ND", name: "North Dakota" },
  { abbr: "OH", name: "Ohio" }, { abbr: "OK", name: "Oklahoma" },
  { abbr: "OR", name: "Oregon" }, { abbr: "PA", name: "Pennsylvania" },
  { abbr: "RI", name: "Rhode Island" }, { abbr: "SC", name: "South Carolina" },
  { abbr: "SD", name: "South Dakota" }, { abbr: "TN", name: "Tennessee" },
  { abbr: "TX", name: "Texas" }, { abbr: "UT", name: "Utah" },
  { abbr: "VT", name: "Vermont" }, { abbr: "VA", name: "Virginia" },
  { abbr: "WA", name: "Washington" }, { abbr: "WV", name: "West Virginia" },
  { abbr: "WI", name: "Wisconsin" }, { abbr: "WY", name: "Wyoming" },
  { abbr: "DC", name: "District of Columbia" },
];

interface ProfileResponse {
  profile_name: string;
  animal_emoji: string;
  animal_name: string;
}

const LANGUAGE_SEGMENTS: Segment<AppLocale>[] = [
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
];

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
  const { profileName, animalEmoji, setProfile, homeState, setHomeState, locale, setLocale } = useProfileStore();
  const t = useT();

  const [generating, setGenerating] = useState(true);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [rerolling, setRerolling] = useState(false);
  const [rerollError, setRerollError] = useState<string | null>(null);
  const [nameKey, setNameKey] = useState(0);

  useEffect(() => {
    if (profileName) return;
    let cancelled = false;
    setGenerating(true);
    apiPost<ProfileResponse>("/profile")
      .then((res) => {
        if (cancelled) return;
        setProfile(res.profile_name, res.animal_emoji, res.animal_name);
      })
      .catch(() => {
        if (cancelled) return;
        setGenerateError(t("profile.generateError"));
      })
      .finally(() => {
        if (!cancelled) setGenerating(false);
      });
    return () => { cancelled = true; };
  }, [profileName, setProfile]);

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
      setRerollError(t("profile.rerollError"));
    } finally {
      setRerolling(false);
    }
  }

  if (!profileName) {
    return (
      <div className="min-h-screen relative overflow-hidden pt-14">
        <PageContainer variant="centered">
          <div className="min-h-[calc(100vh-56px)] flex flex-col items-center justify-center">
            {generateError ? (
              <p className="font-body text-body text-accent-alert text-center">{generateError}</p>
            ) : generating ? (
              <p className="font-body text-body text-text-secondary">{t("profile.generating")}</p>
            ) : null}
          </div>
        </PageContainer>
      </div>
    );
  }

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
          {t("profile.meetGuide")}
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
              animation: "ambient-breathe 6s ease-in-out infinite",
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
                {localizeProfileName(profileName, locale)}
              </motion.h1>
            </motion.div>
          </AnimatePresence>
        </div>

        <motion.p
          className="font-body text-small text-text-muted mt-3"
          variants={staggerItem}
        >
          {t("profile.everyBuild")}
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
          {t("profile.newName")}
        </motion.button>

        {rerollError && (
          <p className="font-body text-small text-accent-alert mt-2">{rerollError}</p>
        )}

        <div className="mt-10 w-full max-w-xs border-t border-border-subtle" />

        <motion.div
          className="mt-6 w-full max-w-xs"
          variants={staggerItem}
        >
          <label
            className="block font-body text-small text-text-secondary mb-2 text-center"
          >
            {t("profile.language")}
          </label>
          <SegmentedControl
            segments={LANGUAGE_SEGMENTS}
            value={locale}
            onChange={setLocale}
            activeColor="bg-accent-info"
            ariaLabel={locale === "es" ? "Elegir idioma" : "Choose language"}
          />
        </motion.div>

        <motion.div
          className="mt-6 w-full max-w-xs"
          variants={staggerItem}
        >
          <label
            htmlFor="home-state"
            className="block font-body text-small text-text-secondary mb-2 text-center"
          >
            {t("profile.stateLabel")}
          </label>
          <select
            id="home-state"
            value={homeState ?? ""}
            onChange={(e) => setHomeState(e.target.value)}
            className="w-full rounded-md border border-border bg-bp-deep text-text-primary font-body px-4 py-3 text-body appearance-none cursor-pointer focus:outline-none focus:border-accent-info focus:shadow-[0_0_0_3px_rgba(123,184,224,0.15)] transition-colors duration-normal"
          >
            <option value="" disabled>{t("profile.statePlaceholder")}</option>
            {US_STATES.map((s) => (
              <option key={s.abbr} value={s.abbr}>{s.name}</option>
            ))}
          </select>
        </motion.div>

        <motion.div
          className="mt-6 flex flex-col items-center gap-3 w-full max-w-xs"
          variants={staggerItem}
        >
          <Button
            onClick={() => {
              const after = sessionStorage.getItem("fp-after-profile");
              if (after) sessionStorage.removeItem("fp-after-profile");
              fireCheckpoint(after || "/set-your-course");
              navigate(after || "/set-your-course");
            }}
            aria-label="Continue to school selection"
            className="w-full"
          >
            {t("profile.start")}
          </Button>

        </motion.div>
      </motion.div>
      </PageContainer>
    </div>
  );
}
