import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AboutScreen } from "./AboutScreen";

function renderAbout() {
  return render(
    <MemoryRouter>
      <AboutScreen />
    </MemoryRouter>,
  );
}

describe("AboutScreen", () => {
  it("renders the page header with kicker, headline, and subhead", () => {
    renderAbout();
    expect(screen.getByText("About")).toBeInTheDocument();
    expect(screen.getByText("Where the numbers come from.")).toBeInTheDocument();
  });

  it("renders all 11 data-source cards plus the Gemma model card", () => {
    renderAbout();
    const ids = [
      "scorecard-field",
      "scorecard-institution",
      "bls-ooh",
      "onet",
      "cip-soc",
      "karpathy",
      "anthropic-econ",
      "bea-rpp",
      "ipeds-finance",
      "eada",
      "bls-oews",
      "gemma-4",
    ];
    for (const id of ids) {
      expect(screen.getByTestId(`source-card-${id}`)).toBeInTheDocument();
    }
  });

  it("renders the Bronze/Silver/Gold pipeline strip", () => {
    renderAbout();
    expect(screen.getByText("Bronze · Raw")).toBeInTheDocument();
    expect(screen.getByText("Silver · Normalized")).toBeInTheDocument();
    expect(screen.getByText("Gold · Consumable")).toBeInTheDocument();
  });

  it("flags Gemma as the model layer with variant=model", () => {
    renderAbout();
    const gemma = screen.getByTestId("source-card-gemma-4");
    expect(gemma.getAttribute("data-variant")).toBe("model");
  });

  it("flags Karpathy as variant=acad and Anthropic as variant=priv", () => {
    renderAbout();
    expect(
      screen.getByTestId("source-card-karpathy").getAttribute("data-variant"),
    ).toBe("acad");
    expect(
      screen.getByTestId("source-card-anthropic-econ").getAttribute("data-variant"),
    ).toBe("priv");
  });

  it("flags caveats on Scorecard Field, CIP-SOC, Karpathy, Anthropic, and EADA", () => {
    renderAbout();
    const expectCaveat = [
      "scorecard-field",
      "cip-soc",
      "karpathy",
      "anthropic-econ",
      "eada",
    ];
    for (const id of expectCaveat) {
      expect(
        screen.getByTestId(`source-card-${id}`).getAttribute("data-has-caveat"),
      ).toBe("true");
    }
  });

  it("links each source card to its official URL", () => {
    renderAbout();
    const blsOews = screen.getByTestId("source-card-bls-oews");
    expect(blsOews.getAttribute("href")).toBe("https://www.bls.gov/oes/");
    expect(blsOews.getAttribute("target")).toBe("_blank");
    expect(blsOews.getAttribute("rel")).toBe("noopener noreferrer");
  });
});
