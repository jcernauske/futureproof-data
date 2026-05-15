/**
 * Horizon Strip Mockup — Shape A
 *
 * USER JOB: "Your first job isn't your career." A 17-year-old sees
 * "Biological Technician, $52K" and needs evidence that's not the ceiling.
 *
 * FEELING: Relief, not swagger. Scan-able. One glance should reveal that the
 * arc keeps going without turning into a pitch.
 *
 * HARDEST DECISIONS:
 *   1. STACK LEGIBILITY — A dozen common rows x ~160px strips = a scrolling
 *      brick. Solved by accordion: at most ONE row is open at a time. The
 *      ROW IS the strip (not a popover, not a new card). Opening a second
 *      row closes the first. The common-list rhythm stays intact.
 *
 *   2. THE GRAD-DEGREE GATE COLOR — Using thrive green would read as
 *      "reward / win", which implies you must get the grad degree to
 *      succeed. That's the opposite of the message. So the gate uses
 *      insight purple (the study/knowledge color), and the caption reads
 *      "opens with a graduate degree" — a door, not a trophy.
 *
 *   3. DOTS FIRST, TITLES ON TAP — Showing four full role titles at once
 *      turns the strip into a cluttered scan. Instead: empty rail with
 *      four dots + tier labels (Today / Early / Mid / Senior + year ranges),
 *      and the role/one-liner/delta row only materializes below on tap.
 *      Keeps the strip's silhouette calm until the student leans in.
 */
import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";
import { STAT_MAP, type StatKey } from "@/data/statExplanations";
import { socEmoji } from "@/data/socEmoji";

// ---------------------------------------------------------------------------
// Stubbed data
// ---------------------------------------------------------------------------

type ExperienceTier = "entry" | "early" | "mid" | "senior";

interface MockNode {
  tier: ExperienceTier;
  tier_label: string;
  years_label: string;
  title: string;
  soc: string;
  one_liner: string;
  unlock: string | null;
  deltas: Partial<Record<StatKey, number>>;
}

interface MockCareerRow {
  soc: string;
  title: string;
  wage: number;
  stats: Record<StatKey, number>;
  horizon: MockNode[];
}

