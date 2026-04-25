import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ProfileScreen } from "./ProfileScreen";
import { useProfileStore } from "@/store/profileStore";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderProfile() {
  return render(
    <MemoryRouter>
      <ProfileScreen />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  fetchMock.mockReset();
  mockNavigate.mockReset();
  useProfileStore.setState({
    profileName: "dancing happy bear",
    animalEmoji: "🐻",
    animalName: "bear",
  });
});

describe("ProfileScreen", () => {
  it("renders profile name", () => {
    renderProfile();
    expect(screen.getByText("Meet your guide")).toBeInTheDocument();
    expect(screen.getByText("dancing happy bear")).toBeInTheDocument();
  });

  it("reroll swaps name", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          profile_name: "bold swift fox",
          animal_emoji: "🦊",
          animal_name: "fox",
        }),
    });

    renderProfile();
    fireEvent.click(
      screen.getByRole("button", { name: "Generate a new profile name" }),
    );

    await waitFor(() => {
      expect(screen.getByText("bold swift fox")).toBeInTheDocument();
    });
  });

  it("auto-generates profile when none exists", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          profile_name: "calm true owl",
          animal_emoji: "🦉",
          animal_name: "owl",
        }),
    });
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
    renderProfile();
    expect(screen.getByText("Generating your character...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("calm true owl")).toBeInTheDocument();
    });
  });
});
