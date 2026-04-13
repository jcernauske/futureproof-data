import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";

interface StatBadgeProps {
  stat: string;
  value: string;
  label: string;
  colorClass: string;
}

export function StatBadge({ stat, value, label, colorClass }: StatBadgeProps) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <div className="flex items-center gap-1.5">
        <span className={`font-data text-sm font-bold ${colorClass}`}>
          {stat}
        </span>
        <AnimatePresence mode="wait">
          <motion.span
            key={value}
            className={`font-data text-sm ${colorClass}`}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={springs.snappy}
          >
            {value}
          </motion.span>
        </AnimatePresence>
      </div>
      <AnimatePresence mode="wait">
        <motion.span
          key={label}
          className="text-xs text-text-muted"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {label}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}
