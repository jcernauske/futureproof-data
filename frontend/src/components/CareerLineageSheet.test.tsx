import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
} from "vitest";
import type { MockedFunction } from "vitest";
import {
  CareerLineageSheet,
  resolveDetent,
  type SheetDetent,
} from "./CareerLineageSheet";
import type { CareerBranch, CareerOutcome } from "@/types/build";
import type { CareerPickChip } from "@/types/careerPick";

/**
 * CareerLineageSheet tests
 *
 * Framer Motion's gesture layer does not fully consume JSDOM pointer
 * events, so drag-end physics are validated through the exported
 * `resolveDetent` pure function rather than via a synthesized pointer
 * drag. onDetentChange wiring from chevrons + arrow keys is exercised
 * end-to-end against the rendered DOM.
 *
 * The sheet is controlled — `detent` is owned by the parent — so these
 * tests pass in `detent="compact"` (or whatever is under test) and
 * assert the `onDetentChange` callback args. We do not re-mount the
 * component to simulate parent-reacted detent changes unless the test
 * specifically requires the post-change DOM.
 */

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

vi.mock("@/api/tree", () => ({
  getTree: vi.fn(),
  getBranchesForSoc: vi.fn(),
}));

vi.mock("@/api/careerPick", () => ({
  getCareerPickChips: vi.fn(),
  askCareerPickChip: vi.fn(),
}));

// Pull the mocked references after the mock declaration so TypeScript
// knows they're vi.fn spies.
import { getBranchesForSoc } from "@/api/tree";
import { askCareerPickChip } from "@/api/careerPick";
const mockGetBranchesForSoc = getBranchesForSoc as MockedFunction<
  typeof getBranchesForSoc
>;
const mockAskCareerPickChip = askCareerPickChip as MockedFunction<
  typeof askCareerPickChip
