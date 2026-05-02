import type { StatFilter } from "@/data/statFilter";
import { useT } from "@/i18n/useT";

interface StatFilterRowProps {
  active: ReadonlySet<StatFilter>;
  onToggle: (filter: StatFilter) => void;
  /** Filters that have at least one match in the underlying tree.
   *  Chips not in the set are skipped to save real estate. */
  available?: ReadonlySet<StatFilter>;
}

const FILTER_ORDER: readonly StatFilter[] = [
  "earnings",
  "ai_resilient",
  "growth",
] as const;

const LABEL_KEY: Record<StatFilter, string> = {
  earnings: "future.stat.earnings",
  ai_resilient: "future.stat.aiResilient",
  growth: "future.stat.growth",
};

/**
 * Stat-improvement filter chips above the /future tree. AND'd
 * within the row (all active filters must improve), AND'd across
 * to education filters. See data/statFilter.ts.
 */
export function StatFilterRow({ active, onToggle, available }: StatFilterRowProps) {
  const t = useT();
  const visibleFilters = available
    ? FILTER_ORDER.filter((f) => available.has(f) || active.has(f))
    : FILTER_ORDER;
  if (visibleFilters.length === 0) return null;
  return (
    <div
      role="group"
      aria-label={t("future.stat.aria")}
      data-testid="stat-filter-row"
      className="flex flex-wrap items-center gap-2"
    >
      <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted mr-1">
        {t("future.stat.label")}
      </span>
      {visibleFilters.map((filter) => {
        const isActive = active.has(filter);
        return (
          <button
            key={filter}
            type="button"
            data-testid={`stat-filter-chip-${filter}`}
            data-active={isActive ? "true" : undefined}
            aria-pressed={isActive}
            onClick={() => onToggle(filter)}
            className={[
              "inline-flex items-center px-3 py-1.5 rounded-full",
              "font-body text-small font-semibold whitespace-nowrap",
              "border transition-colors duration-normal cursor-pointer",
              "focus-visible:outline-none focus-visible:ring-2",
              "focus-visible:ring-[color:var(--color-focus-ring)]",
              isActive
                ? "bg-accent-thrive/15 border-accent-thrive text-accent-thrive"
                : "bg-bp-surface border-border-subtle text-text-secondary hover:text-text-primary hover:border-border-default",
            ].join(" ")}
          >
            {t(LABEL_KEY[filter])}
          </button>
        );
      })}
    </div>
  );
}
