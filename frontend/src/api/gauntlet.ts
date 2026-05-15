import { apiPost } from "@/api/client";
import { mockRerollFight } from "@/api/mockGauntlet";
import type { BossFightResult, BossId } from "@/types/build";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";

export async function rerollFight(
  buildId: string,
  bossId: BossId,
  skillIds: string[],
): Promise<BossFightResult> {
  if (USE_MOCK) return mockRerollFight(bossId, skillIds);
  return apiPost<BossFightResult>(`/build/${buildId}/reroll`, {
    boss_id: bossId,
    skill_ids: skillIds,
  });
}

export async function getFightWrapup(
  buildId: string,
  bossId: BossId,
  allSkillTitles: string[],
  allNarratives: string[],
): Promise<string> {
  const res = await apiPost<{ narrative: string }>(`/build/${buildId}/wrapup`, {
    boss_id: bossId,
    all_skill_titles: allSkillTitles,
    all_narratives: allNarratives,
  });
  return res.narrative;
}