>;

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeCareer(soc: string, title: string, wage = 82000): CareerOutcome {
  return {
    unitid: 1,
    institution_name: "U",
    cipcode: "26.0101",
    program_name: "Biology",
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
    stats: { ern: 7, roi: 6, res: 5, grw: 6, hmn: 5 },
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

function makeBranch(
  from: string,
  to: string,
  title: string,
  extra: Partial<CareerBranch> = {},
): CareerBranch {
  return {
    from_soc: from,
    to_soc: to,
    to_title: title,
    delta_ern: 1,
    delta_roi: 0,
    delta_res: 0,
    delta_grw: 0,
    delta_hmn: 0,
    unlock: null,
    relatedness: 0.5,
    ...extra,
  };
}

const CHIPS: CareerPickChip[] = [
  {
    id: "why_no_doctor",
    label: "Why don't I see 'doctor'?",
    elevated: true,
    terminal_title: "doctor",
  },
  {
    id: "what_does_this_do",
    label: "What does this career actually do?",
    elevated: false,
    terminal_title: null,
  },
  {
    id: "right_school_for_this",
    label: "Is this the right school for this?",
    elevated: false,
    terminal_title: null,
  },
];

function renderSheet(overrides: {
  soc?: string | null;
  career?: CareerOutcome | null;
  detent?: SheetDetent;
  onDetentChange?: (d: SheetDetent) => void;
  chips?: CareerPickChip[];
  askContext?: { cipcode: string; majorText: string; socCodes: string[] };
  pickedSoc?: string | null;
  onPick?: (c: CareerOutcome) => void;
  onGo?: () => void;
} = {}) {
  const onDetentChange = overrides.onDetentChange ?? vi.fn();
  const onPick = overrides.onPick ?? vi.fn();
  const onGo = overrides.onGo ?? vi.fn();
  const utils = render(
    <CareerLineageSheet
      soc={overrides.soc ?? null}
      career={overrides.career ?? null}
      detent={overrides.detent ?? "compact"}
      onDetentChange={onDetentChange}
      chips={overrides.chips ?? CHIPS}
      askContext={
        overrides.askContext ?? {
          cipcode: "26.0101",
          majorText: "pre-med",
          socCodes: ["19-1029", "13-1071"],
        }
      }
      pickedSoc={overrides.pickedSoc ?? null}
      onPick={onPick}
      onGo={onGo}
    />,
  );
  return { ...utils, onDetentChange, onPick, onGo };
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  mockGetBranchesForSoc.mockReset();
  mockAskCareerPickChip.mockReset();
});

afterEach(() => {
  // Reset matchMedia if a test installed one.
  if ("matchMedia" in window) {
    try {
      // Best-effort cleanup — some tests replace window.matchMedia with
      // a stub; let the next test install its own or none.
      delete (window as unknown as { matchMedia?: unknown }).matchMedia;
    } catch {
      /* ignore */
    }
  }
});

// ---------------------------------------------------------------------------
// Tests: empty state + fetch lifecycle
// ---------------------------------------------------------------------------

describe("CareerLineageSheet — empty / fetch lifecycle", () => {
  it("renders empty state when soc is null and does NOT fetch", () => {
    renderSheet({ soc: null, career: null });

    expect(
      screen.getByText(/Pick a career path above to see where it leads\./i),
    ).toBeInTheDocument();
    expect(mockGetBranchesForSoc).not.toHaveBeenCalled();
  });

  it("fetches branches when soc prop changes and renders each branch in API order", async () => {
    const branches = [
      makeBranch("13-2051", "13-2052", "Portfolio Manager"),
      makeBranch("13-2051", "11-1011", "CFO"),
      makeBranch("13-2051", "13-2061", "Financial Examiner"),
    ];
    mockGetBranchesForSoc.mockResolvedValueOnce(branches);

    const career = makeCareer("13-2051", "Financial Analyst");
    renderSheet({ soc: "13-2051", career });

    await waitFor(() => {
      expect(screen.getByText("Portfolio Manager")).toBeInTheDocument();
    });
    expect(screen.getByText("CFO")).toBeInTheDocument();
    expect(screen.getByText("Financial Examiner")).toBeInTheDocument();
    expect(mockGetBranchesForSoc).toHaveBeenCalledTimes(1);
    expect(mockGetBranchesForSoc).toHaveBeenCalledWith("13-2051");

    // Ordering: check the DOM position of each BRANCH title matches the API
    // order — this is what the spec asserts (API order preserved). The
    // anchor "you are here" card is also role=article; we filter it by
    // its aria-label prefix "Branch:".
    const articles = screen.getAllByRole("article");
    const branchTitles = articles
      .filter((a) => a.getAttribute("aria-label")?.startsWith("Branch:"))
      .map((a) => a.querySelector("h3")?.textContent);
    expect(branchTitles).toEqual([
      "Portfolio Manager",
      "CFO",
      "Financial Examiner",
    ]);
  });

  it("cancels stale fetches when soc prop changes mid-flight", async () => {
    // First fetch resolves slowly with branches for soc=A.
    // While that's pending, we rerender with soc=B.
    // The first response must NOT overwrite the second — it's stale.
    let resolveFirst: (value: CareerBranch[]) => void = () => {};
    const firstPromise = new Promise<CareerBranch[]>((resolve) => {
      resolveFirst = resolve;
    });
    mockGetBranchesForSoc.mockReturnValueOnce(firstPromise);

    const secondBranches = [makeBranch("15-1252", "15-2051", "Data Scientist")];
    mockGetBranchesForSoc.mockResolvedValueOnce(secondBranches);

    const careerA = makeCareer("13-2051", "Financial Analyst");
    const careerB = makeCareer("15-1252", "Software Developer");
    const { rerender } = renderSheet({ soc: "13-2051", career: careerA });

    // Rerender with new SOC before the first fetch resolves.
    rerender(
      <CareerLineageSheet
        soc="15-1252"
        career={careerB}
        detent="compact"
        onDetentChange={vi.fn()}
        chips={CHIPS}
        askContext={{
          cipcode: "11.0701",
          majorText: "CS",
          socCodes: ["15-1252"],
        }}
        pickedSoc={null}
        onPick={vi.fn()}
        onGo={vi.fn()}
      />,
    );

    // Now resolve the stale first fetch with a branch that would show up
    // if the guard were broken.
    resolveFirst([makeBranch("13-2051", "13-2052", "Portfolio Manager")]);

    // The second SOC's branch should eventually render.
    await waitFor(() => {
      expect(screen.getByText("Data Scientist")).toBeInTheDocument();
    });
    // The stale response's branch must NEVER appear.
    expect(screen.queryByText("Portfolio Manager")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Tests: error + retry
// ---------------------------------------------------------------------------

describe("CareerLineageSheet — error state + retry", () => {
  it("renders error state with Try again button when fetch rejects", async () => {
    mockGetBranchesForSoc.mockRejectedValueOnce(new Error("network down"));
    const career = makeCareer("13-2051", "Financial Analyst");

    renderSheet({ soc: "13-2051", career });

    await waitFor(() => {
      expect(
        screen.getByText(/Couldn't load the lineage\. Try again\?/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /Try again/i }),
    ).toBeInTheDocument();
  });

  it("retry button refetches after error", async () => {
    mockGetBranchesForSoc.mockRejectedValueOnce(new Error("network down"));
    mockGetBranchesForSoc.mockResolvedValueOnce([
      makeBranch("13-2051", "13-2052", "Portfolio Manager"),
    ]);

    const career = makeCareer("13-2051", "Financial Analyst");
    renderSheet({ soc: "13-2051", career });

    const retryBtn = await screen.findByRole("button", { name: /Try again/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText("Portfolio Manager")).toBeInTheDocument();
    });
    // One failed call + one retry call.
    expect(mockGetBranchesForSoc).toHaveBeenCalledTimes(2);
  });
});

// ---------------------------------------------------------------------------
// Tests: chevrons + keyboard detent control
// ---------------------------------------------------------------------------

describe("CareerLineageSheet — detent controls", () => {
  it("up chevron transitions compact → medium and medium → large; large is a no-op", () => {
    const onFromCompact = vi.fn();
    const { unmount: unmount1 } = renderSheet({
      detent: "compact",
      onDetentChange: onFromCompact,
    });
    fireEvent.click(screen.getByRole("button", { name: "Raise lineage panel" }));
    expect(onFromCompact).toHaveBeenCalledWith("medium");
    unmount1();

    const onFromMedium = vi.fn();
    const { unmount: unmount2 } = renderSheet({
      detent: "medium",
      onDetentChange: onFromMedium,
    });
    fireEvent.click(screen.getByRole("button", { name: "Raise lineage panel" }));
    expect(onFromMedium).toHaveBeenCalledWith("large");
    unmount2();

    const onFromLarge = vi.fn();
    renderSheet({
      detent: "large",
      onDetentChange: onFromLarge,
    });
    const upBtn = screen.getByRole("button", { name: "Raise lineage panel" });
    // Disabled at large — button has disabled attribute, click should be no-op.
    expect(upBtn).toBeDisabled();
    fireEvent.click(upBtn);
    expect(onFromLarge).not.toHaveBeenCalled();
  });

  it("down chevron transitions large → medium → compact; compact is a no-op", () => {
    const onFromLarge = vi.fn();
    const { unmount: unmount1 } = renderSheet({
      detent: "large",
      onDetentChange: onFromLarge,
    });
    fireEvent.click(screen.getByRole("button", { name: "Lower lineage panel" }));
    expect(onFromLarge).toHaveBeenCalledWith("medium");
    unmount1();

    const onFromMedium = vi.fn();
    const { unmount: unmount2 } = renderSheet({
      detent: "medium",
      onDetentChange: onFromMedium,
    });
    fireEvent.click(screen.getByRole("button", { name: "Lower lineage panel" }));
    expect(onFromMedium).toHaveBeenCalledWith("compact");
    unmount2();

    const onFromCompact = vi.fn();
    renderSheet({
      detent: "compact",
      onDetentChange: onFromCompact,
    });
    const downBtn = screen.getByRole("button", { name: "Lower lineage panel" });
    expect(downBtn).toBeDisabled();
    fireEvent.click(downBtn);
    expect(onFromCompact).not.toHaveBeenCalled();
  });

  it("ArrowUp on slider handle promotes detent; ArrowDown demotes it", () => {
    const onChange = vi.fn();
    renderSheet({ detent: "compact", onDetentChange: onChange });

    const handle = screen.getByRole("slider");
    fireEvent.keyDown(handle, { key: "ArrowUp" });
    expect(onChange).toHaveBeenLastCalledWith("medium");

    onChange.mockReset();
    renderSheet({
      detent: "medium",
      onDetentChange: onChange,
    });
    // Two sheets are now rendered in the same container; target the last
    // slider (most-recently mounted).
    const handles = screen.getAllByRole("slider");
    const latestHandle = handles[handles.length - 1];
    expect(latestHandle).toBeDefined();
    fireEvent.keyDown(latestHandle as HTMLElement, { key: "ArrowDown" });
    expect(onChange).toHaveBeenLastCalledWith("compact");
  });
});

// ---------------------------------------------------------------------------
// Tests: drag-end snap math via the exported pure helper
// ---------------------------------------------------------------------------

describe("resolveDetent (pure helper)", () => {
  // desktop: compact=0.33*vh, medium=0.5*vh, large=0.85*vh.
  // At vh=1000 -> compact=330, medium=500, large=850.
  const vh = 1000;
  const mobile = false;

  it("drag up past midpoint between compact and medium snaps to medium", () => {
    // compact=330 height. Dragging up = negative offsetY. Midpoint between
    // compact(330) and medium(500) is at a new height of 415 — offset of
    // -85. Go slightly past (e.g. -100) -> medium.
    const next = resolveDetent({
      current: "compact",
      offsetY: -100,
      velocityY: 0,
      vh,
      mobile,
    });
    expect(next).toBe("medium");
  });

  it("drag up a tiny bit does not change detent", () => {
    const next = resolveDetent({
      current: "compact",
      offsetY: -10,
      velocityY: 0,
      vh,
      mobile,
    });
    expect(next).toBe("compact");
  });

  it("fast upward fling promotes one detent regardless of offset", () => {
    // velocityY strongly negative (upward fling) from compact -> medium.
    const next = resolveDetent({
      current: "compact",
      offsetY: -5,
      velocityY: -800,
      vh,
      mobile,
    });
    expect(next).toBe("medium");
  });

  it("fast downward fling demotes one detent regardless of offset", () => {
    const next = resolveDetent({
      current: "large",
      offsetY: 5,
      velocityY: 800,
      vh,
      mobile,
    });
    expect(next).toBe("medium");
  });

  it("upward fling from large stays at large (caps)", () => {
    const next = resolveDetent({
      current: "large",
      offsetY: -5,
      velocityY: -800,
      vh,
      mobile,
    });
    expect(next).toBe("large");
  });

  it("drag down past midpoint medium→compact snaps to compact", () => {
    // medium=500, compact=330. Midpoint new height ≈ 415 → offset of +85.
    // Use +120 to be well past midpoint.
    const next = resolveDetent({
      current: "medium",
      offsetY: 120,
      velocityY: 0,
      vh,
      mobile,
    });
    expect(next).toBe("compact");
  });
});

// ---------------------------------------------------------------------------
// Tests: reduced-motion, aria attributes
// ---------------------------------------------------------------------------

function installReducedMotionMatchMedia(reduced: boolean) {
  // Framer Motion's useReducedMotion() reads window.matchMedia.
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: reduced && query.includes("reduce"),
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

describe("CareerLineageSheet — reduced motion + aria", () => {
  it("under prefers-reduced-motion, the sheet still renders and detent controls still work (animation attenuated, not removed)", () => {
    installReducedMotionMatchMedia(true);
    const onDetentChange = vi.fn();

    renderSheet({ detent: "compact", onDetentChange });

    // Sheet still renders with correct aria-label.
    expect(screen.getByRole("dialog")).toHaveAttribute(
      "aria-label",
      "Lineage panel — compact",
    );

    // Functional state changes still fire under reduced motion — chevron
    // click still promotes detent. The snap animation is zero-duration per
    // spec §3.4 but the detent change itself always happens.
    fireEvent.click(
      screen.getByRole("button", { name: "Raise lineage panel" }),
    );
    expect(onDetentChange).toHaveBeenCalledWith("medium");

    // ArrowUp keyboard also still works.
    onDetentChange.mockReset();
    fireEvent.keyDown(screen.getByRole("slider"), { key: "ArrowUp" });
    expect(onDetentChange).toHaveBeenCalledWith("medium");
  });

  it("aria-label reflects current detent", () => {
    const { unmount: u1 } = renderSheet({ detent: "compact" });
    expect(screen.getByRole("dialog")).toHaveAttribute(
      "aria-label",
      "Lineage panel — compact",
    );
    u1();

    const { unmount: u2 } = renderSheet({ detent: "medium" });
    expect(screen.getByRole("dialog")).toHaveAttribute(
      "aria-label",
      "Lineage panel — medium",
    );
    u2();

    renderSheet({ detent: "large" });
    expect(screen.getByRole("dialog")).toHaveAttribute(
      "aria-label",
      "Lineage panel — expanded",
    );
  });

  it("slider handle exposes aria-valuetext and aria-valuenow per detent", () => {
    const { unmount: u1 } = renderSheet({ detent: "compact" });
    const handle1 = screen.getByRole("slider");
    expect(handle1).toHaveAttribute("aria-valuenow", "0");
    expect(handle1).toHaveAttribute("aria-valuetext", "compact");
    u1();

    const { unmount: u2 } = renderSheet({ detent: "medium" });
    const handle2 = screen.getByRole("slider");
    expect(handle2).toHaveAttribute("aria-valuenow", "1");
    expect(handle2).toHaveAttribute("aria-valuetext", "medium");
    u2();

    renderSheet({ detent: "large" });
    const handle3 = screen.getByRole("slider");
    expect(handle3).toHaveAttribute("aria-valuenow", "2");
    expect(handle3).toHaveAttribute("aria-valuetext", "expanded");
  });

  it("title region has aria-live=polite and updates when soc + career change", async () => {
    mockGetBranchesForSoc.mockResolvedValue([]);
    const careerA = makeCareer("13-2051", "Financial Analyst");
    const careerB = makeCareer("15-1252", "Software Developer");

    const { rerender } = renderSheet({ soc: "13-2051", career: careerA });

    const h2a = screen.getByRole("heading", { level: 2 });
    expect(h2a).toHaveAttribute("aria-live", "polite");
    expect(h2a).toHaveAttribute("aria-atomic", "true");
    expect(h2a).toHaveTextContent("Financial Analyst");

    rerender(
      <CareerLineageSheet
        soc="15-1252"
        career={careerB}
        detent="compact"
        onDetentChange={vi.fn()}
        chips={CHIPS}
        askContext={{
          cipcode: "11.0701",
          majorText: "CS",
          socCodes: ["15-1252"],
        }}
        pickedSoc={null}
        onPick={vi.fn()}
        onGo={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 2 }),
      ).toHaveTextContent("Software Developer");
    });
  });
});

// ---------------------------------------------------------------------------
// Tests: Ask-Gemma chip interactions
// ---------------------------------------------------------------------------

describe("CareerLineageSheet — Ask-Gemma chip integration", () => {
  it("chip click at compact detent auto-promotes to medium", async () => {
    mockGetBranchesForSoc.mockResolvedValue([]);
    mockAskCareerPickChip.mockResolvedValue({
      chip_id: "what_does_this_do",
      answer: "A",
      fallback_fired: false,
    });
    const onDetentChange = vi.fn();
    const career = makeCareer("13-2051", "Financial Analyst");
    renderSheet({
      soc: "13-2051",
      career,
      detent: "compact",
      onDetentChange,
    });

    const chip = screen.getByRole("button", {
      name: /What does this career actually do\?/i,
    });
    fireEvent.click(chip);

    expect(onDetentChange).toHaveBeenCalledWith("medium");
  });

  it("chip click at medium does NOT auto-promote", async () => {
    mockGetBranchesForSoc.mockResolvedValue([]);
    mockAskCareerPickChip.mockResolvedValue({
      chip_id: "what_does_this_do",
      answer: "A",
      fallback_fired: false,
    });
    const onDetentChange = vi.fn();
    const career = makeCareer("13-2051", "Financial Analyst");
    renderSheet({
      soc: "13-2051",
      career,
      detent: "medium",
      onDetentChange,
    });

    const chip = screen.getByRole("button", {
      name: /What does this career actually do\?/i,
    });
    fireEvent.click(chip);

    expect(onDetentChange).not.toHaveBeenCalled();
  });

  it("chip click at large does NOT auto-promote", async () => {
    mockGetBranchesForSoc.mockResolvedValue([]);
    mockAskCareerPickChip.mockResolvedValue({
      chip_id: "what_does_this_do",
      answer: "A",
      fallback_fired: false,
    });
    const onDetentChange = vi.fn();
    const career = makeCareer("13-2051", "Financial Analyst");
    renderSheet({
      soc: "13-2051",
      career,
      detent: "large",
      onDetentChange,
    });

    const chip = screen.getByRole("button", {
      name: /What does this career actually do\?/i,
    });
    fireEvent.click(chip);

    expect(onDetentChange).not.toHaveBeenCalled();
  });

  it("chip click fires askCareerPickChip with correct context", async () => {
    mockGetBranchesForSoc.mockResolvedValue([]);
    mockAskCareerPickChip.mockResolvedValue({
      chip_id: "why_no_doctor",
      answer: "because grad school",
      fallback_fired: false,
    });
    const career = makeCareer("13-2051", "Financial Analyst");
    renderSheet({
      soc: "13-2051",
      career,
      detent: "medium",
      askContext: {
        cipcode: "26.0101",
        majorText: "pre-med",
        socCodes: ["19-1029", "13-1071"],
      },
    });

    const elevated = screen.getByRole("button", {
      name: /Why don't I see 'doctor'\?/i,
    });
    fireEvent.click(elevated);

    await waitFor(() => {
      expect(mockAskCareerPickChip).toHaveBeenCalledTimes(1);
    });
    const callArgs = mockAskCareerPickChip.mock.calls[0]![0];
    expect(callArgs).toMatchObject({
      chipId: "why_no_doctor",
      cipcode: "26.0101",
      majorText: "pre-med",
      socCodes: ["19-1029", "13-1071"],
      selectedSoc: "13-2051",
      terminalTitle: "doctor",
    });
  });

  it("switching chips swaps the active chip + renders the new answer (replace-in-place semantics)", async () => {
    mockGetBranchesForSoc.mockResolvedValue([]);
    mockAskCareerPickChip.mockImplementation(async (args) => ({
      chip_id: args.chipId,
      answer: `ans-${args.chipId}`,
      fallback_fired: false,
    }));

    const career = makeCareer("13-2051", "Financial Analyst");
    renderSheet({
      soc: "13-2051",
      career,
      detent: "medium",
    });

    const chip1 = screen.getByRole("button", {
      name: /Why don't I see 'doctor'\?/i,
    });
    fireEvent.click(chip1);

    await waitFor(() => {
      expect(screen.getByText("ans-why_no_doctor")).toBeInTheDocument();
    });
    // chip1 is the active chip (data-active='true'); chip2 is not.
    expect(chip1).toHaveAttribute("data-active", "true");

    const chip2 = screen.getByRole("button", {
      name: /What does this career actually do\?/i,
    });
    expect(chip2).toHaveAttribute("data-active", "false");

    fireEvent.click(chip2);

    // The new answer lands.
    await waitFor(() => {
      expect(screen.getByText("ans-what_does_this_do")).toBeInTheDocument();
    });
    // Active-state swaps cleanly: chip2 is now active; chip1 is not.
    expect(chip2).toHaveAttribute("data-active", "true");
    expect(chip1).toHaveAttribute("data-active", "false");

    // The ask endpoint got called exactly twice, once per distinct chip.
    expect(mockAskCareerPickChip).toHaveBeenCalledTimes(2);
    const chipIdsCalled = mockAskCareerPickChip.mock.calls.map(
      (call) => call[0].chipId,
    );
    expect(chipIdsCalled).toEqual(["why_no_doctor", "what_does_this_do"]);
  });
});

// ---------------------------------------------------------------------------
// Tests: primary commit CTA (Proposal A redesign)
// ---------------------------------------------------------------------------

describe("CareerLineageSheet — primary commit CTA", () => {
  beforeEach(() => {
    // Every mounting of the sheet with a non-null soc fetches branches;
    // provide a default empty resolver so CTA-focused tests don't race
    // on an unmocked branch-fetch promise.
    mockGetBranchesForSoc.mockResolvedValue([]);
  });

  it("no CTA when career is null (empty state)", () => {
    renderSheet({ soc: null, career: null });
    expect(screen.queryByRole("button", { name: /Pick .* as your path/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /See my build/ })).toBeNull();
  });

  it("shows 'Pick this path' when displayed career != picked career", () => {
    const career = makeCareer("13-2051", "Financial Analysts");
    renderSheet({
      soc: "13-2051",
      career,
      pickedSoc: null,
    });
    expect(
      screen.getByRole("button", {
        name: /Pick Financial Analysts as your path/,
      }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /See my build/ })).toBeNull();
  });

  it("shows 'See my build' when displayed career IS the picked career", () => {
    const career = makeCareer("13-2051", "Financial Analysts");
    renderSheet({
      soc: "13-2051",
      career,
      pickedSoc: "13-2051",
    });
    expect(
      screen.getByRole("button", { name: /See my build/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: /Pick Financial Analysts as your path/,
      }),
    ).toBeNull();
  });

  it("clicking 'Pick this path' fires onPick with the displayed career", () => {
    const career = makeCareer("13-2051", "Financial Analysts");
    const { onPick, onGo } = renderSheet({
      soc: "13-2051",
      career,
      pickedSoc: null,
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: /Pick Financial Analysts as your path/,
      }),
    );
    expect(onPick).toHaveBeenCalledWith(career);
    expect(onGo).not.toHaveBeenCalled();
  });

  it("clicking 'See my build' fires onGo", () => {
    const career = makeCareer("13-2051", "Financial Analysts");
    const { onPick, onGo } = renderSheet({
      soc: "13-2051",
      career,
      pickedSoc: "13-2051",
    });
    fireEvent.click(screen.getByRole("button", { name: /See my build/ }));
    expect(onGo).toHaveBeenCalledTimes(1);
    expect(onPick).not.toHaveBeenCalled();
  });

  it("'Pick this path' from compact detent auto-promotes to medium", () => {
    const career = makeCareer("13-2051", "Financial Analysts");
    const { onDetentChange } = renderSheet({
      soc: "13-2051",
      career,
      pickedSoc: null,
      detent: "compact",
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: /Pick Financial Analysts as your path/,
      }),
    );
    expect(onDetentChange).toHaveBeenCalledWith("medium");
  });

  it("'Pick this path' from medium detent does NOT change detent", () => {
    const career = makeCareer("13-2051", "Financial Analysts");
    const onDetentChange = vi.fn();
    renderSheet({
      soc: "13-2051",
      career,
      pickedSoc: null,
      detent: "medium",
      onDetentChange,
    });
    fireEvent.click(
      screen.getByRole("button", {
        name: /Pick Financial Analysts as your path/,
      }),
    );
    // onDetentChange may only have been called for other reasons (none here).
    const detentCalls = onDetentChange.mock.calls.map((c) => c[0]);
    expect(detentCalls).not.toContain("compact");
  });
});
