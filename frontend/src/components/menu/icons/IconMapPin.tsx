/**
 * Map Pin icon — surfaces the `get_regional_price_parity` tool in
 * `<GemmaTrace>`. Standard teardrop pin with a small inner ring so it
 * doesn't read as a generic location ping.
 *
 * 16×16 viewBox, 1.5px stroke, `currentColor`.
 */

interface Props {
  size?: number;
  className?: string;
}

export function IconMapPin({ size = 16, className = "" }: Props) {
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
      {/* Teardrop body */}
      <path d="M 8 2 C 5 2 3 4 3 6.6 C 3 9.5 8 14 8 14 C 8 14 13 9.5 13 6.6 C 13 4 11 2 8 2 Z" />
      {/* Inner ring */}
      <circle cx="8" cy="6.6" r="1.6" />
    </svg>
  );
}
