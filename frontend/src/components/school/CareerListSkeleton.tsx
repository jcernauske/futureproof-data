interface CareerListSkeletonProps {
  /** How many placeholder rows to render. Defaults to 4. */
  count?: number;
}

/**
 * Skeleton-loader for the career list — renders placeholder rows
 * shaped like `CareerList` items (▸ glyph + SOC chip + title bar)
 * while `/build/outcomes` + `/build/tier` are in flight. Rows pulse
 * opacity via Tailwind's `animate-pulse` so the surface reads as
 * "content is arriving" rather than "nothing is happening."
 *
 * Sits under the "WHERE THIS COMMONLY LEADS" caption in place of
 * plain loading text.
 */
export function CareerListSkeleton({ count = 4 }: CareerListSkeletonProps) {
  return (
    <ul
      className="flex flex-col gap-3 list-none"
      aria-label="Loading career paths"
      data-testid="career-list-skeleton"
    >
      {Array.from({ length: count }).map((_, i) => (
        <li key={i}>
          <div
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg border border-border-subtle bg-bp-mid animate-pulse"
            aria-hidden="true"
          >
            <span className="font-data text-data-sm text-text-muted/30">▸</span>
            <span className="h-3 w-14 rounded bg-text-muted/20" />
            <span
              className="h-3 flex-1 rounded bg-text-muted/15"
              style={{ maxWidth: `${70 - i * 10}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
