import { apiGet } from "@/api/client";
import type {
  CareerDescription,
  ConfidenceTier,
  SchoolsForCareerResponse,
} from "@/types/build";

interface FetchOpts {
  limit?: number;
  minConfidence?: ConfidenceTier;
  minProgramConfidence?: ConfidenceTier;
  stateAbbr?: string;
  // Two-letter US state code for the student's home state. When set,
  // the backend recomputes published_cost_4yr and stat_roi residency-
  // aware so the leaderboard matches the FINANCES card's "Cost (4 yr)"
  // line on /my-build (spec roi-net-lifetime-value followup).
  homeState?: string;
  buildUnitid?: number;
  buildCipcode?: string;
  // Build's stat_ern + stat_roi (0-10). When both are passed alongside
  // buildUnitid + buildCipcode, the backend computes
  // anchor_estimated_rank for builds whose CIP-substituted program isn't
  // materialized in the leaderboard universe.
  anchorStatErn?: number;
  anchorStatRoi?: number;
}

function buildQuery(opts: FetchOpts | undefined): string {
  if (!opts) return "";
  const params = new URLSearchParams();
  if (opts.limit !== undefined) params.set("limit", String(opts.limit));
  if (opts.minConfidence) params.set("min_confidence", opts.minConfidence);
  if (opts.minProgramConfidence)
    params.set("min_program_confidence", opts.minProgramConfidence);
  if (opts.stateAbbr) params.set("state_abbr", opts.stateAbbr);
  if (opts.homeState) params.set("home_state", opts.homeState);
  if (opts.buildUnitid !== undefined)
    params.set("build_unitid", String(opts.buildUnitid));
  if (opts.buildCipcode) params.set("build_cipcode", opts.buildCipcode);
  if (opts.anchorStatErn !== undefined)
    params.set("anchor_stat_ern", String(opts.anchorStatErn));
  if (opts.anchorStatRoi !== undefined)
    params.set("anchor_stat_roi", String(opts.anchorStatRoi));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchSchoolsBySoc(
  socCode: string,
  opts?: FetchOpts,
): Promise<SchoolsForCareerResponse> {
  return apiGet<SchoolsForCareerResponse>(
    `/careers/${encodeURIComponent(socCode)}/schools${buildQuery(opts)}`,
  );
}

export async function fetchSchoolsByCipAndSoc(
  cipcode: string,
  socCode: string,
  opts?: FetchOpts,
): Promise<SchoolsForCareerResponse> {
  return apiGet<SchoolsForCareerResponse>(
    `/majors/${encodeURIComponent(cipcode)}/schools/for-career/${encodeURIComponent(socCode)}${buildQuery(opts)}`,
  );
}

// GET /careers/{soc_code}/description?occupation_title=... → CareerDescription.
// Powers the structured header card on the sparkle panel for /set-your-course.
// On 502 the panel falls back to the existing freeform-chat-only behavior.
export async function fetchCareerDescription(
  socCode: string,
  occupationTitle: string,
): Promise<CareerDescription> {
  const params = new URLSearchParams({ occupation_title: occupationTitle });
  return apiGet<CareerDescription>(
    `/careers/${encodeURIComponent(socCode)}/description?${params.toString()}`,
  );
}
