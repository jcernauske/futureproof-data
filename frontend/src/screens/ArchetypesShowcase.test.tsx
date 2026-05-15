import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ArchetypesShowcase } from "./ArchetypesShowcase";

const ORIGINAL_NINE = [
  "The Flagship",
  "All Sizzle, No Steak",
  "Good Work If You Can Get It",
  "Beware the AI Buzzsaw",
  "The Hidden Gem",
  "The Prestige Tax",
  "The Calling",
  "The Bull's Eye",
  "The Trades",
];

const MISSING_DATA_THREE = [
  "The Quiet Cohort",
  "Off the BLS Radar",
  "No Brand Gravity",
];

describe("ArchetypesShowcase", () => {
  it("default (/help) renders all 12 archetype aliases", () => {
    render(<ArchetypesShowcase />);
    for (const alias of [...ORIGINAL_NINE, ...MISSING_DATA_THREE]) {
      expect(
        screen.getByText(alias),
        `missing alias: ${alias}`,
      ).toBeInTheDocument();
    }
  });

  it("Kaggle path (showMissingData={false}) renders only the original 9", () => {
    render(<ArchetypesShowcase showMissingData={false} />);
    for (const alias of ORIGINAL_NINE) {
      expect(
        screen.getByText(alias),
        `missing original alias: ${alias}`,
      ).toBeInTheDocument();
    }
    for (const alias of MISSING_DATA_THREE) {
      expect(
        screen.queryByText(alias),
        `Kaggle path leaked missing-data alias: ${alias}`,
      ).not.toBeInTheDocument();
    }
  });

  it("missing-data cards carry their kickers (1 THIN PIPELINE + 2 DATA GAP)", () => {
    render(<ArchetypesShowcase />);
    expect(screen.getAllByText("THIN PIPELINE")).toHaveLength(1);
    expect(screen.getAllByText("DATA GAP")).toHaveLength(2);
  });

  it("page subhead acknowledges 12 cards on the help path", () => {
    render(<ArchetypesShowcase />);
    expect(
      screen.getByText("Same five stats. Twelve honest reads."),
    ).toBeInTheDocument();
  });

  it("page subhead stays at 9 on the Kaggle path", () => {
    render(<ArchetypesShowcase showMissingData={false} />);
    expect(
      screen.getByText("Same five stats. Nine honest verdicts."),
    ).toBeInTheDocument();
  });
});
