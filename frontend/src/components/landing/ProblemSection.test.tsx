import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { ProblemSection } from "./ProblemSection";
import { resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";

/**
 * Section B — The Problem tests.
 *
 * Two typographic receipts — `82% exposed to AI` (accent-insight) and
 * `$400/hour counselor` (accent-alert) — are the voice-guide "typographic
 * receipt" pattern. Their accent colors must match spec §3.5 token table
 * exactly; dropping one to plain body weakens the inline proof.
 *
 * §3.5 also enforces a hard rule: NO THIRD receipt. If a future edit adds
 * one, the power of the pattern collapses. That's a design-auditor concern,
 * not a mechanical test.
 */

describe("ProblemSection", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  it("renders the headline per §3.5 copy ground truth", () => {
    render(<ProblemSection />);
    expect(
      screen.getByText(
        "Your college probably isn't going to mention the ceiling.",
      ),
    ).toBeInTheDocument();
  });

  it("renders paragraph 1 with the 'first/tenth job' framing", () => {
    render(<ProblemSection />);
    // Paragraph 1 contains an inline <span> receipt, so test for the surrounding
    // copy via partial matchers.
    expect(
      screen.getByText(/Admissions brochures tell you about the first job\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /whether your major survives the next decade of automation\./,
      ),
    ).toBeInTheDocument();
  });

  it("renders paragraph 2 — the '400 other students and a quarter-hour' line", () => {
    render(<ProblemSection />);
    expect(
      screen.getByText(
        "Your guidance counselor has 400 other students and a quarter-hour with you.",
      ),
    ).toBeInTheDocument();
  });

  it("renders paragraph 3 — the 'first-gen' closure line", () => {
    render(<ProblemSection />);
    expect(
      screen.getByText(
        /gets a different answer than a first-gen community-college student\. That's the gap FutureProof closes\./,
      ),
    ).toBeInTheDocument();
  });

  it("inline receipt '82% exposed to AI' uses text-accent-insight + font-data", () => {
    render(<ProblemSection />);
    const receipt = screen.getByText("82% exposed to AI");
    expect(receipt.tagName).toBe("SPAN");
    expect(receipt.className).toContain("text-accent-insight");
    expect(receipt.className).toContain("font-data");
  });

  it("inline receipt '$400/hour counselor' uses text-accent-alert + font-data", () => {
    render(<ProblemSection />);
    const receipt = screen.getByText("$400/hour counselor");
    expect(receipt.tagName).toBe("SPAN");
    expect(receipt.className).toContain("text-accent-alert");
    expect(receipt.className).toContain("font-data");
  });

  it("section carries the spec identifier landing-section-problem", () => {
    render(<ProblemSection />);
    const section = document.getElementById("landing-section-problem");
    expect(section).not.toBeNull();
    expect(section?.tagName).toBe("SECTION");
  });
});
