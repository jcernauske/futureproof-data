type WordmarkSize = "sm" | "md" | "lg";

interface WordmarkProps {
  size?: WordmarkSize;
  className?: string;
}

const sizeStyles: Record<WordmarkSize, string> = {
  sm: "text-body-sm font-semibold",
  md: "text-body-lg font-semibold",
  lg: "text-heading font-bold",
};

export function Wordmark({ size = "md", className = "" }: WordmarkProps) {
  return (
    // dir="ltr" locks the spark + name to their original order regardless
    // of the document direction. Brand wordmarks don't mirror in RTL —
    // the wordmark POSITION moves to the right side of the header (which
    // dir="rtl" handles automatically), but the mark itself always reads
    // ✦ FutureProof, never FutureProof ✦.
    <span
      dir="ltr"
      className={`font-display text-text-primary leading-none whitespace-nowrap ${sizeStyles[size]} ${className}`}
      style={{ letterSpacing: "-0.01em" }}
    >
      <span aria-hidden="true" className="text-accent-insight mr-1.5">✦</span>
      FutureProof
    </span>
  );
}
