import { STAT_COLORS } from "./bossData";

interface SkillStatBadgeProps {
  stat: string;
  delta: number;
}

export function SkillStatBadge({ stat, delta }: SkillStatBadgeProps) {
  const colors = STAT_COLORS[stat.toLowerCase()];
  if (!colors || delta === 0) return null;

  const sign = delta > 0 ? "+" : "";

  return (
    <span
      className="font-data font-bold rounded-full"
      style={{
        fontSize: 11,
        letterSpacing: "0.3px",
        padding: "2px 8px",
        color: colors.text,
        background: colors.bg,
      }}
    >
      {stat.toUpperCase()} {sign}{delta}
    </span>
  );
}
