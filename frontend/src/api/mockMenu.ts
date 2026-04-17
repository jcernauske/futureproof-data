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
    hmn: 5,
    wins: 4,
    losses: 0,
    draws: 1,
    profile_name: "Wandering Otter",
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
    hmn: 8,
    wins: 3,
    losses: 1,
    draws: 1,
    profile_name: "Wandering Otter",
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
    hmn: 9,
    wins: 5,
    losses: 0,
    draws: 0,
    profile_name: "Wandering Otter",
  },
];

export async function mockListBuilds(_profileName: string): Promise<BuildSummary[]> {
  await delay(250);
  return SUMMARIES;
}

export async function mockCompareBuilds(buildIds: string[]): Promise<CompareResult> {
  await delay(450);
  const picks = SUMMARIES.filter((s) => buildIds.includes(s.build_id));
  return {
    builds: picks.map((b) => ({
      build_id: b.build_id,
      label: `${b.school_name} — ${b.major_text}`,
      career: b.career_title,
    })),
    stats: [
      { label: "ERN", values: picks.map((b) => b.ern) },
      { label: "ROI", values: picks.map((b) => b.roi) },
      { label: "RES", values: picks.map((b) => b.res) },
      { label: "GRW", values: picks.map((b) => b.grw) },
      { label: "HMN", values: picks.map((b) => b.hmn) },
    ],
    bosses: [
      { label: "AI", values: bossOutcomes(picks, "ai") },
      { label: "Loans", values: bossOutcomes(picks, "loans") },
      { label: "Market", values: bossOutcomes(picks, "market") },
      { label: "Burnout", values: bossOutcomes(picks, "burnout") },
      { label: "Ceiling", values: bossOutcomes(picks, "ceiling") },
    ],
  };
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
  "A minor in something human-edge-heavy (writing, design, ethics) would lift your HMN stat by 1–2 and gives you a hedge against the AI boss. It won't move ERN much, but the pentagon shape becomes more balanced — better against future shocks.",
];

export async function mockChat(_message: string, history: ChatHistoryItem[]): Promise<string> {
  await delay(800);
  const idx = history.filter((h) => h.role === "assistant").length % STARTER_RESPONSES.length;
  return STARTER_RESPONSES[idx]!;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
