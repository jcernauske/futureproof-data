import type { BossFilter } from "@/data/bossFilter";
import { useT } from "@/i18n/useT";

interface BossFilterRowProps {
  active: ReadonlySet<BossFilter>;
  onToggle: (filter: BossFilter) => void;
  /** Filters that have at least one match in the underlying tree.
   *  Chips not in the set are skipped to save real estate. */
  available?: ReadonlySet<BossFilter>;
}

const FILTER_ORDER: readonly BossFilter[] = [
  "boss_ai",
  "boss_market",
  "boss_burnout",
] as const;

const LABEL_KEY: Record<BossFilter, string> = {
  boss_ai: "future.survives.ai",
  boss_market: "future.survives.market",
  boss_burnout: "future.survives.burnout",
};

const ARIA_BOSS: Record<BossFilter, string> = {
  boss_ai: "AI",
  boss_market: "market",
  boss_burnout: "burnout",
};

/**
 * T2.1 — SURVIVES boss-outcome filter row. Shares row geometry with
 * EducationFilterRow / StatFilterRow but uses `accent-caution` as the
 * active accent (gauntlet's "draw" color) — semantic signal that this
 * is the survival/threat axis, not improvement (thrive) or
 * constraint-eligibility (info).
 */
export function BossFilterRow({ active, onToggle, available }: BossFilterRowProps) {
  const t = useT();
  const visibleFilters = available
    ? FILTER_ORDER.filter((f) => available.has(f) || active.has(f))
    : FILTER_ORDER;
  if (visibleFilters.length === 0) return null;
  return (
    <div
      role="group"
      aria-label={t("future.survives.aria")}
      data-testid="boss-filter-row"
      className="flex flex-wrap items-center gap-2"
    >
      <span className="font-data text-[10px] uppercase tracking-wider text-text-muted mr-1">
        {t("future.survives.label")}
      </span>
      {visibleFilters.map((filter) => {
        const isActive = active.has(filter);
        return (
          <button
            key={filter}
            type="button"
            data-testid={`survives-chip-${filter}`}
            data-active={isActive ? "true" : undefined}
            aria-pressed={isActive}
            aria-label={t("future.survives.chipAria").replace(
              "{boss}",
              ARIA_BOSS[filter],
            )}
            onClick={() => onToggle(filter)}
            className={[
              "inline-flex items-center px-3 py-1.5 rounded-full",
              "font-body text-small font-semibold whitespace-nowrap",
              "border transition-colors duration-normal cursor-pointer",
              "focus-visible:outline-none focus-visible:ring-2",
              "focus-visible:ring-[color:var(--color-focus-ring)]",
              isActive
                ? "bg-accent-caution/15 border-accent-caution text-accent-caution"
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
