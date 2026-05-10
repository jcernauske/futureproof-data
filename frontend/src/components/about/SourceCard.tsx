import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { useT } from "@/i18n/useT";

/**
 * SourceCard — the workhorse of the About page. Renders one data source
 * (or the Gemma 4 model layer, via variant="model") with publisher
 * attribution, vintage, what-it-powers blurb, optional caveat, and the
 * official source URL.
 */

export type SourceCardVariant =
  /** U.S. Government dataset — info pill, info-tinted gov badge. */
  | "gov"
  /** Academic / open-source — empathy-tinted badge. */
  | "acad"
  /** Private-sector dataset — insight-tinted badge. */
  | "priv"
  /** Gemma 4 — visually distinct: insight border + glow + model pill. */
  | "model";

export interface SourceCardProps {
  titleKey: string;
  publisherKey: string;
  /** Pre-formatted, locale-stable vintage string. e.g. "May 2024". */
  vintage: string;
  blurbKey: string;
  caveatKey?: string;
  displayUrl: string;
  href: string;
  variant?: SourceCardVariant;
  testId?: string;
}

const VARIANT_PILL: Record<SourceCardVariant, string> = {
  gov: "bg-accent-info/15 text-accent-info",
  acad: "bg-accent-empathy/15 text-accent-empathy",
  priv: "bg-accent-insight/15 text-accent-insight",
  model: "bg-accent-insight/15 text-accent-insight",
};

const VARIANT_PILL_GLYPH: Record<SourceCardVariant, string> = {
  gov: "◆",
  acad: "◆",
  priv: "◆",
  model: "◇",
};

const VARIANT_BADGE_STYLE: Record<SourceCardVariant, string> = {
  gov: "bg-gradient-to-br from-accent-info/20 to-accent-info/5 text-accent-info border-accent-info/30",
  acad: "bg-gradient-to-br from-accent-empathy/20 to-accent-empathy/5 text-accent-empathy border-accent-empathy/30",
  priv: "bg-gradient-to-br from-accent-insight/20 to-accent-insight/5 text-accent-insight border-accent-insight/30",
  model: "bg-gradient-to-br from-accent-insight/30 to-accent-info/15 text-text-primary border-accent-insight/40 shadow-glow-insight",
};

const VARIANT_BADGE_GLYPH: Record<SourceCardVariant, string> = {
  gov: "★",
  acad: "⌬",
  priv: "◈",
  model: "✦",
};

const VARIANT_BADGE_ARIA_KEY: Record<SourceCardVariant, string> = {
  gov: "about.badge.govAria",
  acad: "about.badge.acadAria",
  priv: "about.badge.privAria",
  model: "about.badge.modelAria",
};

function AttributionBadge({ variant }: { variant: SourceCardVariant }) {
  const t = useT();
  return (
    <div
      role="img"
      aria-label={t(VARIANT_BADGE_ARIA_KEY[variant])}
      className={`shrink-0 w-11 h-11 rounded-md flex items-center justify-center font-display text-[18px] font-bold border ${VARIANT_BADGE_STYLE[variant]}`}
    >
      {VARIANT_BADGE_GLYPH[variant]}
    </div>
  );
}

export function SourceCard({
  titleKey,
  publisherKey,
  vintage,
  blurbKey,
  caveatKey,
  displayUrl,
  href,
  variant = "gov",
  testId = "source-card",
}: SourceCardProps) {
  const t = useT();
  const isModel = variant === "model";

  return (
    <motion.a
      data-testid={testId}
      data-variant={variant}
      data-has-caveat={caveatKey ? "true" : "false"}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      whileHover={{ y: -2 }}
      transition={springs.snappy}
      className={[
        "group relative flex flex-col gap-3 p-6 rounded-xl bg-bp-mid shadow-md",
        "border transition-colors duration-normal",
        "hover:bg-bp-surface hover:shadow-lg",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-info focus-visible:ring-offset-2 focus-visible:ring-offset-bp-deep",
        isModel
          ? "border-accent-insight/30 shadow-glow-insight hover:border-accent-insight/50"
          : "border-border-subtle hover:border-border",
      ].join(" ")}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span
          className={`inline-flex items-center gap-1.5 font-body text-micro font-semibold px-3 py-1 rounded-full ${VARIANT_PILL[variant]}`}
        >
          <span aria-hidden="true">{VARIANT_PILL_GLYPH[variant]}</span>
          {t(isModel ? "about.card.modelPill" : "about.card.dataSourcePill")}
        </span>
        <span className="font-data text-micro text-text-muted tracking-wide">
          {vintage}
        </span>
      </div>

      <div className="flex items-start gap-3.5">
        <AttributionBadge variant={variant} />
        <div className="min-w-0 flex-1">
          <p className="font-body text-micro font-semibold uppercase tracking-[1px] text-text-muted mb-1">
            {t(publisherKey)}
          </p>
          <h3 className="font-display text-[20px] leading-snug font-semibold text-text-primary">
            {t(titleKey)}
          </h3>
        </div>
      </div>

      <p className="font-body text-small text-text-secondary leading-relaxed">
        {t(blurbKey)}
      </p>

      {caveatKey && (
        <div
          role="note"
          className="flex items-start gap-2 px-3 py-2.5 rounded-md bg-accent-caution/[0.08] border border-accent-caution/15 font-body text-small text-text-secondary leading-snug"
        >
          <span aria-hidden="true" className="font-display font-bold text-accent-caution shrink-0 leading-relaxed">△</span>
          <span>{t(caveatKey)}</span>
        </div>
      )}

      <div className="mt-auto pt-2 flex items-center justify-between gap-3">
        <span className="font-data text-data-sm text-accent-info border-b border-accent-info/25 pb-px transition-colors duration-fast group-hover:text-text-primary truncate">
          {displayUrl}
          <span aria-hidden="true" className="opacity-60"> ↗</span>
        </span>
      </div>
    </motion.a>
  );
}
