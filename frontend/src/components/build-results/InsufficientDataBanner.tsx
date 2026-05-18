/**
 * InsufficientDataBanner — surfaces College Scorecard PrivacySuppression honestly.
 *
 * When a student picks a career whose program-level earnings + debt are
 * suppressed by the Department of Education (small cohort, <30 federal-
 * loan-recipient completers), the Pentagon renders ERN and ROI as "—".
 * Without context that reads as a glitch. This banner makes the absence
 * meaningful: the suppression is signal, not a bug, and the rest of the
 * build still reflects real outcomes.
 *
 * Sibling to GradCredentialNotice — same Brightpath surface, same left-
 * stripe accent (caution amber), same fade-in idiom. See spec
 * docs/specs/bugfix-post-100-build-test-fixes-bundle.md §3 Bundle 2.
 */

import { motion, useReducedMotion } from "framer-motion";

import { useT } from "@/i18n/useT";
import { springs } from "@/styles/motion";

interface InsufficientDataBannerProps {
  /** Program name (e.g. "Architecture"). Mentioned in the body because
      suppression is per-program — the same school may publish earnings
      for plenty of other majors. */
  programTitle: string;
  /** School display name (e.g. "Howard University"). */
  schoolName: string;
}

export function InsufficientDataBanner({
  programTitle,
  schoolName,
}: InsufficientDataBannerProps) {
  const t = useT();
  const reducedMotion = useReducedMotion();

  return (
    <motion.section
      key="insufficient-data-banner"
      initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springs.smooth}
      aria-labelledby="insufficient-data-banner-title"
      data-testid="insufficient-data-banner"
      className={[
        "relative rounded-xl",
        "bg-bp-mid/60 border border-border-subtle",
        "border-l-[3px] border-l-accent-caution",
        "p-4 tablet:p-5",
        "shadow-md",
      ].join(" ")}
    >
      {/* Row 1: icon + title share a baseline */}
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="shrink-0 mt-0.5 w-5 h-5 inline-flex items-center justify-center text-accent-caution opacity-90"
        >
          {/* ⓘ glyph as inline SVG for consistent sizing across platforms */}
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle
              cx="10"
              cy="10"
              r="8.5"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <circle cx="10" cy="6.5" r="0.9" fill="currentColor" />
            <path
              d="M10 9.5 L10 14"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </span>
        <h3
          id="insufficient-data-banner-title"
          data-testid="insufficient-data-banner-title"
          className="font-display text-body-lg font-semibold text-text-primary leading-tight"
        >
          {t("build.insufficientData.title")}
        </h3>
      </div>
      {/* Row 2: body — indented to align with the title under the icon */}
      <p className="mt-3 pl-8 font-body text-body text-text-secondary leading-relaxed">
        {t("build.insufficientData.body", {
          programTitle,
          schoolName,
        })}
      </p>
    </motion.section>
  );
}
