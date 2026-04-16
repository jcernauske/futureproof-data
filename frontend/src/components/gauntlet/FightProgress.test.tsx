import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FightProgress } from "./FightProgress";
import type { BossFightResult } from "@/types/build";

/**
 * FightProgress tests
 *
 * The FightProgress component renders 5 circles (one per boss) showing:
 * - Resolved fights: colored by result (win=thrive, lose=alert, draw=caution)
 * - Current fight: pulsing with boss-specific color
 * - Upcoming fights: neutral surface color
 *
 * The component uses BOSS_ORDER for fight sequence, so it always renders
 * exactly 5 circles regardless of how many fights are passed in.
 */

function makeFight(
  boss: BossFightResult["boss"],
  result: BossFightResult["result"],
): BossFightResult {
  return {
    boss,
    label: `Fight ${boss}`,
    result,
    raw_score: 6,
    threshold_win: 5,
    threshold_draw: 3,
    reason: "test reason",
    narrative: "test narrative",
    rerolled: false,
    reroll_count: 0,
    original_result: null,
    original_raw_score: null,
  };
}

describe("FightProgress", () => {
  it("renders exactly 5 progress circles", () => {
    render(
      <FightProgress fights={[]} currentFightIndex={0} isGauntletActive={true} />,
    );

    const nav = screen.getByRole("navigation");
    // Each circle is a div inside the nav
    const circles = nav.querySelectorAll("div");
    expect(circles.length).toBe(5);
  });

  it("labels current fight as current", () => {
    render(
      <FightProgress
        fights={[]}
        currentFightIndex={2}
        isGauntletActive={true}
      />,
    );

    // Third boss (market, index 2) should be labeled "current"
    expect(
      screen.getByLabelText(/fight the market.*current/i),
    ).toBeInTheDocument();
  });

  it("labels resolved fights with their result", () => {
    const fights = [
      makeFight("ai", "win"),
      makeFight("loans", "lose"),
    ];

    render(
      <FightProgress
        fights={fights}
        currentFightIndex={2}
        isGauntletActive={true}
      />,
    );

    expect(screen.getByLabelText(/fight ai.*win/i)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/student loans.*lose/i),
    ).toBeInTheDocument();
  });

  it("labels upcoming fights as upcoming", () => {
    render(
      <FightProgress
        fights={[makeFight("ai", "win")]}
        currentFightIndex={1}
        isGauntletActive={true}
      />,
    );

    // Fights after index 1 should be upcoming
    expect(
      screen.getByLabelText(/fight the market.*upcoming/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/fight burnout.*upcoming/i),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/fight the ceiling.*upcoming/i),
    ).toBeInTheDocument();
  });

  it("shows correct progress aria-label", () => {
    render(
      <FightProgress fights={[]} currentFightIndex={3} isGauntletActive={true} />,
    );

    expect(
      screen.getByLabelText(/boss fight progress: 4 of 5/i),
    ).toBeInTheDocument();
  });

  it("all fights show results when gauntlet is inactive", () => {
    const fights = [
      makeFight("ai", "win"),
      makeFight("loans", "lose"),
      makeFight("market", "draw"),
      makeFight("burnout", "win"),
      makeFight("ceiling", "win"),
    ];

    render(
      <FightProgress
        fights={fights}
        currentFightIndex={0}
        isGauntletActive={false}
      />,
    );

    // When gauntlet is inactive, all fights are resolved
    expect(screen.getByLabelText(/fight ai.*win/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/student loans.*lose/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fight the market.*draw/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fight burnout.*win/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/fight the ceiling.*win/i)).toBeInTheDocument();
  });

  it("applies result color classes to resolved fight circles", () => {
    const fights = [makeFight("ai", "win"), makeFight("loans", "lose")];

    render(
      <FightProgress
        fights={fights}
        currentFightIndex={2}
        isGauntletActive={true}
      />,
    );

    const winCircle = screen.getByLabelText(/fight ai.*win/i);
    expect(winCircle.className).toMatch(/accent-thrive/);

    const loseCircle = screen.getByLabelText(/student loans.*lose/i);
    expect(loseCircle.className).toMatch(/accent-alert/);
  });

  it("applies surface color to upcoming fight circles", () => {
    render(
      <FightProgress fights={[]} currentFightIndex={0} isGauntletActive={true} />,
    );

    // Index 1-4 are upcoming (not current, not resolved)
    const upcoming = screen.getByLabelText(/student loans.*upcoming/i);
    expect(upcoming.className).toMatch(/bp-surface/);
  });
});
