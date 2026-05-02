/**
 * Career Compass icon — surfaces the `get_career_paths` tool in
 * `<GemmaTrace>`. Four-pointed compass rose with a small filled
 * center dot. Echoes Gemma's four-pointed sparkle so it reads as
 * family.
 *
 * 16×16 viewBox, 1.5px stroke, `currentColor` so it inherits color
 * from the row's text-color cascade.
 */

interface Props {
  size?: number;
  className?: string;
}

export function IconCareerCompass({ size = 16, className = "" }: Props) {
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
      {/* Four spokes — N, S, E, W */}
      <line x1="8" y1="2" x2="8" y2="14" />
      <line x1="2" y1="8" x2="14" y2="8" />
      {/* Diamond outline accenting the four cardinal points */}
      <path d="M 8 3.5 L 12.5 8 L 8 12.5 L 3.5 8 Z" opacity="0.55" />
      {/* Center filled dot */}
      <circle cx="8" cy="8" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  );
}
