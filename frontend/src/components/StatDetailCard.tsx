import { STAT_MAP, type StatKey } from "@/data/statExplanations";
import { StatHelpTooltip } from "@/components/StatHelpTooltip";

interface StatDetailCardProps {
  statKey: StatKey;
  value: number | null;
}

export function StatDetailCard({ statKey, value }: StatDetailCardProps) {
  const stat = STAT_MAP[statKey];
  const displayValue = value ?? 0;
  const fillPercent = (displayValue / 10) * 100;

  return (
    <article
      id={`stat-${statKey}`}
      aria-label={`${stat.name}: ${displayValue} out of 10`}
      className="bg-bp-mid border border-border-subtle rounded-xl p-4 flex flex-col items-center gap-2"
    >
      <div className="flex items-center gap-1.5">
        <span className="font-data font-bold text-data" style={{ color: stat.color }}>
          {stat.abbreviation}
        </span>
        <StatHelpTooltip stat={stat} />
      </div>
      <p className="font-body font-semibold text-small text-text-secondary">
        {stat.name}
      </p>
      <span className="font-data font-bold text-data-lg" style={{ color: stat.color }}>
        {value !== null ? displayValue : "—"}
      </span>
      <div className="w-full h-1 bg-bp-surface rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-slow"
          style={{
            width: `${fillPercent}%`,
            backgroundColor: stat.color,
          }}
        />
      </div>
    </article>
  );
}
