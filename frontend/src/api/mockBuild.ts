/**
 * Mock API handlers returning realistic data shaped to Pydantic contracts.
 * Used when VITE_USE_MOCK_API=true (default for frontend-only dev).
 * Swap to real API by setting VITE_USE_MOCK_API=false.
 */

import type {
  Build,
  CareerOutcome,
  TieredCareers,
  GauntletResult,
  CareerBranch,
  SkillRec,
  AppliedSkill,
} from "@/types/build";

function makeCareer(
  soc: string,
  title: string,
  wage: number,
  stats: [number, number, number, number, number],
  bosses: [number, number, number, number, number],
  overrides?: Partial<CareerOutcome>,
): CareerOutcome {
  return {
    unitid: 110635,
    institution_name: "University of California-Berkeley",
    cipcode: "11.0701",
    program_name: "Computer Science",
    soc_code: soc,
    occupation_title: title,
    soc_major_group_name: null,
    median_annual_wage: wage,
    // Mock OEWS distribution — slightly tighter band around `wage` than
    // the Scorecard year-one band, since OEWS is mid-career national
    // wage and not a year-one figure.
    wage_p10: wage * 0.6,
    wage_p25: wage * 0.78,
    wage_p75: wage * 1.25,
    wage_p90: wage * 1.55,
    earnings_1yr_median: wage * 0.75,
    earnings_1yr_p25: wage * 0.55,
    earnings_1yr_p75: wage * 0.95,
    debt_median: 28500,
    debt_to_earnings_annual: 0.42,
    education_level_name: "Bachelor's degree",
    growth_category: "Much faster than average",
    // Default to early-career; per-row overrides below set realistic
    // mixed values across designer/analyst/manager roles so dev mode
    // renders all three experience-based sections on /set-your-course.
    work_experience_code: 2,
    net_price_annual: 14200,
    cost_of_attendance_annual: 22800,
    published_cost_4yr: 91200,
    modeled_total_debt: 91200,
    debt_median_reference: 28500,
    institution_control: "Public",
    tuition_in_state: 11442,
    tuition_out_of_state: 41196,
    room_board_on_campus: 17220,
    stats: { ern: stats[0], roi: stats[1], res: stats[2], grw: stats[3], aura: stats[4] },
    bosses: { ai: bosses[0], loans: bosses[1], market: bosses[2], burnout: bosses[3], ceiling: bosses[4] },
    top_5_activities: [
      { activity: "Analyzing data or information", importance: 85 },
      { activity: "Working with computers", importance: 82 },
      { activity: "Making decisions and solving problems", importance: 78 },
      { activity: "Updating and using relevant knowledge", importance: 75 },
      { activity: "Communicating with supervisors and peers", importance: 70 },
    ],
    top_human_activities: [
      { activity: "Creative thinking", importance: 80 },
      { activity: "Complex problem solving", importance: 78 },
    ],
    burnout_drivers: [
      { driver: "Time pressure", severity: "moderate" },
      { driver: "Sitting for extended periods", severity: "high" },
    ],
    stats_available_count: 5,
    overall_confidence: "high",
    match_quality: null,
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    is_out_of_state: false,
    loan_pct: 0.5,
    ...overrides,
  };
}

const COMMON_CAREERS: CareerOutcome[] = [
  // Designer/developer roles need no related experience → code 3.
  makeCareer("15-1252", "Software Developers", 127260, [8, 7, 4, 9, 5], [6, 3, 2, 5, 3], { work_experience_code: 3 }),
  // Analyst roles want <5 years related experience → code 2.
  makeCareer("15-1211", "Computer Systems Analysts", 102240, [7, 6, 5, 7, 6], [5, 4, 3, 4, 4], { work_experience_code: 2 }),
  makeCareer("15-1299", "Computer Occupations, All Other", 95270, [6, 5, 4, 6, 5], [5, 4, 4, 4, 5], { work_experience_code: 3 }),
  makeCareer("15-1244", "Network and Computer Systems Administrators", 90520, [6, 5, 6, 5, 5], [4, 4, 3, 5, 5], { work_experience_code: 2 }),
];

