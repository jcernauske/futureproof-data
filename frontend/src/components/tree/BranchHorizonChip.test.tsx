import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BranchHorizonChip } from "./BranchHorizonChip";
import type { CareerBranch } from "@/types/build";

/**
 * BranchHorizonChip.test.tsx — Tests for the single-chip presentation
 * component that renders a CareerBranch in the horizon map.
 *
 * Hunting for:
 *  - Title truncated to 32 chars with ellipsis
 *  - Dominant stat-delta badge picks largest abs(delta), preserves sign
 *  - Experience badge renders only for "mid" or "senior" tier
 *  - Relatedness color bar via data-tier attribute matches derived tier
 *  - Unlock footer renders when present, hidden when null
 *  - level-unknown indicator when related_education_level is null
 *  - flashing prop applies branch-flash className
 *  - selected prop applies data-selected attribute
 *  - onClick fires on click
 */

function makeBranch(overrides: Partial<CareerBranch> = {}): CareerBranch {
  return {
    from_soc: "13-2051",
    to_soc: "11-3031",
    to_title: "Financial Manager",
    delta_ern: null,
    delta_roi: null,
    delta_res: null,
    delta_grw: null,
    delta_hmn: null,
    unlock: null,
    relatedness: null,
    experience_years: null,
    experience_tier: null,
    experience_delta: null,
    related_education_level: null,
    ...overrides,
  };
}

const noopClick = () => {};

describe("BranchHorizonChip — title truncation", () => {
  it("test_renders_to_title_truncated_to_32_chars_with_ellipsis", () => {
    const long = "Postsecondary Education Administrators And Curriculum Designers"; // > 32
    const branch = makeBranch({ to_title: long, to_soc: "11-9033" });

    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );

    const chip = screen.getByTestId("chip-branch-11-9033");
    // The title text element is the first child div with class horizon-chip-title.
    const titleEl = chip.querySelector(".horizon-chip-title");
    expect(titleEl).not.toBeNull();
    const text = titleEl!.textContent ?? "";
    expect(text.length).toBeLessThanOrEqual(33);
    expect(text.endsWith("…")).toBe(true);
  });

  it("test_short_title_renders_unchanged_no_ellipsis", () => {
    const branch = makeBranch({ to_title: "Pilot", to_soc: "53-2011" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    const chip = screen.getByTestId("chip-branch-53-2011");
    expect(chip.querySelector(".horizon-chip-title")?.textContent).toBe("Pilot");
  });

  it("test_full_title_preserved_in_aria_label_and_title_attrs_for_a11y", () => {
    const long = "Postsecondary Education Administrators And Curriculum Designers";
    const branch = makeBranch({ to_title: long, to_soc: "11-9033" });

    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    const chip = screen.getByTestId("chip-branch-11-9033");
    expect(chip.getAttribute("aria-label")).toBe(long);
    expect(chip.getAttribute("title")).toBe(long);
  });
});

describe("BranchHorizonChip — dominant stat-delta badge", () => {
  it("test_dominant_stat_delta_picks_largest_abs_delta", () => {
    const branch = makeBranch({
      to_soc: "11-3031",
      delta_ern: 5,
      delta_grw: -8,
      delta_hmn: 3,
    });

    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );

    const chip = screen.getByTestId("chip-branch-11-3031");
    const badge = chip.querySelector(".horizon-stat-badge");
    expect(badge).not.toBeNull();
    expect(badge!.textContent).toContain("-8");
    expect(badge!.textContent).toContain("GRW");
    expect(badge!.getAttribute("data-stat")).toBe("grw");
    expect(badge!.getAttribute("data-sign")).toBe("neg");
  });

  it("test_positive_dominant_delta_renders_with_plus_sign", () => {
    const branch = makeBranch({
      to_soc: "11-3031",
      delta_ern: 12,
      delta_grw: 3,
    });

    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    const badge = screen
      .getByTestId("chip-branch-11-3031")
      .querySelector(".horizon-stat-badge");
    expect(badge!.textContent).toContain("+12");
    expect(badge!.textContent).toContain("ERN");
    expect(badge!.getAttribute("data-sign")).toBe("pos");
  });

  it("test_no_badge_when_all_deltas_null", () => {
    const branch = makeBranch({ to_soc: "11-3031" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").querySelector(".horizon-stat-badge"),
    ).toBeNull();
  });
});

describe("BranchHorizonChip — experience badge", () => {
  it("test_experience_badge_renders_for_mid_tier", () => {
    const branch = makeBranch({ to_soc: "11-3031", experience_tier: "mid" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").querySelector(".horizon-exp-badge"),
    ).not.toBeNull();
  });

  it("test_experience_badge_renders_for_senior_tier", () => {
    const branch = makeBranch({ to_soc: "11-3031", experience_tier: "senior" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    const badge = screen
      .getByTestId("chip-branch-11-3031")
      .querySelector(".horizon-exp-badge");
    expect(badge).not.toBeNull();
    expect(badge!.getAttribute("data-tier")).toBe("senior");
  });

  it("test_no_experience_badge_for_early_tier", () => {
    const branch = makeBranch({ to_soc: "11-3031", experience_tier: "early" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").querySelector(".horizon-exp-badge"),
    ).toBeNull();
  });

  it("test_no_experience_badge_for_entry_tier", () => {
    const branch = makeBranch({ to_soc: "11-3031", experience_tier: "entry" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").querySelector(".horizon-exp-badge"),
    ).toBeNull();
  });

  it("test_no_experience_badge_for_null_tier", () => {
    const branch = makeBranch({ to_soc: "11-3031", experience_tier: null });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").querySelector(".horizon-exp-badge"),
    ).toBeNull();
  });
});

describe("BranchHorizonChip — relatedness color bar via data-tier", () => {
  it("test_relatedness_3_renders_data_tier_primary_short", () => {
    const branch = makeBranch({ to_soc: "11-3031", relatedness: 3 });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").getAttribute("data-tier"),
    ).toBe("primary-short");
  });

  it("test_relatedness_8_renders_data_tier_primary_long", () => {
    const branch = makeBranch({ to_soc: "11-3031", relatedness: 8 });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").getAttribute("data-tier"),
    ).toBe("primary-long");
  });

  it("test_relatedness_15_renders_data_tier_supplemental", () => {
    const branch = makeBranch({ to_soc: "11-3031", relatedness: 15 });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").getAttribute("data-tier"),
    ).toBe("supplemental");
  });

  it("test_relatedness_null_omits_data_tier_attribute", () => {
    const branch = makeBranch({ to_soc: "11-3031", relatedness: null });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    // tier is null → data-tier is undefined → attribute absent
    expect(
      screen.getByTestId("chip-branch-11-3031").hasAttribute("data-tier"),
    ).toBe(false);
  });
});

describe("BranchHorizonChip — unlock footer", () => {
  it("test_unlock_footer_renders_when_unlock_present", () => {
    const branch = makeBranch({
      to_soc: "11-3031",
      unlock: "Master's degree",
    });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    const footer = screen
      .getByTestId("chip-branch-11-3031")
      .querySelector(".horizon-chip-unlock");
    expect(footer).not.toBeNull();
    expect(footer!.textContent).toContain("Master's degree");
  });

  it("test_unlock_footer_hidden_when_unlock_null", () => {
    const branch = makeBranch({ to_soc: "11-3031", unlock: null });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen
        .getByTestId("chip-branch-11-3031")
        .querySelector(".horizon-chip-unlock"),
    ).toBeNull();
  });
});

describe("BranchHorizonChip — level-unknown treatment", () => {
  it("test_level_unknown_data_attr_when_related_education_level_is_null", () => {
    const branch = makeBranch({
      to_soc: "11-3031",
      related_education_level: null,
    });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen
        .getByTestId("chip-branch-11-3031")
        .getAttribute("data-level-unknown"),
    ).toBe("true");
  });

  it("test_no_level_unknown_attr_when_related_education_level_is_set", () => {
    const branch = makeBranch({
      to_soc: "11-3031",
      related_education_level: "Bachelor's degree",
    });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen
        .getByTestId("chip-branch-11-3031")
        .hasAttribute("data-level-unknown"),
    ).toBe(false);
  });
});

