import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface LoadingScreenProps {
  profileName: string;
  emoji: string;
  error: string | null;
  onRetry: () => void;
}

const MESSAGES = [
  (name: string, emoji: string) => `Specing ${name} ${emoji}...`,
  () => "Crunching salary data...",
  () => "Sizing up the bosses...",
  () => "Mapping your branches...",
  () => "Asking Gemma for advice...",
  () => "Almost there...",
];

export function LoadingScreen({ profileName, emoji, error, onRetry }: LoadingScreenProps) {
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    if (error) return;
    const interval = setInterval(() => {
      setMsgIndex((prev) => (prev < MESSAGES.length - 1 ? prev + 1 : prev));
    }, 2000);
    return () => clearInterval(interval);
  }, [error]);

  const message = error
    ? "Something went wrong — let's try again"
    : MESSAGES[msgIndex]!(profileName, emoji);

  return (
    <div
      id="region-loading"
      role="status"
      aria-label="Building your career profile"
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bp-void"
    >
      {/* Ambient glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(circle at 50% 45%, rgba(125,212,163,0.25) 0%, rgba(184,169,232,0.25) 30%, transparent 60%)",
        }}
      />

      {/* Floating emoji */}
      <motion.div
        className="text-[80px] mb-8 relative z-10"
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 3, ease: "easeInOut", repeat: Infinity }}
      >
        {emoji}
      </motion.div>

      {/* Loading message */}
      <div className="relative h-10 flex items-center justify-center z-10">
        <AnimatePresence mode="wait">
          <motion.p
            key={message}
            className="font-display font-semibold text-heading text-text-primary text-center px-6"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
          >
            {message}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* Progress dots */}
      {!error && (
        <div className="flex gap-2 mt-8 z-10">
          {Array.from({ length: 6 }).map((_, i) => (
            <motion.div
              key={i}
              className="w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor:
                  i <= msgIndex
                    ? "var(--color-accent-thrive)"
                    : "var(--color-bg-surface)",
              }}
              animate={
                i === msgIndex
                  ? { scale: [1, 1.5, 1], opacity: [0.7, 1, 0.7] }
                  : {}
              }
              transition={
                i === msgIndex
                  ? { duration: 1, repeat: Infinity }
                  : undefined
              }
            />
          ))}
        </div>
      )}

      {/* Retry button on error */}
      {error && (
        <motion.button
          className="mt-8 z-10 font-body font-semibold text-body px-6 py-3 rounded-lg bg-bp-surface border border-border-subtle text-text-primary cursor-pointer hover:bg-bp-raised transition-colors duration-normal"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={onRetry}
        >
          Try Again
        </motion.button>
      )}
    </div>
  );
}