const COMMON_CAREERS: MockCareerRow[] = [
  {
    soc: "19-4021",
    title: "Biological Technician",
    wage: 52140,
    stats: { ern: 2, roi: 3, res: 4, grw: 3, aura: 3 },
    horizon: [
      {
        tier: "entry",
        tier_label: "Today",
        years_label: "0–1 yr",
        title: "Biological Technician",
        soc: "19-4021",
        one_liner: "Lab-bench work — samples, assays, documentation.",
        unlock: null,
        deltas: {},
      },
      {
        tier: "early",
        tier_label: "Early",
        years_label: "1–4 yr",
        title: "Microbiologist",
        soc: "19-1022",
        one_liner: "Owns experiments, writes up findings, trains new techs.",
        unlock: null,
        deltas: { ern: +1, grw: +1 },
      },
      {
        tier: "mid",
        tier_label: "Mid",
        years_label: "4–8 yr",
        title: "Medical Scientist",
        soc: "19-1042",
        one_liner: "Research lead. Grant writing shows up here.",
        unlock: "Master's degree · close relatedness",
        deltas: { ern: +2, res: +1 },
      },
      {
        tier: "senior",
        tier_label: "Senior",
        years_label: "8+ yr",
        title: "Natural Sciences Manager",
        soc: "11-9121",
        one_liner: "Runs the lab. Budget, hiring, research direction.",
        unlock: null,
        deltas: { ern: +2, grw: +1, aura: +1 },
      },
    ],
  },
  {
    soc: "19-1029",
    title: "Biologist",
    wage: 65000,
    stats: { ern: 3, roi: 3, res: 4, grw: 3, aura: 3 },
    horizon: [
      {
        tier: "entry",
        tier_label: "Today",
        years_label: "0–1 yr",
        title: "Biologist",
        soc: "19-1029",
        one_liner: "Field or lab generalist — the starting bench.",
        unlock: null,
        deltas: {},
      },
      {
        tier: "early",
        tier_label: "Early",
        years_label: "1–4 yr",
        title: "Zoologist / Wildlife Biologist",
        soc: "19-1023",
        one_liner: "Specializes, publishes, runs field studies solo.",
        unlock: null,
        deltas: { grw: +1, aura: +1 },
      },
      {
        tier: "mid",
        tier_label: "Mid",
        years_label: "4–8 yr",
        title: "Epidemiologist",
        soc: "19-1041",
        one_liner: "Population-level analysis. Public health pivots here.",
        unlock: "Master's degree · moderate relatedness",
        deltas: { ern: +2, res: +1 },
      },
      {
        tier: "senior",
        tier_label: "Senior",
        years_label: "8+ yr",
        title: "Natural Sciences Manager",
        soc: "11-9121",
        one_liner: "Directs a team of scientists. Strategy and budget.",
        unlock: null,
        deltas: { ern: +2, grw: +1 },
      },
    ],
  },
  {
    soc: "25-1042",
    title: "Biology Teacher, Postsecondary",
    wage: 79170,
    stats: { ern: 3, roi: 3, res: 5, grw: 3, aura: 5 },
    horizon: [
      {
        tier: "entry",
        tier_label: "Today",
        years_label: "0–1 yr",
        title: "Teaching Assistant / Adjunct",
        soc: "25-1042",
        one_liner: "Teaching load while completing grad work.",
        unlock: null,
        deltas: {},
      },
      {
        tier: "early",
        tier_label: "Early",
        years_label: "1–4 yr",
        title: "Postdoctoral Researcher",
        soc: "19-1029",
        one_liner: "Research-heavy, publications drive what comes next.",
        unlock: "Doctorate · high relatedness",
        deltas: { res: +1 },
      },
      {
        tier: "mid",
        tier_label: "Mid",
        years_label: "4–8 yr",
        title: "Assistant Professor",
        soc: "25-1042",
        one_liner: "Own lab, own students, tenure clock ticking.",
        unlock: "Doctorate · high relatedness",
        deltas: { ern: +1, aura: +1 },
      },
      {
        tier: "senior",
        tier_label: "Senior",
        years_label: "8+ yr",
        title: "Full Professor / Dept Chair",
        soc: "25-1042",
        one_liner: "Tenured. Research direction plus department politics.",
        unlock: null,
        deltas: { ern: +2, aura: +2 },
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

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

function HorizonRail({
  nodes,
  activeTier,
  onSelect,
  reducedMotion,
}: {
  nodes: MockNode[];
  activeTier: ExperienceTier;
  onSelect: (tier: ExperienceTier) => void;
  reducedMotion: boolean;
}) {
  return (
    <div className="relative px-2 pt-4 pb-2">
      {/* The rail itself */}
      <div
        aria-hidden="true"
        className="absolute left-5 right-5 top-[calc(1rem+0.5rem)] h-px bg-gradient-to-r from-border-subtle via-border to-border-subtle"
      />

      <div className="relative grid grid-cols-4 gap-2">
        {nodes.map((node) => {
          const isActive = node.tier === activeTier;
          const isLocked = Boolean(node.unlock);
          return (
            <button
              key={node.tier}
              type="button"
              onClick={() => onSelect(node.tier)}
              aria-pressed={isActive}
              aria-label={`${node.tier_label} — ${node.title}`}
              className="group flex flex-col items-center gap-2 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] rounded-lg px-1 py-1"
            >
              <motion.span
                aria-hidden="true"
                initial={false}
                animate={
                  reducedMotion
                    ? {}
                    : isActive
                      ? { scale: 1.15 }
                      : { scale: 1 }
                }
                transition={springs.snappy}
                className={[
                  "relative flex items-center justify-center w-4 h-4 rounded-full",
                  isActive
                    ? isLocked
                      ? "bg-accent-insight shadow-glow-insight"
                      : "bg-accent-thrive shadow-glow-thrive"
                    : isLocked
                      ? "bg-bp-mid ring-1 ring-accent-insight/50"
                      : "bg-bp-mid ring-1 ring-border-strong group-hover:ring-accent-info/60",
                ].join(" ")}
              >
                {isLocked && (
                  <span
                    aria-hidden="true"
                    className={[
                      "absolute -top-3 font-data text-[10px] leading-none",
                      isActive ? "text-accent-insight" : "text-accent-insight/70",
                    ].join(" ")}
                  >
                    ◆
                  </span>
                )}
              </motion.span>
              <span
                className={[
                  "font-data text-micro uppercase tracking-[2px] transition-colors duration-normal",
                  isActive ? "text-text-primary" : "text-text-muted",
                ].join(" ")}
              >
                {node.tier_label}
              </span>
              <span
                className={[
                  "font-body text-micro transition-colors duration-normal",
                  isActive ? "text-text-secondary" : "text-text-muted/70",
                ].join(" ")}
              >
                {node.years_label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function HorizonDetail({
  node,
  reducedMotion,
}: {
  node: MockNode;
  reducedMotion: boolean;
}) {
  const deltas = Object.entries(node.deltas) as Array<[StatKey, number]>;
  const isEntry = node.tier === "entry";
  return (
    <motion.div
      key={node.tier}
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: -6 }}
      transition={reducedMotion ? { duration: 0 } : springs.smooth}
      className="mt-3 border-t border-border-subtle pt-3 flex flex-col gap-2"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="text-[22px] leading-none select-none flex-shrink-0 mt-0.5"
        >
          {socEmoji(node.soc)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h4 className="font-body text-body font-bold text-text-primary">
              {node.title}
            </h4>
            <span className="font-data text-micro text-text-muted">
              {node.soc}
            </span>
          </div>
          <p className="font-body text-small text-text-secondary mt-1">
            {node.one_liner}
          </p>
        </div>
      </div>

      {(deltas.length > 0 || node.unlock) && (
        <div className="flex flex-wrap items-center gap-2 pl-[34px]">
          {isEntry && (
            <span className="font-body text-micro italic text-text-muted">
              The starting bench.
            </span>
          )}
          {deltas.map(([key, value]) => (
            <DeltaPill key={key} statKey={key} value={value} />
          ))}
          {node.unlock && (
            <span
              className="inline-flex items-center gap-1.5 font-body text-micro text-accent-insight/90 bg-accent-insight/10 ring-1 ring-accent-insight/25 rounded-full px-2 py-0.5"
              title="Graduate degree required"
            >
              <span aria-hidden="true" className="font-data">
                ◆
              </span>
              <span>Opens with {node.unlock.toLowerCase()}</span>
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main row — the CareerCard that expands into a horizon strip
// ---------------------------------------------------------------------------

const STAT_ORDER: StatKey[] = ["ern", "roi", "res", "grw", "aura"];

function CareerRow({
  career,
  expanded,
  onToggle,
}: {
  career: MockCareerRow;
  expanded: boolean;
  onToggle: () => void;
}) {
  const reducedMotion = useReducedMotion() ?? false;
  const [activeTier, setActiveTier] = useState<ExperienceTier>("entry");
  const activeNode = useMemo<MockNode | null>(() => {
    const hit = career.horizon.find((n) => n.tier === activeTier);
    if (hit) return hit;
    return career.horizon[0] ?? null;
  }, [career.horizon, activeTier]);

  return (
    <div
      className={[
        "rounded-xl border transition-colors duration-normal",
        expanded
          ? "bg-bp-surface border-border shadow-lg"
          : "bg-bp-mid border-border-subtle hover:bg-bp-surface hover:border-border hover:shadow-lg hover:-translate-y-0.5",
      ].join(" ")}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={`horizon-${career.soc}`}
        className="w-full text-left p-6 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-focus-ring)] rounded-xl"
      >
        <div className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className="text-[32px] leading-none select-none flex-shrink-0"
          >
            {socEmoji(career.soc)}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-body font-bold text-body-lg text-text-primary">
                {career.title}
              </h3>
              <motion.span
                aria-hidden="true"
                animate={{ rotate: expanded ? 180 : 0 }}
                transition={springs.snappy}
                className="font-data text-small text-text-muted mt-1"
              >
                ▾
              </motion.span>
            </div>
            <p className="font-data text-data text-stat-ern mt-1">
              ${career.wage.toLocaleString()}/yr median
            </p>
          </div>
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
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={`horizon-${career.soc}`}
            key="horizon"
            initial={
              reducedMotion ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }
            }
            animate={{ height: "auto", opacity: 1 }}
            exit={
              reducedMotion ? { height: 0, opacity: 0 } : { height: 0, opacity: 0 }
            }
            transition={reducedMotion ? { duration: 0 } : springs.smooth}
            className="overflow-hidden"
          >
            <div className="px-4 pb-5">
              <div className="mx-2 border-t border-border-subtle pt-4">
                <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info mb-1 pl-2">
                  Where this arc goes
                </p>
                <p className="font-body text-small italic text-text-muted pl-2">
                  Your first job isn't your career. Tap a point to see what
                  typically comes next.
                </p>
                <HorizonRail
                  nodes={career.horizon}
                  activeTier={activeTier}
                  onSelect={setActiveTier}
                  reducedMotion={reducedMotion}
                />
                <AnimatePresence mode="wait" initial={false}>
                  {activeNode && (
                    <HorizonDetail
                      key={activeNode.tier}
                      node={activeNode}
                      reducedMotion={reducedMotion}
                    />
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mockup shell — renders just enough Set Your Course context around it
// ---------------------------------------------------------------------------

export function HorizonStripMockup() {
  const [openSoc, setOpenSoc] = useState<string | null>("19-4021");

  return (
    <section aria-label="Horizon Strip mockup" className="flex flex-col gap-4">
      {/* Echoes the live SetYourCourseScreen resolution header so the
          strip sits in its real visual neighborhood. */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-[6px] font-body text-small text-text-muted">
          <span aria-hidden="true" className="text-accent-insight">
            ✦
          </span>
          <span>Matched</span>
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
          <span
            aria-hidden="true"
            className="font-data text-data text-text-muted"
          ></span>
          <h2 className="font-display font-semibold text-heading text-text-primary">
            Where this commonly leads
          </h2>
          <span className="bg-bp-surface rounded-full px-2.5 py-0.5 font-data text-data-sm text-text-muted">
            ({COMMON_CAREERS.length} paths)
          </span>
        </div>
        <p className="font-body text-small text-text-secondary ml-7 mb-4">
          Tap a row to see the arc past the first job.
        </p>

        <div className="flex flex-col gap-3">
          {COMMON_CAREERS.map((career) => (
            <CareerRow
              key={career.soc}
              career={career}
              expanded={openSoc === career.soc}
              onToggle={() =>
                setOpenSoc((prev) => (prev === career.soc ? null : career.soc))
              }
            />
          ))}
        </div>
      </div>
    </section>
  );
}
