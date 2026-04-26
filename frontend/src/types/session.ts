import type { Build, CareerOutcome, TieredCareers } from "./build";

export interface CheckpointPayload {
  screen: string;
  profile_data: {
    profileName: string | null;
    animalEmoji: string | null;
    animalName: string | null;
    homeState: string | null;
    locale?: string;
  } | null;
  build_input_data: Record<string, unknown> | null;
  build_id: string | null;
  gauntlet_data: {
    phase: string;
    currentFightIndex: number;
    fightPhase: string;
    selectedSkillIds: string[];
  } | null;
  tiered_careers_data: TieredCareers | null;
  selected_career_data: CareerOutcome | null;
}

export interface SessionResponse {
  session_id: string;
  last_screen: string;
  profile_data: {
    profileName: string;
    animalEmoji: string;
    animalName: string;
    homeState: string | null;
    locale?: string;
  } | null;
  build_input_data: Record<string, unknown> | null;
  build_id: string | null;
  build: Build | null;
  gauntlet_data: {
    phase: string;
    currentFightIndex: number;
    fightPhase: string;
    selectedSkillIds: string[];
  } | null;
  tiered_careers_data: TieredCareers | null;
  selected_career_data: CareerOutcome | null;
  created_at: string;
  updated_at: string;
}
