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
    <span
      className={`font-display text-text-primary leading-none whitespace-nowrap ${sizeStyles[size]} ${className}`}
      style={{ letterSpacing: "-0.01em" }}
    >
      <span aria-hidden="true" className="text-accent-insight mr-1.5">✦</span>
      FutureProof
    </span>
  );
}
