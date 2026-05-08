import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import type { CareerOutcome } from "@/types/build";
import { socEmoji } from "@/data/socEmoji";
import { useT } from "@/i18n/useT";

interface CareerCardProps {
  career: CareerOutcome;
  picked: boolean;
  onSelect: () => void;
  ernShift?: number;
  educationLabel?: string | null;
  hideNullStats?: boolean;
  onAskGemma?: (career: CareerOutcome) => void;
}

export function CareerCard({
  career,
  picked,
  onSelect,
  educationLabel,
  onAskGemma,
}: CareerCardProps) {
  const wage = career.median_annual_wage;
  const reducedMotion = useReducedMotion() ?? false;
  const t = useT();

  // Salary-row priority chain (experience-aware OEWS branching):
  //   1a. Entry-accessible careers (work_experience_code 2, 3, or null)
  //       → OEWS p10–p25 with "starting range" label. Fixes the
  //       temporal flattening where entry-level cards used to show
  //       p25–p75 of currently-working incumbents (mostly mid-career).
  //   1b. Long-term careers (code 1, requires 5+ years experience)
  //       → OEWS p25–p75 with "typical range" label. p10 here would
  //       be misleading because nobody enters this SOC at year one.
  //   2.  Scorecard p25–p75 (program-specific, year-one) — fallback
  //   3.  Scorecard median — last-resort single number
  //   4.  nothing — omit row entirely
  // Null work_experience_code is treated as early-career so the data
  // still surfaces; per project memory feedback_no_substitution_caveat
  // we never render a "limited data" warning.
  const isEntryAccessible =
    career.work_experience_code === 2 ||
    career.work_experience_code === 3 ||
    career.work_experience_code == null;
  const hasOewsStarting =
    isEntryAccessible &&
    career.wage_p10 != null &&
    career.wage_p25 != null;
  const hasOewsTypical =
    !isEntryAccessible &&
    career.wage_p25 != null &&
    career.wage_p75 != null;
  const hasScRange =
    career.earnings_1yr_p25 != null && career.earnings_1yr_p75 != null;

  // role="button" + tabIndex (instead of <button>) so the sparkle can
  // nest as a real <button> inside without violating button-in-button
  // semantics. Keyboard activation (Enter/Space → onSelect) is wired
  // explicitly. Same pattern the skill card uses on BossBand.
  return (
    <motion.div
      id={`career-${career.soc_code}`}
      role="button"
      tabIndex={0}
      aria-label={`${career.occupation_title}${picked ? " (selected)" : ""}`}
      aria-pressed={picked}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className={`w-full h-full flex flex-col text-left rounded-xl p-5 border cursor-pointer transition-all duration-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] ${
        picked
          ? "bg-bp-surface border-accent-thrive/40 shadow-glow-thrive -translate-y-0.5"
          : "bg-bp-mid border-border-subtle hover:bg-bp-surface hover:border-border hover:shadow-lg hover:-translate-y-0.5"
      }`}
      whileTap={reducedMotion ? undefined : { scale: 0.98 }}
      transition={springs.snappy}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="text-[28px] leading-none select-none flex-shrink-0"
        >
          {socEmoji(career.soc_code)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            {/* Title + sparkle live in the same flex row. The sparkle is
                a sibling of the h3 (not nested inside) so the h3's
                truncation can't clip the button when the title overflows.
                ``shrink-0`` reserves the button's width so the title takes
                whatever's left. ``mt-0.5`` aligns the button's optical
                center with the first text line. */}
            <div className="flex items-start gap-1.5 min-w-0 flex-1">
              <h3 className="font-body font-bold text-body-lg text-text-primary min-w-0">
                {career.occupation_title}
              </h3>
              {onAskGemma && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onAskGemma(career);
                  }}
                  data-testid={`btn-ask-career-${career.soc_code}`}
                  aria-label={`Ask Gemma about ${career.occupation_title}`}
                  className={[
                    "shrink-0 mt-0.5 inline-flex items-center justify-center",
                    "w-5 h-5 rounded-full",
                    "bg-bp-deep/80 border border-border-subtle",
                    "hover:bg-state-loading hover:border-accent-insight/40 hover:scale-110",
                    "active:scale-100",
                    "focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none",
                    "transition-all duration-fast",
                    "cursor-pointer",
                  ].join(" ")}
                >
                  <span aria-hidden className="text-accent-insight text-[11px]">✦</span>
                </button>
              )}
            </div>
            {picked && (
              <span
                aria-hidden="true"
                className="shrink-0 inline-flex items-center bg-accent-thrive/15 text-accent-thrive font-data text-micro font-bold uppercase tracking-[2px] rounded-full px-2 py-0.5"
              >
                Selected
              </span>
            )}
          </div>
          {educationLabel && (
            <p className="font-body text-small text-text-secondary mt-1">
              {educationLabel}
            </p>
          )}
        </div>
      </div>

      <div className="mt-auto pt-3 flex flex-col gap-1 font-data text-data">
        {hasOewsStarting ? (
          <p className="text-stat-ern">
            ${career.wage_p10!.toLocaleString()} – ${career.wage_p25!.toLocaleString()}
            <span className="font-body text-text-muted text-micro ml-1">
              {t("build.startingRange")}
            </span>
          </p>
        ) : hasOewsTypical ? (
          <p className="text-stat-ern">
            ${career.wage_p25!.toLocaleString()} – ${career.wage_p75!.toLocaleString()}
            <span className="font-body text-text-muted text-micro ml-1">
              {t("build.typicalRange")}
            </span>
          </p>
        ) : hasScRange ? (
          <p className="text-stat-ern">
            ${career.earnings_1yr_p25!.toLocaleString()} – ${career.earnings_1yr_p75!.toLocaleString()}
            <span className="text-text-muted text-micro ml-1">year one</span>
          </p>
        ) : career.earnings_1yr_median != null ? (
          <p className="text-stat-ern">
            ${career.earnings_1yr_median.toLocaleString()}
            <span className="text-text-muted text-micro ml-1">year one</span>
          </p>
        ) : null}
        {wage !== null && (
          <p className="text-text-secondary">
            ${wage.toLocaleString()}
            <span className="text-text-muted text-micro ml-1">mid-career</span>
          </p>
        )}
      </div>
    </motion.div>
  );
}
