import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { apiPost } from "@/api/client";
import { useProfileStore } from "@/store/profileStore";
import { PentagonGlow } from "@/components/landing/PentagonGlow";
import { Button } from "@/components/ui/Button";

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

const STARS = Array.from({ length: 12 }, (_, i) => ({
  left: `${[10, 75, 4, 90, 92, 12, 96, 55, 42, 6, 50, 38][i]}%`,
  top: `${[6, 12, 30, 18, 65, 78, 55, 88, 4, 55, 40, 72][i]}%`,
  delay: `${[0, 0.7, 1.5, 0.3, 2.0, 1.1, 0.6, 1.8, 2.3, 0.9, 1.3, 2.6][i]}s`,
  duration: `${[3.5, 4.2, 3.8, 5.0, 3.2, 4.5, 3.9, 4.1, 3.6, 4.8, 5.2, 3.4][i]}s`,
}));

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
    <div className="min-h-screen bg-bp-void relative overflow-hidden pt-14">
      <div className="noise-overlay" />
      <div className="ambient-glow" />

      {STARS.map((star, i) => (
        <div
          key={i}
          className="star"
          style={{
            left: star.left,
            top: star.top,
            animationDelay: star.delay,
            animationDuration: star.duration,
          }}
        />
      ))}

      <motion.div
        className="min-h-screen flex flex-col items-center justify-center px-8 relative"
        variants={staggerContainer}
        initial="hidden"
        animate="show"
      >
        <motion.div className="mb-12" variants={staggerItem}>
          <PentagonGlow />
        </motion.div>

        <motion.div className="text-center max-w-[600px] mb-3" variants={staggerItem}>
          <h1 className="font-display text-heading tablet:text-title font-bold text-text-primary leading-snug">
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
          700K+ data points · 280+ quality rules · 6 public datasets
          <br />
          Every number has a receipt.
        </motion.p>
      </motion.div>
    </div>
  );
}
