import { useT } from "@/i18n/useT";
import type { PathRarityResult } from "@/data/pathRarity";

/**
 * Small chip surfaced on the SelectedNodeCard for non-direct paths.
 * Direct paths render NO badge — absence is the signal that the
 * trajectory is normal. This keeps badge density low and reserves
 * visual weight for paths that actually warrant attention.
 *
 * Color tiering:
 *   adjacent → muted (text-secondary border)
 *   stretch  → caution (amber)
 *   longshot → alert (the only red usage in the tree surface;
 *              justified because the message is "this is statistically
 *              unusual," not "this career is bad" — different semantic
 *              from edge labels' no-red rule)
 */

interface PathRarityBadgeProps {
  rarity: PathRarityResult;
}

export function PathRarityBadge({ rarity }: PathRarityBadgeProps) {
  const t = useT();
  if (rarity.tier === "direct") return null;

  const labelKey = `future.pathRarity.${rarity.tier}`;
  const tooltip = t("future.pathRarity.tooltip");

  const tierClass =
    rarity.tier === "adjacent"
      ? "border-border-default text-text-secondary bg-bp-surface"
      : rarity.tier === "stretch"
        ? "border-accent-caution/50 text-accent-caution bg-accent-caution/10"
        : "border-accent-alert/50 text-accent-alert bg-accent-alert/10";

  return (
    <span
      data-testid="path-rarity-badge"
      data-rarity={rarity.tier}
      title={tooltip}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-data text-[11px] font-bold tracking-wide uppercase border ${tierClass}`}
    >
      <span aria-hidden="true">
        {rarity.tier === "longshot" ? "↯" : rarity.tier === "stretch" ? "↗" : "·"}
      </span>
      <span>{t(labelKey)}</span>
    </span>
  );
}
