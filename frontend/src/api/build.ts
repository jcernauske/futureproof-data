/**
 * Build API client. Uses existing apiPost helper.
 * Mock fallback via VITE_USE_MOCK_API env var.
 *
 * Backend endpoints (from backend/app/routers/builds.py):
 *   POST /build/outcomes  → CareerOutcome[]
 *   POST /build/tier      → TieredCareers
 *   POST /build           → Build (full orchestration)
 */

import { apiGet, apiPost } from "@/api/client";
import { mockGetTieredCareers, mockCreateBuild, mockGetOutcomes } from "@/api/mockBuild";
import type { Build, CareerOutcome, TieredCareers } from "@/types/build";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function getOutcomes(
  unitid: number,
  cipcode: string,
  effort: string,
  loanPct: number,
  studentMajor?: string,
  studentCip?: string,
): Promise<CareerOutcome[]> {
  if (USE_MOCK) return mockGetOutcomes();
  return apiPost<CareerOutcome[]>("/build/outcomes", {
    unitid,
    cipcode,
    effort,
    loan_pct: loanPct,
    student_major: studentMajor ?? null,
    student_cip: studentCip ?? null,
  });
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
): Promise<TieredCareers> {
  if (USE_MOCK) return mockGetTieredCareers();
  const raw = await apiPost<Record<string, CareerOutcome[]>>("/build/tier", {
    outcomes: outcomes.map((o) => ({ ...o })),
    school_name: schoolName,
    program_name: programName,
    cipcode,
  });
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
  });
}
