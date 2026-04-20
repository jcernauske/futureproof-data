import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { CareerList } from "@/components/school/CareerList";
import type { CareerOutcome } from "@/types/build";

interface CollapsibleCareerSectionProps {
  label: string;
  careers: CareerOutcome[];
  defaultOpen: boolean;
  showCount?: boolean;
  pickedSoc: string | null;
  onSelect: (career: CareerOutcome) => void;
  testId?: string;
}

/**
 * Section header + collapsible career list. Used to split the preview
 * into "Where this commonly leads" (expanded) and "Uncommon paths"
 * (collapsed, with count). Header is section-label styled (eyebrow);
 * disclosure glyph rotates 90° on open per DESIGN.md §Disclosure.
 */
export function CollapsibleCareerSection({
  label,
  careers,
  defaultOpen,
  showCount = false,
  pickedSoc,
  onSelect,
  testId,
}: CollapsibleCareerSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  if (careers.length === 0) return null;

  return (
    <div className="flex flex-col" data-testid={testId}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-2 py-2 text-left cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] rounded"
      >
        <motion.span
          aria-hidden="true"
          className="font-data text-data-sm text-accent-info"
          animate={{ rotate: open ? 90 : 0 }}
          transition={springs.smooth}
        >
          ▸
        </motion.span>
        <span className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info">
          {label}
          {showCount ? ` (${careers.length})` : ""}
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={springs.smooth}
            className="overflow-hidden"
          >
            <div className="pt-3">
              <CareerList
                careers={careers}
                pickedSoc={pickedSoc}
                onSelect={onSelect}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
