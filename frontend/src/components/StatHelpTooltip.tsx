import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { springs } from "@/styles/motion";
import type { StatExplanation } from "@/data/statExplanations";

interface StatHelpTooltipProps {
  stat: StatExplanation;
}

export function StatHelpTooltip({ stat }: StatHelpTooltipProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        id={`btn-stat-help-${stat.key}`}
        aria-label={`Learn about ${stat.name}`}
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-bp-surface text-text-muted text-micro font-data cursor-pointer hover:bg-bp-raised hover:text-text-secondary transition-colors duration-normal"
      >
        ?
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            className="absolute z-50 bottom-full mb-2 left-1/2 -translate-x-1/2 w-[280px] bg-bp-raised rounded-lg p-4 shadow-lg"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={springs.smooth}
          >
            <p className={`font-display font-semibold text-heading ${stat.textClass}`}>
              {stat.name}
            </p>
            <p className="font-data text-data-sm text-text-muted mt-0.5">({stat.abbreviation})</p>
            <p className="font-body text-body-sm text-text-primary mt-2">{stat.explanation}</p>
            <p className="font-data text-micro text-text-muted mt-2">Source: {stat.source}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