describe("BranchHorizonChip — flashing + selected + click", () => {
  it("test_flashing_true_applies_branch_flash_className", () => {
    const branch = makeBranch({ to_soc: "11-3031" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={true}
        onClick={noopClick}
      />,
    );
    const chip = screen.getByTestId("chip-branch-11-3031");
    expect(chip.className).toContain("branch-flash");
  });

  it("test_flashing_false_omits_branch_flash_className", () => {
    const branch = makeBranch({ to_soc: "11-3031" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    const chip = screen.getByTestId("chip-branch-11-3031");
    expect(chip.className).not.toContain("branch-flash");
  });

  it("test_selected_true_applies_data_selected_attribute", () => {
    const branch = makeBranch({ to_soc: "11-3031" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={true}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").getAttribute("data-selected"),
    ).toBe("true");
  });

  it("test_selected_false_omits_data_selected_attribute", () => {
    const branch = makeBranch({ to_soc: "11-3031" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={noopClick}
      />,
    );
    expect(
      screen.getByTestId("chip-branch-11-3031").hasAttribute("data-selected"),
    ).toBe(false);
  });

  it("test_clicking_chip_fires_onClick", () => {
    const onClick = vi.fn();
    const branch = makeBranch({ to_soc: "11-3031" });
    render(
      <BranchHorizonChip
        branch={branch}
        selected={false}
        flashing={false}
        onClick={onClick}
      />,
    );
    fireEvent.click(screen.getByTestId("chip-branch-11-3031"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("BranchHorizonChip — SOC rollup badge", () => {
  it("renders Business badge for an 11-XXXX management SOC", () => {
    const branch = makeBranch({ to_soc: "11-9121", to_title: "Natural Sciences Managers" });
    render(
      <BranchHorizonChip branch={branch} selected={false} flashing={false} onClick={noopClick} />,
    );
    const badge = screen.getByTestId("chip-rollup-business");
    expect(badge).toBeInTheDocument();
    expect(badge.getAttribute("data-rollup")).toBe("business");
    expect(badge.textContent).toMatch(/business/i);
  });

  it("renders Technical badge for a 15-XXXX computer/math SOC", () => {
    const branch = makeBranch({ to_soc: "15-2051", to_title: "Data Scientists" });
    render(
      <BranchHorizonChip branch={branch} selected={false} flashing={false} onClick={noopClick} />,
    );
    expect(screen.getByTestId("chip-rollup-technical")).toBeInTheDocument();
  });

  it("renders Trades badge for a 47-XXXX construction SOC", () => {
    const branch = makeBranch({ to_soc: "47-2031", to_title: "Carpenters" });
    render(
      <BranchHorizonChip branch={branch} selected={false} flashing={false} onClick={noopClick} />,
    );
    expect(screen.getByTestId("chip-rollup-trades")).toBeInTheDocument();
  });

  it("renders no rollup badge when SOC major group is unmapped", () => {
    const branch = makeBranch({ to_soc: "55-1010", to_title: "Military Officer" });
    render(
      <BranchHorizonChip branch={branch} selected={false} flashing={false} onClick={noopClick} />,
    );
    expect(screen.queryByTestId(/^chip-rollup-/)).toBeNull();
  });
});
