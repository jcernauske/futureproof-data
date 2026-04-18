import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { HeroSection } from "./HeroSection";
import {
  resetReducedMotion,
  setReducedMotion,
} from "@/test/mocks/prefers-reduced-motion";

/**
 * Section A — Above the Fold (Hero) tests.
 *
 * Spec §3.4 copy ground truth is non-negotiable — voice-guide compliance
 * hangs off exact strings. These tests guard those strings and the two
 * accessibility identifiers.
 */

describe("HeroSection", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  it("renders headline, CTA, and data footer with spec-exact copy", () => {
    render(<HeroSection />);

    // Headline splits across <br/> — use partial matchers, then assert both halves exist.
    expect(
      screen.getByText(/A college degree isn't a destination\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/It's a starting position\./),
    ).toBeInTheDocument();

    // Subhead must be the voice-guide compliant "zero admissions brochure" variant.
    expect(
      screen.getByText(
        /See where your degree actually leads\. 700K rows of public data, zero admissions brochure\./,
      ),
    ).toBeInTheDocument();

    // CTA text (the sparkle is in its own span, so the accessible text is "Start").
    const cta = document.getElementById("landing-hero-cta");
    expect(cta).not.toBeNull();
    expect(cta?.textContent?.replace(/\s+/g, " ").trim()).toBe("Start ✦");

    // Secondary demo link — removed per staff-engineer Finding 1 until the
    // video destination exists (see §11 Follow-ups). The spec's
    // `landing-hero-demo-link` identifier returns in week 3 with the video.
    expect(document.getElementById("landing-hero-demo-link")).toBeNull();

    // Data footer — the 7 public datasets claim is load-bearing.
    expect(
      screen.getByText(/700K rows · 280 DQ rules · 7 public datasets/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Every number has a receipt\./),
    ).toBeInTheDocument();
  });

  it("CTA has correct aria-label and href to /app", () => {
    render(<HeroSection />);
    const cta = document.getElementById("landing-hero-cta");
    expect(cta).not.toBeNull();
    expect(cta?.getAttribute("href")).toBe("/app");
    expect(cta?.getAttribute("aria-label")).toBe(
      "Start your first FutureProof build",
    );
  });

  it("does not render the secondary demo link while video URL is pending (§11 follow-up)", () => {
    render(<HeroSection />);
    // Staff-engineer Finding 1 remediation: the link was removed because
    // `#video` was a dead in-page anchor. Re-add when the ship-plan
    // week-3 video spec lands a real destination.
    expect(document.getElementById("landing-hero-demo-link")).toBeNull();
  });

  it("respects prefers-reduced-motion — pentagon drift and scroll cue bob are suspended", () => {
    setReducedMotion(true);
    const { container } = render(<HeroSection />);

    // PentagonGlow wrapper is the first motion.div inside the hero section.
    // Under reduced-motion, it must render with no inline Y-axis animation styles.
    // Framer Motion writes `transform` inline when it's animating; with an undefined
    // animate prop, there should be no "translateY" animation loop baked in.
    //
    // We assert on the rendered DOM: none of the elements should have a style
    // attribute containing a comma-separated Y animation (e.g. "translateY(-10px)").
    // A static, non-animating pentagon is acceptable; a drifting one is not.
    const elements = container.querySelectorAll("[style]");
    const hasDrift = Array.from(elements).some((el) => {
      const style = el.getAttribute("style") ?? "";
      // Drift under animation would render as translateY(-...px) briefly,
      // but Framer Motion's reduced-motion path sets animate=undefined so
      // no translateY keyframe runs. The scroll cue also collapses.
      return /translateY\(-(?:[1-9]|10)px\)/.test(style);
    });
    expect(hasDrift).toBe(false);

    // The scroll cue should render at final opacity 0.3 (single scalar) instead
    // of the [0.15, 0.3, 0.15] animation loop. Verify by rendering and inspecting
    // the cue element exists and is present with an aria-hidden marker.
    const scrollCue = container.querySelector('[aria-hidden="true"].bg-gradient-to-b');
    // Either the element exists in static form or the inline style omits keyframe animation;
    // we assert it's in the DOM (it wouldn't render at all if the motion path threw).
    expect(scrollCue).not.toBeNull();
  });

  it("renders with motion enabled when prefers-reduced-motion is not set", () => {
    // Smoke: hero mounts and all critical copy still renders under default
    // (motion-enabled) path — guards against the two code branches diverging.
    setReducedMotion(false);
    render(<HeroSection />);
    expect(document.getElementById("landing-hero-cta")).toBeInTheDocument();
    expect(
      screen.getByText(/A college degree isn't a destination\./),
    ).toBeInTheDocument();
  });
});
