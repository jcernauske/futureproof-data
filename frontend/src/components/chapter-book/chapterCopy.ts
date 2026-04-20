/**
 * Chapter Book — single source of truth for voice strings.
 *
 * Spec: docs/specs/feature-chapter-book.md §3.5. Voice: cool, confident,
 * data-honest. No exclamation points. No hype verbs. "Your first job isn't
 * your career" is the North Star.
 *
 * Year labels match Silver canonical tiers per Decision #14 — wording is
 * owned here and by @fp-copywriter, ranges are locked to the data.
 */
export const chapterCopy = {
  titlePage: {
    eyebrow: "The arc ahead",
    subtitle:
      "Your first job isn't your career. Here's what the data shows typically comes next, chapter by chapter.",
  },
  years: {
    entry: "Starting out · 0–1 yr",
    early: "Years 1–4",
    mid: "Years 4–8",
    senior: "8+ yrs",
  },
  anchor: {
    what_changes:
      "This is the role most graduates land in first. The bench, the ticket, the desk — where the work actually starts.",
  },
  locked: {
    sublabel: "Opens with a graduate degree.",
  },
  ceiling: {
    title: "The arc levels off here.",
    what_changes:
      "Most people at this step stay here, grow the skill, or lateral into adjacent roles. It's not a bad place to land — it's just where the typical arc levels off.",
    closingNote: "Not every career keeps climbing. That's information, not a verdict.",
  },
  bookmark: "End of arc. This is what the data shows for most people.",
  back: {
    label: "← Back to all paths",
    ariaLabel: "Back to all paths",
  },
} as const;
