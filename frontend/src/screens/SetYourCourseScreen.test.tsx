/**
 * SetYourCourseScreen.test.tsx
 *
 * Smoke coverage for the unified Set Your Course screen:
 *   - Renders every load-bearing section (school input, effort/loans,
 *     commit + start-over buttons).
 *   - Commit navigates to /reveal.
 *   - Low-confidence resolution surfaces a soft nudge but does NOT
 *     disable the commit button (P1).
 *   - Start-over (after the confirm dialog) resets school / major /
 *     resolution / debug trace (P1).
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";

// Mock every API module the screen pulls in so no network escapes.
vi.mock("@/api/intent", () => ({
  streamIntent: vi.fn(async function* () {
    // No events — the screen stays in its idle state for these tests.
  }),
  dispatchChip: vi.fn(),
  commitResolution: vi.fn(),
}));
vi.mock("@/api/build", () => ({
  getOutcomes: vi.fn().mockResolvedValue([]),
  getTieredCareers: vi.fn().mockResolvedValue({
    common: [],
    less_common: [],
    stretch: [],
  }),
}));
vi.mock("@/api/client", () => ({
  apiGet: vi.fn().mockResolvedValue([]),
  apiPost: vi.fn().mockResolvedValue({ committed: true, logged: false }),
}));

import { commitResolution } from "@/api/intent";
import { SetYourCourseScreen } from "./SetYourCourseScreen";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderScreen() {
  return render(
    <MemoryRouter>
      <SetYourCourseScreen />
    </MemoryRouter>,
  );
}

function seedState(overrides: Partial<ReturnType<typeof useBuildInputStore.getState>> = {}) {
  useProfileStore.setState({
    profileName: "dancing happy bear 🐻",
    animalEmoji: "🐻",
    animalName: "bear",
  });
  useBuildInputStore.setState({
    phase: "major",
    school: {
      unitid: 151351,
      name: "Indiana University",
      institutionControl: null,
      netPriceAnnual: null,
      costOfAttendanceAnnual: null,
    },
    programs: [],
    major: null,
    effort: { level: "balanced", percentile: 50, ernShift: 0 },
    loans: { percentage: 50 },
    initialResolution: null,
    currentResolution: null,
    hasCorrected: false,
    debugTrace: null,
    ...overrides,
  });
  useBuildStore.setState({
    tieredCareers: null,
    selectedCareer: null,
  });
}

beforeEach(() => {
  mockNavigate.mockReset();
  vi.mocked(commitResolution).mockReset();
  vi.mocked(commitResolution).mockResolvedValue({
    committed: true,
    logged: false,
  });
});

// ---------------------------------------------------------------------------
// TestRender
// ---------------------------------------------------------------------------

describe("TestRender", () => {
  it("renders_all_sections — school, major, and commit surfaces all present", () => {
    seedState();
    renderScreen();

    // Mockup-aligned eyebrow + headline.
    expect(screen.getByText(/Where does this take you\?/i)).toBeInTheDocument();
    // School + major labels from the two-column layout.
    expect(screen.getByText(/^Your school$/i)).toBeInTheDocument();
    expect(screen.getByText(/^Your field of study$/i)).toBeInTheDocument();
    expect(screen.getByTestId("major-input")).toBeInTheDocument();
    // Commit + start over (desktop has these; mobile duplicates are in
    // the bottom bar, so just check for presence).
    expect(screen.getByTestId("btn-start-over")).toBeInTheDocument();
    expect(screen.getByTestId("btn-commit")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// TestFlow
// ---------------------------------------------------------------------------

describe("TestFlow", () => {
  it("commit_navigates_to_reveal — tapping commit with a valid resolution routes to /reveal", async () => {
    seedState({
      initialResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
    });

    renderScreen();
    const commit = screen.getByTestId("btn-commit");
    expect(commit).not.toBeDisabled();

    fireEvent.click(commit);

    await waitFor(() => {
      expect(commitResolution).toHaveBeenCalledTimes(1);
      expect(mockNavigate).toHaveBeenCalledWith("/reveal");
    });
  });
});

// ---------------------------------------------------------------------------
// TestLowConfidence (P1)
// ---------------------------------------------------------------------------

describe("TestLowConfidence", () => {
  it("commit_shows_nudge_not_gate — low-confidence resolution surfaces a soft nudge but leaves commit enabled", () => {
    seedState({
      initialResolution: {
        matched_cip: "51.0000",
        matched_title: "Something vaguely health-ish",
        confidence: "low",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: true,
        alternatives: null,
        parent_cip: "",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "51.0000",
        matched_title: "Something vaguely health-ish",
        confidence: "low",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: true,
        alternatives: null,
        parent_cip: "",
        confirmed_focus: null,
      },
    });

    renderScreen();
    const nudge = screen.getByTestId("soft-nudge");
    expect(nudge).toBeInTheDocument();
    expect(nudge.textContent).toMatch(/wasn't sure/i);
    // Commit is NOT disabled — low confidence is a nudge, not a gate.
    const commit = screen.getByTestId("btn-commit");
    expect(commit).not.toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// TestStartOver (P1)
// ---------------------------------------------------------------------------

describe("TestStartOver", () => {
  it("resets_state — confirming start-over clears school, major, resolution, debug trace", async () => {
    seedState({
      initialResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
      currentResolution: {
        matched_cip: "52.1401",
        matched_title: "Marketing",
        confidence: "high",
        reasoning: "",
        careers_preview: [],
        audit_flag: null,
        audit_message: null,
        needs_clarification: false,
        alternatives: [],
        parent_cip: "",
        confirmed_focus: null,
      },
      debugTrace: "prior trace",
    });

    renderScreen();

    // Open confirm dialog.
    fireEvent.click(screen.getByTestId("btn-start-over"));
    expect(await screen.findByTestId("confirm-start-over")).toBeInTheDocument();

    // Confirm.
    fireEvent.click(screen.getByTestId("btn-confirm-start-over"));

    await waitFor(() => {
      const state = useBuildInputStore.getState();
      expect(state.school).toBeNull();
      expect(state.major).toBeNull();
      expect(state.currentResolution).toBeNull();
      expect(state.initialResolution).toBeNull();
      expect(state.debugTrace).toBeNull();
    });
  });
});
