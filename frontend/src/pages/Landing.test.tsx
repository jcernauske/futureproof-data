import { render } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { Landing } from "./Landing";
import { resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";

/**
 * Page-level smoke test for the marketing Landing.
 *
 * The ordering of the 9 sections is load-bearing for the narrative spine
 * (hero → problem → how → receipts → ollama → cta → data → team → footer).
 * If someone rearranges or removes a section this must fail.
 *
 * Route wiring (/ → Landing, /app → Navigate to /set-your-course) is covered by
 * App.test.tsx — not duplicated here.
 */

describe("Landing page", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  it("renders all 9 sections in the spec-mandated order", () => {
    const { container } = render(<Landing />);

    const expectedOrder = [
      "landing-section-hero",
      "landing-section-problem",
      "landing-section-how",
      "landing-section-receipts",
      "landing-section-ollama",
      "landing-section-cta-rail",
      "landing-section-data",
      "landing-section-team",
      "horizon-footer",
    ];

    // Query the live DOM in document order so we catch both "missing"
    // and "wrong order" regressions in one assertion.
    const found = Array.from(
      container.querySelectorAll<HTMLElement>(
        expectedOrder.map((id) => `#${id}`).join(","),
      ),
    ).map((el) => el.id);

    expect(found).toEqual(expectedOrder);
  });

  it("wraps everything in a <main id='landing-root'> per spec §6 deviation note", () => {
    const { container } = render(<Landing />);
    const main = container.querySelector("main#landing-root");
    expect(main).not.toBeNull();
    expect(main?.tagName).toBe("MAIN");
  });
});
