/**
 * Plain-English stat explanations and data sources from PRD v8.
 *
 * Stat metadata used by the build-results pentagon legend
 * (`BuildResultsScreen`), `PentagonChart`, `CareerCard`, and the horizon
 * mockups for stat colors and abbreviations.
 */

export type StatKey = "ern" | "roi" | "res" | "grw" | "hmn";

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
      "Based on what graduates of this program at this school actually earn.",
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
      "How exposed is this career to AI automation? Higher means the work needs humans.",
    explanationKey: "stat.res.explanation",
    source: "Composite AI Exposure (Gemma 4 + Karpathy + Anthropic)",
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
    key: "hmn",
    name: "Human Edge",
    nameKey: "stat.hmn.name",
    abbreviation: "HMN",
    explanation:
      "How much does this job depend on uniquely human skills?",
    explanationKey: "stat.hmn.explanation",
    source: "O*NET Work Activities",
    color: "var(--color-stat-hmn)",
    textClass: "text-stat-hmn",
    bgClass: "bg-stat-hmn",
  },
];

export const STAT_MAP = Object.fromEntries(
  STAT_EXPLANATIONS.map((s) => [s.key, s]),
) as Record<StatKey, StatExplanation>;
