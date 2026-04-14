interface GemmaStarProps {
  size?: number;
  className?: string;
}

export function GemmaStar({ size = 14, className = "" }: GemmaStarProps) {
  return (
    <svg
      viewBox="0 0 40 40"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="gemma-star-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="var(--color-accent-info)" />
          <stop offset="100%" stopColor="var(--color-accent-insight)" />
        </linearGradient>
      </defs>
      <path
        d="M 20 4 C 20 14, 14 20, 4 20 C 14 20, 20 26, 20 36 C 20 26, 26 20, 36 20 C 26 20, 20 14, 20 4 Z"
        fill="url(#gemma-star-grad)"
        opacity="0.8"
      />
      <path
        d="M 20 10 C 20 16, 16 20, 10 20 C 16 20, 20 24, 20 30 C 20 24, 24 20, 30 20 C 24 20, 20 16, 20 10 Z"
        fill="url(#gemma-star-grad)"
      />
    </svg>
  );
}
