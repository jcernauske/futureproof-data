import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("@/api/menu", async () => {
  const actual = await vi.importActual<typeof import("@/api/menu")>(
    "@/api/menu",
  );
  return {
    ...actual,
    listBuilds: vi.fn().mockResolvedValue([]),
  };
});

vi.mock("@/api/client", () => ({
  apiPost: vi.fn().mockResolvedValue({}),
  apiGet: vi.fn().mockResolvedValue({}),
}));

import { AppHeader } from "./AppHeader";
import { useProfileStore } from "@/store/profileStore";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import { useBuildsCountStore } from "@/store/buildsCountStore";
import { useGauntletStore } from "@/store/gauntletStore";
import type {
  SchoolSelection,
  MajorSelection,
} from "@/types/buildInput";
import type { CareerOutcome } from "@/types/build";

const SCHOOL: SchoolSelection = {
  unitid: 100,
  name: "Indiana University",
  institutionControl: "Public",
  stateAbbr: "IN",
  netPriceAnnual: 10000,
  costOfAttendanceAnnual: 30000,
  tuitionInState: 10000,
  tuitionOutOfState: 36000,
};

const MAJOR: MajorSelection = {
  cipCode: "52.0801",
  cipTitle: "Finance",
  rawText: "finance",
  careersPreview: [],
  substitutionApplied: false,
  parentCip: "",
};

const CAREER: CareerOutcome = {
  soc_code: "13-2051",
  occupation_title: "Financial Analyst",
} as unknown as CareerOutcome;

function CurrentPath() {
  const location = useLocation();
  return <div data-testid="current-path">{location.pathname}</div>;
}

function renderHeader(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AppHeader />
      <Routes>
        <Route path="*" element={<CurrentPath />} />
      </Routes>
    </MemoryRouter>,
  );
}

function resetStores() {
  useProfileStore.setState({
    profileName: "calm true owl",
    animalEmoji: "🦉",
    animalName: "owl",
    homeState: null,
    locale: "en",
  });
  useBuildInputStore.setState({
    phase: "school",
    school: null,
    programs: [],
    major: null,
    effort: { level: "balanced", percentile: 50, ernShift: 0 },
    loans: { percentage: 50 },
    initialResolution: null,
    currentResolution: null,
    hasCorrected: false,
    debugTrace: null,
  });
  useBuildStore.setState({
    tieredCareers: null,
    selectedCareer: null,
    isBuilding: false,
    buildingStage: 0,
    build: null,
  });
  useBuildsCountStore.setState({ count: 0, loading: false, error: null });
  useGauntletStore.setState({
    phase: "intro",
    currentFightIndex: 0,
    fightPhase: "entrance",
    selectedSkillIds: new Set(),
    isRescoring: false,
    nextStepsContent: null,
    nextStepsError: false,
  });
}

