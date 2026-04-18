import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { CareerPickScreen } from "./CareerPickScreen";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import type { CareerOutcome, TieredCareers } from "@/types/build";

/**
 * CareerPickScreen tests
 *
 * The API layer is mocked at the module boundary so we can verify the
 * screen's logic in isolation — loading, error + retry, explore-vs-select
 * separation, CTA gating, navigation, and chip prefetch on mount.
 */

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockGetOutcomes = vi.fn();
const mockGetTieredCareers = vi.fn();
vi.mock("@/api/build", () => ({
  getOutcomes: (...args: unknown[]) => mockGetOutcomes(...args),
  getTieredCareers: (...args: unknown[]) => mockGetTieredCareers(...args),
}));

const mockGetCareerPickChips = vi.fn();
vi.mock("@/api/careerPick", () => ({
  getCareerPickChips: (...args: unknown[]) => mockGetCareerPickChips(...args),
  askCareerPickChip: vi.fn(),
}));

const mockGetBranchesForSoc = vi.fn();
vi.mock("@/api/tree", () => ({
  getTree: vi.fn(),
  getBranchesForSoc: (...args: unknown[]) => mockGetBranchesForSoc(...args),
}));

function makeCareer(soc: string, title: string, wage = 100000): CareerOutcome {
  return {
    unitid: 1,
    institution_name: "U",
    cipcode: "11.0701",
    program_name: "CS",
    soc_code: soc,
    occupation_title: title,
    soc_major_group_name: null,
    median_annual_wage: wage,
    earnings_1yr_median: null,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    net_price_annual: null,
    cost_of_attendance_annual: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    room_board_on_campus: null,
    stats: { ern: 7, roi: 6, res: 5, grw: 7, hmn: 5 },
    bosses: { ai: 5, loans: 3, market: 3, burnout: 4, ceiling: 4 },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: 5,
    overall_confidence: "high",
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    loan_pct: 0.5,
  };
}

const TIERS: TieredCareers = {
  common: [
    makeCareer("15-1252", "Software Developers"),
    makeCareer("15-1211", "Computer Systems Analysts"),
  ],
  less_common: [makeCareer("15-2051", "Data Scientists")],
  stretch: [makeCareer("15-1221", "Computer Research Scientists")],
};

beforeEach(() => {
  mockNavigate.mockReset();
  mockGetOutcomes.mockReset();
  mockGetTieredCareers.mockReset();
  mockGetCareerPickChips.mockReset().mockResolvedValue([]);
  mockGetBranchesForSoc.mockReset().mockResolvedValue([]);
  useBuildInputStore.setState({
    phase: "sliders",
    school: {
      unitid: 110635,
      name: "UC Berkeley",
      institutionControl: "Public",
      netPriceAnnual: null,
      costOfAttendanceAnnual: null,
    },
    programs: [],
    major: {
      cipCode: "11.0701",
      cipTitle: "Computer Science",
      rawText: "Computer Science",
      careersPreview: [],
      substitutionApplied: false,
    },
    effort: { level: "balanced", percentile: 50, ernShift: 0 },
    loans: { percentage: 50 },
  });
  useBuildStore.setState({
    tieredCareers: null,
    selectedCareer: null,
    isBuilding: false,
    buildingStage: 0,
    build: null,
    hasSeenStatTutorial: false,
  });
});

function renderScreen() {
  return render(
    <MemoryRouter>
      <CareerPickScreen />
    </MemoryRouter>,
  );
}

