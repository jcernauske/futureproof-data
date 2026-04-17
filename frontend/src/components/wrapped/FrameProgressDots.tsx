import { motion } from "framer-motion";
import { springs } from "@/styles/motion";

interface FrameProgressDotsProps {
  total: number;
  current: number;
}

export function FrameProgressDots({ total, current }: FrameProgressDotsProps) {
  return (
    <div
      role="navigation"
      data-testid="nav-frame-progress"
      aria-label={`Story progress: frame ${current + 1} of ${total}`}
      className="flex items-center gap-1.5 px-4 py-3"
    >
      {Array.from({ length: total }).map((_, i) => {
        const isCurrent = i === current;
        const isPast = i < current;
        return (
          <motion.span
            key={i}
            animate={{
              width: isCurrent ? 20 : 4,
              backgroundColor: isCurrent
                ? "var(--color-accent-thrive)"
                : isPast
                ? "var(--color-text-secondary)"
                : "var(--color-bg-surface)",
            }}
            transition={springs.snappy}
            className="h-1 rounded-full"
            aria-hidden="true"
          />
        );
      })}
    </div>
  );
}
