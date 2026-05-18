/**
 * InsufficientDataBanner — surfaces missing program-level earnings honestly.
 *
 * When ERN and ROI both come back null, the cause is genuinely ambiguous
 * (we can't tell from the data alone). The copy walks the student through
 * the two real possibilities — small federal-loan cohort at a selective
 * school OR a thinly enrolled program at this school — and tells them
 * the question is in their downloadable report.
 *
 * When the BLS occupation-level wage is populated (the common case), we
 * anchor the student to that concrete number so the pentagon's blank
 * slices don't read as a missing answer.
 */

import { motion, useReducedMotion } from "framer-motion";

import { useT } from "@/i18n/useT";
import { springs } from "@/styles/motion";

interface InsufficientDataBannerProps {
  programTitle: string;
  schoolName: string;
  careerTitle: string;
  blsWage: number | null;
}

function formatWage(wage: number): string {
  return `$${Math.round(wage).toLocaleString("en-US")}`;
}

export function InsufficientDataBanner({
  programTitle,
  schoolName,
  careerTitle,
  blsWage,
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
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="shrink-0 mt-0.5 w-5 h-5 inline-flex items-center justify-center text-accent-caution opacity-90"
        >
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

      <div className="mt-3 pl-8 font-body text-body text-text-secondary leading-relaxed space-y-2">
        <p>
          {t("build.insufficientData.lede", { programTitle, schoolName })}
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>{t("build.insufficientData.interpretationSelectivity")}</li>
          <li>{t("build.insufficientData.interpretationThinProgram")}</li>
        </ul>
        <p>
          {t("build.insufficientData.outroAskReport", { careerTitle })}
          {blsWage !== null && (
            <>
              {" "}
              {t("build.insufficientData.blsAnchor", {
                careerTitle,
                blsWage: formatWage(blsWage),
              })}
            </>
          )}
        </p>
      </div>
    </motion.section>
  );
}
