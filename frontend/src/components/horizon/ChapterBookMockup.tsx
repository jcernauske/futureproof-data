/**
 * Chapter Book Mockup — Shape B
 *
 * USER JOB: "Your first job isn't your career." A 17-year-old who already
 * suspects "Microbiologist" is the pick wants a deep, top-to-bottom read on
 * what the next 15 years of that choice typically look like.
 *
 * FEELING: Contemplative. A book, not a map. Vertical cadence, gentle thread
 * running down the left gutter. Quiet authority — the voice of a career
 * librarian, not a hype man.
 *
 * HARDEST DECISIONS:
 *   1. COMMIT TO ONE CAREER — The moment the student taps a row, the other
 *      rows dim to 40% and drop behind; the picked row becomes the book's
 *      title page. That commitment is what makes "top-to-bottom" honest.
 *      A "back to all paths" link returns to scan-mode.
 *
 *   2. THE CEILING CHAPTER — Some careers genuinely cap out mid-career.
 *      Showing an empty fourth chapter would read as broken data. Instead,
 *      the last chapter becomes "This is the ceiling" with a calm one-liner
 *      ("most people stay here, grow the skill, or lateral"). The ceiling
 *      isn't punishing — it's information. No red, no alert; muted caution.
 *
 *   3. LOCKED CHAPTERS ARE INFORMATIONAL, NOT GATED — A chapter that
 *      requires a grad degree collapses by default with a lock glyph and a
 *      calm "opens with a graduate degree" sub-line. It expands on click —
 *      you can read what's inside without committing to the degree. The
 *      lock is about prerequisite visibility, not friction.
 */
import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { springs, staggerItem } from "@/styles/motion";
import { STAT_MAP, type StatKey } from "@/data/statExplanations";
import { socEmoji } from "@/data/socEmoji";

// ---------------------------------------------------------------------------
// Stubbed data
// ---------------------------------------------------------------------------

type ChapterKind = "anchor" | "role" | "ceiling";

interface MockChapter {
  number: number;
  years_label: string;
  kind: ChapterKind;
  title: string;
  soc: string;
  what_changes: string;
  unlock: string | null;
  deltas: Partial<Record<StatKey, number>>;
  stats_snapshot?: Partial<Record<StatKey, number>>;
}

interface MockCareerRow {
  soc: string;
  title: string;
  wage: number;
  stats: Record<StatKey, number>;
  chapters: MockChapter[];
}

