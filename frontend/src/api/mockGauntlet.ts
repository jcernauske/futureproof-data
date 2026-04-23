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

export async function mockGetNextSteps(): Promise<string> {
  await delay(2500);

  return `## Questions to Ask Your Guidance Counselor

1. What AP or dual-enrollment courses align with this career path?
2. Are there internship programs at local companies in this field?
3. What scholarship opportunities exist for students pursuing this major?
4. Can you connect me with alumni who work in this occupation?

## Questions to Ask College Recruiters

1. What percentage of graduates from this program find related employment within a year?
2. Does the program offer co-op or work-study opportunities?
3. What industry partnerships does the department maintain?
4. How does the program incorporate hands-on experience?

## Things to Verify on Your Own

1. Check the BLS Occupational Outlook Handbook for current salary and growth data
2. Search LinkedIn for professionals with this job title — look at their education paths
3. Review Glassdoor for employee satisfaction ratings in this field
4. Research whether this career is available in the region where you want to live

## Points to Discuss with Your Parents

1. The median starting salary for this career is competitive with the loan burden
2. This field has strong growth projections over the next decade
3. The skills learned in this major transfer to adjacent careers if plans change
4. Here are the specific risks identified and the strategies to address them`;
}
