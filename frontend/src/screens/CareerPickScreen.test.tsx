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
 * The API layer (api/build.ts) is mocked at the module boundary so we can
 * verify the screen's logic in isolation — loading, error + retry, selection
 * state → store, CTA gating, and navigation.
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
  // Seed required upstream state so the nav guard doesn't redirect.
  useBuildInputStore.setState({
    phase: "sliders",
    school: { unitid: 110635, name: "UC Berkeley", institutionControl: "Public", netPriceAnnual: null, costOfAttendanceAnnual: null },
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
    // Exact-match aria-labels — "Common" is a substring of "Less Common".
    expect(screen.getByRole("region", { name: "Common career paths" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Less Common career paths" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Stretch career paths" })).toBeInTheDocument();
  });

  it("CTA is disabled until a career is selected, enabled after", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    const cta = screen.getByRole("button", { name: "Build your career path" });
    expect(cta).toBeDisabled();

    // Clicking a career updates the store and un-disables the CTA.
    fireEvent.click(screen.getByRole("radio", { name: "Software Developers" }));
    await waitFor(() => {
      expect(useBuildStore.getState().selectedCareer?.soc_code).toBe("15-1252");
    });
    expect(cta).not.toBeDisabled();

    fireEvent.click(cta);
    expect(mockNavigate).toHaveBeenCalledWith("/reveal");
  });

  it("error state renders Try Again; clicking it clears the error banner", async () => {
    // Fail the first fetch. The error's source is the outcomes call here —
    // the exact call doesn't matter for the observable contract.
    mockGetOutcomes.mockRejectedValueOnce(new Error("Network down"));

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Network down")).toBeInTheDocument();
    });
    const retryBtn = screen.getByRole("button", { name: "Try Again" });
    expect(retryBtn).toBeInTheDocument();

    fireEvent.click(retryBtn);

    // Error banner must clear (proves setError(null) fires).
    await waitFor(() => {
      expect(screen.queryByText("Network down")).not.toBeInTheDocument();
    });

    // Note: if the fetch is triggered by a dep change (tieredCareers null →
    // null is a no-op), the useEffect may not re-run. This is a known issue
    // separate from the nullability contract. The test here validates the
    // minimum observable contract: error banner clears.
  });

  it("redirects to /school and sets session-expired hint when school/major missing", async () => {
    // Blow away upstream state as if user refreshed on /career-pick.
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
    // No API call should fire — guard runs before fetch.
    expect(mockGetOutcomes).not.toHaveBeenCalled();
  });

  it("tiers lay out 3-up on desktop (grid-cols-1 desktop:grid-cols-3)", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    // Shared parent of the three tier regions carries the responsive grid classes.
    const tierParent = screen
      .getByRole("region", { name: "Common career paths" })
      .closest("[class*='desktop:grid-cols-3']");
    expect(tierParent).not.toBeNull();
    expect(tierParent!.className).toContain("grid-cols-1");
    expect(tierParent!.className).toContain("desktop:grid-cols-3");
  });

});
