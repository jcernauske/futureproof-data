/**
 * Build API client. Uses existing apiPost helper.
 * Mock fallback via VITE_USE_MOCK_API env var.
 *
 * Backend endpoints (from backend/app/routers/builds.py):
 *   POST /build/outcomes  → CareerOutcome[]
 *   POST /build/tier      → TieredCareers
 *   POST /build           → Build (full orchestration)
 */

import { apiPost } from "@/api/client";
import { mockGetTieredCareers, mockCreateBuild, mockGetOutcomes } from "@/api/mockBuild";
import type { Build, CareerOutcome, TieredCareers } from "@/types/build";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function getOutcomes(
  unitid: number,
  cipcode: string,
  effort: string,
  loanPct: number,
  studentMajor?: string,
): Promise<CareerOutcome[]> {
  if (USE_MOCK) return mockGetOutcomes();
  return apiPost<CareerOutcome[]>("/build/outcomes", {
    unitid,
    cipcode,
    effort,
    loan_pct: loanPct,
    student_major: studentMajor ?? null,
  });
}

/**
 * Map backend tier keys to frontend-expected keys.
 * Backend uses: "Common paths", "Less common but realistic", "Stretch paths", "All career paths"
 * Frontend uses: common, less_common, stretch
 */
function normalizeTiers(raw: Record<string, CareerOutcome[]>): TieredCareers {
  const result: TieredCareers = { common: [], less_common: [], stretch: [] };
  for (const [key, careers] of Object.entries(raw)) {
    const k = key.toLowerCase();
    if (k.includes("common") && !k.includes("less") && !k.includes("realistic")) {
      result.common.push(...careers);
    } else if (k.includes("less") || k.includes("realistic")) {
      result.less_common.push(...careers);
    } else if (k.includes("stretch")) {
      result.stretch.push(...careers);
    } else {
      // Fallback tier ("All career paths" or unknown) → put in common
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
  });
}
