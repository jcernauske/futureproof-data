/**
 * Chapter Book — single chapter card.
 *
 * Spec: docs/specs/feature-chapter-book.md §3.3. Handles four variants:
 *   - anchor  (chapter 1, the parent career, shows STATS TODAY snapshot)
 *   - role    (standard mid-arc chapter)
 *   - locked  (grad-degree-gated, collapsed by default, expand to read)
 *   - ceiling (synthetic, "arc levels off here", muted caution color)
 */
import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { springs, staggerItem } from "@/styles/motion";
import { STAT_MAP, type StatKey } from "@/data/statExplanations";
import { socEmoji } from "@/data/socEmoji";
import type { Chapter } from "./types";
import { chapterCopy } from "./chapterCopy";

const STAT_ORDER: readonly StatKey[] = ["ern", "roi", "res", "grw", "hmn"];

interface ChapterCardProps {
  chapter: Chapter;
  /** True when this card is the last in the rendered book — adds the
   * bookmark closing line.  */
  isLast: boolean;
}

function DeltaPill({ statKey, value }: { statKey: StatKey; value: number }) {
  const textClass = STAT_MAP[statKey].textClass;
  const sign = value > 0 ? "+" : "";
  return (
    <span
      className="inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5"
      data-testid={`delta-pill-${statKey}`}
    >
      <span
        className={`font-data text-micro uppercase ${textClass}`}
        aria-hidden="true"
      >
        {STAT_MAP[statKey].abbreviation}
      </span>
      <span className="font-data text-data-sm text-text-primary tabular-nums">
        {sign}
        {value}
      </span>
      <span className="sr-only">
        {STAT_MAP[statKey].name} {sign}
        {value}
      </span>
    </span>
  );
}

function SnapshotPill({ statKey, value }: { statKey: StatKey; value: number | undefined }) {
  const textClass = STAT_MAP[statKey].textClass;
  return (
    <span
      className="inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5"
      data-testid={`snapshot-pill-${statKey}`}
    >
      <span
        className={`font-data text-micro uppercase ${textClass}`}
        aria-hidden="true"
      >
        {STAT_MAP[statKey].abbreviation}
      </span>
      <span className="font-data text-micro text-text-secondary tabular-nums">
        {value ?? "—"}
      </span>
    </span>
  );
}

function dotClassForKind(kind: Chapter["kind"]): string {
  switch (kind) {
    case "anchor":
      return "bg-accent-thrive shadow-glow-thrive";
    case "locked":
      return "bg-accent-insight";
    case "ceiling":
      return "bg-accent-caution/80";
    case "role":
    default:
      return "bg-text-muted";
  }
}

function leftBorderClassForKind(kind: Chapter["kind"]): string {
  switch (kind) {
    case "anchor":
      return "border-l-[3px] border-l-accent-thrive";
    case "locked":
      return "border-l-[3px] border-l-accent-insight/70";
    case "ceiling":
      return "border-l-[3px] border-l-accent-caution/80";
    case "role":
    default:
      return "border-l-[3px] border-l-border";
  }
}

