import type { CompareBuild, CompareStatRow } from "@/api/menu";
import { useT } from "@/i18n/useT";

type T = (key: string, vars?: Record<string, string | number>) => string;

const BUILD_COLORS = [
  "var(--color-accent-thrive)",
  "var(--color-accent-info)",
  "var(--color-accent-caution)",
  "var(--color-accent-empathy)",
];

interface CompareSchoolProfileProps {
  builds: CompareBuild[];
  stats: CompareStatRow[];
  highlightIndex: number | null;
}

function fmtDollar(val: number | null): string {
  if (val == null) return "—";
  return val.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function fmtNumber(val: number | null): string {
  if (val == null) return "—";
  return val.toLocaleString("en-US");
}

function fmtRatio(val: number | null): string {
  if (val == null) return "—";
  return val.toFixed(2);
}

interface AuraMetric {
  labelKey: string;
  getValue: (b: CompareBuild) => number | null;
  format: (val: number | null) => string;
  barColor: string;
  fixedScale?: number;
}

const AURA_METRICS: AuraMetric[] = [
  {
    labelKey: "compare.school.endowmentPerStudent",
    getValue: (b) => b.endowment_per_fte,
    format: fmtDollar,
    barColor: "var(--color-accent-info)",
  },
  {
    labelKey: "compare.school.marketingRatio",
    getValue: (b) => b.marketing_ratio,
    format: fmtRatio,
    barColor: "var(--color-accent-caution)",
  },
  {
    labelKey: "compare.school.athleticPerStudent",
    getValue: (b) => b.athletic_spend_per_fte,
    format: fmtDollar,
    barColor: "var(--color-accent-empathy)",
  },
];

const COVERAGE_PILLS: Record<string, string> = {
  full: "bg-accent-thrive/15 text-accent-thrive",
  partial: "bg-accent-caution/15 text-accent-caution",
  minimal: "bg-accent-alert/15 text-accent-alert",
};

export function CompareSchoolProfile({ builds, stats, highlightIndex }: CompareSchoolProfileProps) {
  const t = useT();
  const auraRow = stats.find((s) => s.label === "AURA");
  const allMissing = builds.every(
    (b) => b.endowment_per_fte == null && b.marketing_ratio == null && b.athletic_spend_per_fte == null && b.fte_enrollment == null,
  );

  if (allMissing) {
    return (
      <p className="font-body text-small text-text-muted italic text-center py-6">
        {t("compare.school.unavailable")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-0">
      {/* Zone 1: Identity Cards */}
      <div className="grid grid-cols-1 tablet:grid-cols-2 desktop:grid-cols-4 gap-3">
        {builds.map((build, idx) => {
          const dimmed = highlightIndex !== null && highlightIndex !== idx;
          return (
            <div
              key={build.build_id}
              data-col={idx + 1}
              className="bg-bp-mid/50 rounded-xl p-4 border border-border-subtle transition-opacity duration-200"
              style={{
                opacity: dimmed ? 0.2 : 1,
                borderLeftWidth: "3px",
                borderLeftColor: BUILD_COLORS[idx],
              }}
            >
              <p className="font-display font-semibold text-[16px] text-text-primary mb-1">
                {build.school_name}
              </p>
              <p className="font-body text-small text-text-secondary">
                {build.institution_control ?? "—"} / {build.state_abbr ?? "—"}
              </p>
              <p className="font-data text-data text-text-primary mt-1">
                {build.fte_enrollment != null ? fmtNumber(build.fte_enrollment) : "—"}{" "}
                <span className="text-text-muted">{t("compare.school.students")}</span>
              </p>
            </div>
          );
        })}
      </div>

      {/* Zone 2: AURA Breakdown Table */}
      <div className="mt-5 pt-4 border-t border-border-subtle">
        <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3">
          {t("compare.school.xray")}
        </p>

        {/* Desktop table */}
        <div className="hidden tablet:block">
          <div
            className="grid items-center gap-y-0"
            style={{ gridTemplateColumns: `180px repeat(${builds.length}, 1fr)` }}
          >
            {/* Header */}
            <div />
            {builds.map((build) => (
              <p key={build.build_id} className="font-body text-[11px] font-bold uppercase text-text-muted text-center pb-2">
                {build.school_name}
              </p>
            ))}

            {/* Metric rows */}
            {AURA_METRICS.map((metric) => {
              const values = builds.map(metric.getValue);
              const maxVal = metric.fixedScale ?? Math.max(...values.filter((v): v is number => v != null), 1);
              return (
                <AuraTableRow
                  key={metric.labelKey}
                  metric={metric}
                  t={t}
                  builds={builds}
                  values={values}
                  maxVal={maxVal}
                  highlightIndex={highlightIndex}
                />
              );
            })}

            {/* AURA Score row */}
            {auraRow && (
              <>
                <span className="font-body text-small text-text-secondary py-2.5 border-t border-border-subtle">
                  {t("compare.school.auraScore")}
                </span>
                {auraRow.values.map((val, idx) => {
                  const dimmed = highlightIndex !== null && highlightIndex !== idx;
                  const pct = val != null ? (val / 10) * 100 : 0;
                  return (
                    <div
                      key={builds[idx]?.build_id ?? idx}
                      data-col={idx + 1}
                      className="flex items-center gap-2 justify-center py-2.5 border-t border-border-subtle transition-opacity duration-200"
                      style={{ opacity: dimmed ? 0.2 : 1 }}
                    >
                      <div className="w-16 h-1.5 rounded-full bg-white/[0.06] overflow-hidden shrink-0">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${pct}%`, background: "var(--color-accent-insight)" }}
                        />
                      </div>
                      <span className={`font-data text-data whitespace-nowrap ${val == null ? "text-text-muted" : "text-text-primary"}`}>
                        {val != null ? val.toFixed(1) : "—"}
                      </span>
                    </div>
                  );
                })}
              </>
            )}

            {/* Coverage row */}
            <span className="font-body text-small text-text-secondary py-2.5 border-t border-border-subtle">
              {t("compare.school.coverage")}
            </span>
            {builds.map((build, idx) => {
              const dimmed = highlightIndex !== null && highlightIndex !== idx;
              const tier = build.coverage_tier;
              const pillClass = tier ? COVERAGE_PILLS[tier] ?? "" : "";
              const tierLabel = tier ? t(`compare.school.coverageTier.${tier}`) : null;
              return (
                <div
                  key={build.build_id}
                  data-col={idx + 1}
                  className="flex justify-center py-2.5 border-t border-border-subtle transition-opacity duration-200"
                  style={{ opacity: dimmed ? 0.2 : 1 }}
                >
                  {tier ? (
                    <span className={`${pillClass} rounded-full px-3 py-0.5 font-data text-data-sm font-bold`}>
                      {tierLabel}
                    </span>
                  ) : (
                    <span className="font-data text-data text-text-muted">—</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Mobile cards */}
        <div className="tablet:hidden flex flex-col gap-3">
          {builds.map((build, idx) => {
            const dimmed = highlightIndex !== null && highlightIndex !== idx;
            const auraVal = auraRow?.values[idx] ?? null;
            return (
              <div
                key={build.build_id}
                data-col={idx + 1}
                className="bg-bp-mid/50 rounded-xl p-4 border border-border-subtle transition-opacity duration-200"
                style={{ opacity: dimmed ? 0.2 : 1 }}
              >
                <p className="font-display font-semibold text-[14px] text-text-primary mb-2">
                  {build.school_name}
                </p>
                {AURA_METRICS.map((metric) => {
                  const val = metric.getValue(build);
                  return (
                    <div key={metric.labelKey} className="flex justify-between py-1.5 border-t border-border-subtle">
                      <span className="font-body text-small text-text-secondary">{t(metric.labelKey)}</span>
                      <span className={`font-data text-data ${val == null ? "text-text-muted" : "text-text-primary"}`}>
                        {metric.format(val)}
                      </span>
                    </div>
                  );
                })}
                <div className="flex justify-between py-1.5 border-t border-border-subtle">
                  <span className="font-body text-small text-text-secondary">{t("compare.school.auraScore")}</span>
                  <span className={`font-data text-data ${auraVal == null ? "text-text-muted" : "text-text-primary"}`}>
                    {auraVal != null ? auraVal.toFixed(1) : "—"}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-t border-border-subtle">
                  <span className="font-body text-small text-text-secondary">{t("compare.school.coverage")}</span>
                  {build.coverage_tier ? (
                    <span className={`${COVERAGE_PILLS[build.coverage_tier] ?? ""} rounded-full px-3 py-0.5 font-data text-data-sm font-bold`}>
                      {t(`compare.school.coverageTier.${build.coverage_tier}`)}
                    </span>
                  ) : (
                    <span className="font-data text-data text-text-muted">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* AURA Score Basis note */}
      {builds.some((b) => b.aura_score_basis) && (
        <p className="font-data text-data-sm text-text-muted italic mt-3">
          {t("compare.school.auraBasis", {
            basis: builds
              .map((b) => b.aura_score_basis)
              .filter((v): v is string => Boolean(v))
              .map((raw) => {
                // Look up a localized label for the enum; fall back to
                // the raw backend string if no translation exists yet
                // (better than rendering "compare.school.auraBasisLabel.X"
                // verbatim on screen).
                const localized = t(`compare.school.auraBasisLabel.${raw}`);
                return localized.startsWith("compare.school.auraBasisLabel.")
                  ? raw
                  : localized;
              })
              .join(" / "),
          })}
        </p>
      )}
    </div>
  );
}

function AuraTableRow({
  metric,
  t,
  builds,
  values,
  maxVal,
  highlightIndex,
}: {
  metric: AuraMetric;
  t: T;
  builds: CompareBuild[];
  values: (number | null)[];
  maxVal: number;
  highlightIndex: number | null;
}) {
  return (
    <>
      <span className="font-body text-small text-text-secondary py-2.5 border-t border-border-subtle">
        {t(metric.labelKey)}
      </span>
      {values.map((val, idx) => {
        const dimmed = highlightIndex !== null && highlightIndex !== idx;
        const pct = val != null ? (val / maxVal) * 100 : 0;
        return (
          <div
            key={builds[idx]?.build_id ?? idx}
            data-col={idx + 1}
            className="flex items-center gap-2 justify-center py-2.5 border-t border-border-subtle transition-opacity duration-200"
            style={{ opacity: dimmed ? 0.2 : 1 }}
          >
            {val != null ? (
              <>
                <div className="w-16 h-1.5 rounded-full bg-white/[0.06] overflow-hidden shrink-0">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, background: metric.barColor }}
                  />
                </div>
                <span className="font-data text-data text-text-primary whitespace-nowrap">
                  {metric.format(val)}
                </span>
              </>
            ) : (
              <span className="font-data text-data text-text-muted">—</span>
            )}
          </div>
        );
      })}
    </>
  );
}
