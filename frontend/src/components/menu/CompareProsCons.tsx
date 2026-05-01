import type { BuildProsCons, CompareBuild } from "@/api/menu";

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-caution)",
  "var(--color-accent-empathy)",
];

interface CompareProsConsProps {
  builds: CompareBuild[];
  prosCons: BuildProsCons[];
  highlightIndex: number | null;
}

function shortLabel(name: string, maxLen = 28): string {
  if (name.length <= maxLen) return name;
  return name.slice(0, maxLen - 1).trimEnd() + "…";
}

export function CompareProsCons({
  builds,
  prosCons,
  highlightIndex,
}: CompareProsConsProps) {
  // Re-order pros/cons to match the visual build order from `builds`. Skip
  // any pros/cons entries that don't match a build in the result set.
  const ordered = builds
    .map((b, idx) => {
      const entry = prosCons.find((pc) => pc.build_id === b.build_id);
      if (!entry) return null;
      return { build: b, entry, idx };
    })
    .filter((x): x is { build: CompareBuild; entry: BuildProsCons; idx: number } => x !== null);

  if (ordered.length === 0) return null;

  return (
    <div
      data-testid="compare-pros-cons"
      className="grid grid-cols-1 tablet:grid-cols-2 gap-4"
    >
      {ordered.map(({ build, entry, idx }) => {
        const color = BUILD_COLORS[idx];
        const dimmed = highlightIndex !== null && highlightIndex !== idx;
        return (
          <article
            key={build.build_id}
            data-testid={`pros-cons-${build.build_id}`}
            className={[
              "rounded-xl p-4 border border-border-subtle bg-bp-deep/40",
              "transition-opacity duration-normal",
              dimmed ? "opacity-40" : "opacity-100",
            ].join(" ")}
            style={{ borderLeftColor: color, borderLeftWidth: 3 }}
          >
            <header className="flex items-baseline justify-between gap-2 mb-3">
              <h4 className="font-display text-heading text-text-primary line-clamp-1">
                {shortLabel(build.school_name)}
              </h4>
              <p className="font-data text-micro text-text-muted line-clamp-1">
                {build.career}
              </p>
            </header>

            {entry.pros.length > 0 && (
              <ul className="flex flex-col gap-2 mb-3">
                {entry.pros.map((p, i) => (
                  <li
                    key={`pro-${i}`}
                    className="flex gap-2 font-body text-small text-text-primary leading-snug"
                  >
                    <span
                      aria-hidden
                      className="text-accent-thrive font-bold mt-0.5 shrink-0"
                    >
                      ✓
                    </span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            )}

            {entry.cons.length > 0 && (
              <ul className="flex flex-col gap-2">
                {entry.cons.map((c, i) => (
                  <li
                    key={`con-${i}`}
                    className="flex gap-2 font-body text-small text-text-secondary leading-snug"
                  >
                    <span
                      aria-hidden
                      className="text-accent-alert font-bold mt-0.5 shrink-0"
                    >
                      −
                    </span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            )}
          </article>
        );
      })}
    </div>
  );
}
