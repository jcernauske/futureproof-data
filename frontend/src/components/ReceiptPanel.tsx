import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { springs } from "@/styles/motion";

interface ReceiptPanelProps {
  id: string;
  label: string;
  children: React.ReactNode;
}

export function ReceiptPanel({ id, label, children }: ReceiptPanelProps) {
  const [open, setOpen] = useState(false);

  return (
    <span className="inline-block relative">
      <button
        id={`btn-receipt-${id}`}
        aria-label={`View data source for ${label}`}
        aria-expanded={open}
        aria-controls={`panel-receipt-${id}`}
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-bp-surface text-text-muted text-micro font-data cursor-pointer hover:bg-bp-raised hover:text-text-secondary transition-colors duration-normal"
      >
        ?
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            id={`panel-receipt-${id}`}
            role="region"
            aria-label={`Data provenance for ${label}`}
            className="mt-2 bg-bp-surface border border-border-subtle rounded-md p-3"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={springs.smooth}
          >
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="font-data text-data-sm text-text-muted"
            >
              {children}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}
