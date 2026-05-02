/**
 * Per-tool label translation map for `<GemmaTrace>`.
 *
 * The pedagogical view of each tool-call row reads from this map: the
 * row's friendly sentence comes from `hint(args)`, the icon comes from
 * `resolveTraceIcon(icon)`, and the screen-reader announcement uses
 * `label`.
 *
 * Keeps the translation layer in TypeScript (Decision #5) so the
 * backend stays a faithful telemetry source and the frontend can
 * localize labels alongside `i18n/strings.ts` later.
 *
 * The 5 entries here match `_TOOLS` in
 * `backend/app/services/ask_gemma.py`. Adding new tools later (e.g.
 * web_search if `feature-agentic-school-research.md` is revived) is a
 * map-entry addition, not a refactor.
 */

import type { ToolLabel } from "@/types/gemmaTrace";

function strArg(args: Record<string, unknown>, key: string): string {
  const v = args[key];
  return typeof v === "string" ? v : "";
}

function numArg(args: Record<string, unknown>, key: string): string {
  const v = args[key];
  if (typeof v === "number") return String(v);
  if (typeof v === "string") return v;
  return "";
}

export const TOOL_LABEL_MAP: Record<string, ToolLabel> = {
  get_career_paths: {
    label: "Career outcomes lookup",
    icon: "IconCareerCompass",
    hint: (args) => {
      const major = strArg(args, "student_major");
      const cip = strArg(args, "cipcode") || strArg(args, "student_cip");
      const unitid = numArg(args, "unitid");
      // School and major slots are populated when the caller hands them
      // through; we never make up labels here. School name is rarely
      // in the args (the loop is school-scoped); fall back to the CIP
      // / unitid identifiers in monospace-feeling parens.
      if (major) {
        return `Looking up career outcomes for ${major}.`;
      }
      if (cip && unitid) {
        return `Looking up career outcomes for program ${cip} at school ${unitid}.`;
      }
      if (cip) {
        return `Looking up career outcomes for program ${cip}.`;
      }
      return "Looking up career outcomes.";
    },
  },

  get_occupation_data: {
    label: "Occupation lookup",
    icon: "IconBriefcaseStack",
    hint: (args) => {
      const soc = strArg(args, "soc_code");
      if (soc) {
        return `Pulling BLS data for occupation ${soc}.`;
      }
      return "Pulling BLS occupation data.";
    },
  },

  get_regional_price_parity: {
    label: "Cost-of-living lookup",
    icon: "IconMapPin",
    hint: (args) => {
      const state = strArg(args, "state") || strArg(args, "state_fips");
      if (state) {
        return `Checking cost-of-living for ${state}.`;
      }
      return "Checking regional cost-of-living.";
    },
  },

  compare_purchasing_power: {
    label: "Purchasing-power comparison",
    icon: "IconScale",
    hint: (args) => {
      const a =
        strArg(args, "state_a") ||
        strArg(args, "from_state") ||
        strArg(args, "origin");
      const b =
        strArg(args, "state_b") ||
        strArg(args, "to_state") ||
        strArg(args, "destination");
      if (a && b) {
        return `Comparing purchasing power between ${a} and ${b}.`;
      }
      if (a) {
        return `Comparing purchasing power from ${a}.`;
      }
      return "Comparing purchasing power across states.";
    },
  },

  get_career_branches: {
    label: "Career branches lookup",
    icon: "IconBranch",
    hint: (args) => {
      const soc = strArg(args, "soc_code") || strArg(args, "from_soc");
      if (soc) {
        return `Looking up career branches from ${soc}.`;
      }
      return "Looking up career branches.";
    },
  },

  get_schools_for_career: {
    label: "Schools-for-career leaderboard",
    icon: "IconMortarboard",
    hint: (args) => {
      const soc = strArg(args, "soc_code");
      const cip = strArg(args, "cipcode");
      const state = strArg(args, "state_abbr");
      if (state && soc) {
        return `Ranking schools in ${state} for occupation ${soc}.`;
      }
      if (cip && soc) {
        return `Ranking schools for program ${cip} leading to occupation ${soc}.`;
      }
      if (soc) {
        return `Ranking schools that lead to occupation ${soc}.`;
      }
      return "Ranking schools for this career.";
    },
  },
};

/**
 * Default label for unknown tool names. Per Decision #15 (forward-
 * compat), unknown tools must render a sensible row rather than crash
 * the trace. Today all 5 tools are mapped — this fallback exists for
 * resilience only.
 */
export const DEFAULT_TOOL_LABEL: ToolLabel = {
  label: "Tool call",
  icon: "IconWrench",
  hint: () => "Gemma is consulting a tool.",
};

export function resolveToolLabel(toolName: string): ToolLabel {
  return TOOL_LABEL_MAP[toolName] ?? DEFAULT_TOOL_LABEL;
}
