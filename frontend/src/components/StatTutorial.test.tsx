import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { StatTutorial } from "./StatTutorial";

/**
 * StatTutorial tests
 *
 * Verifies the user's escape hatches (Skip) and happy path (Next x5 → Got it).
 * These call onComplete — the parent is what owns hasSeenStatTutorial, so
 * "did onComplete fire" is the real contract.
 */

const STATS = { ern: 7, roi: 6, res: 5, grw: 8, hmn: 4 };

describe("StatTutorial", () => {
  it("renders the first stat on mount", () => {
    render(<StatTutorial stats={STATS} onComplete={vi.fn()} />);
    expect(screen.getByText("Earning Power")).toBeInTheDocument();
    expect(screen.getByText("(ERN)")).toBeInTheDocument();
    // First stat should show "Next →", not "Got it"
    expect(
      screen.getByRole("button", { name: "Next stat" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Got it" }),
    ).not.toBeInTheDocument();
  });

  it("Skip button calls onComplete immediately", () => {
    const onComplete = vi.fn();
    render(<StatTutorial stats={STATS} onComplete={onComplete} />);
    fireEvent.click(screen.getByRole("button", { name: "Skip tutorial" }));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("advances through all 5 stats and calls onComplete on final 'Got it'", async () => {
    const onComplete = vi.fn();
    render(<StatTutorial stats={STATS} onComplete={onComplete} />);

    // AnimatePresence mode="wait" defers rendering the next step until the
    // previous exit animation completes, so we use findByRole (which waits)
    // to detect the label transition. The "Next stat" → "Got it" aria-label
    // flip is the cleanest observable signal of reaching the final step.
    fireEvent.click(screen.getByRole("button", { name: "Next stat" })); // ERN -> ROI
    fireEvent.click(await screen.findByRole("button", { name: "Next stat" })); // ROI -> RES
    fireEvent.click(await screen.findByRole("button", { name: "Next stat" })); // RES -> GRW
    fireEvent.click(await screen.findByRole("button", { name: "Next stat" })); // GRW -> HMN

    // On the last step, "Next stat" is replaced by "Got it".
    const gotIt = await screen.findByRole("button", { name: "Got it" });
    expect(onComplete).not.toHaveBeenCalled();
    fireEvent.click(gotIt);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
