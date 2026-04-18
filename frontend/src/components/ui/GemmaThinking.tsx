import { GemmaSpinner } from "@/components/ui/GemmaSpinner";

interface GemmaThinkingProps {
  /** Sentence fragment — convention is "Gemma is …ing …". */
  message: string;
  /** Spinner diameter in pixels. Defaults to 28 to match inline use (see /school). */
  size?: number;
  className?: string;
}

/**
 * Standard inline indicator for any moment Gemma is thinking.
 * Pairs the animated GemmaSpinner with the canonical attribution typography
 * (Nunito, text-small, text-secondary) so every Gemma-call surface reads the same.
 *
 * Callers wrap with AnimatePresence/motion for entrance/exit effects.
 */
export function GemmaThinking({ message, size = 28, className = "" }: GemmaThinkingProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center gap-3 ${className}`}
    >
      <GemmaSpinner size={size} />
      <span className="font-body text-small text-text-secondary">
        {message}
      </span>
    </div>
  );
}
