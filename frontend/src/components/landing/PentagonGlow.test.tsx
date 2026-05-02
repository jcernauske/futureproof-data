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

  it("renders vertex dot groups for all five stats", () => {
    const { container } = render(<PentagonGlow />);
    // Each vertex has 3 circles (halo + glow + dot) = 15
    // Plus 1 core glow circle + 10 floating particles = 26 total
    const circles = container.querySelectorAll("svg circle");
    expect(circles.length).toBeGreaterThanOrEqual(15);
  });

  it("renders five stat labels", () => {
    const { container } = render(<PentagonGlow />);
    const labels = Array.from(container.querySelectorAll("span")).filter((el) =>
      ["Earnings", "ROI", "Resilience", "Growth", "Brand Gravity"].includes(el.textContent ?? "")
    );
    expect(labels.length).toBe(5);
  });
});
