import { motion, useReducedMotion } from "framer-motion";
import { springs, stagger } from "@/styles/motion";

/**
 * Section G — Data Sources (Transparency Block)
 * 7-row dataset table styled as a receipt panel. Karpathy = 815 (not 342).
 * See spec §3.10 + §4 Content Ground Truth.
 */

interface DatasetRow {
  identifier: string;
  source: string;
  rows: string;
  powers: string;
}

const DATASETS: DatasetRow[] = [
  {
    identifier: "landing-data-row-scorecard",
    source: "College Scorecard (Field of Study)",
    rows: "69,947",
    powers: "ERN, ROI, Loans",
  },
  {
    identifier: "landing-data-row-bls",
    source: "BLS Occupational Outlook",
    rows: "832",
    powers: "Growth, Ceiling",
  },
  {
    identifier: "landing-data-row-onet",
    source: "O*NET Task & Work Context",
    rows: "798",
    powers: "HMN, Burnout",
  },
  {
    identifier: "landing-data-row-karpathy",
    source: "Karpathy AI Exposure",
    rows: "815",
    powers: "RES, Fight AI",
  },
  {
    identifier: "landing-data-row-anthropic",
    source: "Anthropic Economic Index",
    rows: "587",
    powers: "AI velocity",
  },
  {
    identifier: "landing-data-row-bea",
    source: "BEA Regional Price Parities",
    rows: "51",
    powers: "Geo adjustment",
  },
  {
    identifier: "landing-data-row-cipsoc",
    source: "CIP-SOC Crosswalk",
    rows: "626,406",
    powers: "The core query",
  },
];

export function DataSourcesSection() {
  const prefersReducedMotion = useReducedMotion();

  const reveal = (delay = 0) =>
    prefersReducedMotion
      ? { initial: false, animate: { opacity: 1, y: 0 } }
      : {
          initial: { opacity: 0, y: 24 },
          whileInView: { opacity: 1, y: 0 },
          viewport: { once: true, margin: "-80px" },
          transition: { ...springs.smooth, delay },
        };

  const tableReveal = prefersReducedMotion
    ? { initial: false, animate: { opacity: 1, scale: 1 } }
    : {
        initial: { opacity: 0, scale: 0.96 },
        whileInView: { opacity: 1, scale: 1 },
        viewport: { once: true, margin: "-80px" },
        transition: { ...springs.smooth, delay: 0.2 },
      };

  const rowReveal = (index: number) =>
    prefersReducedMotion
      ? { initial: false, animate: { opacity: 1, x: 0 } }
      : {
          initial: { opacity: 0, x: -8 },
          whileInView: { opacity: 1, x: 0 },
          viewport: { once: true, margin: "-80px" },
          transition: { ...springs.smooth, delay: 0.3 + index * stagger.fast },
        };

  return (
    <section
      id="landing-section-data"
      className="relative px-6 tablet:px-10 py-16 tablet:py-20 desktop:py-24"
    >
      <div
        aria-hidden
        className="absolute left-1/2 top-0 h-[80px] w-px -translate-x-1/2 bg-gradient-to-b from-border-subtle to-transparent"
      />
      <div className="mx-auto max-w-[960px]">
        <motion.h2
          className="font-display font-bold text-heading tablet:text-title text-text-primary"
          {...reveal(0)}
        >
          How we know.
        </motion.h2>
        <motion.p
          className="mt-6 font-body text-body tablet:text-body-lg text-text-secondary max-w-[62ch] leading-relaxed"
          {...reveal(0.1)}
        >
          Every number FutureProof shows you traces back to one of these public
          datasets. Click any row to see how it flows through the pipeline.
        </motion.p>

        <motion.div
          className="mt-10 bg-bp-mid border border-border-subtle rounded-xl p-6"
          {...tableReveal}
        >
          <div
            role="table"
            aria-label="Public datasets powering FutureProof"
            className="w-full"
          >
            <div
              role="row"
              className="grid grid-cols-[1fr_auto_1fr] tablet:grid-cols-[2fr_auto_1.2fr] gap-4 pb-3 mb-3 border-b border-border-subtle font-data font-bold text-[11px] tracking-[2px] uppercase text-accent-info"
            >
              <span role="columnheader">Source</span>
              <span role="columnheader" className="text-right">
                Rows
              </span>
              <span role="columnheader">Powers</span>
            </div>

            {DATASETS.map((row, index) => (
              <motion.div
                key={row.identifier}
                id={row.identifier}
                role="row"
                className="grid grid-cols-[1fr_auto_1fr] tablet:grid-cols-[2fr_auto_1.2fr] gap-4 py-3 px-2 border-l-[3px] border-transparent border-b border-border-subtle last:border-b-0 transition-colors duration-fast hover:bg-bp-surface hover:border-l-accent-insight"
                {...rowReveal(index)}
              >
                <span
                  role="cell"
                  className="font-body font-semibold text-body-sm text-text-primary"
                >
                  {row.source}
                </span>
                <span
                  role="cell"
                  className="font-data text-data text-text-secondary text-right tabular-nums"
                >
                  {row.rows}
                </span>
                <span
                  role="cell"
                  className="font-body text-small text-text-muted"
                >
                  {row.powers}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.p
          className="mt-6 font-body text-small text-text-muted italic max-w-[720px] leading-relaxed"
          {...reveal(prefersReducedMotion ? 0 : 0.3 + DATASETS.length * stagger.fast + 0.2)}
        >
          Composite AI exposure blends Gemma 4 task-level scoring, Karpathy's
          job-description baseline, and Anthropic's observed adoption share.
          Gemma scores 1.75 points more conservatively than Karpathy on average
          across 372 overlapping occupations.
        </motion.p>
      </div>
    </section>
  );
}
