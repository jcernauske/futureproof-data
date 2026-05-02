/**
 * Scale icon — surfaces the `compare_purchasing_power` tool in
 * `<GemmaTrace>`. Two-pan balance scale, beam horizontal, two dishes
 * hanging. Canonical comparison glyph; works for two-state and any
 * future two-X comparison.
 *
 * 16×16 viewBox, 1.5px stroke, `currentColor`.
 */

interface Props {
  size?: number;
  className?: string;
}

export function IconScale({ size = 16, className = "" }: Props) {
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
      {/* Vertical post */}
      <line x1="8" y1="3.5" x2="8" y2="13" />
      {/* Beam */}
      <line x1="3" y1="4.5" x2="13" y2="4.5" />
      {/* Hanging strings to dishes */}
      <line x1="4" y1="4.5" x2="4" y2="6.5" opacity="0.7" />
      <line x1="12" y1="4.5" x2="12" y2="6.5" opacity="0.7" />
      {/* Left dish */}
      <path d="M 1.8 6.5 L 6.2 6.5 L 5.2 9 L 2.8 9 Z" />
      {/* Right dish */}
      <path d="M 9.8 6.5 L 14.2 6.5 L 13.2 9 L 10.8 9 Z" />
      {/* Base */}
      <line x1="5.5" y1="13" x2="10.5" y2="13" />
    </svg>
  );
}
