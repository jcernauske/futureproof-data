import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { springs } from "@/styles/motion";

interface CompareAccordionProps {
  title: string;
  icon: React.ReactNode;
  testId: string;
  ariaLabel: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function CompareAccordion({
  title,
  icon,
  testId,
  ariaLabel,
  children,
  defaultOpen = false,
}: CompareAccordionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section
      data-testid={testId}
      aria-label={ariaLabel}
      className="bg-bp-deep border border-border-subtle rounded-[20px] overflow-hidden"
    >
      <button
        type="button"
        data-testid={`btn-toggle-${testId}`}
        aria-expanded={open}
        aria-label={open ? `Collapse ${title.toLowerCase()}` : `Expand ${title.toLowerCase()}`}
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-bp-mid transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-bp-deep"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-accent-info text-base">{icon}</span>
          <span className="font-display font-medium text-sm text-text-secondary">
            {title}
          </span>
        </div>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={springs.snappy}
          className="text-text-muted"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              height: springs.smooth,
              opacity: { duration: 0.2, ease: "easeOut" },
            }}
            className="overflow-hidden"
          >
            <div className="border-t border-border-subtle px-5 pb-5 pt-4">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
