import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { LandingScreen } from "./LandingScreen";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const noSessionResponse = { ok: false, status: 404 } as Response;

function renderLanding() {
  return render(
    <MemoryRouter>
      <LandingScreen />
    </MemoryRouter>,
  );
}

async function renderLandingAndWait() {
  fetchMock.mockResolvedValueOnce(noSessionResponse);
  renderLanding();
  await screen.findByRole("button", { name: "Start building your future" });
}

beforeEach(() => {
  fetchMock.mockReset();
  mockNavigate.mockReset();
});

describe("LandingScreen", () => {
  it("renders tagline and CTA", async () => {
    await renderLandingAndWait();
    expect(
      screen.getByText(/A college degree isn't a destination/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Start building your future" }),
    ).toBeInTheDocument();
  });

  it("CTA calls API and navigates to /profile", async () => {
    await renderLandingAndWait();

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          profile_name: "dancing happy bear",
          animal_emoji: "🐻",
          animal_name: "bear",
        }),
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Start building your future" }),
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/profile");
    });
  });

  it("shows error on API failure", async () => {
    await renderLandingAndWait();

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "Server error" }),
    });

    fireEvent.click(
      screen.getByRole("button", { name: "Start building your future" }),
    );

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });
});
