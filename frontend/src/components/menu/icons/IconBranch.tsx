/**
 * Branch icon — surfaces the `get_career_branches` tool in
 * `<GemmaTrace>`. Short trunk that splits into two upward branches,
 * directly mirroring the Branch Tree wordless metaphor. When a judge
 * sees this icon they immediately know "Gemma is querying the branch
 * tree data."
 *
 * 16×16 viewBox, 1.5px stroke, `currentColor`.
 */

interface Props {
  size?: number;
  className?: string;
}

export function IconBranch({ size = 16, className = "" }: Props) {
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
      {/* Trunk */}
      <line x1="8" y1="14" x2="8" y2="9" />
      {/* Left branch */}
      <path d="M 8 9 C 8 6.5 5.5 5.5 4 4" />
      {/* Right branch */}
      <path d="M 8 9 C 8 6.5 10.5 5.5 12 4" />
      {/* Endpoint dots */}
      <circle cx="4" cy="4" r="1.1" fill="currentColor" stroke="none" />
      <circle cx="12" cy="4" r="1.1" fill="currentColor" stroke="none" />
      <circle cx="8" cy="14" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  );
}
