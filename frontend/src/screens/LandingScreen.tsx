import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";
import { PentagonGlow } from "@/components/landing/PentagonGlow";
import { Button } from "@/components/ui/Button";
import { PageContainer } from "@/components/ui/PageContainer";

interface ProfileResponse {
  profile_name: string;
  animal_emoji: string;
  animal_name: string;
}

const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.15, delayChildren: 0.05 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: springs.smooth,
  },
};

export function LandingScreen() {
  const navigate = useNavigate();
  const setProfile = useProfileStore((s) => s.setProfile);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<ProfileResponse>("/profile");
      setProfile(res.profile_name, res.animal_emoji, res.animal_name);
      navigate("/profile");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
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
        <motion.div className="mb-12" variants={staggerItem}>
          <PentagonGlow />
        </motion.div>

        <motion.div className="text-center max-w-[720px] mb-3" variants={staggerItem}>
          <h1 className="font-display text-hero tablet:text-hero-tablet desktop:text-hero-desktop font-bold text-text-primary leading-[1.1]">
            A college degree isn't a destination.
            <br />
            It's a <span className="gradient-tagline">starting position.</span>
          </h1>
        </motion.div>

        <motion.p
          className="font-body text-body-sm tablet:text-body-lg text-text-secondary mb-12 text-center max-w-[440px] leading-normal"
          variants={staggerItem}
        >
          See where every path leads — powered by real data and Gemma AI.
        </motion.p>

        <motion.div
          className="flex flex-col items-center gap-3"
          variants={staggerItem}
        >
          <Button
            onClick={handleStart}
            loading={loading}
            aria-label="Start building your future"
            className="w-full mobile:w-auto"
          >
            {loading ? "Generating your profile..." : "See where your path leads ✦"}
          </Button>

          {error && (
            <p className="font-body text-small text-accent-alert text-center">
              {error}
            </p>
          )}
        </motion.div>

        <motion.p
          className="absolute bottom-8 font-data text-micro text-text-muted text-center leading-normal tracking-wide"
          style={{ opacity: 0.4 }}
          variants={staggerItem}
        >
          700K rows · 280 DQ rules · 7 public datasets
          <br />
          Every number has a receipt.
        </motion.p>
      </motion.div>
      </PageContainer>
    </div>
  );
}
