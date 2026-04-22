import { STAT_COLORS } from "./bossData";

interface StatBarRowProps {
  stat: string;
  value: number | null;
}

export function StatBarRow({ stat, value }: StatBarRowProps) {
  const colors = STAT_COLORS[stat];
  const v = value ?? 0;
  const fillPct = (v / 10) * 100;

  return (
    <div className="flex items-center gap-2">
      <span
        className="font-data uppercase font-bold"
        style={{ fontSize: 11, width: 28, color: colors?.text }}
      >
        {stat.toUpperCase()}
      </span>
      <div className="flex-1 h-1 rounded-full bg-bp-deep">
        <div
          className="h-full rounded-full"
          style={{
            width: `${fillPct}%`,
            background: colors?.text,
            opacity: 0.8,
            transition: "width 0.4s ease-out",
          }}
        />
      </div>
      <span className="font-data text-text-secondary" style={{ fontSize: 11, width: 16, textAlign: "right" }}>
        {v}
      </span>
    </div>
  );
}
