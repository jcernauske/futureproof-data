/**
 * Archetypes Showcase — pentagons that teach how to read a build.
 *
 * Route: /help (12 cards — nine archetypes + three missing-data examples)
 *        /mockups/archetypes (9 cards — Kaggle screenshot path, stable URL)
 *
 * Nine real (school, major, career) archetypes plus three illustrative
 * missing-data cards that explain what a null axis means. The first
 * nine were originally built for the Kaggle writeup screenshot — schools
 * are aliased so the writeup doesn't single any institution out. The full
 * mapping (school name, CIPCODE, SOC, raw numbers) lives at
 * docs/reference/kaggle-pentagon-archetypes.md so the screenshot is
 * reproducible and auditable.
 *
 * Uses the exact PentagonChart component that renders on /my-build, with
 * animation off so the screenshot is deterministic. PentagonChart already
 * collapses null axes to the center and renders the label with an em-dash
 * — see PentagonChart.tsx:45-64.
 */
import { PageContainer } from "@/components/ui/PageContainer";
import { PentagonChart } from "@/components/PentagonChart";
import type { PentagonStats } from "@/types/build";

type ArchetypeKicker = "THIN PIPELINE" | "DATA GAP";

interface Archetype {
  alias: string;
  tagline: string;
  stats: PentagonStats;
  // Missing-data cards get a kicker above the title. Real-shape archetypes
  // (the original nine) leave it undefined.
  kicker?: ArchetypeKicker;
}

// Stats sourced from consumable.program_career_paths + consumable.institution_aura
// on 2026-05-13 via scripts/_archetype_probe.py and _archetype_probe3.py. See
// docs/reference/kaggle-pentagon-archetypes.md for the unmasked rows.
const ARCHETYPES: Archetype[] = [
  {
    alias: "The Flagship",
    tagline: "The shape everything else is judged against.",
    stats: { ern: 10, roi: 10, res: 7, grw: 7, aura: 7 },
  },
  {
    alias: "All Sizzle, No Steak",
    tagline: "The brand was not a paycheck.",
    stats: { ern: 3, roi: 1, res: 7, grw: 4, aura: 9 },
  },
  {
    alias: "Good Work If You Can Get It",
    tagline: "$120K starting. Also disappearing.",
    stats: { ern: 10, roi: 10, res: 7, grw: 3, aura: 8 },
  },
  {
    alias: "Beware the AI Buzzsaw",
    tagline: "Looks like a win until you read the resilience axis.",
    stats: { ern: 9, roi: 7, res: 3, grw: 3, aura: 10 },
  },
  {
    alias: "The Hidden Gem",
    tagline: "The unglamourous pick that quietly beats the brand schools.",
    stats: { ern: 8, roi: 10, res: 9, grw: 10, aura: 3 },
  },
  {
    alias: "The Prestige Tax",
    tagline: "You bought the sweatshirt. You did not buy the ROI.",
    stats: { ern: 7, roi: 2, res: 8, grw: 3, aura: 10 },
  },
  {
    alias: "The Calling",
    tagline: "Society needs the work. Society won't pay for it.",
    stats: { ern: 2, roi: 5, res: 9, grw: 9, aura: 5 },
  },
  {
    alias: "The Bull's Eye",
    tagline: "Perfectly balanced. The middle of every axis.",
    stats: { ern: 5, roi: 5, res: 5, grw: 6, aura: 6 },
  },
  {
    alias: "The Trades",
    tagline: "Low brand, high hands. AI can't weld.",
    stats: { ern: 5, roi: 10, res: 9, grw: 5, aura: 1 },
  },
];

