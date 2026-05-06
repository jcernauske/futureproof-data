/**
 * TypeScript types matching Pydantic models in backend/app/models/career.py.
 * These are the API contract — shapes match what the backend returns verbatim.
 */

export interface PentagonStats {
  ern: number | null;
  roi: number | null;
  res: number | null;  // blended from raw_stat_res + raw_stat_hmn
  grw: number | null;
  aura: number | null;  // institution-level brand gravity
}

export interface BossScores {
  ai: number | null;
  loans: number | null;
  market: number | null;
  burnout: number | null;
  ceiling: number | null;
}

export interface CareerOutcome {
  unitid: number;
  institution_name: string;
  cipcode: string;
  program_name: string;
  soc_code: string;
  occupation_title: string;
  soc_major_group_name: string | null;

  median_annual_wage: number | null;
  earnings_1yr_median: number | null;
  earnings_1yr_p25: number | null;
  earnings_1yr_p75: number | null;
  debt_median: number | null;
  debt_to_earnings_annual: number | null;
  education_level_name: string | null;
  growth_category: string | null;

  // Cost-of-attendance fields (from raw-ingest-college-scorecard-institution).
  // Nullable for institutions where the Scorecard didn't publish institution-level
  // cost data. Per the 2026-05-02 cost-anchor change:
  //   - ROI stat → DTE = published_cost_4yr / earnings (loan_pct-independent).
  //   - Loans Boss → modeled_total_debt = published_cost_4yr × loan_pct.
  // net_price_annual is retained as a "for context" reference only —
  // it does NOT drive scores anymore.
  net_price_annual: number | null;
  cost_of_attendance_annual: number | null;
  // Residency-aware 4-year sticker (full COA × 4, plus the OOS tuition
  // gap × 4 for out-of-state public-school applicants). Single source
  // of truth for ROI's DTE and the Student Loans Boss's modeled debt.
  // Null when cost_of_attendance_annual is missing.
  published_cost_4yr: number | null;
  modeled_total_debt: number | null;
  debt_median_reference: number | null;
  institution_control: string | null;
  tuition_in_state: number | null;
  tuition_out_of_state: number | null;
  is_out_of_state: boolean;
  room_board_on_campus: number | null;

  // Cost-based ROI provenance.
  //   roi_cost_basis = "cost_of_attendance" when net_price × 4 drove the ROI,
  //                    "debt_median" when the fallback fired,
  //                    "none" when neither was available.
  //   financed_dte   = (modeled_total_debt / earnings_1yr_median), the
  //                    loan_pct-aware ratio used to score the Student Loans
  //                    Boss. Distinct from debt_to_earnings_annual which is
  //                    the loan_pct-independent cost-vs-earnings ratio.
  roi_cost_basis?: "cost_of_attendance" | "debt_median" | "none" | null;
  financed_dte?: number | null;

  stats: PentagonStats;
  bosses: BossScores;

  // Raw inputs to the blended RES (Decision 4 in pentagon-stat-reshape):
  // Fight AI scores from these underlying integers, not the rounded
  // display value on stats.res.
  raw_stat_res?: number | null;
  raw_stat_hmn?: number | null;

  // AURA provenance, stamped from the per-build aura lookup so receipts
  // can cite basis/version without a follow-up MCP query.
  aura_score_basis?: string | null;
  aura_score_version?: string | null;

  top_5_activities: Array<Record<string, unknown>>;
  top_human_activities: Array<Record<string, unknown>>;
  burnout_drivers: Array<Record<string, unknown>>;

  stats_available_count: number | null;
  overall_confidence: string | null;

  match_quality: string | null;

  substitution_applied: boolean;
  reported_cipcode: string | null;
  substituted_cipcode: string | null;
  data_caveat: Record<string, unknown> | null;

  loan_pct: number;
}

export interface TieredCareers {
  common: CareerOutcome[];
  less_common: CareerOutcome[];
  stretch: CareerOutcome[];
}

export type BossOutcome = "win" | "lose" | "draw" | "unknown";
export type BossId = "ai" | "loans" | "market" | "burnout" | "ceiling";

export interface BossFightResult {
  boss: BossId;
  label: string;
  result: BossOutcome;
  raw_score: number | null;
  threshold_win: number;
  threshold_draw: number;
  reason: string;
  narrative: string;
  rerolled: boolean;
  reroll_count: number;
  original_result: BossOutcome | null;
  original_raw_score: number | null;
  applied_skill_titles: string[];
}

export interface GauntletResult {
  fights: BossFightResult[];
  wins: number;
  losses: number;
  draws: number;
  unknown: number;
  verdict: string;
}

