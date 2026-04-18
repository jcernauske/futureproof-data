/**
 * TypeScript types mirroring backend/app/models/career_pick.py.
 * Shapes match what GET /career-pick/chips and POST /career-pick/ask
 * return verbatim.
 */

export interface CareerPickChip {
  id: string;
  label: string;
  elevated: boolean;
  terminal_title: string | null;
}

export interface AskCareerPickRequest {
  chip_id: string;
  cipcode: string;
  major_text: string;
  soc_codes: string[];
  selected_soc?: string | null;
  terminal_title?: string | null;
}

export interface AskCareerPickResponse {
  chip_id: string;
  answer: string;
  fallback_fired: boolean;
}
