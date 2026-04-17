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

function makeResult(buildCount: 2 | 3): CompareResult {
  const builds = [
    { build_id: "a", label: "Build A", career: "Career A" },
    { build_id: "b", label: "Build B", career: "Career B" },
    { build_id: "c", label: "Build C", career: "Career C" },
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
      { label: "HMN", values: valuesFor(4) },
    ],
    bosses: [],
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

  it("legend lists every build's label", () => {
    render(<PentagonOverlay result={makeResult(3)} />);

    const legend = screen.getByTestId("overlay-legend");
    expect(legend).toHaveTextContent("Build A");
    expect(legend).toHaveTextContent("Build B");
    expect(legend).toHaveTextContent("Build C");
  });

  it("aria-label reports the build count for screen readers", () => {
    render(<PentagonOverlay result={makeResult(2)} />);
    expect(screen.getByTestId("svg-pentagon-overlay")).toHaveAttribute(
      "aria-label",
      "Pentagon overlay comparing 2 builds",
    );
  });
});
