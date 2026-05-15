import type { BossFightResult, BossId } from "@/types/build";

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function mockRerollFight(
  bossId: BossId,
  _skillIds: string[],
): Promise<BossFightResult> {
  await delay(1200);

  const labels: Record<BossId, string> = {
    ai: "Fight AI",
    loans: "Student Loans",
    market: "The Market",
    burnout: "Burnout",
    ceiling: "The Ceiling",
  };

  return {
    boss: bossId,
    label: labels[bossId],
    result: "draw",
    raw_score: 4,
    threshold_win: 5,
    threshold_draw: 3,
    reason: "Skills equipped — gap narrowed but not closed.",
    narrative:
      "The skills you equipped moved the needle. You're closer to a win, but the structural gap remains. This is progress — keep building.",
    rerolled: true,
    reroll_count: 1,
    original_result: "lose",
    original_raw_score: 2,
    applied_skill_titles: ["Mock Skill"],
  };
}