const LESS_COMMON_CAREERS: CareerOutcome[] = [
  makeCareer("15-2051", "Data Scientists", 108020, [7, 6, 3, 8, 4], [7, 3, 2, 4, 3], { work_experience_code: 2 }),
  makeCareer("15-1243", "Database Administrators", 101000, [7, 6, 5, 5, 5], [5, 3, 3, 4, 5], { work_experience_code: 2 }),
  // Manager roles need 5+ years → code 1, the long-term bucket.
  makeCareer("11-3021", "Computer and Information Systems Managers", 164070, [9, 8, 6, 7, 7], [4, 2, 2, 6, 3], { work_experience_code: 1 }),
];

const STRETCH_CAREERS: CareerOutcome[] = [
  makeCareer("15-1221", "Computer and Information Research Scientists", 136620, [8, 7, 3, 7, 4], [7, 3, 3, 4, 2], { work_experience_code: 1 }),
  makeCareer("17-2061", "Computer Hardware Engineers", 132360, [8, 7, 7, 6, 6], [3, 3, 3, 4, 4], {
    work_experience_code: 2,
    substitution_applied: true,
    reported_cipcode: "11.0701",
    substituted_cipcode: "14.0901",
    data_caveat: { reason: "Broad CIP match used", detail: "Program-level data not available for this SOC; using parent CIP family data." },
  }),
];

export async function mockGetOutcomes(): Promise<CareerOutcome[]> {
  await delay(300);
  return [...COMMON_CAREERS, ...LESS_COMMON_CAREERS, ...STRETCH_CAREERS];
}

export async function mockGetTieredCareers(): Promise<TieredCareers> {
  await delay(600);
  return {
    common: COMMON_CAREERS,
    less_common: LESS_COMMON_CAREERS,
    stretch: STRETCH_CAREERS,
  };
}

