import { useId, useMemo } from "react";
import { useT } from "@/i18n/useT";
import {
  EXPERIENCE_TIERS,
  type ExperienceRange,
} from "@/data/experienceFilter";

/**
 * Discrete range slider for the /future tree's experience-tier
 * filter. Two overlaid `<input type="range">` elements share the
 * same domain [0, 3] and snap to tier indices: entry / early / mid
 * / senior. Active range is highlighted between the two thumbs.
 *
 * Replaces the per-edge "Mid+" / "Senior+" experience pills (T1.1
 * step 2) — the slider is the single locus for "what tier of jobs
 * do I want to see."
 */

interface ExperienceRangeSliderProps {
  range: ExperienceRange;
  onChange: (range: ExperienceRange) => void;
}

const TIER_LABEL_KEY: Record<(typeof EXPERIENCE_TIERS)[number], string> = {
  entry: "future.edge.tier.entry",
  early: "future.edge.tier.early",
  mid: "future.edge.tier.mid",
  senior: "future.edge.tier.senior",
};

const MIN_IDX = 0;
const MAX_IDX = EXPERIENCE_TIERS.length - 1;

export function ExperienceRangeSlider({
  range,
  onChange,
}: ExperienceRangeSliderProps) {
  const t = useT();
  const id = useId();
  const [minIdx, maxIdx] = range;

  const tierLabels = useMemo(
    () => EXPERIENCE_TIERS.map((tier) => t(TIER_LABEL_KEY[tier])),
    [t],
  );

  const minLabel = tierLabels[minIdx]!;
  const maxLabel = tierLabels[maxIdx]!;
  const summary =
    minIdx === maxIdx ? minLabel : `${minLabel} → ${maxLabel}`;

  const handleMin = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Math.min(Number(e.target.value), maxIdx);
    if (v !== minIdx) onChange([v, maxIdx]);
  };
  const handleMax = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Math.max(Number(e.target.value), minIdx);
    if (v !== maxIdx) onChange([minIdx, v]);
  };

  // Active-range highlight: percent positions of the two thumbs along
  // the track, used to size the colored fill between them.
  const span = MAX_IDX - MIN_IDX;
  const minPct = ((minIdx - MIN_IDX) / span) * 100;
  const maxPct = ((maxIdx - MIN_IDX) / span) * 100;

  return (
    <div
      role="group"
      aria-label={t("future.experience.aria")}
      data-testid="experience-range-slider"
      className="flex flex-row flex-wrap items-center gap-x-3 gap-y-2"
    >
      <span className="font-data text-[10px] uppercase tracking-wider text-text-muted">
        {t("future.experience.label")}
      </span>
      <div
        className="relative flex-1 min-w-[200px] max-w-[320px] h-6 select-none"
        data-testid="experience-slider-track-container"
      >
        {/* Track background — slightly thicker than before so the
            active fill above it has more presence. */}
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 rounded-full bg-bp-deep border border-border-subtle" />
        {/* Active range fill — accent-thrive at full opacity for max
            contrast against the dark deep track. */}
        <div
          className="absolute top-1/2 -translate-y-1/2 h-2 rounded-full bg-accent-thrive shadow-[0_0_8px_rgba(125,212,163,0.45)]"
          style={{ left: `${minPct}%`, right: `${100 - maxPct}%` }}
          data-testid="experience-slider-fill"
        />
        {/* Tick marks at each tier position — purely decorative */}
        {EXPERIENCE_TIERS.map((tier, i) => (
          <span
            key={tier}
            aria-hidden="true"
            className="absolute top-1/2 -translate-y-1/2 w-1 h-1 rounded-full bg-text-muted/60 z-[1]"
            style={{
              left: `calc(${(i / span) * 100}% - 2px)`,
            }}
          />
        ))}
        {/* Min thumb (lower-z so the max thumb sits on top when they overlap) */}
        <input
          id={`${id}-min`}
          type="range"
          min={MIN_IDX}
          max={MAX_IDX}
          step={1}
          value={minIdx}
          onChange={handleMin}
          aria-label={t("future.experience.minAria")}
          aria-valuetext={minLabel}
          className="experience-slider-input experience-slider-input--min"
        />
        {/* Max thumb */}
        <input
          id={`${id}-max`}
          type="range"
          min={MIN_IDX}
          max={MAX_IDX}
          step={1}
          value={maxIdx}
          onChange={handleMax}
          aria-label={t("future.experience.maxAria")}
          aria-valuetext={maxLabel}
          className="experience-slider-input experience-slider-input--max"
        />
      </div>
      <span
        className="font-body text-small font-semibold text-text-secondary tabular-nums whitespace-nowrap"
        data-testid="experience-slider-summary"
      >
        {summary}
      </span>
    </div>
  );
}
