import { useEffect } from "react";
import { motion } from "framer-motion";
import { transitions, staggerContainer, staggerItem, stagger, springs } from "@/styles/motion";
import { useProfileStore } from "@/store/profileStore";

interface GauntletIntroProps {
  onComplete: () => void;
}

export function GauntletIntro({ onComplete }: GauntletIntroProps) {
  const { animalEmoji } = useProfileStore();

  useEffect(() => {
    const timer = setTimeout(onComplete, 2500);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <motion.div
      id="region-gauntlet-intro"
      role="status"
      aria-label="The gauntlet begins"
      className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6"
      {...transitions.fade}
    >
      <span className="font-data text-[11px] text-text-muted uppercase tracking-[2px] mb-6">
        THE GAUNTLET
      </span>

      <motion.h1
        className="font-display font-bold text-display text-text-primary max-w-md"
        {...transitions.fadeInUp}
        transition={{ ...springs.smooth, delay: 0.3 }}
      >
        5 threats stand between you and your future.
      </motion.h1>

      <motion.div
        className="text-[60px] mt-8"
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
      >
        {animalEmoji || "\u{1F43B}"}
      </motion.div>

      <motion.div
        className="flex items-center gap-2 mt-8"
        variants={staggerContainer(0.6, stagger.fast)}
        initial="hidden"
        animate="visible"
      >
        {Array.from({ length: 5 }).map((_, i) => (
          <motion.div
            key={i}
            className="w-3 h-3 rounded-full bg-bp-surface"
            variants={staggerItem}
          />
        ))}
      </motion.div>
    </motion.div>
  );
}
