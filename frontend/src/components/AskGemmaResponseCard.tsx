import { motion, useReducedMotion } from "framer-motion";
import { GemmaStar } from "@/components/ui/GemmaStar";
import { GemmaThinking } from "@/components/ui/GemmaThinking";
import { chipResponseExpand } from "@/styles/motion";

interface AskGemmaResponseCardProps {
  loading: boolean;
  answer: string | null;
  onRegenerate: () => void;
  onClose: () => void;
  /**
   * Current sheet detent — drives the max-height ceiling so Gemma's 4–6
   * sentences aren't truncated at the large detent. §3.3 / §3.5.
   */
  detent?: "medium" | "large";
}

function RegenerateIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 12a9 9 0 1 0 3.07-6.77" />
      <polyline points="3 4 3 10 9 10" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  );
}

export function AskGemmaResponseCard({
  loading,
  answer,
  onRegenerate,
  onClose,
  detent = "medium",
}: AskGemmaResponseCardProps) {
  const reducedMotion = useReducedMotion() ?? false;
  // §3.3 + §3.5: detent-aware max-height. Mobile-first defaults; tablet+
  // applies the desktop/tablet cap per §3.5.
  const heightCap =
    detent === "large"
      ? "max-h-[440px] tablet:max-h-[360px]"
      : "max-h-[220px] tablet:max-h-40";

  // Reduced-motion degradation: skip the height spring, keep a minimal
  // opacity fade so the card still mounts/unmounts visibly.
  const sectionMotion = reducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: 0.12, ease: "linear" as const },
      }
    : chipResponseExpand;

  return (
    <motion.section
      role="region"
      aria-live="polite"
      aria-label="Gemma answer"
      initial={sectionMotion.initial}
      animate={sectionMotion.animate}
      exit={sectionMotion.exit}
      transition={sectionMotion.transition}
      className="overflow-hidden"
    >
      <div className={`
        mt-3 bg-bp-surface rounded-xl p-5 tablet:p-6
        border-l-[3px] border-l-accent-insight
        ${heightCap} overflow-y-auto
      `}>
        <div className="flex items-center gap-2 mb-3">
          <GemmaStar size={14} />
          <span className="font-body text-small font-semibold text-text-secondary">
            Gemma
          </span>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-4">
            <GemmaThinking message="Gemma is answering…" />
          </div>
        ) : (
          <p className="font-body text-body text-text-primary leading-relaxed whitespace-pre-line">
            {answer}
          </p>
        )}
        <div className="flex justify-end items-center gap-2 mt-4">
          <button
            type="button"
            onClick={onRegenerate}
            disabled={loading}
            aria-label="Regenerate answer"
            className="
              inline-flex items-center gap-2
              h-10 px-4 rounded-lg
              font-body font-bold text-small
              text-accent-info bg-transparent
              hover:text-text-primary hover:bg-white/[0.05]
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors duration-normal
              focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-[color:var(--color-focus-ring)]
            "
          >
            <RegenerateIcon />
            Regenerate
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close answer"
            className="
              w-8 h-8 rounded-full
              bg-bp-surface text-text-secondary
              hover:bg-bp-raised hover:text-text-primary
              inline-flex items-center justify-center
              transition-colors duration-normal
              focus-visible:outline-none focus-visible:ring-2
              focus-visible:ring-[color:var(--color-focus-ring)]
            "
          >
            <CloseIcon />
          </button>
        </div>
      </div>
    </motion.section>
  );
}
