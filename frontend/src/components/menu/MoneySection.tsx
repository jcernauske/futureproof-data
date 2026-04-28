import type { CompareBuild } from "@/api/menu";

interface MoneySectionProps {
  builds: CompareBuild[];
  highlightIndex?: number | null;
}

function formatSalaryShort(val: number | null): string {
  if (val == null) return "n/a";
  return `$${Math.round(val / 1000)}K`;
}

export function MoneySection({ builds, highlightIndex = null }: MoneySectionProps) {
  return (
    <div
      className="bg-bp-deep border border-border-subtle rounded-[20px] p-5"
      data-testid="money-section"
    >
      <div
        className="grid items-center"
        style={{ gridTemplateColumns: `140px repeat(${builds.length}, 1fr)` }}
      >
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full shrink-0 bg-stat-ern" />
          <span className="font-display font-medium text-sm text-text-secondary">
            Salary
          </span>
        </div>

        {builds.map((build, idx) => (
          <div
            key={build.build_id}
            data-col={idx + 1}
            data-testid={`salary-${build.build_id}`}
            className="flex justify-center transition-opacity duration-200"
            style={{
              opacity: highlightIndex !== null && highlightIndex !== idx ? 0.2 : 1,
            }}
          >
            <span className="font-data text-[22px] font-bold text-stat-ern">
              {formatSalaryShort(build.median_annual_wage)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
