import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { DataSourcesSection } from "./DataSourcesSection";
import { resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";

/**
 * Section G — Data Sources tests.
 *
 * The seven row counts are CANONICAL per §4 Content Ground Truth. If any
 * count drifts — especially Karpathy (815, NOT 342) — these assertions
 * catch it before the landing page lies to judges.
 *
 * Spec §3.10 + §4 tie the table copy to three source-of-truth documents:
 *   - docs/specs/completed/three-signal-ai-exposure-composite-v3.md (Karpathy=815)
 *   - docs/specs/completed/ingest-anthropic-economic-index.md (Anthropic=587)
 *   - CIP-SOC crosswalk (626,406)
 */

describe("DataSourcesSection", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  it("renders headline 'How we know.' per voice guide", () => {
    render(<DataSourcesSection />);
    expect(screen.getByText("How we know.")).toBeInTheDocument();
  });

  it("renders all 7 dataset rows with spec-canonical identifiers", () => {
    render(<DataSourcesSection />);
    const expectedIds = [
      "landing-data-row-scorecard",
      "landing-data-row-bls",
      "landing-data-row-onet",
      "landing-data-row-karpathy",
      "landing-data-row-anthropic",
      "landing-data-row-bea",
      "landing-data-row-cipsoc",
    ];

    expectedIds.forEach((id) => {
      expect(document.getElementById(id)).not.toBeNull();
    });

    // Order matches spec §3.10 / §4 Content Ground Truth table order.
    const rows = Array.from(
      document.querySelectorAll<HTMLElement>(
        expectedIds.map((id) => `#${id}`).join(","),
      ),
    ).map((el) => el.id);
    expect(rows).toEqual(expectedIds);
  });

  it("each row displays the CANONICAL row count — catches future drift", () => {
    render(<DataSourcesSection />);

    // Exact counts per §4 Content Ground Truth. Karpathy = 815 is the
    // most drift-prone number (stale copies live in LICENSE_SOURCES.md
    // and elsewhere that claim 342).
    const expected: Record<string, string> = {
      "landing-data-row-scorecard": "69,947",
      "landing-data-row-bls": "832",
      "landing-data-row-onet": "798",
      "landing-data-row-karpathy": "815",
      "landing-data-row-anthropic": "587",
      "landing-data-row-bea": "51",
      "landing-data-row-cipsoc": "626,406",
    };

    Object.entries(expected).forEach(([id, count]) => {
      const row = document.getElementById(id);
      expect(row, `row ${id} must render`).not.toBeNull();
      expect(
        row?.textContent,
        `row ${id} must contain canonical count ${count}`,
      ).toContain(count);
    });
  });

  it("Karpathy row is explicitly 815, NOT the stale 342", () => {
    render(<DataSourcesSection />);
    const row = document.getElementById("landing-data-row-karpathy");
    expect(row).not.toBeNull();
    expect(row?.textContent).toContain("815");
    // Explicit negative: if someone reverts to the raw-source count, fail.
    expect(row?.textContent).not.toContain("342");
  });

  it("each row names what the dataset POWERS", () => {
    render(<DataSourcesSection />);
    const expected: Record<string, string> = {
      "landing-data-row-scorecard": "ERN, ROI, Loans",
      "landing-data-row-bls": "Growth, Ceiling",
      "landing-data-row-onet": "HMN, Burnout",
      "landing-data-row-karpathy": "RES baseline",
      "landing-data-row-anthropic": "RES confidence, velocity",
      "landing-data-row-bea": "Geo adjustment",
      "landing-data-row-cipsoc": "The core query",
    };

    Object.entries(expected).forEach(([id, powers]) => {
      const row = document.getElementById(id);
      expect(row?.textContent).toContain(powers);
    });
  });

  it("renders the footnote disambiguating composite AI exposure", () => {
    render(<DataSourcesSection />);
    expect(
      screen.getByText(
        /Composite AI exposure blends Gemma 4 task-level scoring, Karpathy's job-description baseline, and Anthropic's observed adoption share\./,
      ),
    ).toBeInTheDocument();
    // The "1.75 points more conservatively" spec-precise number must ship.
    expect(
      screen.getByText(/Gemma scores 1\.75 points more conservatively/),
    ).toBeInTheDocument();
  });
});