export async function mockCreateBuild(
  selectedSoc: string,
  profileName: string,
  schoolName: string,
): Promise<Build> {
  await delay(2500);

  const allCareers = [...COMMON_CAREERS, ...LESS_COMMON_CAREERS, ...STRETCH_CAREERS];
  const career = allCareers.find((c) => c.soc_code === selectedSoc) ?? COMMON_CAREERS[0]!;

  const gauntlet: GauntletResult = {
    fights: [
      { boss: "ai", label: "Fight AI", result: "win", raw_score: 6, threshold_win: 5, threshold_draw: 3, reason: "Strong human-skill mix keeps this career relevant.", narrative: "Your creativity gives you an edge machines can't match.", rerolled: false, reroll_count: 0, original_result: null, original_raw_score: null, applied_skill_titles: [] },
      { boss: "loans", label: "Student Loans", result: "win", raw_score: 7, threshold_win: 5, threshold_draw: 3, reason: "High earnings relative to debt load.", narrative: "Your earning power outpaces your debt comfortably.", rerolled: false, reroll_count: 0, original_result: null, original_raw_score: null, applied_skill_titles: [] },
      { boss: "market", label: "The Market", result: "win", raw_score: 8, threshold_win: 5, threshold_draw: 3, reason: "This field is growing much faster than average.", narrative: "The market is hungry for people like you.", rerolled: false, reroll_count: 0, original_result: null, original_raw_score: null, applied_skill_titles: [] },
      { boss: "burnout", label: "Burnout", result: "draw", raw_score: 4, threshold_win: 5, threshold_draw: 3, reason: "Moderate stress factors — manageable but present.", narrative: "Burnout is real in this field, but awareness is your armor.", rerolled: false, reroll_count: 0, original_result: null, original_raw_score: null, applied_skill_titles: [] },
      { boss: "ceiling", label: "The Ceiling", result: "win", raw_score: 7, threshold_win: 5, threshold_draw: 3, reason: "Strong upward mobility with management paths available.", narrative: "The ceiling is high — your growth potential is real.", rerolled: false, reroll_count: 0, original_result: null, original_raw_score: null, applied_skill_titles: [] },
    ],
    wins: 4,
    losses: 0,
    draws: 1,
    unknown: 0,
    verdict: "Strong build — you're well-positioned for this career.",
  };

  const branches: CareerBranch[] = [
    { from_soc: career.soc_code, to_soc: "11-3021", to_title: "IT Manager", delta_ern: 2, delta_roi: 1, delta_res: 1, delta_grw: 0, delta_aura: 0, unlock: "5+ years experience", relatedness: 0.85, experience_years: 6, experience_tier: "mid", experience_delta: 4, related_education_level: "Bachelor's degree" },
    { from_soc: career.soc_code, to_soc: "15-2051", to_title: "Data Scientist", delta_ern: 1, delta_roi: 0, delta_res: -1, delta_grw: 2, delta_aura: 0, unlock: "Graduate degree", relatedness: 0.72, experience_years: 3, experience_tier: "early", experience_delta: 1, related_education_level: "Master's degree" },
    { from_soc: career.soc_code, to_soc: "15-1221", to_title: "Research Scientist", delta_ern: 1, delta_roi: 1, delta_res: -1, delta_grw: 1, delta_aura: 0, unlock: "PhD", relatedness: 0.65, experience_years: 9, experience_tier: "senior", experience_delta: 7, related_education_level: "Doctoral or professional degree" },
  ];

  const skillRecs: SkillRec[] = [
    { title: "Cloud Architecture", stat_impact: "ERN +1, GRW +1", rationale: "Cloud skills are the #1 hiring signal in this field right now." },
    { title: "Technical Leadership", stat_impact: "RES +2, ERN +1", rationale: "People management unlocks the highest earning trajectories." },
    { title: "Open Source Contributions", stat_impact: "RES +1, GRW +1", rationale: "Visible portfolio work builds resilience against market shifts." },
  ];

  const skillPool: AppliedSkill[] = [
    { id: "sk-cloud", title: "Cloud Architecture", rationale: "Cloud skills are the #1 hiring signal.", targets: ["market", "ceiling"], delta_ern: 1, delta_roi: 0, delta_res: 0, delta_grw: 1, delta_burnout_raw: 0, delta_ceiling_raw: 2, delta_loans_raw: 0 },
    { id: "sk-lead", title: "Technical Leadership", rationale: "People management unlocks higher earnings.", targets: ["burnout", "ceiling"], delta_ern: 1, delta_roi: 0, delta_res: 2, delta_grw: 0, delta_burnout_raw: -1, delta_ceiling_raw: 3, delta_loans_raw: 0 },
  ];

  return {
    build_id: `build-${Date.now()}`,
    created_at: new Date().toISOString(),
    school_name: schoolName,
    unitid: career.unitid,
    major_text: "Computer Science",
    cipcode: career.cipcode,
    program_name: career.program_name,
    effort: "balanced",
    loan_pct: 0.5,
    career,
    gauntlet,
    branches,
    skill_recs: skillRecs,
    guidance: `${profileName}, you picked ${career.occupation_title} — and the data says you're in strong shape. Your earning power is solid, with graduates from this program pulling in a median of $${(career.median_annual_wage ?? 0).toLocaleString()} per year. The ROI on your degree looks healthy given your loan situation. This field is growing fast, which means opportunity is expanding, not shrinking. The one area to watch is burnout — this career has real demands, but awareness is half the battle. Overall, this is a path with momentum behind it.`,
    skills_crafted: [],
    skill_pool: skillPool,
    next_steps: "Ready to fight the bosses and see how your build holds up?",
  };
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
