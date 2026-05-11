import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { AppRoutes } from "./App";
import { useProfileStore } from "@/store/profileStore";
import { useBuildsCountStore } from "@/store/buildsCountStore";

vi.mock("@/api/session", () => ({
  clearSession: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/api/menu", async () => {
  const actual = await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    listBuilds: vi.fn().mockResolvedValue([]),
  };
});

// AppHeader mounts InferenceBadge which fetches /health on mount via fetch().
// Without this mock, the badge's request would consume the test's first
// fetchMock.mockResolvedValueOnce, causing profile-generation tests to fail.
vi.mock("@/api/health", () => ({
  fetchHealth: vi.fn().mockResolvedValue({
    status: "ok",
    project: "futureproof",
    version: "0.1.0",
    inference_backend: "ollama",
    inference_model: "gemma4:e4b",
  }),
}));

const profileResponseQueue: Array<() => Promise<unknown>> = [];

const fetchMock = vi.fn((url: string, _init?: RequestInit) => {
  if (typeof url === "string" && url.includes("/health/warmup")) {
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  }
  const next = profileResponseQueue.shift();
  if (next) return next();
  return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
});
vi.stubGlobal("fetch", fetchMock);

function enqueueProfile(data: { profile_name: string; animal_emoji: string; animal_name: string }) {
  profileResponseQueue.push(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(data) }),
  );
}

describe("App routes", () => {
  beforeEach(() => {
    fetchMock.mockClear();
    profileResponseQueue.length = 0;
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("/ redirects to /set-your-course which bounces to /profile for auto-generation", async () => {
    enqueueProfile({ profile_name: "calm true owl", animal_emoji: "🦉", animal_name: "owl" });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(
      await screen.findByText("calm true owl"),
    ).toBeInTheDocument();
  });

  // Regression guard for refactor-prune-deprecated-build-flow.
  // /reveal previously rendered RevealScreen (which mounted the
  // "Fight the Bosses" CTA + CareerDetail). After the prune, /reveal
  // is unmapped — the route table should produce no RevealScreen content.
  it("/reveal route is not declared (regression: dead route stays dead)", () => {
    render(
      <MemoryRouter initialEntries={["/reveal"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    // RevealScreen's signature CTA must not render.
    expect(screen.queryByText(/Fight the Bosses/i)).not.toBeInTheDocument();
    // Defense in depth: /reveal must NOT silently redirect anywhere
    // that surfaces BuildResultsScreen content either.
    expect(screen.queryByRole("region", { name: /finances/i })).not.toBeInTheDocument();
    // And no SetYourCourseScreen content should appear (no implicit redirect).
    expect(screen.queryByText(/Spec my build/i)).not.toBeInTheDocument();
  });

  // Regression guard for refactor-prune-deprecated-build-flow.
  // /career-pick previously rendered CareerPickScreen (tier sections,
  // "You picked" persistent chip). After the prune, /career-pick is
  // unmapped — the route table should produce no CareerPickScreen content.
  it("/career-pick route is not declared (regression: dead route stays dead)", () => {
    render(
      <MemoryRouter initialEntries={["/career-pick"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    // CareerPickScreen's "You picked" persistent chip must not render.
    expect(screen.queryByText(/You picked/i)).not.toBeInTheDocument();
    // Tier section copy from CareerPickScreen must not render.
    expect(screen.queryByText(/Pick a path/i)).not.toBeInTheDocument();
    // Defense in depth: must not silently redirect to a live screen.
    expect(screen.queryByText(/Spec my build/i)).not.toBeInTheDocument();
  });

});

describe("AppHeader visibility by route", () => {
  beforeEach(() => {
    fetchMock.mockClear();
    profileResponseQueue.length = 0;
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
    useBuildsCountStore.setState({ count: 0, loading: false, error: null });
  });

  it("renders header on / (redirects to app)", async () => {
    enqueueProfile({ profile_name: "calm true owl", animal_emoji: "🦉", animal_name: "owl" });
    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(document.querySelector("header")).toBeInTheDocument();
  });

  it("renders header on /profile", async () => {
    enqueueProfile({ profile_name: "bold swift fox", animal_emoji: "🦊", animal_name: "fox" });
    render(
      <MemoryRouter initialEntries={["/profile"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(document.querySelector("header")).toBeInTheDocument();
  });

  it("renders New Build and My Builds on /profile (persistent rack)", async () => {
    enqueueProfile({ profile_name: "bold swift fox", animal_emoji: "🦊", animal_name: "fox" });
    render(
      <MemoryRouter initialEntries={["/profile"]}>
        <AppRoutes />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("header-new-build")).toBeInTheDocument();
    expect(screen.getByTestId("header-my-builds")).toBeInTheDocument();
  });

});

describe("Profile-guard redirects", () => {
  beforeEach(() => {
    fetchMock.mockClear();
    profileResponseQueue.length = 0;
    useProfileStore.setState({
      profileName: null,
      animalEmoji: null,
      animalName: null,
    });
  });

  it("/menu redirects to /builds", async () => {
    enqueueProfile({ profile_name: "calm true owl", animal_emoji: "🦉", animal_name: "owl" });
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
    enqueueProfile({ profile_name: "dancing happy bear", animal_emoji: "🐻", animal_name: "bear" });
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
