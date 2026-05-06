import { motion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";
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

/**
 * Editorial pros/cons -- each build gets a full-width card with
 * flowing prose instead of bullet lists. The build's identity color
 * runs as a top accent stripe. Reads like a reviewer's take, not a
 * feature matrix.
 */
export function CompareProsCons({
  builds,
  prosCons,
  highlightIndex,
}: CompareProsConsProps) {
  const ordered = builds
    .map((b, idx) => {
      const entry = prosCons.find((pc) => pc.build_id === b.build_id);
      if (!entry) return null;
      return { build: b, entry, idx };
    })
    .filter(
      (x): x is { build: CompareBuild; entry: BuildProsCons; idx: number } =>
        x !== null,
    );

  if (ordered.length === 0) return null;

  return (
    <motion.div
      data-testid="compare-pros-cons"
      className="grid grid-cols-1 tablet:grid-cols-2 gap-4"
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: stagger.normal } },
      }}
    >
      {ordered.map(({ build, entry, idx }) => {
        const color = BUILD_COLORS[idx];
        const dimmed = highlightIndex !== null && highlightIndex !== idx;
        const hasPros = entry.pros.length > 0;
        const hasCons = entry.cons.length > 0;
        const isLastOdd = idx === ordered.length - 1 && ordered.length % 2 === 1;

        return (
          <motion.article
            key={build.build_id}
            data-testid={`pros-cons-${build.build_id}`}
            variants={{
              hidden: { opacity: 0, y: 16 },
              visible: { opacity: 1, y: 0, transition: springs.smooth },
            }}
            className={[
              "rounded-lg border border-border-subtle bg-bp-mid/50 overflow-hidden",
              "transition-opacity duration-normal",
              dimmed ? "opacity-40" : "opacity-100",
              isLastOdd ? "tablet:max-w-[calc(50%-8px)]" : "",
            ].join(" ")}
          >
            {/* Top accent stripe -- build identity color */}
            <div
              className="h-[3px] w-full"
              style={{ background: color }}
            />

            <div className="px-5 py-4 tablet:px-6">
              {/* Header: school + career on one line */}
              <div className="flex items-baseline gap-3 mb-3">
                <h4 className="font-display text-[18px] font-semibold text-text-primary leading-snug line-clamp-1">
                  {shortLabel(build.school_name)}
                </h4>
                <span className="font-data text-data-sm text-text-muted whitespace-nowrap">
                  {build.career}
                </span>
              </div>

              {/* Editorial prose -- strengths */}
              {hasPros && (
                <div className="mb-2">
                  <span className="font-data text-[10px] font-bold uppercase tracking-widest text-accent-thrive">
                    Strengths
                  </span>
                  <p className="mt-1 font-body text-[15px] text-text-primary leading-relaxed">
                    {entry.pros.join(". ")}{entry.pros.length > 0 && !entry.pros[entry.pros.length - 1]!.endsWith(".") ? "." : ""}
                  </p>
                </div>
              )}

              {/* Editorial prose -- watch for */}
              {hasCons && (
                <div>
                  <span className="font-data text-[10px] font-bold uppercase tracking-widest text-accent-alert">
                    Watch for
                  </span>
                  <p className="mt-1 font-body text-[15px] text-text-secondary leading-relaxed">
                    {entry.cons.join(". ")}{entry.cons.length > 0 && !entry.cons[entry.cons.length - 1]!.endsWith(".") ? "." : ""}
                  </p>
                </div>
              )}
            </div>
          </motion.article>
        );
      })}
    </motion.div>
  );
}