const COMMON_CAREERS: MockCareerRow[] = [
  {
    soc: "19-4021",
    title: "Biological Technician",
    wage: 52140,
    stats: { ern: 2, roi: 3, res: 4, grw: 3, hmn: 3 },
    chapters: [
      {
        number: 1,
        years_label: "Years 0–3",
        kind: "anchor",
        title: "Biological Technician",
        soc: "19-4021",
        what_changes:
          "Lab-bench work — samples, assays, documentation. The career starts here for most biology grads.",
        unlock: null,
        deltas: {},
        stats_snapshot: { ern: 2, roi: 3, res: 4, grw: 3, hmn: 3 },
      },
      {
        number: 2,
        years_label: "Years 3–8",
        kind: "role",
        title: "Microbiologist",
        soc: "19-1022",
        what_changes:
          "You own experiments. Writing up findings and training new techs takes up more of the week than the bench does.",
        unlock: null,
        deltas: { ern: +1, grw: +1 },
      },
      {
        number: 3,
        years_label: "Years 8–15",
        kind: "role",
        title: "Medical Scientist",
        soc: "19-1042",
        what_changes:
          "Research lead. Grant writing shows up here. Most people at this step finished a graduate degree along the way.",
        unlock: "Master's degree · close relatedness",
        deltas: { ern: +2, res: +1 },
      },
      {
        number: 4,
        years_label: "Past 15",
        kind: "role",
        title: "Natural Sciences Manager",
        soc: "11-9121",
        what_changes:
          "Runs the lab. Budget, hiring, research direction. The work becomes more about people than pipettes.",
        unlock: null,
        deltas: { ern: +2, grw: +1, hmn: +1 },
      },
    ],
  },
  {
    soc: "19-1029",
    title: "Biologist",
    wage: 65000,
    stats: { ern: 3, roi: 3, res: 4, grw: 3, hmn: 3 },
    chapters: [
      {
        number: 1,
        years_label: "Years 0–3",
        kind: "anchor",
        title: "Biologist",
        soc: "19-1029",
        what_changes: "Field or lab generalist — the starting bench.",
        unlock: null,
        deltas: {},
        stats_snapshot: { ern: 3, roi: 3, res: 4, grw: 3, hmn: 3 },
      },
      {
        number: 2,
        years_label: "Years 3–8",
        kind: "role",
        title: "Zoologist / Wildlife Biologist",
        soc: "19-1023",
        what_changes:
          "Specialization kicks in. Publications and field studies start to define the next step.",
        unlock: null,
        deltas: { grw: +1, hmn: +1 },
      },
      {
        number: 3,
        years_label: "Years 8–15",
        kind: "role",
        title: "Epidemiologist",
        soc: "19-1041",
        what_changes:
          "Population-level analysis. Many people pivot through public health at this step.",
        unlock: "Master's degree · moderate relatedness",
        deltas: { ern: +2, res: +1 },
      },
      {
        number: 4,
        years_label: "Past 15",
        kind: "role",
        title: "Natural Sciences Manager",
        soc: "11-9121",
        what_changes:
          "Directs a team of scientists. Strategy and budget take the foreground.",
        unlock: null,
        deltas: { ern: +2, grw: +1 },
      },
    ],
  },
  {
    soc: "19-1099",
    title: "Laboratory Animal Caretaker",
    wage: 34740,
    stats: { ern: 1, roi: 2, res: 5, grw: 2, hmn: 4 },
    chapters: [
      {
        number: 1,
        years_label: "Years 0–3",
        kind: "anchor",
        title: "Laboratory Animal Caretaker",
        soc: "19-1099",
        what_changes:
          "Hands-on animal husbandry — feeding, housing, records for research subjects.",
        unlock: null,
        deltas: {},
        stats_snapshot: { ern: 1, roi: 2, res: 5, grw: 2, hmn: 4 },
      },
      {
        number: 2,
        years_label: "Years 3–8",
        kind: "role",
        title: "Animal Care Supervisor",
        soc: "19-1099",
        what_changes:
          "Manages a small team, runs scheduling, handles regulatory compliance paperwork.",
        unlock: null,
        deltas: { ern: +1, hmn: +1 },
      },
      {
        number: 3,
        years_label: "Years 8+",
        kind: "ceiling",
        title: "This is the ceiling",
        soc: "19-1099",
        what_changes:
          "Most people in this role stay here, grow the skill, or lateral into veterinary-tech work. It's not a bad place to land — it's just where the arc typically levels off.",
        unlock: null,
        deltas: {},
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Chapter card
// ---------------------------------------------------------------------------

const STAT_ORDER: StatKey[] = ["ern", "roi", "res", "grw", "hmn"];

function DeltaPill({ statKey, value }: { statKey: StatKey; value: number }) {
  const stat = STAT_MAP[statKey];
  const sign = value > 0 ? "+" : "";
  return (
    <span className="inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5">
      <span className={`font-data text-micro uppercase ${stat.textClass}`}>
        {statKey.toUpperCase()}
      </span>
      <span className="font-data text-data-sm text-text-primary">
        {sign}
        {value}
      </span>
    </span>
  );
}

function StatSnapshotRow({
  snapshot,
}: {
  snapshot: Partial<Record<StatKey, number>>;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {STAT_ORDER.map((key) => {
        const stat = STAT_MAP[key];
        return (
          <span
            key={key}
            className="inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5"
          >
            <span className={`font-data text-micro uppercase ${stat.textClass}`}>
              {key.toUpperCase()}
            </span>
            <span className="font-data text-micro text-text-secondary">
              {snapshot[key] ?? "—"}
            </span>
          </span>
        );
      })}
    </div>
  );
}

function ChapterCard({
  chapter,
  isLast,
  reducedMotion,
}: {
  chapter: MockChapter;
  isLast: boolean;
  reducedMotion: boolean;
}) {
  const locked = Boolean(chapter.unlock);
  const [open, setOpen] = useState<boolean>(!locked);
  const deltas = Object.entries(chapter.deltas) as Array<[StatKey, number]>;

  const ringClass = (() => {
    if (chapter.kind === "anchor") return "border-l-[3px] border-l-accent-thrive";
    if (chapter.kind === "ceiling") return "border-l-[3px] border-l-accent-caution/80";
    if (locked) return "border-l-[3px] border-l-accent-insight/70";
    return "border-l-[3px] border-l-border";
  })();

  return (
    <motion.article
      variants={staggerItem}
      className={[
        "relative bg-bp-mid border border-border-subtle rounded-xl p-5",
        "transition-colors duration-normal",
        ringClass,
      ].join(" ")}
    >
      {/* Thread dot sitting on the left edge, aligned with the chapter head */}
      <span
        aria-hidden="true"
        className={[
          "absolute -left-[7px] top-6 w-3 h-3 rounded-full ring-2 ring-bp-deep",
          chapter.kind === "anchor"
            ? "bg-accent-thrive shadow-glow-thrive"
            : chapter.kind === "ceiling"
              ? "bg-accent-caution/80"
              : locked
                ? "bg-accent-insight"
                : "bg-text-muted",
        ].join(" ")}
      />

      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info">
            Chapter {chapter.number} · {chapter.years_label}
          </p>
          <div className="flex items-baseline gap-2 flex-wrap mt-1">
            {chapter.kind !== "ceiling" && (
              <span aria-hidden="true" className="text-[22px] leading-none mr-1">
                {socEmoji(chapter.soc)}
              </span>
            )}
            <h3
              className={[
                "font-body font-bold text-body-lg",
                chapter.kind === "ceiling"
                  ? "text-accent-caution/90"
                  : "text-text-primary",
              ].join(" ")}
            >
              {chapter.title}
            </h3>
            {chapter.kind === "role" && (
              <span className="font-data text-micro text-text-muted">
                {chapter.soc}
              </span>
            )}
          </div>
        </div>

        {locked && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={open ? "Collapse chapter" : "Expand locked chapter"}
            className="inline-flex items-center gap-1.5 rounded-full bg-accent-insight/10 ring-1 ring-accent-insight/25 px-2.5 py-1 font-body text-micro text-accent-insight cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] hover:bg-accent-insight/20 transition-colors duration-normal"
          >
            <span aria-hidden="true" className="font-data">
              ◆
            </span>
            <span>{open ? "Hide" : "Read"}</span>
            <motion.span
              aria-hidden="true"
              animate={{ rotate: open ? 180 : 0 }}
              transition={springs.snappy}
              className="font-data text-[10px]"
            >
              ▾
            </motion.span>
          </button>
        )}
      </header>

      {locked && (
        <p className="mt-2 font-body text-small text-accent-insight/90">
          Opens with {chapter.unlock?.toLowerCase()}.
        </p>
      )}

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="chapter-body"
            initial={
              reducedMotion
                ? { height: "auto", opacity: 1 }
                : { height: 0, opacity: 0 }
            }
            animate={{ height: "auto", opacity: 1 }}
            exit={
              reducedMotion
                ? { height: 0, opacity: 0 }
                : { height: 0, opacity: 0 }
            }
            transition={reducedMotion ? { duration: 0 } : springs.smooth}
            className="overflow-hidden"
          >
            <div className="pt-3 flex flex-col gap-3">
              <p className="font-body text-body text-text-secondary leading-relaxed">
                {chapter.what_changes}
              </p>

              {chapter.stats_snapshot && (
                <div className="flex flex-col gap-1.5">
                  <p className="font-body text-micro uppercase tracking-[2px] text-text-muted">
                    Stats today
                  </p>
                  <StatSnapshotRow snapshot={chapter.stats_snapshot} />
                </div>
              )}

              {deltas.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <p className="font-body text-micro uppercase tracking-[2px] text-text-muted">
                    What shifts
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {deltas.map(([key, value]) => (
                      <DeltaPill key={key} statKey={key} value={value} />
                    ))}
                  </div>
                </div>
              )}

              {chapter.kind === "ceiling" && (
                <p className="font-body text-small italic text-text-muted">
                  Not every career keeps climbing. That's information, not a
                  verdict.
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* The closing bookmark — only on last chapter */}
      {isLast && (
        <div className="mt-4 pt-3 border-t border-border-subtle flex items-center gap-2 font-body text-small text-text-muted">
          <span aria-hidden="true" className="text-accent-thrive/70">
            ✦
          </span>
          <span>End of arc. This is what the data shows for most people.</span>
        </div>
      )}
    </motion.article>
  );
}

// ---------------------------------------------------------------------------
// Row card — the collapsed version that opens into the book
// ---------------------------------------------------------------------------

function RowCardCollapsed({
  career,
  dimmed,
  onOpen,
}: {
  career: MockCareerRow;
  dimmed: boolean;
  onOpen: () => void;
}) {
  return (
    <motion.button
      type="button"
      onClick={onOpen}
      animate={{ opacity: dimmed ? 0.35 : 1 }}
      transition={{ duration: 0.25 }}
      className={[
        "w-full text-left rounded-xl p-6 border bg-bp-mid border-border-subtle",
        "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)]",
        dimmed
          ? ""
          : "hover:bg-bp-surface hover:border-border hover:shadow-lg hover:-translate-y-0.5 transition-all duration-normal",
      ].join(" ")}
      disabled={dimmed}
      aria-label={`Read the arc for ${career.title}`}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="text-[32px] leading-none select-none flex-shrink-0"
        >
          {socEmoji(career.soc)}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="font-body font-bold text-body-lg text-text-primary">
            {career.title}
          </h3>
          <p className="font-data text-data text-stat-ern mt-1">
            ${career.wage.toLocaleString()}/yr median
          </p>
        </div>
        {!dimmed && (
          <span
            aria-hidden="true"
            className="font-body text-small italic text-text-muted whitespace-nowrap"
          >
            Read the arc →
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5 mt-3">
        {STAT_ORDER.map((key) => {
          const stat = STAT_MAP[key];
          return (
            <span
              key={key}
              className="inline-flex items-center gap-1 bg-bp-surface rounded-full px-2 py-0.5"
            >
              <span
                className={`font-data text-micro uppercase ${stat.textClass}`}
              >
                {key.toUpperCase()}
              </span>
              <span className="font-data text-micro text-text-secondary">
                {career.stats[key]}
              </span>
            </span>
          );
        })}
      </div>
    </motion.button>
  );
}

// ---------------------------------------------------------------------------
// Open book — title page + chapter stack
// ---------------------------------------------------------------------------

function OpenBook({
  career,
  onClose,
  reducedMotion,
}: {
  career: MockCareerRow;
  onClose: () => void;
  reducedMotion: boolean;
}) {
  const totalYears = "~15 years";
  return (
    <motion.div
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
      transition={reducedMotion ? { duration: 0 } : springs.smooth}
      className="relative rounded-xl border border-border bg-bp-mid/60 shadow-lg overflow-hidden"
    >
      {/* Title page */}
      <div className="px-6 pt-6 pb-4 flex items-start justify-between gap-3 border-b border-border-subtle">
        <div className="min-w-0">
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info">
            The arc ahead · {totalYears}
          </p>
          <div className="flex items-baseline gap-3 mt-1">
            <span aria-hidden="true" className="text-[28px] leading-none">
              {socEmoji(career.soc)}
            </span>
            <h2 className="font-display text-heading font-semibold text-text-primary">
              {career.title}
            </h2>
          </div>
          <p className="mt-2 font-body text-body text-text-secondary max-w-[52ch]">
            Your first job isn't your career. Here's what the data shows
            typically comes next, chapter by chapter.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 inline-flex items-center gap-1 font-body text-small text-text-muted hover:text-text-secondary transition-colors duration-normal cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] rounded px-2 py-1"
          aria-label="Close the arc view, return to the full career list"
        >
          <span aria-hidden="true">←</span>
          <span>Back to all paths</span>
        </button>
      </div>

      {/* Chapter stack — vertical thread on the left */}
      <div className="relative px-6 pt-6 pb-6">
        <span
          aria-hidden="true"
          className="absolute left-[28px] top-6 bottom-6 w-px bg-gradient-to-b from-accent-thrive/60 via-border to-border-subtle"
        />

        <motion.div
          className="flex flex-col gap-4 pl-6"
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: { staggerChildren: reducedMotion ? 0 : 0.08 },
            },
          }}
          initial="hidden"
          animate="visible"
        >
          {career.chapters.map((chapter, i) => (
            <ChapterCard
              key={chapter.number}
              chapter={chapter}
              isLast={i === career.chapters.length - 1}
              reducedMotion={reducedMotion}
            />
          ))}
        </motion.div>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main mockup
// ---------------------------------------------------------------------------

export function ChapterBookMockup() {
  const reducedMotion = useReducedMotion() ?? false;
  const [openSoc, setOpenSoc] = useState<string | null>(null);

  const openCareer = useMemo<MockCareerRow | null>(
    () => (openSoc ? COMMON_CAREERS.find((c) => c.soc === openSoc) ?? null : null),
    [openSoc],
  );

  return (
    <section aria-label="Chapter Book mockup" className="flex flex-col gap-4">
      {/* Echoes the live SetYourCourseScreen resolution header. */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-[6px] font-body text-small text-text-muted">
          <span aria-hidden="true" className="text-accent-insight">
            ✦
          </span>
          <span>Gemma matched</span>
          <span className="font-bold text-accent-insight">
            &ldquo;biology&rdquo;
          </span>
        </div>
        <div className="flex items-baseline gap-3 pl-[22px]">
          <span className="font-display text-subheading font-semibold text-accent-insight">
            Biology, General
          </span>
          <span className="font-body text-small text-text-secondary">
            · Iowa State University
          </span>
        </div>
      </div>

      <div>
        <div className="flex items-center gap-3 mb-2">
          <h2 className="font-display font-semibold text-heading text-text-primary">
            Where this commonly leads
          </h2>
          <span className="bg-bp-surface rounded-full px-2.5 py-0.5 font-data text-data-sm text-text-muted">
            ({COMMON_CAREERS.length} paths)
          </span>
        </div>
        <p className="font-body text-small text-text-secondary mb-4">
          {openCareer
            ? "Reading one arc. Close to return to the full list."
            : "Pick a path to read its arc, chapter by chapter."}
        </p>

        <div className="flex flex-col gap-3">
          <AnimatePresence mode="wait" initial={false}>
            {openCareer ? (
              <OpenBook
                key={`book-${openCareer.soc}`}
                career={openCareer}
                onClose={() => setOpenSoc(null)}
                reducedMotion={reducedMotion}
              />
            ) : null}
          </AnimatePresence>

          {COMMON_CAREERS.map((career) => {
            // When a book is open, the picked card is hidden (it becomes
            // the book's title page). Other cards dim to 35% and disable —
            // they're still there, but the focus is on the open arc.
            if (openCareer && openCareer.soc === career.soc) return null;
            return (
              <RowCardCollapsed
                key={career.soc}
                career={career}
                dimmed={Boolean(openCareer)}
                onOpen={() => setOpenSoc(career.soc)}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}
