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
  institution_control: string | null;
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

export interface BuildProsCons {
  build_id: string;
  pros: string[];
  cons: string[];
}

export interface ComparePivotal {
  meta_tradeoff: string;
  meta_explanation: string;
  decade_projection: string;
  pivot_question: string;
}

export interface CompareInsights {
  money_insight: string | null;
  compare_summary: string | null;
  pros_cons: BuildProsCons[] | null;
  pivotal: ComparePivotal | null;
}

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

// ---------------------------------------------------------------------------
// Ask Gemma — scope-aware chat (POST /chat/ask).
// Mirrors the backend AskScope discriminated union (models/api.py).
// ---------------------------------------------------------------------------

export type AskStatTarget = "ERN" | "ROI" | "RES" | "GRW" | "HMN";
export type AskBossTarget =
  | "ai"
  | "loans"
  | "market"
  | "burnout"
  | "ceiling";

export type AskScope =
  | { kind: "stat"; build_ids: [string]; target_id: AskStatTarget }
  | { kind: "boss"; build_ids: [string]; target_id: AskBossTarget }
  | { kind: "skill"; build_ids: [string]; target_id: string }
  | { kind: "build"; build_ids: [string]; target_id?: null }
  | { kind: "compare"; build_ids: string[]; target_id?: null }
  | { kind: "branch"; build_ids: [string]; target_id: string };

export interface AskResponse {
  response: string;
  tool_calls: { tool: string; ok: boolean; duration_ms: number }[];
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
  if (USE_MOCK) return { money_insight: null, compare_summary: null, pros_cons: null, pivotal: null };
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

export async function askGemma(
  scope: AskScope,
  message: string,
  history: ChatHistoryItem[],
  locale?: string,
): Promise<AskResponse> {
  if (USE_MOCK) {
    const text = await mockChat(message, history);
    return { response: text, tool_calls: [] };
  }
  return apiPost<AskResponse>("/chat/ask", {
    scope,
    message,
    history,
    locale: locale ?? undefined,
  });
}
