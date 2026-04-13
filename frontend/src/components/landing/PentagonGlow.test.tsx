import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PentagonGlow } from "./PentagonGlow";

describe("PentagonGlow", () => {
  it("renders SVG element", () => {
    const { container } = render(<PentagonGlow />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("renders five vertex circles in SVG", () => {
    const { container } = render(<PentagonGlow />);
    const circles = container.querySelectorAll("svg circle");
    expect(circles.length).toBe(5);
  });

  it("renders five stat labels", () => {
    const { container } = render(<PentagonGlow />);
    const labels = container.querySelectorAll(".stat-label-fade");
    expect(labels.length).toBe(5);
  });
});
