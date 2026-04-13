export type EffortLevel = "working" | "balanced" | "all_in";

export interface SchoolSelection {
  unitid: number;
  name: string;
  institutionControl: string | null;
}

export interface MajorSelection {
  cipCode: string;
  cipTitle: string;
  rawText: string;
  careersPreview: string[];
  substitutionApplied: boolean;
}

export interface EffortSelection {
  level: EffortLevel;
  percentile: 25 | 50 | 75;
  ernShift: -1 | 0 | 1;
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
}
