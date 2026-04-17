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
}

export interface CompareBuild {
  build_id: string;
  label: string;
  career: string;
}

export interface CompareStatRow {
  label: string;
  values: (number | null)[];
}

export interface CompareBossRow {
  label: string;
  values: string[];
}

export interface CompareResult {
  builds: CompareBuild[];
  stats: CompareStatRow[];
  bosses: CompareBossRow[];
}

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export async function listBuilds(profileName: string): Promise<BuildSummary[]> {
  if (USE_MOCK) return mockListBuilds(profileName);
  const res = await apiGet<{ builds: BuildSummary[] }>(
    `/builds?profile_name=${encodeURIComponent(profileName)}`,
  );
  return res.builds;
}

export async function compareBuilds(buildIds: string[]): Promise<CompareResult> {
  if (USE_MOCK) return mockCompareBuilds(buildIds);
  return apiPost<CompareResult>("/builds/compare", { build_ids: buildIds });
}

export async function sendChat(
  buildId: string,
  message: string,
  history: ChatHistoryItem[],
): Promise<string> {
  if (USE_MOCK) return mockChat(message, history);
  const res = await apiPost<{ response: string }>(
    `/build/${encodeURIComponent(buildId)}/chat`,
    { message, history },
  );
  return res.response;
}