export function ChapterCard({ chapter, isLast }: ChapterCardProps) {
  const reducedMotion = useReducedMotion();
  // Locked chapters open/close locally. Anchor/role/ceiling are always
  // open. Initial state: locked → collapsed.
  const [expanded, setExpanded] = useState(chapter.kind !== "locked");

  const deltaEntries = STAT_ORDER.filter(
    (key) => chapter.deltas[key] !== undefined,
  ).map((key) => [key, chapter.deltas[key] as number] as const);

  const showDeltaRow = chapter.kind === "role" || chapter.kind === "locked";
  const showSnapshotRow = chapter.kind === "anchor" && chapter.stats_snapshot !== undefined;

  return (
    <motion.article
      variants={staggerItem}
      className={`relative bg-bp-mid border border-border-subtle rounded-xl p-5 transition-colors duration-normal ${leftBorderClassForKind(chapter.kind)}`}
      data-testid={`chapter-${chapter.number}-${chapter.soc ?? "ceiling"}`}
      data-chapter-kind={chapter.kind}
      aria-labelledby={`chapter-${chapter.number}-title`}
    >
      {/* Thread dot — absolute positioned onto the parent stack's thread line */}
      <span
        aria-hidden="true"
        className={`absolute -left-[7px] top-6 w-3 h-3 rounded-full ring-2 ring-bp-deep ${dotClassForKind(chapter.kind)}`}
      />

      {/* Eyebrow: CHAPTER N · YEARS LABEL */}
      <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info">
        Chapter {chapter.number} · {chapter.years_label}
      </p>

      {/* Title row */}
      {chapter.kind === "ceiling" ? (
        <h3
          id={`chapter-${chapter.number}-title`}
          data-testid={`chapter-${chapter.number}-title`}
          className="mt-1 font-body font-bold text-body-lg text-accent-caution/90"
        >
          {chapter.title}
        </h3>
      ) : (
        <div className="mt-1 flex items-baseline justify-between gap-3 flex-wrap">
          <div className="flex items-baseline gap-2 flex-wrap">
            {chapter.soc ? (
              <span
                className="text-[22px] leading-none mr-1"
                aria-hidden="true"
              >
                {socEmoji(chapter.soc)}
              </span>
            ) : null}
            <h3
              id={`chapter-${chapter.number}-title`}
              data-testid={`chapter-${chapter.number}-title`}
              className="font-body font-bold text-body-lg text-text-primary"
            >
              {chapter.title}
            </h3>
            {chapter.soc ? (
              <span
                className="font-data text-micro text-text-muted tabular-nums"
                aria-label="Standard Occupational Classification code"
              >
                {chapter.soc}
              </span>
            ) : null}
          </div>

          {chapter.kind === "locked" ? (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              aria-expanded={expanded}
              aria-controls={`chapter-${chapter.number}-body`}
              aria-label={
                expanded
                  ? `Hide chapter ${chapter.number}`
                  : `Read chapter ${chapter.number}: opens with a graduate degree`
              }
              data-testid={`chapter-lock-${chapter.number}`}
              className="inline-flex items-center gap-1.5 rounded-full bg-accent-insight/10 ring-1 ring-accent-insight/25 px-2.5 py-1 font-body text-micro text-accent-insight cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] hover:bg-accent-insight/20 transition-colors duration-normal"
            >
              <span className="font-data" aria-hidden="true">
                ◆
              </span>
              <span>{expanded ? "Hide" : "Read"}</span>
              <motion.span
                aria-hidden="true"
                animate={{ rotate: expanded ? 180 : 0 }}
                transition={reducedMotion ? { duration: 0 } : springs.snappy}
                className="inline-block"
              >
                ▾
              </motion.span>
            </button>
          ) : null}
        </div>
      )}

      {/* Locked sub-line (visible when collapsed) */}
      {chapter.kind === "locked" && !expanded ? (
        <p className="mt-2 font-body text-small text-accent-insight/90">
          {chapterCopy.locked.sublabel}
        </p>
      ) : null}

      {/* Body — always open for anchor/role/ceiling; expandable for locked */}
      <AnimatePresence initial={false}>
        {(chapter.kind !== "locked" || expanded) && (
          <motion.div
            key={`chapter-${chapter.number}-body`}
            id={`chapter-${chapter.number}-body`}
            initial={
              chapter.kind === "locked" && !reducedMotion
                ? { height: 0, opacity: 0 }
                : false
            }
            animate={{ height: "auto", opacity: 1 }}
            exit={
              reducedMotion
                ? { opacity: 0 }
                : { height: 0, opacity: 0 }
            }
            transition={reducedMotion ? { duration: 0 } : springs.smooth}
            className="overflow-hidden"
          >
            {chapter.what_changes ? (
              <p className="mt-3 font-body text-body text-text-secondary leading-relaxed max-w-[58ch]">
                {chapter.what_changes}
              </p>
            ) : null}

            {showSnapshotRow ? (
              <div className="mt-4">
                <p className="font-body text-micro uppercase tracking-[2px] text-text-muted">
                  Stats today
                </p>
                <div
                  className="mt-2 flex flex-wrap gap-1.5"
                  data-testid="stats-snapshot"
                >
                  {STAT_ORDER.map((key) => (
                    <SnapshotPill
                      key={key}
                      statKey={key}
                      value={chapter.stats_snapshot?.[key]}
                    />
                  ))}
                </div>
              </div>
            ) : null}

            {showDeltaRow && deltaEntries.length > 0 ? (
              <div className="mt-4">
                <p className="font-body text-micro uppercase tracking-[2px] text-text-muted">
                  What shifts
                </p>
                <div
                  className="mt-2 flex flex-wrap gap-1.5"
                  data-testid="delta-row"
                >
                  {deltaEntries.map(([key, value]) => (
                    <DeltaPill key={key} statKey={key} value={value} />
                  ))}
                </div>
              </div>
            ) : null}

            {chapter.kind === "ceiling" ? (
              <p className="mt-3 font-body text-small italic text-text-muted">
                {chapterCopy.ceiling.closingNote}
              </p>
            ) : null}

            {isLast ? (
              <div className="mt-4 pt-3 border-t border-border-subtle flex items-center gap-2 font-body text-small text-text-muted">
                <span
                  aria-hidden="true"
                  className="text-accent-thrive/70"
                >
                  ✦
                </span>
                <span>{chapterCopy.bookmark}</span>
              </div>
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}
