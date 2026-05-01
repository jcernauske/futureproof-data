import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { BranchHorizonMap } from "./BranchHorizonMap";
import type { CareerBranch } from "@/types/build";

/**
 * BranchHorizonMap.test.tsx — Tests for the SOC-taxonomy chip grid that
 * replaces BranchTreeFlow on /branch-tree.
 *
 * Hunting for:
 *  - Taxonomy lane headers render only when that bucket has entries
 *  - Up to LANE_CAP=6 chips per lane; "+N more" affordance for overflow
 *  - Click "+N more" expands the lane inline
 *  - Hide-supplemental toggle filters across all lanes
 *  - Clicking a chip fires onSelectNode("chip-{to_soc}")
 *  - flashing chip applies branch-flash className via highlightedNodeIds
 *  - Empty lanes render data-testid="lane-empty-{lane}" placeholder
 *  - selected chip applies data-selected attribute
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
    related_education_level: "Bachelor's degree",
    ...overrides,
  };
}

function makeBusinessBranches(count: number): CareerBranch[] {
  return Array.from({ length: count }, (_, i) =>
    makeBranch({
      to_soc: `11-300${i}`,
      to_title: `Business Career ${i}`,
      relatedness: i + 1,
      related_education_level: "Bachelor's degree",
    }),
  );
}

describe("BranchHorizonMap — lane structure", () => {
  it("test_renders_only_populated_soc_taxonomy_lane_headers", () => {
    const branches = [
      makeBranch({ to_soc: "11-3031", relatedness: 1 }),
      makeBranch({ to_soc: "15-2051", relatedness: 1 }),
      makeBranch({ to_soc: "27-1024", relatedness: 1 }),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    expect(screen.getByTestId("lane-header-business")).toBeInTheDocument();
    expect(screen.getByTestId("lane-header-technical")).toBeInTheDocument();
    expect(screen.getByTestId("lane-header-arts")).toBeInTheDocument();
    expect(screen.queryByTestId("lane-header-education")).toBeNull();
    expect(screen.queryByTestId("lane-header-care")).toBeNull();
    expect(screen.queryByTestId("lane-header-service")).toBeNull();
    expect(screen.queryByTestId("lane-header-trades")).toBeNull();
  });

  it("test_renders_region_branch_horizon_container", () => {
    render(
      <BranchHorizonMap
        branches={[]}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );
    expect(screen.getByTestId("region-branch-horizon")).toBeInTheDocument();
  });
});

describe("BranchHorizonMap — lane cap + expand", () => {
  it("test_renders_one_chip_per_branch_up_to_lane_cap_of_6", () => {
    const branches = makeBusinessBranches(10);

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    // 6 chips visible (lane cap)
    for (let i = 0; i < 6; i++) {
      expect(screen.getByTestId(`chip-branch-11-300${i}`)).toBeInTheDocument();
    }
    // Chips beyond cap not yet rendered
    for (let i = 6; i < 10; i++) {
      expect(screen.queryByTestId(`chip-branch-11-300${i}`)).toBeNull();
    }
    // Expand button present with overflow count = 4
    const expandBtn = screen.getByTestId("btn-lane-expand-business");
    expect(expandBtn).toBeInTheDocument();
    expect(expandBtn.textContent).toContain("4");
  });

  it("test_clicking_expand_more_expands_lane_inline", () => {
    const branches = makeBusinessBranches(10);

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    fireEvent.click(screen.getByTestId("btn-lane-expand-business"));

    // All 10 chips visible after expand
    for (let i = 0; i < 10; i++) {
      expect(screen.getByTestId(`chip-branch-11-300${i}`)).toBeInTheDocument();
    }
    // Expand button is gone, collapse button present
    expect(screen.queryByTestId("btn-lane-expand-business")).toBeNull();
    expect(screen.getByTestId("btn-lane-collapse-business")).toBeInTheDocument();
  });

  it("test_clicking_collapse_returns_to_capped_view", () => {
    const branches = makeBusinessBranches(10);

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    fireEvent.click(screen.getByTestId("btn-lane-expand-business"));
    fireEvent.click(screen.getByTestId("btn-lane-collapse-business"));

    // Back to 6 visible
    for (let i = 0; i < 6; i++) {
      expect(screen.getByTestId(`chip-branch-11-300${i}`)).toBeInTheDocument();
    }
    expect(screen.queryByTestId("chip-branch-11-3007")).toBeNull();
    expect(screen.getByTestId("btn-lane-expand-business")).toBeInTheDocument();
  });

  it("test_no_expand_button_when_lane_at_or_under_cap", () => {
    const branches = makeBusinessBranches(3);

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );
    expect(screen.queryByTestId("btn-lane-expand-business")).toBeNull();
  });
});

describe("BranchHorizonMap — hide supplemental toggle", () => {
  it("test_hide_supplemental_toggle_filters_across_all_lanes", () => {
    // Mix of supplemental + non-supplemental rows distributed across lanes.
    const branches: CareerBranch[] = [
      makeBranch({
        to_soc: "11-1001",
        relatedness: 1,
        related_education_level: "Bachelor's degree",
      }),
      makeBranch({
        to_soc: "11-1002",
        relatedness: 15,
        related_education_level: "Bachelor's degree",
      }),
      makeBranch({
        to_soc: "15-1001",
        relatedness: 8,
        related_education_level: "Master's degree",
      }),
      makeBranch({
        to_soc: "15-1002",
        relatedness: 18,
        related_education_level: "Master's degree",
      }),
      makeBranch({
        to_soc: "27-1001",
        relatedness: 4,
        related_education_level: "Doctoral or professional degree",
      }),
      makeBranch({
        to_soc: "27-1002",
        relatedness: 22,
        related_education_level: "Doctoral or professional degree",
      }),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    // All 6 chips visible before toggle
    expect(screen.getByTestId("chip-branch-11-1002")).toBeInTheDocument();
    expect(screen.getByTestId("chip-branch-15-1002")).toBeInTheDocument();
    expect(screen.getByTestId("chip-branch-27-1002")).toBeInTheDocument();

    // Toggle hide supplemental
    fireEvent.click(screen.getByTestId("toggle-hide-supplemental"));

    // Supplementals removed from every lane
    expect(screen.queryByTestId("chip-branch-11-1002")).toBeNull();
    expect(screen.queryByTestId("chip-branch-15-1002")).toBeNull();
    expect(screen.queryByTestId("chip-branch-27-1002")).toBeNull();

    // Non-supplementals retained
    expect(screen.getByTestId("chip-branch-11-1001")).toBeInTheDocument();
    expect(screen.getByTestId("chip-branch-15-1001")).toBeInTheDocument();
    expect(screen.getByTestId("chip-branch-27-1001")).toBeInTheDocument();
  });

  it("test_hide_supplemental_toggle_updates_overflow_count_after_filter", () => {
    // 8 lateral branches: 4 PS, 4 Supplemental.
    // Without filter: 8 → cap 6, "+2 more" shown.
    // With filter: 4 → no overflow, no expand button.
    const branches: CareerBranch[] = [
      ...Array.from({ length: 4 }, (_, i) =>
        makeBranch({
          to_soc: `11-20${i}`,
          relatedness: i + 1,
          related_education_level: "Bachelor's degree",
        }),
      ),
      ...Array.from({ length: 4 }, (_, i) =>
        makeBranch({
          to_soc: `11-30${i}`,
          relatedness: 12 + i,
          related_education_level: "Bachelor's degree",
        }),
      ),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    expect(screen.getByTestId("btn-lane-expand-business")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("toggle-hide-supplemental"));
    expect(screen.queryByTestId("btn-lane-expand-business")).toBeNull();
  });
});

describe("BranchHorizonMap — chip click + select", () => {
  it("test_clicking_a_chip_fires_onSelectNode_with_chip_to_soc_id", () => {
    const onSelectNode = vi.fn();
    const branches = [
      makeBranch({
        to_soc: "11-3031",
        relatedness: 1,
        related_education_level: "Bachelor's degree",
      }),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={onSelectNode}
      />,
    );

    fireEvent.click(screen.getByTestId("chip-branch-11-3031"));
    expect(onSelectNode).toHaveBeenCalledTimes(1);
    expect(onSelectNode).toHaveBeenCalledWith("chip-11-3031");
  });

  it("test_selected_chip_applies_data_selected_attribute", () => {
    const branches = [
      makeBranch({
        to_soc: "13-1075",
        relatedness: 1,
        related_education_level: "Bachelor's degree",
      }),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId="chip-13-1075"
        onSelectNode={() => {}}
      />,
    );

    expect(
      screen.getByTestId("chip-branch-13-1075").getAttribute("data-selected"),
    ).toBe("true");
  });
});

describe("BranchHorizonMap — flash highlight", () => {
  it("test_flashing_chip_applies_branch_flash_className", () => {
    const branches = [
      makeBranch({
        to_soc: "13-1075",
        relatedness: 1,
        related_education_level: "Bachelor's degree",
      }),
      makeBranch({
        to_soc: "13-2051",
        relatedness: 2,
        related_education_level: "Bachelor's degree",
      }),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
        highlightedNodeIds={new Set(["chip-13-1075"])}
      />,
    );

    expect(
      screen.getByTestId("chip-branch-13-1075").className,
    ).toContain("branch-flash");
    expect(
      screen.getByTestId("chip-branch-13-2051").className,
    ).not.toContain("branch-flash");
  });
});

describe("BranchHorizonMap — empty lanes", () => {
  it("test_empty_taxonomy_lanes_are_hidden_when_other_lanes_have_entries", () => {
    const branches = [
      makeBranch({
        to_soc: "11-1001",
        relatedness: 1,
        related_education_level: "Master's degree",
      }),
      makeBranch({
        to_soc: "11-1002",
        relatedness: 2,
        related_education_level: "Master's degree",
      }),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Master's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    expect(screen.queryByTestId("lane-empty-technical")).toBeNull();
    expect(screen.queryByTestId("lane-empty-arts")).toBeNull();
    expect(screen.queryByTestId("lane-empty-business")).toBeNull();
  });

  it("test_empty_lane_placeholder_has_role_status_for_a11y", () => {
    render(
      <BranchHorizonMap
        branches={[]}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );
    const placeholder = screen.getByTestId("lane-empty-business");
    expect(placeholder.getAttribute("role")).toBe("status");
  });

  it("test_single_empty_state_when_no_taxonomy_lanes_have_entries", () => {
    render(
      <BranchHorizonMap
        branches={[]}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );
    expect(screen.getByTestId("lane-empty-business")).toBeInTheDocument();
    expect(screen.queryByTestId("lane-empty-technical")).toBeNull();
    expect(screen.queryByTestId("lane-empty-arts")).toBeNull();
    expect(screen.queryByTestId("lane-empty-education")).toBeNull();
    expect(screen.queryByTestId("lane-empty-care")).toBeNull();
    expect(screen.queryByTestId("lane-empty-service")).toBeNull();
    expect(screen.queryByTestId("lane-empty-trades")).toBeNull();
  });
});

describe("BranchHorizonMap — chip ordering inside a lane", () => {
  it("test_chips_render_in_relatedness_ASC_order_within_a_lane", () => {
    // Mix of relatedness 5, 1, 3 — all Business. After sort: 1, 3, 5.
    const branches = [
      makeBranch({
        to_soc: "11-5005",
        relatedness: 5,
        related_education_level: "Bachelor's degree",
      }),
      makeBranch({
        to_soc: "11-5001",
        relatedness: 1,
        related_education_level: "Bachelor's degree",
      }),
      makeBranch({
        to_soc: "11-5003",
        relatedness: 3,
        related_education_level: "Bachelor's degree",
      }),
    ];

    render(
      <BranchHorizonMap
        branches={branches}
        buildEduLevel="Bachelor's degree"
        selectedNodeId={null}
        onSelectNode={() => {}}
      />,
    );

    // Find the business lane container, then collect chips in DOM order.
    const region = screen.getByTestId("region-branch-horizon");
    const lateralLane = region.querySelector('[data-lane="business"]')!;
    const chips = within(lateralLane as HTMLElement).getAllByTestId(/^chip-branch-/);
    const ids = chips.map((c) => c.getAttribute("data-testid"));

    expect(ids).toEqual([
      "chip-branch-11-5001",
      "chip-branch-11-5003",
      "chip-branch-11-5005",
    ]);
  });
});
