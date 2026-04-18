import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { ReceiptsSection } from "./ReceiptsSection";
import { resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";

/**
 * Section D — Receipts Story tests.
 *
 * The screenshot's alt text must match §3.15 exactly — it's the accessible
 * name judges depend on when the receipt panel hasn't been captured yet.
 * The four receipt lines are the voice-guide "every number has a receipt"
 * proof point; exact copy + correct order guards against soft-pedaling.
 */

describe("ReceiptsSection", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  it("renders section headline, lead, and kicker", () => {
    render(<ReceiptsSection />);
    expect(screen.getByText("Every number is tappable.")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Your stats aren't vibes\. Tap any number and you get the raw inputs, the thresholds, the source datasets, and the exact computation that produced it\./,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Your college brochure didn't do that."),
    ).toBeInTheDocument();
  });

  it("screenshot has descriptive alt text matching spec §3.15 exactly", () => {
    render(<ReceiptsSection />);
    const screenshot = document.getElementById("landing-receipts-screenshot");
    expect(screenshot).not.toBeNull();
    expect(screenshot?.tagName).toBe("IMG");
    expect(screenshot?.getAttribute("alt")).toBe(
      "Expanded stat receipt panel showing raw inputs, thresholds, and source datasets.",
    );
    // Below-the-fold optimization per §2 Decision 12.
    expect(screenshot?.getAttribute("loading")).toBe("lazy");
    expect(screenshot?.getAttribute("decoding")).toBe("async");
  });

  it("receipt stat block renders all four lines in spec order", () => {
    render(<ReceiptsSection />);

    // Order matters — this is the stacked DOM list.
    const expectedLines = [
      "700,000 cross-source rows.",
      "280 data quality rules.",
      "Seven data contracts.",
      "A chaos-monkey-hardened pipeline that catches its own mistakes before they reach you.",
    ];

    expectedLines.forEach((line) => {
      expect(screen.getByText(line)).toBeInTheDocument();
    });

    // Verify they render in the correct document order (not reshuffled).
    const body = document.body.textContent ?? "";
    let lastIndex = -1;
    expectedLines.forEach((line) => {
      const idx = body.indexOf(line);
      expect(idx).toBeGreaterThan(lastIndex);
      lastIndex = idx;
    });
  });

  it("first three receipt lines carry the correct accent color tokens", () => {
    render(<ReceiptsSection />);

    const thriveLine = screen.getByText("700,000 cross-source rows.");
    expect(thriveLine.className).toContain("text-accent-thrive");

    const insightLine = screen.getByText("280 data quality rules.");
    expect(insightLine.className).toContain("text-accent-insight");

    const infoLine = screen.getByText("Seven data contracts.");
    expect(infoLine.className).toContain("text-accent-info");
  });
});
