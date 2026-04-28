/**
 * Menu (Screen 10) API client.
 *
 * Endpoints (resolved by architect 2026-04-16):
 *   GET  /builds?profile_name=X        → { builds: BuildSummary[] }
 *   POST /builds/compare               → { builds, stats, bosses }
 *   POST /build/{build_id}/chat        → { response }   (guidance_router.py:19)
 *
 * Mock fallback via VITE_USE_MOCK_API.
 */

import { apiGet, apiPost } from "@/api/client";
import {
  mockListBuilds,
  mockCompareBuilds,
  mockChat,
} from "@/api/mockMenu";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export interface BuildSummary {
  build_id: string;
  created_at: string;
  school_name: string;
  major_text: string;
  career_title: string;
  ern: number | null;
  roi: number | null;
  res: number | null;
  grw: number | null;
  hmn: number | null;
  wins: number;
  losses: number;
  draws: number;
  profile_name: string;
  animal_emoji: string | null;
}

export interface CompareBuild {
  build_id: string;
  label: string;
  career: string;
  soc_code: string;
  profile_name: string;
  animal_emoji: string | null;
  school_name: string;
  major_text: string;
  effort: string;
  loan_pct: number;
  median_annual_wage: number | null;
  net_price_annual: number | null;
  modeled_total_debt: number | null;
  tuition_annual: number | null;
  is_out_of_state: boolean;
}

export interface CompareStatRow {
  label: string;
  values: (number | null)[];
}

export interface CompareBossRow {
  label: string;
  boss_id: string;
  values: string[];
  skill_counts: number[];
  original_values: string[];
}

export interface CompareBranchBuild {
  build_id: string;
  career: string;
  destinations: {
    to_title: string;
    to_soc: string;
    delta_ern: number | null;
    delta_grw: number | null;
  }[];
}

export interface CompareResult {
  builds: CompareBuild[];
  stats: CompareStatRow[];
  bosses: CompareBossRow[];
  branches: CompareBranchBuild[];
}

export interface CompareInsights {
  money_insight: string | null;
  compare_summary: string | null;
}

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export async function listBuilds(profileName?: string): Promise<BuildSummary[]> {
  if (USE_MOCK) return mockListBuilds(profileName ?? "");
  const query = profileName
    ? `?profile_name=${encodeURIComponent(profileName)}`
    : "";
  const res = await apiGet<{ builds: BuildSummary[] }>(`/builds${query}`);
  return res.builds;
}

export async function compareBuilds(buildIds: string[]): Promise<CompareResult> {
  if (USE_MOCK) return mockCompareBuilds(buildIds);
  return apiPost<CompareResult>("/builds/compare", { build_ids: buildIds });
}

export async function compareInsights(buildIds: string[]): Promise<CompareInsights> {
  if (USE_MOCK) return { money_insight: null, compare_summary: null };
  return apiPost<CompareInsights>("/builds/compare-insights", { build_ids: buildIds });
}

export async function sendChat(
  buildId: string,
  message: string,
  history: ChatHistoryItem[],
  locale?: string,
): Promise<string> {
  if (USE_MOCK) return mockChat(message, history);
  const res = await apiPost<{ response: string }>(
    `/build/${encodeURIComponent(buildId)}/chat`,
    { message, history, locale: locale ?? undefined },
  );
  return res.response;
}
