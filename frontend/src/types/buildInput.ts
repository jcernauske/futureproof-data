export type EffortLevel = "working_hard" | "working" | "balanced" | "focused" | "all_in";

export interface SchoolSelection {
  unitid: number;
  name: string;
  institutionControl: string | null;
  netPriceAnnual: number | null;
  costOfAttendanceAnnual: number | null;
}

export interface MajorSelection {
  cipCode: string;
  cipTitle: string;
  rawText: string;
  careersPreview: string[];
  substitutionApplied: boolean;
  // School's reported broad same-family CIP when substitution will apply
  // (from IntentResult.parent_cip). Empty string when the school reports
  // the student's major directly. Every backend call that looks up a
  // school row (build/outcomes, build/tier, build, career-pick/chips)
  // must send `parentCip || cipCode` — the substitution branch in the
  // MCP handler keys off the school's broad cip, not the matched leaf.
  parentCip: string;
}

export interface EffortSelection {
  level: EffortLevel;
  percentile: 10 | 25 | 50 | 75 | 90;
  ernShift: -2 | -1 | 0 | 1 | 2;
}

export interface LoanSelection {
  percentage: 0 | 25 | 50 | 75 | 100;
}

export interface BuildInput {
  school: SchoolSelection;
  major: MajorSelection;
  effort: EffortSelection;
  loans: LoanSelection;
  profileName: string;
}

export interface SchoolSearchResult {
  unitid: number;
  institution_name: string;
  institution_control: string | null;
  net_price_annual: number | null;
  cost_of_attendance_annual: number | null;
}

export interface ProgramResult {
  unitid: number;
  institution_name: string;
  cipcode: string;
  program_name: string;
  cip_family_name: string | null;
  earnings_1yr_median: number | null;
  debt_median: number | null;
}

export interface IntentResult {
  matched_cip: string;
  matched_title: string;
  confidence: string;
  reasoning: string;
  careers_preview: string[];
  audit_flag: string | null;
  audit_message: string | null;
  needs_clarification: boolean;
  alternatives: Array<{ cip: string; title: string; why: string }> | null;
  parent_cip: string;
  // Optional broad CIP explicitly reported by the school — separate from
  // parent_cip which is the Gemma-inferred parent. Defaults to parent_cip
  // when the backend doesn't distinguish the two. See spec §4.
  school_reported_cip4?: string;
  // Student-named sub-specialty verified by Gemma via tool call. Only set
  // through the chip-dispatch flow — never on initial resolution. Optional
  // so existing fixtures that predate the field still satisfy the shape.
  // See spec §2 Decision #16.
  confirmed_focus?: string | null;
}

/**
 * Community Suggestions surface — ranked crowd signals keyed by
 * (unitid, input_normalized). See spec §4 "Community Suggestions Surface".
 */
export interface Suggestion {
  clicked_soc: string;
  clicked_career_title: string;
  canonical_cip4: string;
  count: number;
}
