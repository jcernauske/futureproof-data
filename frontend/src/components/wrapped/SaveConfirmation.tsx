import { motion } from "framer-motion";
import { springs } from "@/styles/motion";

interface SaveConfirmationProps {
  profileName: string;
  profileEmoji: string;
  schoolName: string;
  careerTitle: string;
  wins: number;
  draws: number;
  losses: number;
}

export function SaveConfirmation({
  profileName,
  profileEmoji,
  schoolName,
  careerTitle,
  wins,
  draws,
  losses,
}: SaveConfirmationProps) {
  return (
    <div
      role="status"
      aria-label="Build saved successfully"
      data-testid="region-save-confirm"
      className="min-h-screen w-full flex items-center justify-center bg-bp-deep px-8"
    >
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.smooth}
        className="flex flex-col items-center gap-6 text-center max-w-xl"
      >
        <motion.div
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ ...springs.bouncy, delay: 0.1 }}
          className="relative flex items-center justify-center w-[160px] h-[160px] rounded-full"
          style={{
            background:
              "radial-gradient(circle at 50% 50%, rgba(125,212,163,0.28) 0%, transparent 65%)",
          }}
        >
          <span className="text-[96px] leading-none">{profileEmoji || "✦"}</span>
        </motion.div>

        <motion.svg
          width="56"
          height="56"
          viewBox="0 0 56 56"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35 }}
          aria-hidden="true"
        >
          <motion.circle
            cx="28"
            cy="28"
            r="25"
            fill="none"
            stroke="var(--color-accent-thrive)"
            strokeWidth="2.5"
            strokeDasharray="160"
            initial={{ strokeDashoffset: 160 }}
            animate={{ strokeDashoffset: 0 }}
            transition={{ duration: 0.45, ease: "easeOut", delay: 0.4 }}
          />
          <motion.path
            d="M16 29 L24 37 L40 20"
            fill="none"
            stroke="var(--color-accent-thrive)"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.35, ease: "easeOut", delay: 0.55 }}
          />
        </motion.svg>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springs.smooth, delay: 0.55 }}
          className="font-display text-display text-text-primary"
        >
          Build saved ✦
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
          className="text-body text-text-secondary"
        >
          {profileName || "Anonymous"} · {schoolName} · {careerTitle}
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.85 }}
          className="font-data text-data-lg text-text-secondary tracking-[0.25em]"
        >
          {wins}W · {draws}D · {losses}L
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.05 }}
          className="text-small text-text-muted italic mt-2"
        >
          Developing your wrapped…
        </motion.p>
      </motion.div>
    </div>
  );
}
