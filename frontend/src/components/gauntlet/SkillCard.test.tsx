import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SkillCard } from "./SkillCard";
import type { AppliedSkill } from "@/types/build";

/**
 * SkillCard tests
 *
 * The SkillCard renders a single equippable skill with stat delta pills.
 * It acts as a checkbox (toggle on/off). The getStatDeltas helper filters
 * out zero-value deltas and formats the rest as "+N" or "-N" pills.
 *
 * Key behaviors tested:
 * - Title, rationale, and stat deltas render correctly
 * - Toggle fires callback
 * - aria-checked reflects selected state
 * - Zero deltas are excluded from display
 * - Positive deltas get thrive color, negative get alert color
 */

function makeSkill(overrides?: Partial<AppliedSkill>): AppliedSkill {
  return {
    id: "sk-cloud",
    title: "Cloud Architecture",
    rationale: "Cloud skills are the #1 hiring signal.",
    targets: ["market", "ceiling"],
    delta_ern: 1,
    delta_roi: 0,
    delta_res: 0,
    delta_grw: 1,
    delta_hmn: 0,
    delta_burnout_raw: 0,
    delta_ceiling_raw: 2,
    ...overrides,
  };
}

describe("SkillCard", () => {
  it("renders skill title and rationale", () => {
    render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={vi.fn()} />,
    );

    expect(screen.getByText("Cloud Architecture")).toBeInTheDocument();
    expect(
      screen.getByText("Cloud skills are the #1 hiring signal."),
    ).toBeInTheDocument();
  });

  it("renders non-zero stat deltas as pills", () => {
    render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={vi.fn()} />,
    );

    // ERN +1, GRW +1, CEIL +2 should appear; ROI, RES, HMN, BRN are 0
    expect(screen.getByText(/ERN \+1/)).toBeInTheDocument();
    expect(screen.getByText(/GRW \+1/)).toBeInTheDocument();
    expect(screen.getByText(/CEIL \+2/)).toBeInTheDocument();
    expect(screen.queryByText(/ROI/)).not.toBeInTheDocument();
    expect(screen.queryByText(/RES/)).not.toBeInTheDocument();
    expect(screen.queryByText(/HMN/)).not.toBeInTheDocument();
    expect(screen.queryByText(/BRN/)).not.toBeInTheDocument();
  });

  it("renders negative deltas with alert styling", () => {
    const skill = makeSkill({
      delta_ern: -2,
      delta_roi: 0,
      delta_res: 0,
      delta_grw: 0,
      delta_hmn: 0,
    });
    render(
      <SkillCard skill={skill} selected={false} onToggle={vi.fn()} />,
    );

    const pill = screen.getByText(/ERN -2/);
    expect(pill).toBeInTheDocument();
    // Negative delta should have alert color class
    expect(pill.className).toMatch(/accent-alert/);
  });

  it("renders positive deltas with thrive styling", () => {
    render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={vi.fn()} />,
    );

    const pill = screen.getByText(/ERN \+1/);
    expect(pill.className).toMatch(/accent-thrive/);
  });

  it("renders no delta pills when all deltas are zero", () => {
    const skill = makeSkill({
      delta_ern: 0,
      delta_roi: 0,
      delta_res: 0,
      delta_grw: 0,
      delta_hmn: 0,
      delta_burnout_raw: 0,
      delta_ceiling_raw: 0,
    });
    render(
      <SkillCard skill={skill} selected={false} onToggle={vi.fn()} />,
    );

    for (const label of ["ERN", "ROI", "RES", "GRW", "HMN", "BRN", "CEIL"]) {
      expect(screen.queryByText(new RegExp(label))).not.toBeInTheDocument();
    }
  });

  it("calls onToggle when clicked", () => {
    const onToggle = vi.fn();
    render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={onToggle} />,
    );

    fireEvent.click(screen.getByRole("checkbox"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("has aria-checked=false when not selected", () => {
    render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={vi.fn()} />,
    );

    expect(screen.getByRole("checkbox")).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("has aria-checked=true when selected", () => {
    render(
      <SkillCard skill={makeSkill()} selected={true} onToggle={vi.fn()} />,
    );

    expect(screen.getByRole("checkbox")).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("renders checkmark SVG only when selected", () => {
    const { rerender } = render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={vi.fn()} />,
    );

    // No checkmark when unselected
    expect(screen.queryByRole("checkbox")?.querySelector("svg")).toBeNull();

    rerender(
      <SkillCard skill={makeSkill()} selected={true} onToggle={vi.fn()} />,
    );

    // Checkmark appears when selected
    expect(
      screen.getByRole("checkbox").querySelector("svg"),
    ).toBeInTheDocument();
  });

  it("has accessible label with stat deltas", () => {
    render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={vi.fn()} />,
    );

    const checkbox = screen.getByRole("checkbox");
    const label = checkbox.getAttribute("aria-label") ?? "";
    expect(label).toContain("Cloud Architecture");
    expect(label).toContain("ERN");
    expect(label).toContain("GRW");
    expect(label).toContain("CEIL");
  });

  it("flips burnout sign so negative raw displays as positive", () => {
    const skill = makeSkill({
      delta_ern: 0,
      delta_roi: 0,
      delta_res: 0,
      delta_grw: 0,
      delta_hmn: 0,
      delta_burnout_raw: -2,
      delta_ceiling_raw: 0,
    });
    render(
      <SkillCard skill={skill} selected={false} onToggle={vi.fn()} />,
    );

    const pill = screen.getByText(/BRN \+2/);
    expect(pill).toBeInTheDocument();
    expect(pill.className).toMatch(/accent-thrive/);
  });

  it("renders ceiling delta as CEIL badge", () => {
    const skill = makeSkill({
      delta_ern: 0,
      delta_roi: 0,
      delta_res: 0,
      delta_grw: 0,
      delta_hmn: 0,
      delta_burnout_raw: 0,
      delta_ceiling_raw: 3,
    });
    render(
      <SkillCard skill={skill} selected={false} onToggle={vi.fn()} />,
    );

    expect(screen.getByText(/CEIL \+3/)).toBeInTheDocument();
  });

  it("includes boss-specific id attribute", () => {
    const { container } = render(
      <SkillCard skill={makeSkill()} selected={false} onToggle={vi.fn()} />,
    );

    expect(container.querySelector("#card-skill-sk-cloud")).toBeInTheDocument();
  });
});
