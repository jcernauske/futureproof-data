import { apiPost } from "@/api/client";
import { mockRerollFight, mockGetNextSteps } from "@/api/mockGauntlet";
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

export async function getNextSteps(buildId: string): Promise<string> {
  if (USE_MOCK) return mockGetNextSteps();
  const res = await apiPost<{ checklist: string }>(`/build/${buildId}/next-steps`);
  return res.checklist;
}
