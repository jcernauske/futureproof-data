/**
 * BuildCard.test.tsx (P1)
 *
 * Verifies the Save Slot Card surface contract: school, career, W/L/D
 * tally, mini pentagon present, and tap fires the onTap handler.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BuildCard } from "./BuildCard";
import type { BuildSummary } from "@/api/menu";

function makeSummary(overrides: Partial<BuildSummary> = {}): BuildSummary {
  return {
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
    losses: 1,
    draws: 2,
    profile_name: "Wandering Otter",
    ...overrides,
  };
}

describe("BuildCard", () => {
  it("renders school, major, and career text (P1)", () => {
    render(
      <BuildCard build={makeSummary()} emoji="🦦" onTap={() => {}} />,
    );

    expect(screen.getByText("UC Berkeley")).toBeInTheDocument();
    // The component composes "{major_text} · {career_title}" — match either.
    expect(screen.getByText(/Computer Science/)).toBeInTheDocument();
    expect(screen.getByText(/Software Developers/)).toBeInTheDocument();
  });

  it("renders W/L/D tally (P1)", () => {
    render(<BuildCard build={makeSummary()} emoji="🦦" onTap={() => {}} />);

    // Each digit lives in its own colored span — assert all three appear.
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders the mini pentagon SVG (P1)", () => {
    render(<BuildCard build={makeSummary()} emoji="🦦" onTap={() => {}} />);

    expect(
      screen.getByRole("img", { name: /Mini pentagon stat shape/i }),
    ).toBeInTheDocument();
  });

  it("clicking the card fires onTap (P1)", () => {
    const onTap = vi.fn();
    render(<BuildCard build={makeSummary()} emoji="🦦" onTap={onTap} />);

    fireEvent.click(screen.getByTestId("card-build-berkeley-cs-001"));
    expect(onTap).toHaveBeenCalledTimes(1);
  });

  it("aria-label combines school and career (a11y contract)", () => {
    render(<BuildCard build={makeSummary()} emoji="🦦" onTap={() => {}} />);

    expect(
      screen.getByLabelText("UC Berkeley — Software Developers"),
    ).toBeInTheDocument();
  });

  it("falls back to raw timestamp string when created_at is unparseable (saboteur)", () => {
    render(
      <BuildCard
        build={makeSummary({ created_at: "not-a-date" })}
        emoji="🦦"
        onTap={() => {}}
      />,
    );
    expect(screen.getByText("not-a-date")).toBeInTheDocument();
  });
});
