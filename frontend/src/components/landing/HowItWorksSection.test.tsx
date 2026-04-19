import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { HowItWorksSection } from "./HowItWorksSection";
import { resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";

/**
 * Section C — How It Works tests.
 *
 * Three cards, three identifiers, three captions forming the spine
 * `see / fight / see`. Spec §3.6 copy ground truth is load-bearing
 * — if someone softens "You fight the bosses." into "You see the
 * fights." the RPG metaphor collapses.
 */

describe("HowItWorksSection", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  it("renders the section headline", () => {
    render(<HowItWorksSection />);
    expect(
      screen.getByText("Three things happen when you spec a build."),
    ).toBeInTheDocument();
  });

  it("renders three cards with identifiers landing-how-stats-card / gauntlet-card / branches-card", () => {
    render(<HowItWorksSection />);
    expect(
      document.getElementById("landing-how-stats-card"),
    ).toBeInTheDocument();
    expect(
      document.getElementById("landing-how-gauntlet-card"),
    ).toBeInTheDocument();
    expect(
      document.getElementById("landing-how-branches-card"),
    ).toBeInTheDocument();

    // All three must be <article> elements per spec §3.15.
    expect(
      document.getElementById("landing-how-stats-card")?.tagName,
    ).toBe("ARTICLE");
    expect(
      document.getElementById("landing-how-gauntlet-card")?.tagName,
    ).toBe("ARTICLE");
    expect(
      document.getElementById("landing-how-branches-card")?.tagName,
    ).toBe("ARTICLE");
  });

  it("STATS card has correct label, heading, and body copy", () => {
    render(<HowItWorksSection />);
    const card = document.getElementById("landing-how-stats-card");
    expect(card).not.toBeNull();
    expect(card?.textContent).toContain("STATS");
    expect(card?.textContent).toContain("You see the stats.");
    expect(card?.textContent).toContain(
      "Five numbers, one to ten. Every stat has a tappable receipt. No vibes, no admissions-brochure gloss — just where the number came from.",
    );
  });

  it("GAUNTLET card has correct label, heading, and body copy", () => {
    render(<HowItWorksSection />);
    const card = document.getElementById("landing-how-gauntlet-card");
    expect(card).not.toBeNull();
    expect(card?.textContent).toContain("GAUNTLET");
    expect(card?.textContent).toContain("You fight the bosses.");
    expect(card?.textContent).toContain(
      "Fight AI, Student Loans, the Market, Burnout, the Ceiling. Each boss is a real career threat, scored from real data. Lose one? Reroll with a skill, see what changes.",
    );
  });

  it("BRANCHES card has correct label, heading, and body copy", () => {
    render(<HowItWorksSection />);
    const card = document.getElementById("landing-how-branches-card");
    expect(card).not.toBeNull();
    expect(card?.textContent).toContain("BRANCHES");
    expect(card?.textContent).toContain("You see the branches.");
    expect(card?.textContent).toContain(
      "A degree isn't one job — it's a starting position. Tap any career and the tree unfolds: the ten other careers your major actually leads to, with the stat deltas that come with each.",
    );
  });

  it("each card contains decorative thematic art marked aria-hidden", () => {
    render(<HowItWorksSection />);
    const cards = [
      "landing-how-stats-card",
      "landing-how-gauntlet-card",
      "landing-how-branches-card",
    ];
    cards.forEach((id) => {
      const card = document.getElementById(id);
      // Each card has a decorative art element (aria-hidden div containing
      // a thematic SVG or styled DOM). Decorative art is intentionally
      // unannounced — the heading + body do the screen-reader work.
      const art = card?.querySelector("[aria-hidden]");
      expect(art).not.toBeNull();
    });
  });

  it("cards render in spec order (stats, gauntlet, branches)", () => {
    const { container } = render(<HowItWorksSection />);
    const cards = Array.from(
      container.querySelectorAll<HTMLElement>(
        "#landing-how-stats-card, #landing-how-gauntlet-card, #landing-how-branches-card",
      ),
    ).map((el) => el.id);

    expect(cards).toEqual([
      "landing-how-stats-card",
      "landing-how-gauntlet-card",
      "landing-how-branches-card",
    ]);
  });
});
