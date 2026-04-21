/**
 * Chapter Book — shared test fixtures.
 *
 * Used by bucketBranches.test.ts, ChapterBook.test.tsx, ChapterCard.test.tsx.
 * These fixtures describe a realistic Biological Technician arc so the
 * behaviors under test read like real data, not contrived setups.
 */
import type { CareerBranch, CareerOutcome } from "@/types/build";

export function makeCareer(
  overrides: Partial<CareerOutcome> = {},
): CareerOutcome {
  return {
    unitid: 153603,
    institution_name: "Iowa State University",
    cipcode: "26.0101",
    program_name: "Biology, General",
    soc_code: "19-4021",
    occupation_title: "Biological Technician",
    soc_major_group_name: "Life, Physical, and Social Science",
    median_annual_wage: 52140,
    earnings_1yr_median: 38000,
    earnings_1yr_p25: 32000,
    earnings_1yr_p75: 45000,
    debt_median: 24000,
    debt_to_earnings_annual: 0.63,
    education_level_name: "Bachelor's degree",
    growth_category: "Average",
    net_price_annual: 20000,
    cost_of_attendance_annual: 28000,
    modeled_total_debt: 80000,
    debt_median_reference: 24000,
    institution_control: "Public",
    tuition_in_state: 9000,
    tuition_out_of_state: 24000,
    room_board_on_campus: 11000,
    stats: { ern: 2, roi: 3, res: 4, grw: 3, hmn: 3 },
    bosses: { ai: 1, loans: 2, market: 2, burnout: 1, ceiling: 2 },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: 5,
    overall_confidence: "high",
    match_quality: null,
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    loan_pct: 1.0,
    ...overrides,
  };
}

export function makeBranch(
  overrides: Partial<CareerBranch> & Pick<CareerBranch, "to_soc" | "to_title">,
): CareerBranch {
  return {
    from_soc: "19-4021",
    delta_ern: 0,
    delta_roi: 0,
    delta_res: 0,
    delta_grw: 0,
    delta_hmn: 0,
    unlock: null,
    relatedness: 0.8,
    experience_years: null,
    experience_tier: null,
    experience_delta: null,
    related_education_level: null,
    ...overrides,
  };
}

/**
 * Full four-tier arc: entry (parent anchor only) → early → mid → senior.
 * Used when a test needs a canonical "all chapters present" book.
 */
export const branchesFullArc: CareerBranch[] = [
  makeBranch({
    to_soc: "19-1022",
    to_title: "Microbiologist",
    delta_ern: 1,
    delta_grw: 1,
    relatedness: 0.92,
    experience_years: 3,
    experience_tier: "early",
    experience_delta: 2,
    related_education_level: "Bachelor's degree",
  }),
  makeBranch({
    to_soc: "19-1042",
    to_title: "Medical Scientist",
    delta_ern: 2,
    delta_res: 1,
    relatedness: 0.78,
    experience_years: 7,
    experience_tier: "mid",
    experience_delta: 6,
    related_education_level: "Master's degree",
  }),
  makeBranch({
    to_soc: "11-9121",
    to_title: "Natural Sciences Manager",
    delta_ern: 2,
    delta_grw: 1,
    delta_hmn: 1,
    relatedness: 0.65,
    experience_years: 10,
    experience_tier: "senior",
    experience_delta: 9,
    related_education_level: "Bachelor's degree",
  }),
];