describe("AppHeader — right-zone visibility rules", () => {
  beforeEach(() => {
    resetStores();
  });

  it("renders header on / (no landing page)", () => {
    renderHeader("/");
    expect(document.querySelector("header")).toBeInTheDocument();
  });

  it("hides all right-zone CTAs during active gauntlet fight", () => {
    useBuildInputStore.setState({ school: SCHOOL, major: MAJOR });
    useBuildStore.setState({ selectedCareer: CAREER });
    useBuildsCountStore.setState({ count: 3, loading: false, error: null });
    useGauntletStore.setState({ phase: "fighting" });
    renderHeader("/gauntlet");
    expect(screen.queryByTestId("header-my-builds")).not.toBeInTheDocument();
    expect(screen.queryByTestId("header-new-build")).not.toBeInTheDocument();
    expect(screen.queryByTestId("header-compare")).not.toBeInTheDocument();
  });

  it("still hides during final-boss phase of the gauntlet", () => {
    useBuildInputStore.setState({ school: SCHOOL, major: MAJOR });
    useBuildsCountStore.setState({ count: 3, loading: false, error: null });
    useGauntletStore.setState({ phase: "final_boss" });
    renderHeader("/gauntlet");
    expect(screen.queryByTestId("header-my-builds")).not.toBeInTheDocument();
    expect(screen.queryByTestId("header-new-build")).not.toBeInTheDocument();
    expect(screen.queryByTestId("header-compare")).not.toBeInTheDocument();
  });

  it("shows persistent CTAs on /gauntlet when phase is not active fight", () => {
    useBuildInputStore.setState({ school: SCHOOL, major: MAJOR });
    useBuildsCountStore.setState({ count: 3, loading: false, error: null });
    useGauntletStore.setState({ phase: "intro" });
    renderHeader("/gauntlet");
    expect(screen.getByTestId("header-my-builds")).toBeInTheDocument();
    expect(screen.getByTestId("header-new-build")).toBeInTheDocument();
    expect(screen.getByTestId("header-compare")).toBeInTheDocument();
  });

  it("always renders 'New Build' label (no Try Another flex)", () => {
    useBuildsCountStore.setState({ count: 1, loading: false, error: null });
    const { unmount } = renderHeader("/builds");
    expect(screen.getByTestId("header-new-build")).toHaveTextContent(
      "New Build",
    );
    // Persistent rack: My Builds icon is visible even on /builds for consistency.
    expect(screen.getByTestId("header-my-builds")).toBeInTheDocument();
    unmount();

    useBuildInputStore.setState({ school: SCHOOL, major: MAJOR });
    renderHeader("/my-build");
    expect(screen.getByTestId("header-new-build")).toHaveTextContent(
      "New Build",
    );
    expect(screen.getByTestId("header-my-builds")).toBeInTheDocument();
  });

  it("My Builds icon shows everywhere in-app regardless of count", () => {
    useBuildsCountStore.setState({ count: 0, loading: false, error: null });
    renderHeader("/profile");
    expect(screen.getByTestId("header-my-builds")).toBeInTheDocument();
    expect(screen.queryByTestId("header-builds-count")).not.toBeInTheDocument();
  });

  it("renders count badge when count >= 1, omits the badge node when count is 0 or null", () => {
    useBuildInputStore.setState({ school: SCHOOL });
    useBuildsCountStore.setState({ count: 3, loading: false, error: null });
    const { unmount } = renderHeader("/set-your-course");
    expect(screen.getByTestId("header-builds-count")).toHaveTextContent("3");
    unmount();

    useBuildsCountStore.setState({ count: 0, loading: false, error: null });
    renderHeader("/set-your-course");
    expect(screen.queryByTestId("header-builds-count")).not.toBeInTheDocument();
    expect(screen.getByTestId("header-my-builds")).toBeInTheDocument();
  });

  it("renders 9+ when count exceeds 9", () => {
    useBuildInputStore.setState({ school: SCHOOL });
    useBuildsCountStore.setState({ count: 12, loading: false, error: null });
    renderHeader("/my-build");
    expect(screen.getByTestId("header-builds-count")).toHaveTextContent("9+");
  });

  it("New Build is visible even with no school/major/career context", () => {
    useBuildsCountStore.setState({ count: 2, loading: false, error: null });
    renderHeader("/profile");
    expect(screen.getByTestId("header-new-build")).toBeInTheDocument();
    expect(screen.getByTestId("header-my-builds")).toBeInTheDocument();
  });

  it("Compare button is always visible in-app, disabled when count < 2", () => {
    useBuildsCountStore.setState({ count: 0, loading: false, error: null });
    const { unmount: u0 } = renderHeader("/my-build");
    expect(screen.getByTestId("header-compare")).toBeDisabled();
    u0();

    useBuildsCountStore.setState({ count: 1, loading: false, error: null });
    const { unmount: u1 } = renderHeader("/my-build");
    expect(screen.getByTestId("header-compare")).toBeDisabled();
    u1();

    useBuildsCountStore.setState({ count: 2, loading: false, error: null });
    renderHeader("/my-build");
    expect(screen.getByTestId("header-compare")).toBeEnabled();
  });

  it("Compare disabled aria-label explains how to enable it", () => {
    useBuildsCountStore.setState({ count: 0, loading: false, error: null });
    renderHeader("/my-build");
    expect(screen.getByTestId("header-compare")).toHaveAttribute(
      "aria-label",
      "Compare — save at least two builds to enable",
    );
  });

  it("Compare button navigates to /builds?select=1", () => {
    useBuildsCountStore.setState({ count: 3, loading: false, error: null });
    renderHeader("/my-build");
    fireEvent.click(screen.getByTestId("header-compare"));
    expect(screen.getByTestId("current-path")).toHaveTextContent("/builds");
  });

  it("aria-label on My Builds reflects the count", () => {
    useBuildInputStore.setState({ school: SCHOOL });
    useBuildsCountStore.setState({ count: 3, loading: false, error: null });
    renderHeader("/my-build");
    const button = screen.getByTestId("header-my-builds");
    expect(button).toHaveAttribute("aria-label", "My Builds (3)");
  });

  it("aria-label on My Builds reads 'nine or more' for 10+", () => {
    useBuildInputStore.setState({ school: SCHOOL });
    useBuildsCountStore.setState({ count: 50, loading: false, error: null });
    renderHeader("/my-build");
    const button = screen.getByTestId("header-my-builds");
    expect(button).toHaveAttribute("aria-label", "My Builds (9 or more)");
  });

  it("aria-label on New Build is consistent across routes", () => {
    useBuildInputStore.setState({ school: SCHOOL });
    const { unmount } = renderHeader("/my-build");
    expect(screen.getByTestId("header-new-build")).toHaveAttribute(
      "aria-label",
      "Start a new build",
    );
    unmount();

    renderHeader("/builds");
    expect(screen.getByTestId("header-new-build")).toHaveAttribute(
      "aria-label",
      "Start a new build",
    );
  });
});

