/**
 * Plain-English stat explanations and data sources from PRD v8.
 *
 * Stat metadata used by the build-results pentagon legend
 * (`BuildResultsScreen`), `PentagonChart`, `CareerCard`, and the horizon
 * mockups for stat colors and abbreviations.
 */

export type StatKey = "ern" | "roi" | "res" | "grw" | "aura";

export interface StatExplanation {
  key: StatKey;
  name: string;
  nameKey: string;
  abbreviation: string;
  explanation: string;
  explanationKey: string;
  source: string;
  // Raw CSS var — only for SVG `fill`/`stroke` where Tailwind classes can't reach.
  color: string;
  // Tailwind utility classes — use these in `className` for anything HTML/CSS.
  textClass: string;
  bgClass: string;
}

export const STAT_EXPLANATIONS: StatExplanation[] = [
  {
    key: "ern",
    name: "Earning Power",
    nameKey: "stat.ern.name",
    abbreviation: "ERN",
    explanation:
      "Compares what graduates of this program at this school earn against peers in the same field, blended with how this career's wages rank among all U.S. occupations.",
    explanationKey: "stat.ern.explanation",
    source: "College Scorecard + BLS",
    color: "var(--color-stat-ern)",
    textClass: "text-stat-ern",
    bgClass: "bg-stat-ern",
  },
  {
    key: "roi",
    name: "Return on Investment",
    nameKey: "stat.roi.name",
    abbreviation: "ROI",
    explanation:
      "Compares the total cost of attending this program (4 years) to your starting salary. Doesn't depend on how you finance it — that's Fight Student Loans.",
    explanationKey: "stat.roi.explanation",
    source: "College Scorecard",
    color: "var(--color-stat-roi)",
    textClass: "text-stat-roi",
    bgClass: "bg-stat-roi",
  },
  {
    key: "res",
    name: "AI Resilience",
    nameKey: "stat.res.name",
    abbreviation: "RES",
    explanation:
      "How well your career holds up against AI. Blends two signals: how much the work still needs people, and how poorly automation actually does it today.",
    explanationKey: "stat.res.explanation",
    source: "Karpathy AI Exposure + Anthropic Economic Index + O*NET task profiles",
    color: "var(--color-stat-res)",
    textClass: "text-stat-res",
    bgClass: "bg-stat-res",
  },
  {
    key: "grw",
    name: "Growth Outlook",
    nameKey: "stat.grw.name",
    abbreviation: "GRW",
    explanation:
      "Is this field growing or shrinking? Based on 10-year job projections.",
    explanationKey: "stat.grw.explanation",
    source: "BLS Occupational Outlook",
    color: "var(--color-stat-grw)",
    textClass: "text-stat-grw",
    bgClass: "bg-stat-grw",
  },
  {
    key: "aura",
    name: "Brand Gravity",
    nameKey: "stat.aura.name",
    abbreviation: "AURA",
    explanation:
      "How much weight your school's name carries — endowment per student, marketing reach, athletic budget. Real signal, not vibes. Some schools don't have it yet.",
    explanationKey: "stat.aura.explanation",
    source: "IPEDS Finance + EADA athletics",
    color: "var(--color-stat-aura)",
    textClass: "text-stat-aura",
    bgClass: "bg-stat-aura",
  },
];

export const STAT_MAP = Object.fromEntries(
  STAT_EXPLANATIONS.map((s) => [s.key, s]),
) as Record<StatKey, StatExplanation>;
