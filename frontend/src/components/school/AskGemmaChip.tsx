import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { Button } from "@/components/ui/Button";
import { GemmaStar } from "@/components/ui/GemmaStar";
import type { ChipId } from "@/api/intent";

const CLARIFIER_MAX = 280;

interface AskGemmaChipProps {
  onChip: (id: ChipId, clarifier?: string) => void;
  busy: boolean;
  /** Pulse the chip when the current resolution is low-confidence. */
  softNudge?: boolean;
}

/**
 * The single Gemma-heavy correction affordance. Renders as a ghost-
 * sized caution-colored chip that lives inline in the commit bar next
 * to "Yes, continue." Tapping it opens a modal dialog with the
 * clarifier form — a scoped 280-char textarea with Ask Gemma / Cancel
 * actions. The modal overlays the main form without collapsing the
 * career preview, so the student can reference what they were looking
 * at while composing the clarifier.
 */
export function AskGemmaChip({
  onChip,
  busy,
  softNudge = false,
}: AskGemmaChipProps) {
  const [open, setOpen] = useState(false);
  const [clarifier, setClarifier] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => textareaRef.current?.focus(), 60);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setClarifier("");
      }
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open]);

  function submit() {
    const text = clarifier.trim();
    if (!text) return;
    onChip("not_expected", text.slice(0, CLARIFIER_MAX));
    setOpen(false);
    setClarifier("");
  }

  function cancel() {
    setOpen(false);
    setClarifier("");
  }

  const chipClasses = [
    "inline-flex items-center gap-2 px-[18px] py-[10px]",
    "rounded-full font-body text-small font-bold",
    "border border-border bg-transparent text-accent-caution",
    "transition-all duration-normal cursor-pointer",
    "hover:bg-accent-caution/8 hover:border-accent-caution/40",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    softNudge ? "animate-chip-pulse-caution" : "",
  ].join(" ");

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={busy}
        className={chipClasses}
        data-testid="chip-not-expected"
      >
        <GemmaStar size={14} />
        Not what I expected
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            key="ask-gemma-overlay"
            className="fixed inset-0 z-50 bg-bp-void/70 backdrop-blur-sm flex items-center justify-center px-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="ask-gemma-dialog-title"
            onClick={cancel}
          >
            <motion.div
              className={[
                "max-w-md w-full rounded-xl p-6 flex flex-col gap-4",
                "bg-bp-mid border border-accent-caution/30",
                "shadow-[0_0_40px_rgba(242,212,119,0.18)]",
              ].join(" ")}
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              transition={springs.smooth}
              data-testid="ask-gemma-modal"
              onClick={(e) => e.stopPropagation()}
            >
              <div
                id="ask-gemma-dialog-title"
                className="flex items-center gap-2 font-body text-small font-bold text-accent-caution"
              >
                <GemmaStar size={14} />
                Not what I expected
              </div>
              <div>
                <label
                  htmlFor="ask-gemma-clarifier"
                  className="block font-body text-small font-bold text-text-secondary mb-1"
                >
                  What were you hoping to see?
                </label>
                <span className="block font-body text-small text-text-muted mb-3">
                  Name a job, a field, whatever's missing.
                </span>
                <textarea
                  id="ask-gemma-clarifier"
                  ref={textareaRef}
                  value={clarifier}
                  onChange={(e) =>
                    setClarifier(e.target.value.slice(0, CLARIFIER_MAX))
                  }
                  maxLength={CLARIFIER_MAX}
                  rows={4}
                  className="w-full min-h-12 bg-bp-deep text-text-primary font-body text-body rounded-md border border-border px-4 py-3 focus:border-accent-info focus:shadow-[0_0_0_3px_var(--color-focus-ring)] focus:outline-none transition-all duration-normal placeholder:text-text-muted resize-y"
                  placeholder="e.g. brand manager, UX designer, something with less math…"
                  data-testid="clarifier-textarea"
                />
                <div className="mt-2 text-right font-data text-micro text-text-muted">
                  {clarifier.length} / {CLARIFIER_MAX}
                </div>
              </div>
              <div className="flex items-center justify-end gap-3">
                <Button
                  variant="ghost"
                  onClick={cancel}
                  disabled={busy}
                  data-testid="clarifier-cancel"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={submit}
                  disabled={busy || clarifier.trim().length === 0}
                  data-testid="clarifier-submit"
                >
                  <span className="inline-flex items-center gap-1.5">
                    <svg viewBox="0 0 40 40" width={18} height={18} aria-hidden="true" className="fill-current">
                      <path d="M 20 4 C 20 14, 14 20, 4 20 C 14 20, 20 26, 20 36 C 20 26, 26 20, 36 20 C 26 20, 20 14, 20 4 Z" opacity="0.8" />
                      <path d="M 20 10 C 20 16, 16 20, 10 20 C 16 20, 20 24, 20 30 C 20 24, 24 20, 30 20 C 24 20, 20 16, 20 10 Z" />
                    </svg>
                    Ask Gemma
                  </span>
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