describe("CareerPickScreen", () => {
  it("renders all three tiers with their careers after load", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });
    expect(screen.getByText("Computer Systems Analysts")).toBeInTheDocument();
    expect(screen.getByText("Data Scientists")).toBeInTheDocument();
    expect(screen.getByText("Computer Research Scientists")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Common career paths" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Less Common career paths" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Stretch career paths" }),
    ).toBeInTheDocument();
  });

  it("tiers render stacked vertically, each individually collapsible", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    // Outer container is always single-column (no desktop:grid-cols-3).
    const common = screen.getByRole("region", { name: "Common career paths" });
    const outer = common.closest("[class*='grid-cols-1']");
    expect(outer).not.toBeNull();
    expect(outer!.className).not.toContain("desktop:grid-cols-3");

    // Each tier disclosure toggles independently.
    const stretchToggle = screen.getByRole("button", {
      name: /Stretch/,
      expanded: true,
    });
    fireEvent.click(stretchToggle);
    expect(stretchToggle).toHaveAttribute("aria-expanded", "false");

    // Clicking inside Common doesn't change Stretch's state.
    const commonSelectBtn = screen.getAllByRole("radio", {
      name: "Software Developers",
    })[0]!;
    fireEvent.click(commonSelectBtn);
    expect(stretchToggle).toHaveAttribute("aria-expanded", "false");
  });

  it("clicking a card populates the lineage sheet with that card's SOC", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    // Click the card body (not the inner pick button). The "Explore lineage
    // for {title}" button is the card root — onExplore fires on that click.
    const exploreBtn = screen.getByRole("button", {
      name: "Explore lineage for Software Developers",
    });
    fireEvent.click(exploreBtn);

    // Sheet fetches branches for the clicked SOC.
    await waitFor(() => {
      expect(mockGetBranchesForSoc).toHaveBeenCalledWith("15-1252");
    });

    // But onExplore must NOT commit the pick to the store.
    expect(useBuildStore.getState().selectedCareer).toBeNull();
  });

  it("explore and select are distinct gestures (spec §2 Decision #5)", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    const pickBtn = screen.getAllByRole("radio", {
      name: "Software Developers",
    })[0]!;
    fireEvent.click(pickBtn);

    await waitFor(() => {
      expect(useBuildStore.getState().selectedCareer?.soc_code).toBe(
        "15-1252",
      );
    });
    // Clicking the pick button must NOT populate the sheet.
    expect(mockGetBranchesForSoc).not.toHaveBeenCalled();
  });

  it("CTA is disabled until a career is selected, enabled after; commits → /reveal", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    const cta = screen.getByRole("button", { name: "Build your career path" });
    expect(cta).toBeDisabled();

    const pickBtn = screen.getAllByRole("radio", {
      name: "Software Developers",
    })[0]!;
    fireEvent.click(pickBtn);
    await waitFor(() => {
      expect(useBuildStore.getState().selectedCareer?.soc_code).toBe(
        "15-1252",
      );
    });
    expect(cta).not.toBeDisabled();

    fireEvent.click(cta);
    expect(mockNavigate).toHaveBeenCalledWith("/reveal");
  });

  it("error state renders Try Again; clicking it clears the error banner", async () => {
    mockGetOutcomes.mockRejectedValueOnce(new Error("Network down"));

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Network down")).toBeInTheDocument();
    });
    const retryBtn = screen.getByRole("button", { name: "Try Again" });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.queryByText("Network down")).not.toBeInTheDocument();
    });
  });

  it("redirects to /school and sets session-expired hint when school/major missing", async () => {
    useBuildInputStore.setState({
      phase: "school",
      school: null,
      programs: [],
      major: null,
      effort: { level: "balanced", percentile: 50, ernShift: 0 },
      loans: { percentage: 50 },
    });
    sessionStorage.removeItem("fp-nav-hint");

    renderScreen();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/school", { replace: true });
    });
    expect(sessionStorage.getItem("fp-nav-hint")).toBe("session-expired");
    expect(mockGetOutcomes).not.toHaveBeenCalled();
  });

  it("prefetches chips on mount once tiered careers resolve", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);
    mockGetCareerPickChips.mockResolvedValueOnce([
      {
        id: "what_does_this_do",
        label: "What does this career actually do?",
        elevated: false,
        terminal_title: null,
      },
    ]);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockGetCareerPickChips).toHaveBeenCalledWith({
        cipcode: "11.0701",
        majorText: "Computer Science",
        socCodes: ["15-1252", "15-1211", "15-2051", "15-1221"],
      });
    });
  });
});
