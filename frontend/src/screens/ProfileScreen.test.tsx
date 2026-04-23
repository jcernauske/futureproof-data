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
    expect(screen.getByText("We'll call you")).toBeInTheDocument();
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

  it("lookup found navigates", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          found: true,
          profile_name: "calm true owl",
          animal_emoji: "🦉",
          animal_name: "owl",
          builds: [],
        }),
    });

    renderProfile();
    fireEvent.click(screen.getByText("Already have a name?"));
    const input = screen.getByPlaceholderText("Type your name...");
    fireEvent.change(input, { target: { value: "calm true owl" } });
    fireEvent.click(screen.getByRole("button", { name: "Look up profile" }));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/school");
    });
  });

  it("lookup suggestion shown", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          found: false,
          suggestion: "steady bold turtle 🐢",
        }),
    });

    renderProfile();
    fireEvent.click(screen.getByText("Already have a name?"));
    const input = screen.getByPlaceholderText("Type your name...");
    fireEvent.change(input, { target: { value: "steaby blod turtl" } });
    fireEvent.click(screen.getByRole("button", { name: "Look up profile" }));

    await waitFor(() => {
      expect(
        screen.getByText((_, el) =>
          el?.textContent === "Did you mean steady bold turtle 🐢?" || false,
        ),
      ).toBeInTheDocument();
    });
  });

  it("lookup not found shows error", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          found: false,
        }),
    });

    renderProfile();
    fireEvent.click(screen.getByText("Already have a name?"));
    const input = screen.getByPlaceholderText("Type your name...");
    fireEvent.change(input, { target: { value: "nonexistent name" } });
    fireEvent.click(screen.getByRole("button", { name: "Look up profile" }));

    await waitFor(() => {
      expect(
        screen.getByText("No profile found with that name."),
      ).toBeInTheDocument();
    });
  });

  it("redirects to /app if no profile", () => {
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
    renderProfile();
    expect(mockNavigate).toHaveBeenCalledWith("/app");
  });
});
