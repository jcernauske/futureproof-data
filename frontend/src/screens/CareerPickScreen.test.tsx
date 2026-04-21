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
    match_quality: null,
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
      parentCip: "",
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

describe("CareerPickScreen — lookup cip routing (regression)", () => {
  it("routes parentCip to /build/outcomes + /build/tier + /career-pick/chips when substitution applies", async () => {
    // Regression anchor: before the IU+Marketing fix, the screen sent
    // major.cipCode (the matched leaf, e.g. "52.14") to every endpoint.
    // When the school only reports the broad family cip, the backend
    // falls into the broaden-fallback and returns non-marketing careers.
    // The fix routes parentCip when it's non-empty.
    useBuildInputStore.setState({
      phase: "sliders",
      school: {
        unitid: 151351,
        name: "Indiana University-Bloomington",
        institutionControl: "Public",
        netPriceAnnual: null,
        costOfAttendanceAnnual: null,
      },
      programs: [],
      major: {
        cipCode: "52.14",
        cipTitle: "Marketing",
        rawText: "marketing",
        careersPreview: [],
        substitutionApplied: true,
        parentCip: "52.01",
      },
      effort: { level: "balanced", percentile: 50, ernShift: 0 },
      loans: { percentage: 50 },
    });

    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(mockGetOutcomes).toHaveBeenCalled();
    });

    // /build/outcomes must get the school's reported broad cip, not the
    // matched leaf — that's the cip the MCP substitution branch keys on.
    expect(mockGetOutcomes).toHaveBeenCalledWith(
      151351,
      "52.01",
      "balanced",
      0.5,
      "marketing",
    );

    // /build/tier must see the same lookup cip so tiering matches the
    // substituted career row set.
    await waitFor(() => {
      expect(mockGetTieredCareers).toHaveBeenCalled();
    });
    const tierArgs = mockGetTieredCareers.mock.calls[0]!;
    expect(tierArgs[3]).toBe("52.01");

    // /career-pick/chips: backend reads the same school row, same rule.
    await waitFor(() => {
      expect(mockGetCareerPickChips).toHaveBeenCalled();
    });
    expect(mockGetCareerPickChips.mock.calls[0]![0]).toMatchObject({
      cipcode: "52.01",
      majorText: "marketing",
    });
  });

  it("falls back to cipCode when parentCip is empty (school reports the leaf directly)", async () => {
    // Non-regression for schools that report the specific cip (e.g. ISU
    // reports 52.14 Marketing directly). parentCip="" → send cipCode.
    useBuildInputStore.setState({
      phase: "sliders",
      school: {
        unitid: 151111,
        name: "Indiana State University",
        institutionControl: "Public",
        netPriceAnnual: null,
        costOfAttendanceAnnual: null,
      },
      programs: [],
      major: {
        cipCode: "52.14",
        cipTitle: "Marketing",
        rawText: "marketing",
        careersPreview: [],
        substitutionApplied: false,
        parentCip: "",
      },
      effort: { level: "balanced", percentile: 50, ernShift: 0 },
      loans: { percentage: 50 },
    });

    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(mockGetOutcomes).toHaveBeenCalled();
    });
    expect(mockGetOutcomes.mock.calls[0]![1]).toBe("52.14");
  });
});

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

  it("tiers render stacked vertically", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    const common = screen.getByRole("region", { name: "Common career paths" });
    const outer = common.closest("[class*='grid-cols-1']");
    expect(outer).not.toBeNull();
    expect(outer!.className).not.toContain("desktop:grid-cols-3");
  });

  it("clicking a card populates the lineage sheet with that card's SOC", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    const cardBtn = screen.getByRole("button", {
      name: "Software Developers",
    });
    fireEvent.click(cardBtn);

    await waitFor(() => {
      expect(mockGetBranchesForSoc).toHaveBeenCalledWith("15-1252");
    });
  });

  it("no document-level commit CTA — commit lives inside the lineage sheet", async () => {
    // Proposal A redesign: the old "Build your career path" / "See my
    // build ✦" CTA at the bottom of the document was removed. The
    // commit action now lives inside the sheet's title-row primary
    // button ("Pick this path →" / "See my build ✦"). This test
    // guards the deletion so a future refactor doesn't silently
    // reintroduce a discoverability-hostile bottom CTA.
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: "Build your career path" }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: /See my build/i }),
    ).toBeNull();
  });

  it("renders the persistent You Picked chip when a career is committed", async () => {
    mockGetOutcomes.mockResolvedValueOnce([]);
    mockGetTieredCareers.mockResolvedValueOnce(TIERS);

    renderScreen();

    await waitFor(() => {
      expect(screen.getByText("Software Developers")).toBeInTheDocument();
    });

    // No pick → no chip.
    expect(screen.queryByRole("button", { name: "Clear pick" })).toBeNull();

    // Simulate the sheet having committed a pick (the sheet's CTA calls
    // onPick which sets selectedCareer in the store).
    useBuildStore.setState({ selectedCareer: TIERS.common[0]! });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Clear pick" }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getAllByText("Software Developers").length,
    ).toBeGreaterThanOrEqual(2); // once in the card, once in the chip

    // × button clears the pick.
    fireEvent.click(screen.getByRole("button", { name: "Clear pick" }));
    await waitFor(() => {
      expect(useBuildStore.getState().selectedCareer).toBeNull();
    });
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
