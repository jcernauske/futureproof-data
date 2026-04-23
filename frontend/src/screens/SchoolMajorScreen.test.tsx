import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { SchoolMajorScreen } from "./SchoolMajorScreen";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";

/**
 * SchoolMajorScreen session-expired banner test.
 *
 * RevealScreen and CareerPickScreen set sessionStorage["fp-nav-hint"] =
 * "session-expired" before redirecting here when upstream state is lost.
 * This screen must:
 *   1. Read the hint on mount
 *   2. Show the banner
 *   3. Clear the hint (so it doesn't resurface on subsequent navigations)
 *   4. Hide the banner after 6 seconds
 */

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

beforeEach(() => {
  mockNavigate.mockReset();
  sessionStorage.clear();
  // Seed a profile so the screen doesn't redirect to "/"
  useProfileStore.setState({
    profileName: "dancing happy bear",
    animalEmoji: "🐻",
    animalName: "bear",
  });
  useBuildInputStore.setState({
    phase: "school",
    school: null,
    programs: [],
    major: null,
    effort: { level: "balanced", percentile: 50, ernShift: 0 },
    loans: { percentage: 50 },
  });
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("SchoolMajorScreen — session-expired banner", () => {
  it("shows banner when fp-nav-hint=session-expired and clears the hint", async () => {
    sessionStorage.setItem("fp-nav-hint", "session-expired");

    render(
      <MemoryRouter>
        <SchoolMajorScreen />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Your session reset\. Pick your school and major/),
      ).toBeInTheDocument();
    });
    // Hint must be consumed on mount so it doesn't fire again.
    expect(sessionStorage.getItem("fp-nav-hint")).toBeNull();
  });

  it("does not re-show banner on a second mount after the hint was consumed", async () => {
    sessionStorage.setItem("fp-nav-hint", "session-expired");

    const first = render(
      <MemoryRouter>
        <SchoolMajorScreen />
      </MemoryRouter>,
    );
    // Hint read + banner shown on first mount.
    await waitFor(() => {
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
    expect(sessionStorage.getItem("fp-nav-hint")).toBeNull();
    first.unmount();

    // Second mount (e.g., user navigates back later). No hint -> no banner.
    render(
      <MemoryRouter>
        <SchoolMajorScreen />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("does NOT show banner when hint is absent", () => {
    render(
      <MemoryRouter>
        <SchoolMajorScreen />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/Your session reset/)).not.toBeInTheDocument();
  });
});
