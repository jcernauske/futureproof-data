import { apiGet } from "@/api/client";
import type {
  ConfidenceTier,
  SchoolsForCareerResponse,
} from "@/types/build";

interface FetchOpts {
  limit?: number;
  minConfidence?: ConfidenceTier;
  minProgramConfidence?: ConfidenceTier;
  stateAbbr?: string;
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
