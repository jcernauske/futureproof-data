import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { LandingFooter } from "./LandingFooter";
import { resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";

/**
 * Section I — Footer tests.
 *
 * Current surface is the minimum-viable footer after staff-engineer Finding 1
 * remediation: wordmark + Live app link + disclaimer + data-line echo. The
 * Kaggle / GitHub / Video / Brightsmith / Voice guide / Disclaimers links were
 * removed because their destinations 404. They come back once the week-3
 * video, hackathon launch, and doc pages exist (see §11 Follow-ups).
 *
 * External links (when re-added) MUST carry target="_blank" rel="noopener
 * noreferrer" — these tests stay positioned to re-catch that requirement when
 * the broader nav returns.
 */

describe("LandingFooter", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  it("footer renders with id landing-footer and bg-bp-deep", () => {
    render(<LandingFooter />);
    const footer = document.getElementById("landing-footer");
    expect(footer).not.toBeNull();
    expect(footer?.tagName).toBe("FOOTER");
    expect(footer?.className).toContain("bg-bp-deep");
  });

  it("wordmark 'FutureProof' renders in the footer", () => {
    render(<LandingFooter />);
    expect(screen.getByText("FutureProof")).toBeInTheDocument();
  });

  it("Live app link renders with href=/app and opens in the same tab", () => {
    render(<LandingFooter />);
    const liveApp = document.getElementById("landing-footer-live-app");
    expect(liveApp).not.toBeNull();
    expect(liveApp?.tagName).toBe("A");
    expect(liveApp?.getAttribute("href")).toBe("/app");
    expect(liveApp?.getAttribute("target")).not.toBe("_blank");
    expect(liveApp?.textContent).toBe("Live app");
  });

  it("pre-launch: broken-destination footer links are absent (see §11 follow-ups)", () => {
    render(<LandingFooter />);
    // All six of these come back once their destinations exist. Until then,
    // rendering them would 404 a judge clicking through the footer — that's
    // what staff-engineer Finding 1 required us to cut.
    const pendingIds = [
      "landing-footer-kaggle",
      "landing-footer-github",
      "landing-footer-video",
      "landing-footer-brightsmith",
      "landing-footer-voice-guide",
      "landing-footer-disclaimers",
    ];
    pendingIds.forEach((id) => {
      expect(
        document.getElementById(id),
        `${id} must be absent until its destination exists`,
      ).toBeNull();
    });
  });

  it("disclaimer text matches voice guide exactly", () => {
    render(<LandingFooter />);
    expect(
      screen.getByText(
        "AI-estimated. Not a substitute for professional career counseling.",
      ),
    ).toBeInTheDocument();
  });

  it("data-line echo matches hero's data footer", () => {
    render(<LandingFooter />);
    expect(
      screen.getByText(
        /700K rows · 280 DQ rules · 7 public datasets · Every number has a receipt\./,
      ),
    ).toBeInTheDocument();
  });
});
