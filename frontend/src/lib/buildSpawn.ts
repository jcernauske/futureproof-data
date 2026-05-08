/**
 * Build-spawn helper for the leaderboard "build at this school" affordance.
 *
 * Called from CompareSchoolsPanel when a student clicks a row to spawn a
 * fresh build at the chosen (school, major) for the same career. Inherits
 * effort + loan_pct from the current build, sets all the relevant stores,
 * fires the streaming build, and falls back to the blocking endpoint on
 * stream failure. The student is already on `/my-build`; isBuilding flips
 * true so the loading screen renders, then the new build settles.
 *
 * The original build is preserved server-side (auto-saved on skeleton) and
 * remains visible in the /builds menu — fresh-build, not switch.
 *
 * Mirrors the runBuild() logic in BuildResultsScreen.tsx but is callable
 * from anywhere a SchoolForCareerRow + current-build context are available.
 */

import { createBuild, createBuildStream } from "@/api/build";
import type { BuildParams, BuildStreamEvent } from "@/api/build";
import { fireCheckpoint } from "@/lib/checkpoint";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useBuildsCountStore } from "@/store/buildsCountStore";
import type {
  Build,
  CareerOutcome,
  SchoolForCareerRow,
} from "@/types/build";
import type { AppLocale } from "@/i18n/locales";
import type { EffortSelection, LoanSelection } from "@/types/buildInput";

interface SpawnContext {
  profileName: string;
  effort: EffortSelection;
  loans: LoanSelection;
  homeState: string | null;
  animalEmoji: string | null;
  locale: AppLocale;
}

function publishedCost4yrForRow(
  row: SchoolForCareerRow,
  homeState: string | null,
): number | null {
  const coa = row.cost_of_attendance_annual;
  if (coa === null || coa <= 0) return null;
  if (!row.institution_control?.startsWith("Public")) return coa * 4;
  if (!homeState || !row.state_abbr) return coa * 4;
  if (homeState === row.state_abbr) return coa * 4;
  const inState = row.tuition_in_state;
  const outState = row.tuition_out_of_state;
  if (inState === null || outState === null) return coa * 4;
  const gap = outState - inState;
  return gap > 0 ? (coa + gap) * 4 : coa * 4;
}

/**
 * Build a minimal CareerOutcome from a leaderboard row. Most fields default
 * to null/[] — the streaming build response replaces the entire object on
 * skeleton, so we only need enough to satisfy the type and feed
 * runBuild's params (which only reads soc_code + occupation_title).
 */
function rowToCareerOutcome(row: SchoolForCareerRow): CareerOutcome {
  return {
    unitid: row.unitid,
    institution_name: row.institution_name,
    cipcode: row.cipcode,
    program_name: row.program_name,
    soc_code: row.soc_code,
    occupation_title: row.occupation_title,
    soc_major_group_name: null,
    median_annual_wage: null,
    wage_p10: null,
    wage_p25: null,
    wage_p75: null,
    wage_p90: null,
    earnings_1yr_median: row.earnings_1yr_median,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    work_experience_code: null,
    net_price_annual: row.net_price_annual,
    cost_of_attendance_annual: row.cost_of_attendance_annual,
    published_cost_4yr: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: row.institution_control,
    tuition_in_state: row.tuition_in_state,
    tuition_out_of_state: row.tuition_out_of_state,
    is_out_of_state: false,
    room_board_on_campus: null,
    stats: { ern: row.stat_ern, roi: row.stat_roi, res: null, grw: null, aura: null },
    bosses: { ai: null, loans: null, market: null, burnout: null, ceiling: null },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: null,
    overall_confidence: row.overall_confidence,
    match_quality: row.match_quality,
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    loan_pct: 1.0,
  };
}

