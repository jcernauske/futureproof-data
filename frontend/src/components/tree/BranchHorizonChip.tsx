import { useT } from "@/i18n/useT";
import {
  dominantStatDelta,
  relatednessTier,
  socRollup,
  truncateTitle,
  type RelatednessTier,
} from "@/data/horizonLayout";
import type { CareerBranch } from "@/types/build";

interface BranchHorizonChipProps {
  branch: CareerBranch;
  selected: boolean;
  flashing: boolean;
  onClick: () => void;
}

const TIER_DATA: Record<RelatednessTier, string> = {
  "Primary-Short": "primary-short",
  "Primary-Long": "primary-long",
  "Supplemental": "supplemental",
};

const STAT_LABEL: Record<"ern" | "grw" | "hmn" | "res", string> = {
  ern: "ERN",
  grw: "GRW",
  hmn: "HMN",
  res: "RES",
};

export function BranchHorizonChip({
  branch,
  selected,
  flashing,
  onClick,
}: BranchHorizonChipProps) {
  const t = useT();
  const tier = relatednessTier(branch.relatedness);
  const dominant = dominantStatDelta(branch);
  const expTier = branch.experience_tier;
  const showExpBadge = expTier === "mid" || expTier === "senior";
  const levelUnknown = branch.related_education_level == null;
  const rollup = socRollup(branch.to_soc);

  const className = [
    "horizon-chip",
    flashing ? "branch-flash" : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type="button"
      data-testid={`chip-branch-${branch.to_soc}`}
      data-tier={tier ? TIER_DATA[tier] : undefined}
      data-selected={selected ? "true" : undefined}
      data-level-unknown={levelUnknown ? "true" : undefined}
      onClick={onClick}
      className={className}
      aria-label={branch.to_title}
      title={branch.to_title}
    >
      <div className="horizon-chip-title">{truncateTitle(branch.to_title)}</div>

      <div className="horizon-chip-meta">
        {dominant && (
          <span
            className="horizon-stat-badge"
            data-stat={dominant.stat}
            data-sign={dominant.value < 0 ? "neg" : "pos"}
          >
            {dominant.value > 0 ? "+" : ""}
            {dominant.value} {STAT_LABEL[dominant.stat]}
          </span>
        )}
        {rollup && (
          <span
            className="horizon-rollup-badge"
            data-rollup={rollup}
            data-testid={`chip-rollup-${rollup}`}
          >
            {t(`tree.chip.rollup.${rollup}`)}
          </span>
        )}
        {showExpBadge && (
          <span className="horizon-exp-badge" data-tier={expTier ?? undefined}>
            {expTier === "senior"
              ? t("tree.chip.experience.senior")
              : t("tree.chip.experience.mid")}
          </span>
        )}
      </div>

      {branch.unlock && (
        <div className="horizon-chip-unlock">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M19 11H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2z" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>{branch.unlock}</span>
        </div>
      )}
    </button>
  );
}
