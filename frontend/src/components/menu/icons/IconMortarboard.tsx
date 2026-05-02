/**
 * Mortarboard (graduation cap) icon — surfaces the
 * `get_schools_for_career` tool in `<GemmaTrace>`. The career-to-
 * school leaderboard. Visually distinct from the briefcase
 * (occupation) and compass (career-paths-by-school+major) so judges
 * can tell at a glance "Gemma is comparing SCHOOLS for this career."
 *
 * 16×16 viewBox, 1.5px stroke, `currentColor`.
 */

interface Props {
  size?: number;
  className?: string;
}

export function IconMortarboard({ size = 16, className = "" }: Props) {
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
      {/* Cap board — diamond/parallelogram top */}
      <path d="M 8 3 L 14.5 6 L 8 9 L 1.5 6 Z" />
      {/* Crown band — under the board, where the head goes */}
      <path d="M 4 7.4 V 10.5 C 4 11.5 5.8 12.4 8 12.4 C 10.2 12.4 12 11.5 12 10.5 V 7.4" />
      {/* Tassel — short cord hanging from the right edge */}
      <line x1="13.5" y1="6.7" x2="13.5" y2="9.5" />
      <circle cx="13.5" cy="10.1" r="0.7" fill="currentColor" stroke="none" />
    </svg>
  );
}
