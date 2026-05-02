/**
 * Briefcase Stack icon — surfaces the `get_occupation_data` tool in
 * `<GemmaTrace>`. Briefcase silhouette with a small horizontal divider
 * line across the body suggesting "layered records." Universal job
 * glyph; the divider whispers "data record" without becoming a chart.
 *
 * 16×16 viewBox, 1.5px stroke, `currentColor`.
 */

interface Props {
  size?: number;
  className?: string;
}

export function IconBriefcaseStack({ size = 16, className = "" }: Props) {
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
      {/* Briefcase body */}
      <rect x="2" y="5" width="12" height="9" rx="1.4" />
      {/* Handle on top */}
      <path d="M 6 5 V 4 a 1.2 1.2 0 0 1 1.2 -1.2 h 1.6 a 1.2 1.2 0 0 1 1.2 1.2 V 5" />
      {/* Layered record divider */}
      <line x1="3.5" y1="9" x2="12.5" y2="9" opacity="0.7" />
    </svg>
  );
}
