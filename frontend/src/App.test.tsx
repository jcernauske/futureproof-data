import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders FutureProof title", () => {
    render(<App />);
    expect(screen.getByText("FutureProof")).toBeInTheDocument();
  });

  it("renders with dark background", () => {
    render(<App />);
    const main = screen.getByRole("main");
    expect(main).toHaveClass("bg-bp-deep");
  });

  it("has accessible main landmark with aria-label", () => {
    render(<App />);
    const main = screen.getByRole("main", {
      name: "FutureProof design system shell",
    });
    expect(main).toBeInTheDocument();
  });

  it("renders API status indicator", () => {
    render(<App />);
    const status = screen.getByRole("status", {
      name: "Backend API connection status",
    });
    expect(status).toBeInTheDocument();
  });

  it("renders all six accent color swatches", () => {
    render(<App />);
    const expectedColors = [
      "thrive",
      "alert",
      "caution",
      "insight",
      "info",
      "empathy",
    ];
    for (const color of expectedColors) {
      expect(screen.getByText(color)).toBeInTheDocument();
    }
  });
});
