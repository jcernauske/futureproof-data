/**
 * GradCredentialNotice — Brightpath notice tile for graduate-credential careers.
 *
 * Renders ABOVE the career preview in the Set Your Course resolution surface.
 * Two visual variants driven by `tone`:
 *   - "caution" (chip path): accent-caution left stripe — "your understanding
 *     of how to reach this career was incomplete"
 *   - "info" (pre-flag path): accent-info left stripe — softer; the student
 *     already signaled grad-school awareness by typing "pre-X"
 *
 * Contains:
 *   - Header: full credential name + parenthetical acronym
 *   - Subhead: 1 sentence naming the career and BLS as the source
 *   - Body: 1 sentence reframing (feeder introduction)
 *   - Feeder-major cards: 3–5 compact tappable cards
 *   - Footer: guidance on how to proceed
 *
 * @see docs/specs/feature-requires-graduate-credential.md §3
 */

import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FeederMajorData {
  cip4: string;
  cip_title: string;
  note: string;
  offered_at_school: boolean;
}

export interface GradCredentialNoticeProps {
  /** Full credential name, e.g. "Doctor of Physical Therapy" */
  credentialNameFull: string;
  /** Credential acronym, e.g. "DPT" */
  credentialAcronym: string;
  /** The career title the student named, e.g. "Physical Therapist" */
  targetCareerTitle: string;
  /** School name for the body copy */
  schoolName: string;
  /** 3–5 feeder-major cards */
  feeders: FeederMajorData[];
  /** Visual tone — drives accent color and lead copy variant */
  tone: "caution" | "info";
  /**
   * Pre-flag lead copy override. When tone="info", this replaces the
   * default subhead with the pre-flag prose (e.g. "Pre-PT isn't an
   * undergrad major itself — it's a track toward DPT school...").
   * When undefined, uses the standard BLS-citation subhead.
   */
  preFlagProse?: string;
  /** Called when a feeder card is tapped. Receives the CIP4 code. */
  onAcceptFeeder: (cip4: string) => void;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface FeederCardProps {
  feeder: FeederMajorData;
  tone: "caution" | "info";
  index: number;
  onTap: () => void;
}

function FeederCard({ feeder, tone, index, onTap }: FeederCardProps) {
  const reducedMotion = useReducedMotion();
  const ctaColor =
    tone === "caution" ? "text-accent-thrive" : "text-accent-info";
  const ctaMutedColor = "text-text-muted";

  return (
    <motion.button
      type="button"
      onClick={onTap}
      initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        ...springs.smooth,
        delay: index * stagger.normal,
      }}
      whileTap={{ scale: 0.97 }}
      className={[
        "group relative flex flex-col text-left",
        "min-w-[160px] w-[200px] tablet:w-auto tablet:min-w-[160px] tablet:flex-1",
        "shrink-0 snap-start",
        "bg-bp-mid border border-border-subtle rounded-xl p-4",
        "hover:bg-bp-surface hover:border-border",
        "hover:shadow-md hover:-translate-y-0.5",
        "transition-all duration-normal",
        "cursor-pointer",
        "focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[color:var(--color-focus-ring)] focus-visible:ring-offset-2",
      ].join(" ")}
      data-testid={`feeder-card-${feeder.cip4}`}
    >
      {/* "Not offered here" pill */}
      {!feeder.offered_at_school && (
        <span
          className="absolute top-2 right-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-state-error font-body text-micro font-semibold text-accent-alert"
          data-testid="feeder-not-offered-pill"
        >
          <span aria-hidden="true">&#9671;</span>
          not offered here
        </span>
      )}

      {/* Title */}
      <span className="font-display text-body font-semibold text-text-primary leading-snug pr-6">
        {feeder.cip_title}
      </span>

      {/* Note */}
      <span className="mt-2 font-body text-small text-text-secondary leading-relaxed line-clamp-2 flex-1">
        {feeder.note}
      </span>

      {/* Divider + CTA */}
      <span className="mt-3 pt-3 border-t border-border-subtle flex items-center gap-1">
        <span
          className={[
            "font-body text-small font-semibold",
            feeder.offered_at_school ? ctaColor : ctaMutedColor,
            "group-hover:underline",
          ].join(" ")}
        >
          Switch to this major
        </span>
        <span
          className={[
            "text-small",
            feeder.offered_at_school ? ctaColor : ctaMutedColor,
            "transition-transform duration-fast group-hover:translate-x-0.5",
          ].join(" ")}
          aria-hidden="true"
        >
          &rarr;
        </span>
      </span>
    </motion.button>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function GradCredentialNotice({
  credentialNameFull,
  credentialAcronym,
  targetCareerTitle,
  schoolName,
  feeders,
  tone,
  preFlagProse,
  onAcceptFeeder,
}: GradCredentialNoticeProps) {
  const reducedMotion = useReducedMotion();

  // Accent stripe color
  const stripeClass =
    tone === "caution" ? "border-l-accent-caution" : "border-l-accent-info";

  // Subhead copy
  const subhead =
    preFlagProse ??
    `According to the Bureau of Labor Statistics (BLS), becoming a ${targetCareerTitle} requires a ${credentialAcronym} — graduate school.`;

  // Body copy
  const body = `Here are common undergrad majors students at ${schoolName} take to prepare for ${credentialAcronym} school.`;

  return (
    <AnimatePresence mode="wait">
      <motion.section
        key="grad-credential-notice"
        initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -12 }}
        transition={springs.smooth}
        aria-label={`Graduate credential notice: ${credentialNameFull}`}
        className={[
          "relative rounded-xl",
          "bg-bp-mid/60 border border-border-subtle",
          "border-l-[3px]",
          stripeClass,
          "p-4 tablet:p-5",
          "shadow-md",
        ].join(" ")}
        data-testid="grad-credential-notice"
      >
        {/* Header — credential name */}
        <h3 className="font-display text-heading font-semibold text-text-primary leading-tight">
          {credentialNameFull} ({credentialAcronym})
        </h3>

        {/* Subhead — BLS citation or pre-flag prose */}
        <p className="mt-3 font-body text-body text-text-secondary leading-normal">
          {subhead}
        </p>

        {/* Body — reframe */}
        <p className="mt-2 font-body text-body text-text-primary leading-normal">
          {body}
        </p>

        {/* Feeder cards row */}
        <div
          className={[
            "mt-4",
            // Mobile: horizontal scroll with snap
            "flex gap-3 overflow-x-auto snap-x snap-mandatory",
            "pb-2", // breathing room for scroll thumb
            // Tablet+: flex-wrap so cards flow naturally
            "tablet:flex-wrap tablet:overflow-x-visible tablet:snap-none tablet:pb-0",
          ].join(" ")}
          data-testid="feeder-cards-row"
        >
          {feeders.map((feeder, i) => (
            <FeederCard
              key={feeder.cip4}
              feeder={feeder}
              tone={tone}
              index={i}
              onTap={() => onAcceptFeeder(feeder.cip4)}
            />
          ))}
        </div>

        {/* Footer guidance */}
        <p className="mt-4 font-body text-small text-text-muted leading-relaxed">
          Tap a major to switch your build. Your career preview below still
          shows the {targetCareerTitle} path.
        </p>
      </motion.section>
    </AnimatePresence>
  );
}
