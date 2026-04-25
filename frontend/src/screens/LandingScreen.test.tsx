import { render } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { LandingScreen } from "./LandingScreen";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

describe("LandingScreen", () => {
  it("redirects to /set-your-course", () => {
    render(
      <MemoryRouter>
        <LandingScreen />
      </MemoryRouter>,
    );
    expect(mockNavigate).toHaveBeenCalledWith("/set-your-course", { replace: true });
  });
});
