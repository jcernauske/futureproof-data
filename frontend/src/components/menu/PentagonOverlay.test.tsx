/**
 * PentagonOverlay.test.tsx
 *
 * P0: Renders one polygon group per build (verified via overlay-shape-{idx}
 * testids). Also defends against off-by-one iteration over the builds array.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PentagonOverlay } from "./PentagonOverlay";
import type { CompareResult } from "@/api/menu";

function makeBuild(id: string, label: string) {
  return {
    build_id: id,
    label,
    career: `Career ${id.toUpperCase()}`,
    soc_code: "00-0000",
    profile_name: label,
    animal_emoji: null,
    school_name: label,
    major_text: "Test",
    effort: "balanced",
    loan_pct: 0.5,
    median_annual_wage: null,
    net_price_annual: null,
    modeled_total_debt: null,
    tuition_annual: null,
    is_out_of_state: false,
    institution_control: null,
  };
}

function makeResult(buildCount: 2 | 3): CompareResult {
  const builds = [
    makeBuild("a", "Build A"),
    makeBuild("b", "Build B"),
    makeBuild("c", "Build C"),
  ].slice(0, buildCount);

  const valuesFor = (n: number) =>
    Array.from({ length: buildCount }, (_, i) => Math.min(10, n + i));

  return {
    builds,
    stats: [
      { label: "ERN", values: valuesFor(5) },
      { label: "ROI", values: valuesFor(6) },
      { label: "RES", values: valuesFor(7) },
      { label: "GRW", values: valuesFor(8) },
      { label: "AURA", values: valuesFor(4) },
    ],
    bosses: [],
    branches: [],
  };
}

describe("PentagonOverlay", () => {
  it("renders one polygon group per build with overlay-shape-{idx} testids (P0)", () => {
    render(<PentagonOverlay result={makeResult(2)} />);

    expect(screen.getByTestId("overlay-shape-0")).toBeInTheDocument();
    expect(screen.getByTestId("overlay-shape-1")).toBeInTheDocument();
    // No third build — must NOT be present (saboteur: prove iteration is bounded).
    expect(screen.queryByTestId("overlay-shape-2")).not.toBeInTheDocument();
  });

  it("renders three shapes when comparing three builds (P0)", () => {
    render(<PentagonOverlay result={makeResult(3)} />);

    expect(screen.getByTestId("overlay-shape-0")).toBeInTheDocument();
    expect(screen.getByTestId("overlay-shape-1")).toBeInTheDocument();
    expect(screen.getByTestId("overlay-shape-2")).toBeInTheDocument();
    expect(screen.queryByTestId("overlay-shape-3")).not.toBeInTheDocument();
  });

});
