import type { EducationFilter } from "@/data/educationFilter";
import { useT } from "@/i18n/useT";

interface EducationFilterRowProps {
  active: ReadonlySet<EducationFilter>;
  onToggle: (filter: EducationFilter) => void;
}

const FILTER_ORDER: readonly EducationFilter[] = [
  "bachelors",
  "masters",
  "doctoral",
] as const;

const LABEL_KEY: Record<EducationFilter, string> = {
  bachelors: "future.filter.bachelors",
  masters: "future.filter.masters",
  doctoral: "future.filter.doctoral",
};

/**
 * Multi-select filter chips above the /future tree. OR'd: any active
 * chip matches; zero active = unfiltered. Hides non-matching L1
 * branches per Decision (educationFilter) — see filterTreeByEducation.
 */
export function EducationFilterRow({
  active,
  onToggle,
}: EducationFilterRowProps) {
  const t = useT();
  return (
    <div
      role="group"
      aria-label={t("future.filter.aria")}
      data-testid="education-filter-row"
      className="flex flex-wrap items-center gap-2"
    >
      <span className="font-mono text-[10px] uppercase tracking-wider text-text-muted mr-1">
        {t("future.filter.label")}
      </span>
      {FILTER_ORDER.map((filter) => {
        const isActive = active.has(filter);
        return (
          <button
            key={filter}
            type="button"
            data-testid={`filter-chip-${filter}`}
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
                ? "bg-accent-info/15 border-accent-info text-accent-info"
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