describe("AppHeader — toast firing", () => {
  beforeEach(() => {
    resetStores();
  });

  it("fires the saved-to-builds toast on New Build when there is build context, not when there isn't", () => {
    useBuildInputStore.setState({ school: SCHOOL, major: MAJOR });
    useBuildStore.setState({ selectedCareer: CAREER });
    useBuildsCountStore.setState({ count: 1, loading: false, error: null });
    const { unmount } = renderHeader("/my-build");
    fireEvent.click(screen.getByTestId("header-new-build"));
    const toast = screen.getByTestId("header-toast");
    expect(toast).toHaveTextContent(
      "Indiana University · Finance saved to your builds",
    );
    unmount();

    // No-context route (/builds with no school/major/career) should NOT fire a toast.
    resetStores();
    useBuildsCountStore.setState({ count: 1, loading: false, error: null });
    renderHeader("/builds");
    fireEvent.click(screen.getByTestId("header-new-build"));
    expect(screen.queryByTestId("header-toast")).not.toBeInTheDocument();
  });

  it("toast omits the dot separator when only school is set", () => {
    useBuildInputStore.setState({ school: SCHOOL });
    renderHeader("/set-your-course");
    fireEvent.click(screen.getByTestId("header-new-build"));
    expect(screen.getByTestId("header-toast")).toHaveTextContent(
      "Indiana University saved to your builds",
    );
    expect(
      screen.getByTestId("header-toast").textContent ?? "",
    ).not.toContain("·");
  });

  // Toast auto-dismiss timing is covered in isolation by Toast.test.tsx.
  // Asserting it here is brittle because the AnimatePresence exit animation
  // can leave the node in the DOM with opacity:0 even after the close fires.
});

describe("AppHeader — Try Another navigation", () => {
  beforeEach(() => {
    resetStores();
  });

  it("Try Another clears profile + inputs and navigates to /profile", () => {
    useBuildInputStore.setState({ school: SCHOOL, major: MAJOR });
    useBuildStore.setState({ selectedCareer: CAREER });
    renderHeader("/my-build");
    fireEvent.click(screen.getByTestId("header-new-build"));
    expect(screen.getByTestId("current-path")).toHaveTextContent("/profile");
    expect(useProfileStore.getState().profileName).toBeNull();
    expect(useBuildInputStore.getState().school).toBeNull();
    expect(useBuildInputStore.getState().major).toBeNull();
  });
});
