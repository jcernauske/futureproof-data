import type { CompareBuild, CompareBossRow } from "@/api/menu";
import { useT } from "@/i18n/useT";

interface RiskHeadlineGridProps {
  bosses: CompareBossRow[];
  builds: CompareBuild[];
  buildColors: string[];
  highlightIndex?: number | null;
}

const RESULT_PILL: Record<string, string> = {
  WIN: "bg-accent-thrive/15 text-accent-thrive",
  LOSE: "bg-accent-alert/15 text-accent-alert",
  DRAW: "bg-accent-caution/15 text-accent-caution",
};

// Backend emits English "WIN"/"LOSE"/"DRAW"/"UNKNOWN" sentinel strings;
// the pill text gets routed through `t()` so the user sees the active
// locale's word, while the styling key (RESULT_PILL above) stays
// English-stable.
const RESULT_LABEL_KEY: Record<string, string> = {
  WIN: "build.risk.result.win",
  LOSE: "build.risk.result.lose",
  DRAW: "build.risk.result.draw",
  UNKNOWN: "build.risk.result.unknown",
};

const BOSS_LABEL_KEY: Record<string, string> = {
  ai: "build.boss.ai.shortName",
  loans: "build.boss.loans.shortName",
  market: "build.boss.market.shortName",
  burnout: "build.boss.burnout.shortName",
  ceiling: "build.boss.ceiling.shortName",
};

const BOSS_DOT_COLORS: Record<string, string> = {
  ai: "var(--color-boss-ai)",
  loans: "var(--color-boss-loans)",
  market: "var(--color-boss-market)",
  burnout: "var(--color-boss-burnout)",
  ceiling: "var(--color-boss-ceiling)",
};

export function RiskHeadlineGrid({
  bosses,
  builds,
  highlightIndex = null,
}: RiskHeadlineGridProps) {
  const t = useT();
  return (
    <div
      className="bg-bp-deep border border-border-subtle rounded-[20px] p-5 overflow-hidden"
      data-testid="risk-headline-grid"
    >
      {/* Header row */}
      <div
        className="grid items-center pb-2 mb-1 border-b border-border"
        style={{ gridTemplateColumns: `140px repeat(${builds.length}, 1fr)` }}
      >
        <div className="font-data text-[11px] uppercase tracking-wider text-text-muted">
          {t("compare.risk.bossHeader")}
        </div>
        {builds.map((build, idx) => (
          <div
            key={build.build_id}
            data-col={idx + 1}
            className="text-center font-body text-[11px] font-bold uppercase text-text-muted transition-opacity duration-200"
            style={{ opacity: highlightIndex !== null && highlightIndex !== idx ? 0.2 : 1 }}
          >
            {build.school_name}
          </div>
        ))}
      </div>

      {/* Boss rows */}
      {bosses.map((boss, bossIdx) => (
        <div
          key={boss.boss_id}
          data-testid={`card-risk-${boss.boss_id}`}
          className={`grid items-center py-2.5 ${
            bossIdx > 0 ? "border-t border-border-subtle" : ""
          }`}
          style={{ gridTemplateColumns: `140px repeat(${builds.length}, 1fr)` }}
        >
          <div className="flex items-center gap-2 pr-3">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: BOSS_DOT_COLORS[boss.boss_id] ?? "var(--color-text-muted)" }}
            />
            <span className="font-display font-medium text-sm text-text-secondary">
              {BOSS_LABEL_KEY[boss.boss_id]
                ? t(BOSS_LABEL_KEY[boss.boss_id]!)
                : boss.label}
            </span>
          </div>
          {builds.map((build, buildIdx) => {
            const result = boss.values[buildIdx] ?? "—";
            const skillCount = boss.skill_counts?.[buildIdx] ?? 0;
            const isSkillAssisted = skillCount > 0;
            const pill = RESULT_PILL[result] ?? "bg-bp-deep text-text-muted";
            const resultLabelKey = RESULT_LABEL_KEY[result];
            const resultLabel = resultLabelKey ? t(resultLabelKey) : result;
            const dimmed = highlightIndex !== null && highlightIndex !== buildIdx;
            return (
              <div
                key={build.build_id}
                data-col={buildIdx + 1}
                className="flex items-center justify-center transition-opacity duration-200"
                style={{ opacity: dimmed ? 0.2 : 1 }}
              >
                <span className="relative inline-flex">
                  <span
                    className={`font-data text-sm font-bold px-4 py-1.5 rounded-full tracking-wider min-w-[64px] text-center ${pill}`}
                  >
                    {resultLabel}
                  </span>
                  {isSkillAssisted && (
                    <span
                      data-testid={`badge-skill-${boss.boss_id}-${build.build_id}`}
                      aria-label={t(
                        skillCount === 1 ? "compare.risk.skillsAriaLabel" : "compare.risk.skillsAriaLabelPlural",
                        { n: skillCount },
                      )}
                      className="absolute -top-2.5 -right-3 inline-flex items-center gap-0.5 font-data text-[11px] font-bold text-white px-2 py-0.5 rounded-full bg-red-700 shadow-sm"
                    >
                      <span className="text-[10px]">&#x25C6;</span>
                      {skillCount}
                    </span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
