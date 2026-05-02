/**
 * Wrench icon — generic fallback for unknown tool names in
 * `<GemmaTrace>`. Echoes the existing ⚙ glyph in the Tool-Call
 * Indicator chip. Should never appear in v1 (the 5 known tools all
 * have specific icons), but `feature-agentic-school-research.md` may
 * add tools later — this is the forward-compat seam.
 *
 * 16×16 viewBox, 1.5px stroke, `currentColor`.
 */

interface Props {
  size?: number;
  className?: string;
}

export function IconWrench({ size = 16, className = "" }: Props) {
  return (
    <svg
      viewBox="0 0 16 16"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {/* Wrench head — open jaw */}
      <path d="M 10.5 2.5 a 3 3 0 0 0 -3 4.6 L 2.6 12 a 1.4 1.4 0 0 0 2 2 l 4.9 -4.9 a 3 3 0 0 0 4.6 -3 l -2 2 l -2 -2 z" />
    </svg>
  );
}