export async function spawnBuildFromRow(
  row: SchoolForCareerRow,
  ctx: SpawnContext,
): Promise<void> {
  const publishedCost4yr = publishedCost4yrForRow(row, ctx.homeState);
  const buildInputStore = useBuildInputStore.getState();
  const buildStore = useBuildStore.getState();

  // 1. Update buildInputStore so the nav guard on /my-build stays satisfied
  //    and a subsequent "Adjust effort & loans" navigates back into a sane
  //    Set Your Course state.
  buildInputStore.setSchool({
    unitid: row.unitid,
    name: row.institution_name,
    institutionControl: row.institution_control,
    stateAbbr: row.state_abbr,
    netPriceAnnual: row.net_price_annual,
    costOfAttendanceAnnual: row.cost_of_attendance_annual,
    tuitionInState: row.tuition_in_state,
    tuitionOutOfState: row.tuition_out_of_state,
  });
  buildInputStore.setMajor({
    cipCode: row.cipcode,
    cipTitle: row.program_name,
    rawText: row.program_name,
    careersPreview: [],
    substitutionApplied: false,
    parentCip: "",
  });
  // Effort + loans: carry over from current build (they're already in store).

  // 2. Reset buildStore for a fresh build.
  buildStore.setBuild(null as unknown as Build);
  buildStore.setSelectedCareer(rowToCareerOutcome(row));
  buildStore.setIsBuilding(true);

  // 3. Fire the streaming build with the same param shape runBuild uses.
  const params: BuildParams = {
    profile_name: ctx.profileName,
    school_name: row.institution_name,
    unitid: row.unitid,
    cipcode: row.cipcode,
    cip_title: row.program_name,
    major_text: row.program_name,
    effort: ctx.effort.level,
    loan_pct: ctx.loans.percentage / 100,
    selected_soc: row.soc_code,
    selected_title: row.occupation_title,
    student_major: row.program_name,
    student_cip: null,
    home_state: ctx.homeState,
    school_state: row.state_abbr,
    published_cost_4yr: publishedCost4yr,
    animal_emoji: ctx.animalEmoji,
    locale: ctx.locale,
    // Branch-spawned builds re-enter the same SOC the user clicked
    // (no chip flow, no resolved intent). Empty list — backend skips
    // SOC expansion and uses the crosswalk verbatim.
    intent_keywords: [],
  };

  const onEvent = (event: BuildStreamEvent) => {
    switch (event.type) {
      case "skeleton":
        buildStore.setBuild(event.build);
        buildStore.setIsBuilding(false);
        useBuildsCountStore.getState().refresh();
        fireCheckpoint("/my-build");
        break;
      case "boss_narrative": {
        const current = useBuildStore.getState().build;
        if (!current) return;
        useBuildStore.getState().updateBuild((prev) => ({
          ...prev,
          gauntlet: {
            ...prev.gauntlet,
            fights: prev.gauntlet.fights.map((f) =>
              f.boss === event.boss_id ? { ...f, narrative: event.narrative } : f,
            ),
          },
        }));
        break;
      }
      case "skill_recs":
        useBuildStore.getState().updateBuild((prev) => ({
          ...prev,
          skill_recs: event.recs,
        }));
        break;
      case "skill_pool":
        useBuildStore.getState().updateBuild((prev) => ({
          ...prev,
          skill_pool: event.pool,
        }));
        break;
      case "guidance":
        useBuildStore.getState().updateBuild((prev) => ({
          ...prev,
          guidance: event.narrative,
        }));
        break;
      case "done":
        break;
    }
  };

  try {
    await createBuildStream(params, onEvent);
  } catch {
    // Stream failed — fall back to blocking build.
    try {
      const result = await createBuild(
        ctx.profileName,
        row.institution_name,
        row.unitid,
        row.cipcode,
        row.program_name,
        row.program_name,
        ctx.effort.level,
        ctx.loans.percentage / 100,
        row.soc_code,
        row.occupation_title,
        row.program_name,
        undefined,
        ctx.homeState ?? undefined,
        row.state_abbr ?? undefined,
        publishedCost4yr,
        ctx.animalEmoji ?? undefined,
        ctx.locale,
      );
      buildStore.setBuild(result);
      buildStore.setIsBuilding(false);
      useBuildsCountStore.getState().refresh();
      fireCheckpoint("/my-build");
    } catch (err) {
      buildStore.setIsBuilding(false);
      throw err;
    }
  }
}
