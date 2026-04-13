import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders landing screen at root route", () => {
    render(<App />);
    expect(
      screen.getByText(/A college degree isn't a destination/),
    ).toBeInTheDocument();
  });

  it("renders CTA button", () => {
    render(<App />);
    expect(
      screen.getByRole("button", { name: "Start building your future" }),
    ).toBeInTheDocument();
  });
});