export interface CareerBranch {
  from_soc: string;
  to_soc: string;
  to_title: string;
  delta_ern: number | null;
  delta_roi: number | null;
  delta_res: number | null;
  delta_grw: number | null;
  // Pentagon-stat-reshape Decision 5: AURA is institution-invariant.
  // Branches stay at the same school by construction, so delta_aura
  // is always 0. Field present in the contract so the radar overlay
  // can iterate 5 deltas uniformly.
  delta_aura: number;
  unlock: string | null;
  relatedness: number | null;
  // O*NET experience requirements (onet-experience-requirements spec,
  // Gold contract v1.2.0). Nullable when O*NET lacks ETE coverage.
  experience_years: number | null;
  experience_tier: "entry" | "early" | "mid" | "senior" | null;
  experience_delta: number | null;
  // Typed education level of the target occupation. Used by the Chapter
  // Book to detect grad-degree-gated chapters (feature-chapter-book
  // Decision #12). Nullable.
  related_education_level: string | null;
}

export interface SkillRec {
  title: string;
  stat_impact: string;
  rationale: string;
}

export interface AppliedSkill {
  id: string;
  title: string;
  rationale: string;
  targets: BossId[];
  delta_ern: number;
  delta_roi: number;
  delta_res: number;  // absorbs former delta_hmn impact
  delta_grw: number;
  // delta_hmn REMOVED (pentagon-stat-reshape v1.2). AURA is
  // institution-level → skills cannot shift it.
  delta_burnout_raw: number;
  delta_ceiling_raw: number;
}

// Peer-school leaderboard (feature-compare-schools-for-career.md).
// Mirrors backend.app.models.career.SchoolsForCareerResponse.

export type LeaderboardMode = "by_soc" | "by_cip_and_soc";
export type ConfidenceTier = "high" | "medium" | "low";
export type LeaderboardMatchQuality =
  | "full"
  | "partial_no_onet"
  | "partial_no_bls"
  | "scorecard_only"
  // Synthetic anchor row constructed client-side from build data when the
  // build's (unitid, cipcode) is absent from the leaderboard universe.
  // Backend supplies the rank via `anchor_estimated_rank`.
  | "estimated";

export interface SchoolForCareerRow {
  rank: number;
  unitid: number;
  institution_name: string;
  institution_control: string | null;
  state_abbr: string | null;
  cipcode: string;
  program_name: string;
  soc_code: string;
  occupation_title: string;
  stat_ern: number | null;
  stat_roi: number | null;
  earnings_1yr_median: number | null;
  net_price_annual: number | null;
  cost_of_attendance_annual: number | null;
  tuition_in_state: number | null;
  tuition_out_of_state: number | null;
  // Residency-aware fields stamped by the backend when home_state is
  // passed (spec roi-net-lifetime-value followup, "apples-to-apples
  // leaderboard"). published_cost_4yr is the residency-aware 4-year
  // sticker; the leaderboard's "Cost (4 yr)" column displays this so
  // it matches the FINANCES card. stat_roi_in_state preserves the
  // pre-adjustment score for transparency. roi_residency_adjusted is
  // the boolean flag.
  published_cost_4yr: number | null;
  stat_roi_in_state: number | null;
  roi_residency_adjusted: boolean;
  overall_confidence: ConfidenceTier;
  confidence_tier_program: string | null;
  match_quality: LeaderboardMatchQuality;
  is_anchor: boolean;
  // Number of institutions in this row's multi-campus family
  // (flagship + branches). 1 for standalone schools and any school not
  // in the frozen family config. Spec:
  // feature-branch-campus-suppression.md.
  family_size: number;
}

export interface SchoolsForCareerResponse {
  mode: LeaderboardMode;
  soc_code: string;
  occupation_title: string;
  cipcode: string | null;
  program_name: string | null;
  rows: SchoolForCareerRow[];
  anchor_in_top_n: boolean;
  total_qualifying_programs: number;
  // When the caller passed `anchor_stat_ern` + `anchor_stat_roi` and the
  // (unitid, cipcode) is absent from the filtered universe, this carries
  // the rank counted against `total_qualifying_programs`. Frontend uses
  // it to render a synthetic anchor row from build data.
  anchor_estimated_rank: number | null;
  confidence_filter_applied: ConfidenceTier;
  state_filter_applied: string | null;
  min_program_confidence_applied: ConfidenceTier;
  generated_at: string;
}

export interface Build {
  build_id: string;
  created_at: string;
  school_name: string;
  unitid: number;
  major_text: string;
  cipcode: string;
  program_name: string;
  effort: string;
  loan_pct: number;
  career: CareerOutcome;
  gauntlet: GauntletResult;
  branches: CareerBranch[];
  skill_recs: SkillRec[];
  guidance: string;
  skills_crafted: AppliedSkill[];
  skill_pool: AppliedSkill[];
  next_steps: string;
  horizonIndex?: number;    // 0..47 inclusive, locked at first /app/save view
  profile_name?: string;
  parent_build_id?: string | null;
  home_state?: string | null;
  animal_emoji?: string | null;
}
