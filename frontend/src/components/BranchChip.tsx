import { motion, useReducedMotion } from "framer-motion";
import type { CareerBranch } from "@/types/build";

interface BranchChipProps {
  branch: CareerBranch;
}

const STAT_META: Array<{
  key: keyof Pick<
    CareerBranch,
    "delta_ern" | "delta_roi" | "delta_res" | "delta_grw" | "delta_hmn"
  >;
  label: string;
  className: string;
}> = [
  {
    key: "delta_ern",
    label: "ERN",
    className: "bg-stat-ern/[0.15] text-stat-ern",
  },
  {
    key: "delta_roi",
    label: "ROI",
    className: "bg-stat-roi/[0.15] text-stat-roi",
  },
  {
    key: "delta_res",
    label: "RES",
    className: "bg-stat-res/[0.15] text-stat-res",
  },
  {
    key: "delta_grw",
    label: "GRW",
    className: "bg-stat-grw/[0.15] text-stat-grw",
  },
  {
    key: "delta_hmn",
    label: "HMN",
    className: "bg-stat-hmn/[0.15] text-stat-hmn",
  },
];

function formatDelta(value: number): string {
  const magnitude = Math.min(Math.abs(Math.trunc(value)), 3);
  if (magnitude === 0) return "";
  const glyph = value > 0 ? "+" : "-";
  return glyph.repeat(magnitude);
}

export function BranchChip({ branch }: BranchChipProps) {
  const reducedMotion = useReducedMotion() ?? false;
  const rationale = branch.unlock;

  return (
    <motion.article
      tabIndex={0}
      role="article"
      aria-label={`Branch: ${branch.to_title}`}
      whileHover={reducedMotion ? undefined : { y: -2 }}
      className="
        shrink-0 min-w-[220px] max-w-[260px] snap-start
        bg-bp-mid border border-border-subtle hover:border-border
        rounded-xl p-4
        shadow-md hover:shadow-lg
        transition-colors duration-normal
        focus-visible:outline-none focus-visible:ring-2
        focus-visible:ring-[color:var(--color-focus-ring)]
      "
    >
      <h3 className="font-body text-body font-bold text-text-primary line-clamp-2">
        {branch.to_title}
      </h3>
      <div className="flex flex-wrap gap-1.5 mt-2">
        {STAT_META.map(({ key, label, className }) => {
          const raw = branch[key];
          if (raw === null || raw === undefined || raw === 0) return null;
          const delta = formatDelta(raw);
          if (!delta) return null;
          return (
            <span
              key={key}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-data text-data-sm font-bold ${className}`}
            >
              {label} {delta}
            </span>
          );
        })}
      </div>
      {rationale ? (
        <p className="font-body text-small text-text-secondary italic mt-2 line-clamp-2">
          {rationale}
        </p>
      ) : null}
    </motion.article>
  );
}
