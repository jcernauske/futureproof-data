import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { Button } from "@/components/ui/Button";
import { GemmaStar } from "@/components/ui/GemmaStar";
import type { ChipId } from "@/api/intent";

const CLARIFIER_MAX = 280;

interface CorrectionChipsProps {
  onChip: (id: ChipId, clarifier?: string) => void;
  busy: boolean;
  showLessCommon: boolean;
  softNudge?: boolean;
}

/**
 * The three-chip correction rail for the Set Your Course screen.
 *
 * Layout matches the mockup's `.chips` + `.clarifier-inline` pattern:
 * - Primary chip "Not what I expected" with a GemmaStar mark. When
 *   tapped, it expands into a clarifier container holding a textarea
 *   with a 280-char count and Ask Gemma / Cancel actions. The other
 *   two chips remain visible during expansion.
 * - Ghost chip "Show me less common paths" (local toggle, no fetch).
 * - Ghost chip "Change my major" (reset, no fetch).
 *
 * No outer card — the section-level wrapper owns the "Something feel
 * off?" separator and vertical rhythm. A consent-of-loop disclosure
 * one-liner sits below the rail per spec §1 Success Criteria.
 */
export function CorrectionChips({
  onChip,
  busy,
  showLessCommon,
  softNudge = false,
}: CorrectionChipsProps) {
  const [clarifierOpen, setClarifierOpen] = useState(false);
  const [clarifier, setClarifier] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (clarifierOpen) {
      setTimeout(() => textareaRef.current?.focus(), 60);
    }
  }, [clarifierOpen]);

  function handleOpenClarifier() {
    setClarifierOpen(true);
  }

  function handleCancelClarifier() {
    setClarifierOpen(false);
    setClarifier("");
  }

  function handleSubmitClarifier() {
    const text = clarifier.trim();
    if (!text) return;
    onChip("not_expected", text.slice(0, CLARIFIER_MAX));
    setClarifierOpen(false);
    setClarifier("");
  }

  // The primary chip distinguishes itself through the GemmaStar glyph,
  // caution-colored text, and heavier weight — not through a fill or a
  // bright ring. A filled/bordered look here reads as "already selected"
  // instead of "worth trying." Match the ghost border so the two states
  // differ in emphasis, not in activation status.
  const primaryChipClasses = [
    "inline-flex items-center gap-2 px-[18px] py-[10px]",
    "rounded-full font-body text-small font-bold",
    "border border-border bg-transparent text-accent-caution",
    "transition-all duration-normal cursor-pointer",
    "hover:bg-accent-caution/8 hover:border-accent-caution/40",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    softNudge ? "animate-chip-pulse-caution" : "",
  ].join(" ");

  const ghostChipClasses = [
    "inline-flex items-center gap-2 px-[18px] py-[10px]",
    "rounded-full font-body text-small font-semibold",
    "border border-border bg-transparent text-text-secondary",
    "transition-all duration-normal cursor-pointer",
    "hover:bg-white/5 hover:border-border-strong hover:text-text-primary",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]",
    "disabled:opacity-50 disabled:cursor-not-allowed",
  ].join(" ");

  const ghostSecondaries = (
    <>
      <button
        type="button"
        onClick={() => onChip("show_less_common")}
        disabled={busy}
        aria-pressed={showLessCommon}
        className={ghostChipClasses}
        data-testid="chip-show-less-common"
      >
        {showLessCommon
          ? "Hide less common paths"
          : "Show me less common paths"}
      </button>
      <button
        type="button"
        onClick={() => onChip("change_major")}
        disabled={busy}
        className={ghostChipClasses}
        data-testid="chip-change-major"
      >
        Change my major
      </button>
    </>
  );

  return (
    <div className="flex flex-col gap-3" data-testid="correction-chips">
      <AnimatePresence initial={false} mode="wait">
        {clarifierOpen ? (
          <motion.div
            key="clarifier-block"
            className="flex flex-col gap-3"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={springs.smooth}
          >
            <div
              className={[
                "rounded-xl p-5 flex flex-col gap-4",
                "bg-accent-caution/5 border border-accent-caution/30",
                "shadow-[0_0_24px_rgba(242,212,119,0.14)]",
              ].join(" ")}
            >
              <div className="flex items-center gap-2 font-body text-small font-bold text-accent-caution">
                <GemmaStar size={14} />
                Not what I expected
              </div>
              <div>
                <label
                  htmlFor="correction-clarifier"
                  className="block font-body text-small font-bold text-text-secondary mb-1"
                >
                  What were you hoping to see?
                </label>
                <span className="block font-body text-small text-text-muted mb-3">
                  Name a job, a field, whatever's missing.
                </span>
                <textarea
                  id="correction-clarifier"
                  ref={textareaRef}
                  value={clarifier}
                  onChange={(e) =>
                    setClarifier(e.target.value.slice(0, CLARIFIER_MAX))
                  }
                  maxLength={CLARIFIER_MAX}
                  rows={3}
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
                  onClick={handleCancelClarifier}
                  disabled={busy}
                  data-testid="clarifier-cancel"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={handleSubmitClarifier}
                  disabled={busy || clarifier.trim().length === 0}
                  data-testid="clarifier-submit"
                >
                  <span className="inline-flex items-center gap-2">
                    <GemmaStar size={12} />
                    Ask Gemma
                  </span>
                </Button>
              </div>
            </div>
            {/* Ghost chips remain visible below the expanded clarifier
                per mockup scenario 06. */}
            <div className="flex flex-wrap items-center gap-2">
              {ghostSecondaries}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="chips-row"
            className="flex flex-wrap items-center gap-2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={springs.smooth}
          >
            <button
              type="button"
              onClick={handleOpenClarifier}
              disabled={busy}
              className={primaryChipClasses}
              data-testid="chip-not-expected"
            >
              <GemmaStar size={14} />
              Not what I expected
            </button>
            {ghostSecondaries}
          </motion.div>
        )}
      </AnimatePresence>

      <p className="font-body text-small text-text-muted italic">
        Your choices help other students find their path. We don't track who
        you are — just that someone found this mapping useful.
      </p>
    </div>
  );
}
