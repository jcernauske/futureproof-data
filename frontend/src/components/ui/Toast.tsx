import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";

interface ToastProps {
  open: boolean;
  message: string;
  durationMs?: number;
  onClose: () => void;
  testId?: string;
}

const toastVariants = {
  hidden: { opacity: 0, y: -8 },
  visible: { opacity: 1, y: 0, transition: springs.smooth },
  exit: { opacity: 0, y: -8, transition: { duration: 0.3, ease: "easeOut" as const } },
};

export function Toast({
  open,
  message,
  durationMs = 1000,
  onClose,
  testId = "header-toast",
}: ToastProps) {
  // Stable ref so unrelated parent renders (locale switch, gauntlet phase tick,
  // route change) don't reset the dismiss timer via a churning onClose identity.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(() => onCloseRef.current(), durationMs);
    return () => clearTimeout(timer);
  }, [open, message, durationMs]);

  return (
    <AnimatePresence mode="wait">
      {open && (
        <motion.div
          key={message}
          data-testid={testId}
          role="status"
          aria-live="polite"
          className="fixed left-1/2 -translate-x-1/2 top-[68px] z-[110] flex items-center gap-2 px-4 py-2 rounded-full bg-bp-raised border border-border-subtle shadow-lg font-body text-small font-semibold text-text-primary pointer-events-none max-w-[calc(100vw-64px)]"
          variants={toastVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
        >
          <span className="text-accent-thrive" aria-hidden="true">
            ✦
          </span>
          <span className="truncate">{message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
