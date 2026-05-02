/**
 * Mock handlers for Screen 10. Used when VITE_USE_MOCK_API=true.
 * Returns realistic shapes matching the FastAPI contracts.
 */

import type {
  BuildSummary,
  ChatHistoryItem,
  CompareResult,
} from "@/api/menu";

const SUMMARIES: BuildSummary[] = [
  {
    build_id: "berkeley-cs-001",
    created_at: "2026-04-12T18:30:00Z",
    school_name: "UC Berkeley",
    major_text: "Computer Science",
    career_title: "Software Developers",
    ern: 8,
    roi: 7,
    res: 4,
    grw: 9,
    aura: 5,
    wins: 4,
    losses: 0,
    draws: 1,
    profile_name: "Wandering Otter",
    animal_emoji: "🦦",
  },
  {
    build_id: "iu-bloom-mkt-001",
    created_at: "2026-04-09T14:12:00Z",
    school_name: "Indiana University Bloomington",
    major_text: "Marketing",
    career_title: "Marketing Managers",
    ern: 6,
    roi: 6,
    res: 7,
    grw: 5,
    aura: 8,
    wins: 3,
    losses: 1,
    draws: 1,
    profile_name: "Wandering Otter",
    animal_emoji: "🦦",
  },
  {
    build_id: "purdue-nursing-001",
    created_at: "2026-04-05T22:00:00Z",
    school_name: "Purdue University",
    major_text: "Nursing",
    career_title: "Registered Nurses",
    ern: 6,
    roi: 8,
    res: 9,
    grw: 7,
    aura: 9,
    wins: 5,
    losses: 0,
    draws: 0,
    profile_name: "Wandering Otter",
    animal_emoji: "🦦",
  },
];

export async function mockListBuilds(_profileName: string): Promise<BuildSummary[]> {
  await delay(250);
  return SUMMARIES;
}

const MOCK_EXTRA: Record<string, { soc_code: string; wage: number | null; cost: number | null; debt: number | null }> = {
  "berkeley-cs-001": { soc_code: "15-1252", wage: 130000, cost: 16200, debt: 32400 },
  "iu-bloom-mkt-001": { soc_code: "11-2021", wage: 140040, cost: 11400, debt: 22800 },
  "purdue-nursing-001": { soc_code: "29-1141", wage: 86070, cost: 9800, debt: 19600 },
};

const MOCK_SKILL_COUNTS: Record<string, Record<string, number>> = {
  "berkeley-cs-001": { ai: 0, loans: 0, market: 0, burnout: 1, ceiling: 0 },
  "iu-bloom-mkt-001": { ai: 1, loans: 0, market: 0, burnout: 0, ceiling: 2 },
  "purdue-nursing-001": { ai: 0, loans: 0, market: 0, burnout: 0, ceiling: 0 },
};

export async function mockCompareBuilds(buildIds: string[]): Promise<CompareResult> {
  await delay(450);
  const picks = SUMMARIES.filter((s) => buildIds.includes(s.build_id));
  return {
    builds: picks.map((b) => {
      const extra = MOCK_EXTRA[b.build_id] ?? { soc_code: "00-0000", wage: null, cost: null, debt: null };
      return {
        build_id: b.build_id,
        label: `${b.school_name} — ${b.major_text}`,
        career: b.career_title,
        soc_code: extra.soc_code,
        profile_name: b.profile_name,
        animal_emoji: b.animal_emoji,
        school_name: b.school_name,
        major_text: b.major_text,
        effort: "balanced",
        loan_pct: 0.5,
        median_annual_wage: extra.wage,
        net_price_annual: extra.cost,
        modeled_total_debt: extra.debt,
        tuition_annual: extra.cost,
        is_out_of_state: false,
        institution_control: null,
      };
    }),
    stats: [
      { label: "ERN", values: picks.map((b) => b.ern) },
      { label: "ROI", values: picks.map((b) => b.roi) },
      { label: "RES", values: picks.map((b) => b.res) },
      { label: "GRW", values: picks.map((b) => b.grw) },
      { label: "AURA", values: picks.map((b) => b.aura) },
    ],
    bosses: [
      { label: "AI", boss_id: "ai", values: bossOutcomes(picks, "ai"), skill_counts: skillCounts(picks, "ai"), original_values: bossOutcomes(picks, "ai") },
      { label: "Loans", boss_id: "loans", values: bossOutcomes(picks, "loans"), skill_counts: skillCounts(picks, "loans"), original_values: bossOutcomes(picks, "loans") },
      { label: "Market", boss_id: "market", values: bossOutcomes(picks, "market"), skill_counts: skillCounts(picks, "market"), original_values: bossOutcomes(picks, "market") },
      { label: "Burnout", boss_id: "burnout", values: bossOutcomes(picks, "burnout"), skill_counts: skillCounts(picks, "burnout"), original_values: bossOutcomes(picks, "burnout") },
      { label: "Ceiling", boss_id: "ceiling", values: bossOutcomes(picks, "ceiling"), skill_counts: skillCounts(picks, "ceiling"), original_values: bossOutcomes(picks, "ceiling") },
    ],
    branches: picks.map((b) => ({
      build_id: b.build_id,
      career: b.career_title,
      destinations: [
        { to_title: "Senior " + b.career_title, to_soc: "00-0001", delta_ern: 2, delta_grw: -1 },
        { to_title: "Director", to_soc: "00-0002", delta_ern: 3, delta_grw: 0 },
      ],
    })),
  };
}

function skillCounts(builds: BuildSummary[], boss: string): number[] {
  return builds.map((b) => MOCK_SKILL_COUNTS[b.build_id]?.[boss] ?? 0);
}

const FIXED_BOSS_RESULTS: Record<string, Record<string, string>> = {
  "berkeley-cs-001": {
    ai: "LOSE",
    loans: "WIN",
    market: "WIN",
    burnout: "DRAW",
    ceiling: "WIN",
  },
  "iu-bloom-mkt-001": {
    ai: "WIN",
    loans: "DRAW",
    market: "WIN",
    burnout: "WIN",
    ceiling: "DRAW",
  },
  "purdue-nursing-001": {
    ai: "WIN",
    loans: "WIN",
    market: "WIN",
    burnout: "LOSE",
    ceiling: "DRAW",
  },
};

function bossOutcomes(builds: BuildSummary[], boss: string): string[] {
  return builds.map((b) => FIXED_BOSS_RESULTS[b.build_id]?.[boss] ?? "—");
}

const STARTER_RESPONSES = [
  "Solid question. Based on your build, the data points to a clear tradeoff: your earning power is strong but your AI exposure is non-trivial. Internships at firms blending engineering with domain knowledge — health tech, climate tech — would harden your build against automation while keeping the salary trajectory.",
  "Looking at your stats, the in-state path keeps your ROI healthy because of net price. Out-of-state would push your modeled total debt up by roughly 60%, which moves Loans from WIN into DRAW territory. The career market is about the same in both states for this role.",
  "A minor in something human-judgment-heavy (writing, design, ethics) would lift your RES stat by 1–2 and gives you a hedge against the AI boss. It won't move ERN much, but the pentagon shape becomes more balanced — better against future shocks. AURA is institution-level so no minor can shift it.",
];

export async function mockChat(_message: string, history: ChatHistoryItem[]): Promise<string> {
  await delay(800);
  const idx = history.filter((h) => h.role === "assistant").length % STARTER_RESPONSES.length;
  return STARTER_RESPONSES[idx]!;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
