import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BossBand } from "./BossBand";
import type { AppliedSkill, BossFightResult } from "@/types/build";

vi.mock("@/api/gauntlet", () => ({
  rerollFight: vi.fn(),
  getFightWrapup: vi.fn(),
}));

function makeFight(overrides: Partial<BossFightResult> = {}): BossFightResult {
  return {
    boss: "loans",
    label: "Pay Your Loans",
    result: "lose",
    raw_score: 8,
    threshold_win: 14,
    threshold_draw: 10,
    reason: "Debt load is high.",
    narrative: "Loans are the main pressure point.",
    rerolled: false,
    reroll_count: 0,
    original_result: null,
    original_raw_score: null,
    applied_skill_titles: [],
    ...overrides,
  };
}

function makeSkill(overrides: Partial<AppliedSkill> = {}): AppliedSkill {
  return {
    id: "skill-1",
    title: "Scholarship Sprint",
    rationale: "Cut the financed amount.",
    targets: ["loans"],
    delta_ern: 0,
    delta_roi: 1,
    delta_res: 0,
    delta_grw: 0,
    delta_burnout_raw: 0,
    delta_ceiling_raw: 0,
    delta_loans_raw: -1,
    ...overrides,
  };
}

function renderBand(props: {
  fight?: BossFightResult;
  skillPool?: AppliedSkill[];
  skillPoolLoading?: boolean;
}) {
  return render(
    <BossBand
      fight={props.fight ?? makeFight()}
      buildId="build-1"
      playerEmoji="*"
      playerName="Alex"
      skillPool={props.skillPool ?? []}
      skillPoolLoading={props.skillPoolLoading}
      onRerollComplete={() => {}}
      onSkillsConsumed={() => {}}
      isRevealed
      isSealed={false}
      isVsActive={false}
      isVsDone
      isSealedVisible={false}
    />,
  );
}

describe("BossBand skill pool loading", () => {
  it("shows a skill loading panel when skills have not arrived for a losing fight", () => {
    renderBand({ skillPoolLoading: true });

    expect(screen.getByTestId("skill-pool-loading-loans")).toBeInTheDocument();
    expect(screen.getByText("Researching skills to help you win…")).toBeInTheDocument();
  });

  it("hides the loading panel once matching skills are available", () => {
    renderBand({ skillPoolLoading: true, skillPool: [makeSkill()] });

    expect(screen.queryByTestId("skill-pool-loading-loans")).not.toBeInTheDocument();
    expect(screen.getByText("Equip Skills")).toBeInTheDocument();
  });
});
