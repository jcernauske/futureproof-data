import { render, screen, fireEvent, within } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AskGemmaChipRow } from "./AskGemmaChipRow";
import type { CareerPickChip } from "@/types/careerPick";

/**
 * AskGemmaChipRow tests (P0)
 *
 * - Chips render in the order delivered by the parent (the API owns ordering).
 * - Elevated chip is styled distinctly (data-elevated=true + accent-alert
 *   class signature) and is ALWAYS first.
 * - Enter/Space on a chip invokes onChipClick.
 * - The elevated chip carries aria-describedby pointing at the elevation
 *   hint id the PARENT owns (passed in as `elevationHintId`).
 */

const ELEVATED: CareerPickChip = {
  id: "why_no_doctor",
  label: "Why don't I see 'doctor'?",
  elevated: true,
  terminal_title: "doctor",
};

const BASE_A: CareerPickChip = {
  id: "what_does_this_do",
  label: "What does this career actually do?",
  elevated: false,
  terminal_title: null,
};

const BASE_B: CareerPickChip = {
  id: "right_school_for_this",
  label: "Is this the right school for this?",
  elevated: false,
  terminal_title: null,
};

describe("AskGemmaChipRow", () => {
  it("renders chips in the order delivered by the parent", () => {
    render(
      <AskGemmaChipRow
        chips={[ELEVATED, BASE_A, BASE_B]}
        activeChipId={null}
        onChipClick={vi.fn()}
        elevationHintId="hint-test"
      />,
    );
    const chips = screen.getAllByTestId("ask-gemma-chip");
    expect(chips.map((c) => c.textContent?.trim())).toEqual([
      "Why don't I see 'doctor'?",
      "What does this career actually do?",
      "Is this the right school for this?",
    ]);
  });

  it("elevated chip is styled distinctly: data-elevated='true' + accent-alert class signature", () => {
    render(
      <AskGemmaChipRow
        chips={[ELEVATED, BASE_A]}
        activeChipId={null}
        onChipClick={vi.fn()}
        elevationHintId="hint-test"
      />,
    );
    const chips = screen.getAllByTestId("ask-gemma-chip");
    const elevated = chips[0]!;
    const nonElevated = chips[1]!;

    expect(elevated).toHaveAttribute("data-elevated", "true");
    expect(nonElevated).toHaveAttribute("data-elevated", "false");

    // accent-alert class signature — the rgba(244, 169, 126, ...) palette
    // is the Brightpath alert accent. Non-elevated uses the info palette.
    expect(elevated.className).toMatch(/244,\s*169,\s*126/);
    expect(elevated.className).toMatch(/text-accent-alert/);
    expect(nonElevated.className).not.toMatch(/244,\s*169,\s*126/);
    expect(nonElevated.className).toMatch(/accent-info/);
  });

  it("keyboard Enter on a chip fires onChipClick with the chip object", () => {
    const onClick = vi.fn();
    render(
      <AskGemmaChipRow
        chips={[ELEVATED, BASE_A]}
        activeChipId={null}
        onChipClick={onClick}
        elevationHintId="hint-test"
      />,
    );
    const chip = screen.getByRole("button", {
      name: /What does this career actually do\?/i,
    });
    fireEvent.keyDown(chip, { key: "Enter" });
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(BASE_A);
  });

  it("keyboard Space on a chip fires onChipClick with the chip object", () => {
    const onClick = vi.fn();
    render(
      <AskGemmaChipRow
        chips={[ELEVATED, BASE_A]}
        activeChipId={null}
        onChipClick={onClick}
        elevationHintId="hint-test"
      />,
    );
    const elevatedChip = screen.getByRole("button", {
      name: /Why don't I see 'doctor'\?/i,
    });
    fireEvent.keyDown(elevatedChip, { key: " " });
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(ELEVATED);
  });

  it("click on a chip fires onChipClick with the chip object", () => {
    const onClick = vi.fn();
    render(
      <AskGemmaChipRow
        chips={[ELEVATED, BASE_A, BASE_B]}
        activeChipId={null}
        onChipClick={onClick}
        elevationHintId="hint-test"
      />,
    );
    const chip = screen.getByRole("button", {
      name: /Is this the right school for this\?/i,
    });
    fireEvent.click(chip);
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith(BASE_B);
  });

  it("elevated chip carries aria-describedby pointing at the parent's elevation hint id", () => {
    const hintId = "parent-owned-hint-id";
    render(
      <AskGemmaChipRow
        chips={[ELEVATED, BASE_A]}
        activeChipId={null}
        onChipClick={vi.fn()}
        elevationHintId={hintId}
      />,
    );
    const elevated = screen.getByRole("button", {
      name: /Why don't I see 'doctor'\?/i,
    });
    expect(elevated).toHaveAttribute("aria-describedby", hintId);

    // Non-elevated chips must NOT have aria-describedby for the hint — the
    // hint is only relevant to the elevated chip.
    const nonElevated = screen.getByRole("button", {
      name: /What does this career actually do\?/i,
    });
    expect(nonElevated).not.toHaveAttribute("aria-describedby");
  });

  it("active chip is marked with data-active='true'", () => {
    render(
      <AskGemmaChipRow
        chips={[ELEVATED, BASE_A]}
        activeChipId="what_does_this_do"
        onChipClick={vi.fn()}
        elevationHintId="hint-test"
      />,
    );
    const active = screen.getByRole("button", {
      name: /What does this career actually do\?/i,
    });
    expect(active).toHaveAttribute("data-active", "true");

    const inactive = screen.getByRole("button", {
      name: /Why don't I see 'doctor'\?/i,
    });
    expect(inactive).toHaveAttribute("data-active", "false");
  });

  it("returns null when chips list is empty", () => {
    const { container } = render(
      <AskGemmaChipRow
        chips={[]}
        activeChipId={null}
        onChipClick={vi.fn()}
        elevationHintId="hint-test"
      />,
    );
    // No role="group" rendered → empty container.
    expect(container.firstChild).toBeNull();
  });

  it("chip row is accessible as a named group", () => {
    render(
      <AskGemmaChipRow
        chips={[BASE_A]}
        activeChipId={null}
        onChipClick={vi.fn()}
        elevationHintId="hint-test"
      />,
    );
    const group = screen.getByRole("group", {
      name: "Ask the Guide about this screen",
    });
    // The chip is inside the group, not a sibling.
    expect(
      within(group).getByRole("button", {
        name: /What does this career actually do\?/i,
      }),
    ).toBeInTheDocument();
  });
});
