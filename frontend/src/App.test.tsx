import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { AppRoutes } from "./App";
import { useProfileStore } from "@/store/profileStore";

vi.mock("@/api/session", () => ({
  getSession: vi.fn().mockResolvedValue(null),
  clearSession: vi.fn().mockResolvedValue(undefined),
}));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

describe("App routes", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("marketing Landing is rendered at /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(document.getElementById("landing-root")).toBeInTheDocument();
    expect(document.getElementById("landing-hero-cta")).toBeInTheDocument();
  });

  it("/app redirects to /set-your-course which bounces to /profile for auto-generation", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          profile_name: "calm true owl",
          animal_emoji: "🦉",
          animal_name: "owl",
        }),
    });
    render(
      <MemoryRouter initialEntries={["/app"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText("calm true owl"),
    ).toBeInTheDocument();
  });
});

describe("AppHeader visibility by route", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("does not render on marketing landing /", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(document.querySelector("header")).not.toBeInTheDocument();
  });

  it("renders header on /profile", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          profile_name: "bold swift fox",
          animal_emoji: "🦊",
          animal_name: "fox",
        }),
    });
    render(
      <MemoryRouter initialEntries={["/profile"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(document.querySelector("header")).toBeInTheDocument();
  });
});

describe("Profile-guard redirects", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("/menu redirects to /builds", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          profile_name: "calm true owl",
          animal_emoji: "🦉",
          animal_name: "owl",
        }),
    });
    render(
      <MemoryRouter initialEntries={["/menu"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText("calm true owl"),
    ).toBeInTheDocument();
  });

  it("ProfileScreen auto-generates profile when none exists", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          profile_name: "dancing happy bear",
          animal_emoji: "🐻",
          animal_name: "bear",
        }),
    });
    render(
      <MemoryRouter initialEntries={["/profile"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText("dancing happy bear"),
    ).toBeInTheDocument();
  });
});
