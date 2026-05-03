/**
 * Build API client. Uses existing apiPost helper.
 * Mock fallback via VITE_USE_MOCK_API env var.
 *
 * Backend endpoints (from backend/app/routers/builds.py):
 *   POST /build/outcomes  → CareerOutcome[]
 *   POST /build/tier      → TieredCareers
 *   POST /build           → Build (full orchestration)
 */

import { apiDelete, apiGet, apiPost, formatErrorDetail } from "@/api/client";
import { mockGetTieredCareers, mockCreateBuild, mockGetOutcomes } from "@/api/mockBuild";
import type { Build, CareerOutcome, SkillRec, AppliedSkill, TieredCareers } from "@/types/build";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function getOutcomes(
  unitid: number,
  cipcode: string,
  effort: string,
  loanPct: number,
  studentMajor?: string,
  studentCip?: string,
  signal?: AbortSignal,
  intentKeywords?: string[],
  homeState?: string | null,
): Promise<CareerOutcome[]> {
  if (USE_MOCK) return mockGetOutcomes();
  return apiPost<CareerOutcome[]>(
    "/build/outcomes",
    {
      unitid,
      cipcode,
      effort,
      loan_pct: loanPct,
      student_major: studentMajor ?? null,
      student_cip: studentCip ?? null,
      intent_keywords: intentKeywords ?? [],
      home_state: homeState ?? null,
    },
    { signal },
  );
}

// Map backend tier labels to frontend keys.
// Backend ships these exact strings from /build/tier. Adding a new one?
// Extend this allowlist — silent fallback string-matching is how careers get misrouted.
const TIER_KEY_MAP: Record<string, keyof TieredCareers> = {
  "common paths": "common",
  "less common but realistic": "less_common",
  "stretch paths": "stretch",
};

function normalizeTiers(raw: Record<string, CareerOutcome[]>): TieredCareers {
  const result: TieredCareers = { common: [], less_common: [], stretch: [] };
  for (const [key, careers] of Object.entries(raw)) {
    const mapped = TIER_KEY_MAP[key.toLowerCase()];
    if (mapped) {
      result[mapped].push(...careers);
    } else if (key.toLowerCase() === "all career paths") {
      // Sentinel tier from backend fallback path — route to common for display.
      result.common.push(...careers);
    } else {
      console.warn(`[build.normalizeTiers] unknown tier key "${key}" — routing to common`);
      result.common.push(...careers);
    }
  }
  return result;
}

export async function getTieredCareers(
  outcomes: CareerOutcome[],
  schoolName: string,
  programName: string,
  cipcode: string,
  studentMajorText?: string,
  intentKeywords?: string[],
  signal?: AbortSignal,
): Promise<TieredCareers> {
  if (USE_MOCK) return mockGetTieredCareers();
  const raw = await apiPost<Record<string, CareerOutcome[]>>(
    "/build/tier",
    {
      outcomes: outcomes.map((o) => ({ ...o })),
      school_name: schoolName,
      program_name: programName,
      cipcode,
      student_major_text: studentMajorText ?? null,
      intent_keywords: intentKeywords ?? [],
    },
    { signal },
  );
  return normalizeTiers(raw);
}

export async function getBuild(buildId: string): Promise<Build> {
  return apiGet<Build>(`/build/${encodeURIComponent(buildId)}`);
}

export async function createBuild(
  profileName: string,
  schoolName: string,
  unitid: number,
  cipcode: string,
  cipTitle: string,
  majorText: string,
  effort: string,
  loanPct: number,
  selectedSoc: string,
  selectedTitle: string,
  studentMajor?: string,
  studentCip?: string,
  homeState?: string,
  schoolState?: string,
  publishedCost4yr?: number | null,
  animalEmoji?: string,
  locale?: string,
): Promise<Build> {
  if (USE_MOCK) return mockCreateBuild(selectedSoc, profileName, schoolName);
  return apiPost<Build>("/build", {
    profile_name: profileName,
    school_name: schoolName,
    unitid,
    cipcode,
    cip_title: cipTitle,
    major_text: majorText,
    effort,
    loan_pct: loanPct,
    selected_soc: selectedSoc,
    selected_title: selectedTitle,
    student_major: studentMajor ?? null,
    student_cip: studentCip ?? null,
    home_state: homeState ?? null,
    school_state: schoolState ?? null,
    published_cost_4yr: publishedCost4yr ?? null,
    animal_emoji: animalEmoji ?? null,
    locale: locale ?? "en",
  });
}

export async function deleteBuild(buildId: string): Promise<void> {
  if (USE_MOCK) return;
  await apiDelete(`/build/${encodeURIComponent(buildId)}`);
}

// --- Streaming build creation ---

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface BuildParams {
  profile_name: string;
  school_name: string;
  unitid: number;
  cipcode: string;
  cip_title: string;
  major_text: string;
  effort: string;
  loan_pct: number;
  selected_soc: string;
  selected_title: string;
  student_major: string | null;
  student_cip: string | null;
  home_state: string | null;
  school_state: string | null;
  published_cost_4yr: number | null;
  animal_emoji: string | null;
  locale: string;
}

export type BuildStreamEvent =
  | { type: "skeleton"; build: Build }
  | { type: "boss_narrative"; boss_id: string; narrative: string }
  | { type: "skill_recs"; recs: SkillRec[] }
  | { type: "skill_pool"; pool: AppliedSkill[] }
  | { type: "guidance"; narrative: string }
  | { type: "done"; build_id: string }
  | { type: "error"; detail: string };

export async function createBuildStream(
  params: BuildParams,
  onEvent: (event: BuildStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  if (USE_MOCK) {
    const build = await mockCreateBuild(
      params.selected_soc, params.profile_name, params.school_name,
    );
    onEvent({ type: "skeleton", build });
    onEvent({ type: "done", build_id: build.build_id });
    return;
  }

  const res = await fetch(`${API_BASE}/build/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
    signal,
  });

  if (!res.ok) {
    const parsed = await res.json().catch(() => ({}));
    throw new Error(formatErrorDetail(parsed, res.status));
  }

  if (!res.body) {
    throw new Error("Build stream produced no body");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split("\n\n");
      buffer = frames.pop()!;

      for (const frame of frames) {
        if (!frame.trim()) continue;
        const eventMatch = frame.match(/^event:\s*(.+)$/m);
        const dataMatch = frame.match(/^data:\s*(.+)$/m);
        if (!eventMatch || !dataMatch) continue;

        const eventType = eventMatch[1]!;
        const data = JSON.parse(dataMatch[1]!);

        switch (eventType) {
          case "skeleton":
            onEvent({ type: "skeleton", build: data as Build });
            break;
          case "boss_narrative":
            onEvent({ type: "boss_narrative", boss_id: data.boss_id, narrative: data.narrative });
            break;
          case "skill_recs":
            onEvent({ type: "skill_recs", recs: data as SkillRec[] });
            break;
          case "skill_pool":
            onEvent({ type: "skill_pool", pool: data as AppliedSkill[] });
            break;
          case "guidance":
            onEvent({ type: "guidance", narrative: data.narrative });
            break;
          case "done":
            onEvent({ type: "done", build_id: data.build_id });
            break;
          case "error":
            throw new Error(data.detail);
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // reader may already be closed
    }
  }
}