// Missing-data archetypes — illustrative shapes that teach what a null
// axis means. PentagonChart collapses null axes to the center and labels
// them with an em-dash, so the dimple is the visual story.
//
// Quiet Cohort is the only one of the three with an "illiquid pipeline"
// reading: College Scorecard suppresses earnings (and therefore ROI) when
// a program graduates fewer than ~30 students per year. That's a real
// signal about cohort size, not just data availability.
//
// Off-the-BLS-Radar and No-Brand-Gravity are pure data-coverage gaps:
// the federal source has nothing to say about that axis for this
// (school, major, career) combination. Missing != bad.
const MISSING_DATA_ARCHETYPES: Archetype[] = [
  {
    alias: "The Quiet Cohort",
    tagline:
      "Too few grads per year to publish a salary. Small cohort, thin alumni network.",
    stats: { ern: null, roi: null, res: 7, grw: 7, aura: 5 },
    kicker: "THIN PIPELINE",
  },
  {
    alias: "Off the BLS Radar",
    tagline:
      "BLS doesn't forecast every job. Missing growth ≠ stagnant — the federal forecaster skipped this one.",
    stats: { ern: 6, roi: 7, res: 8, grw: null, aura: 6 },
    kicker: "DATA GAP",
  },
  {
    alias: "No Brand Gravity",
    tagline:
      "Schools without endowment or athletic-spending data go quiet on brand. Not a bad school — a quiet one.",
    stats: { ern: 6, roi: 9, res: 7, grw: 7, aura: null },
    kicker: "DATA GAP",
  },
];

function kickerColor(kicker: ArchetypeKicker): string {
  // THIN PIPELINE leans into the "this is a real signal about cohort size"
  // reading — amber/caution. DATA GAP is neutral muted text so it reads as
  // "we just don't know," not "this is bad."
  return kicker === "THIN PIPELINE"
    ? "text-accent-caution"
    : "text-text-muted";
}

function ArchetypeCard({ archetype }: { archetype: Archetype }) {
  return (
    <article className="flex flex-col items-center gap-5 rounded-[20px] border border-border-subtle bg-bp-mid p-6">
      <header className="text-center">
        {archetype.kicker && (
          <p
            className={`font-data text-micro font-bold uppercase tracking-[2px] mb-2 ${kickerColor(archetype.kicker)}`}
          >
            {archetype.kicker}
          </p>
        )}
        <h2 className="font-display text-display-sm font-semibold text-text-primary leading-snug">
          {archetype.alias}
        </h2>
        <p className="font-body text-body-sm text-text-secondary mt-2 max-w-[32ch] mx-auto italic">
          {archetype.tagline}
        </p>
      </header>
      <PentagonChart stats={archetype.stats} size={320} animated={false} />
    </article>
  );
}

interface ArchetypesShowcaseProps {
  // Hide the three missing-data cards (Kaggle screenshot route uses this).
  // Defaults to true so /help shows all twelve.
  showMissingData?: boolean;
}

export function ArchetypesShowcase({
  showMissingData = true,
}: ArchetypesShowcaseProps = {}) {
  const cards = showMissingData
    ? [...ARCHETYPES, ...MISSING_DATA_ARCHETYPES]
    : ARCHETYPES;

  // Page intro copy is different for the 9-card Kaggle path vs the 12-card
  // in-app help path so the subhead doesn't overclaim ("every pentagon is
  // a real build") on the three illustrative cards.
  const kicker = showMissingData
    ? "Twelve pentagons, twelve ways to read a build"
    : "Nine pentagons, nine different stories";
  const headline = showMissingData
    ? "Same five stats. Twelve honest reads."
    : "Same five stats. Nine honest verdicts.";
  const subhead = showMissingData
    ? "The first nine are real (school, major, career) builds from federal data, schools anonymized — what different shapes mean. The last three are illustrative — what a gap means, when a federal source has nothing to say."
    : "Every pentagon below is a real (school, major, career) path from federal data. Schools are anonymized — the shape is the story.";

  return (
    <div className="min-h-screen relative py-12">
      <PageContainer variant="bleed" className="py-6">
        <header className="text-center mb-12 max-w-[720px] mx-auto">
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info mb-2">
            {kicker}
          </p>
          <h1 className="font-display text-hero font-semibold text-text-primary leading-tight">
            {headline}
          </h1>
          <p className="font-body text-body-lg text-text-secondary mt-3">
            {subhead}
          </p>
        </header>

        <div className="grid grid-cols-3 gap-6 items-stretch">
          {cards.map((a) => (
            <ArchetypeCard key={a.alias} archetype={a} />
          ))}
        </div>
      </PageContainer>
    </div>
  );
}
