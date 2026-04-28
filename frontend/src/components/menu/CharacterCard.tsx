import type { CompareBuild, CompareStatRow } from "@/api/menu";

interface CharacterCardProps {
  build: CompareBuild;
  stats: CompareStatRow[];
  buildIndex: number;
  highlighted?: boolean;
  onOpen?: () => void;
}

const STAT_BARS: { label: string; color: string }[] = [
  { label: "ERN", color: "var(--color-stat-ern)" },
  { label: "ROI", color: "var(--color-stat-roi)" },
  { label: "RES", color: "var(--color-stat-res)" },
  { label: "GRW", color: "var(--color-stat-grw)" },
  { label: "HMN", color: "var(--color-stat-hmn)" },
];

function formatCost(val: number | null): string {
  if (val == null) return "n/a";
  return `$${val.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function CharacterCard({ build, stats, buildIndex, highlighted = true, onOpen }: CharacterCardProps) {
  const statMap: Record<string, number | null> = {};
  for (const row of stats) {
    statMap[row.label] = row.values[buildIndex] ?? null;
  }

  return (
    <article
      data-testid={`card-character-${build.build_id}`}
      aria-label={`${build.school_name} ${build.major_text}`}
      className="bg-bp-mid border border-border-subtle rounded-[20px] px-5 pt-6 pb-5 transition-all duration-200 cursor-pointer h-full flex flex-col"
      style={{
        opacity: highlighted ? 1 : 0.2,
        borderColor: highlighted ? undefined : undefined,
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <p className="font-display font-semibold text-[20px] text-text-primary leading-tight">
          {build.school_name}
        </p>
        {onOpen && (
          <button
            type="button"
            aria-label={`Open ${build.school_name} build`}
            onClick={onOpen}
            className="shrink-0 mt-0.5 w-6 h-6 rounded-md flex items-center justify-center text-text-muted hover:text-accent-info hover:bg-accent-info/10 transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M5.25 2.333H3.5a1.167 1.167 0 0 0-1.167 1.167v7a1.167 1.167 0 0 0 1.167 1.167h7A1.167 1.167 0 0 0 11.667 10.5V8.75M8.167 2.333h3.5v3.5M5.833 8.167 11.667 2.333" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        )}
      </div>
      <p className="text-sm text-text-secondary mb-4">{build.major_text}</p>

      <div className="flex flex-col gap-2 mb-4">
        {STAT_BARS.map(({ label, color: statColor }) => {
          const val = statMap[label] ?? 0;
          const pct = Math.max(0, Math.min(100, (val / 10) * 100));
          return (
            <div key={label} className="flex items-center gap-2">
              <span
                className="font-data text-[10px] font-bold uppercase tracking-wider w-8 shrink-0"
                style={{ color: statColor }}
              >
                {label}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${pct}%`, background: statColor }}
                />
              </div>
              <span
                className="font-data text-[11px] font-bold w-6 text-right shrink-0"
                style={{ color: statColor }}
              >
                {val ?? "—"}
              </span>
            </div>
          );
        })}
      </div>

      <div className="border-t border-border-subtle mt-auto" />
      <div className="flex justify-between items-baseline pt-3">
        <span className="text-xs text-text-muted">
          {build.is_out_of_state ? "Out-of-state tuition (4 yr)" : "In-state tuition (4 yr)"}
        </span>
        <span className="font-data text-base font-bold text-accent-caution">
          {formatCost(build.tuition_annual != null ? build.tuition_annual * 4 : null)}
        </span>
      </div>
    </article>
  );
}
