/**
 * CompareView.test.tsx
 *
 * Covers:
 * - Renders one Risk Headline card per boss (P0)
 * - Character cards for each build (P0)
 * - Money section with salary figures (P0)
 * - Skill count badges on boss outcomes (P0)
 * - Gemma summary renders after compareInsights resolves (P2)
 * - Handles 2, 3, and 4 builds (P0)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CompareView } from "./CompareView";
import type { CompareResult, CompareInsights } from "@/api/menu";

const mockCompareBuilds = vi.fn();
const mockCompareInsights = vi.fn();
const mockAskGemma = vi.fn();
// askGemmaStream — happy-path SSE-equivalent default. Compare-scope
// chat goes through askGemmaStream now. Per Authorized Test
// Modifications (§4 / C7).
const mockAskGemmaStream = vi.fn().mockImplementation(
  async (..._args: unknown[]) => {
    const final = { type: "final_text" as const, response: "ok" };
    const done = { type: "done" as const };
    const onEvent = _args[3] as ((e: unknown) => void) | undefined;
    if (onEvent) {
      onEvent(final);
      onEvent(done);
    }
    return { response: "ok", events: [final, done] };
  },
);
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    compareBuilds: (...args: unknown[]) => mockCompareBuilds(...args),
    compareInsights: (...args: unknown[]) => mockCompareInsights(...args),
    askGemma: (...args: unknown[]) => mockAskGemma(...args),
    askGemmaStream: (...args: Parameters<typeof import("@/api/menu").askGemmaStream>) =>
      mockAskGemmaStream(...args),
  };
});

function makeBuild(
  id: string,
  school: string,
  major: string,
  career: string,
  soc: string,
  wage: number | null = 80000,
  cost: number | null = 15000,
  debt: number | null = 30000,
) {
  return {
    build_id: id,
    label: `${school} — ${major}`,
    career,
    soc_code: soc,
    profile_name: `Test ${school}`,
    animal_emoji: "🦊",
    school_name: school,
    major_text: major,
    effort: "balanced",
    loan_pct: 0.5,
    median_annual_wage: wage,
    net_price_annual: cost,
    modeled_total_debt: debt,
    tuition_annual: cost,
    is_out_of_state: false,
    institution_control: null,
  };
}

function makeCompareResult(overrides: Partial<CompareResult> = {}): CompareResult {
  return {
    builds: [
      makeBuild("berkeley-cs-001", "UC Berkeley", "Computer Science", "Software Developers", "15-1252", 130000, 16200, 32400),
      makeBuild("iu-bloom-mkt-001", "IU Bloomington", "Marketing", "Marketing Managers", "11-2021", 140040, 11400, 22800),
    ],
    stats: [
      { label: "ERN", values: [8, 6] },
      { label: "ROI", values: [7, 6] },
      { label: "RES", values: [4, 7] },
      { label: "GRW", values: [9, 5] },
      { label: "AURA", values: [5, 8] },
    ],
    bosses: [
      { label: "AI", boss_id: "ai", values: ["LOSE", "WIN"], skill_counts: [0, 1], original_values: ["LOSE", "LOSE"] },
      { label: "Loans", boss_id: "loans", values: ["WIN", "WIN"], skill_counts: [0, 0], original_values: ["WIN", "WIN"] },
      { label: "Market", boss_id: "market", values: ["WIN", "WIN"], skill_counts: [0, 0], original_values: ["WIN", "WIN"] },
      { label: "Burnout", boss_id: "burnout", values: ["DRAW", "DRAW"], skill_counts: [0, 0], original_values: ["DRAW", "DRAW"] },
      { label: "Ceiling", boss_id: "ceiling", values: ["WIN", "WIN"], skill_counts: [0, 0], original_values: ["WIN", "WIN"] },
    ],
    branches: [
      { build_id: "berkeley-cs-001", career: "Software Developers", destinations: [{ to_title: "Tech Lead", to_soc: "15-1299", delta_ern: 2, delta_grw: -1 }] },
      { build_id: "iu-bloom-mkt-001", career: "Marketing Managers", destinations: [{ to_title: "Marketing Director", to_soc: "11-2021", delta_ern: 3, delta_grw: 0 }] },
    ],
    ...overrides,
  };
}

function makeInsights(overrides: Partial<CompareInsights> = {}): CompareInsights {
  return {
    money_insight: null,
    compare_summary: null,
    pros_cons: null,
    pivotal: null,
    ...overrides,
  };
}

function renderCV(buildIds: string[], onBack: () => void = () => {}) {
  return render(
    <MemoryRouter>
      <CompareView buildIds={buildIds} onBack={onBack} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockCompareBuilds.mockReset();
  mockCompareInsights.mockReset();
  mockAskGemma.mockReset();
  mockCompareInsights.mockReturnValue(new Promise(() => {}));
});

describe("CompareView", () => {
  // --- P0: renders one card per boss ---

  it("renders one Risk Headline card per boss in the result (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("card-risk-ai")).toBeInTheDocument();
    });
    expect(screen.getByTestId("card-risk-loans")).toBeInTheDocument();
    expect(screen.getByTestId("card-risk-market")).toBeInTheDocument();
    expect(screen.getByTestId("card-risk-burnout")).toBeInTheDocument();
    expect(screen.getByTestId("card-risk-ceiling")).toBeInTheDocument();
  });

  // --- P0: character cards ---

  it("renders character cards for each build (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("card-character-berkeley-cs-001")).toBeInTheDocument();
    });
    expect(screen.getByTestId("card-character-iu-bloom-mkt-001")).toBeInTheDocument();
  });

  // --- P0: boss grid with skill badges ---

  it("renders boss grid with skill count badges (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("badge-skill-ai-iu-bloom-mkt-001")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("badge-skill-ai-berkeley-cs-001")).not.toBeInTheDocument();
  });

  // --- P0: money section ---

  it("renders salary figures in money section (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("salary-berkeley-cs-001")).toBeInTheDocument();
    });
    expect(screen.getByTestId("salary-iu-bloom-mkt-001")).toBeInTheDocument();
    expect(screen.getByText("$130K")).toBeInTheDocument();
    expect(screen.getByText("$140K")).toBeInTheDocument();
  });

  // --- P0: handles 2, 3, and 4 builds ---

  it("handles 3 builds (P0)", async () => {
    const threeBuild = makeCompareResult({
      builds: [
        makeBuild("a", "School A", "Major A", "Career A", "11-0001"),
        makeBuild("b", "School B", "Major B", "Career B", "11-0002"),
        makeBuild("c", "School C", "Major C", "Career C", "11-0003"),
      ],
      stats: [
        { label: "ERN", values: [7, 6, 8] },
        { label: "ROI", values: [6, 7, 5] },
        { label: "RES", values: [5, 4, 6] },
        { label: "GRW", values: [8, 9, 7] },
        { label: "AURA", values: [4, 5, 3] },
      ],
      bosses: [
        { label: "AI", boss_id: "ai", values: ["WIN", "DRAW", "LOSE"], skill_counts: [0, 0, 0], original_values: ["WIN", "DRAW", "LOSE"] },
        { label: "Loans", boss_id: "loans", values: ["WIN", "WIN", "WIN"], skill_counts: [0, 0, 0], original_values: ["WIN", "WIN", "WIN"] },
        { label: "Market", boss_id: "market", values: ["WIN", "WIN", "WIN"], skill_counts: [0, 0, 0], original_values: ["WIN", "WIN", "WIN"] },
        { label: "Burnout", boss_id: "burnout", values: ["DRAW", "DRAW", "DRAW"], skill_counts: [0, 0, 0], original_values: ["DRAW", "DRAW", "DRAW"] },
        { label: "Ceiling", boss_id: "ceiling", values: ["WIN", "WIN", "WIN"], skill_counts: [0, 0, 0], original_values: ["WIN", "WIN", "WIN"] },
      ],
      branches: [
        { build_id: "a", career: "Career A", destinations: [] },
        { build_id: "b", career: "Career B", destinations: [] },
        { build_id: "c", career: "Career C", destinations: [] },
      ],
    });
    mockCompareBuilds.mockResolvedValue(threeBuild);

    renderCV(["a", "b", "c"]);

    await waitFor(() => {
      expect(screen.getByTestId("card-character-a")).toBeInTheDocument();
    });
    expect(screen.getByTestId("card-character-b")).toBeInTheDocument();
    expect(screen.getByTestId("card-character-c")).toBeInTheDocument();
  });

  it("handles 4 builds (P0)", async () => {
    const fourBuild = makeCompareResult({
      builds: [
        makeBuild("a", "School A", "Major A", "Career A", "11-0001"),
        makeBuild("b", "School B", "Major B", "Career B", "11-0002"),
        makeBuild("c", "School C", "Major C", "Career C", "11-0003"),
        makeBuild("d", "School D", "Major D", "Career D", "11-0004"),
      ],
      stats: [
        { label: "ERN", values: [7, 6, 8, 5] },
        { label: "ROI", values: [6, 7, 5, 8] },
        { label: "RES", values: [5, 4, 6, 7] },
        { label: "GRW", values: [8, 9, 7, 6] },
        { label: "AURA", values: [4, 5, 3, 9] },
      ],
      bosses: [
        { label: "AI", boss_id: "ai", values: ["WIN", "DRAW", "LOSE", "WIN"], skill_counts: [0, 0, 0, 0], original_values: ["WIN", "DRAW", "LOSE", "WIN"] },
        { label: "Loans", boss_id: "loans", values: ["WIN", "WIN", "WIN", "WIN"], skill_counts: [0, 0, 0, 0], original_values: ["WIN", "WIN", "WIN", "WIN"] },
        { label: "Market", boss_id: "market", values: ["WIN", "WIN", "WIN", "WIN"], skill_counts: [0, 0, 0, 0], original_values: ["WIN", "WIN", "WIN", "WIN"] },
        { label: "Burnout", boss_id: "burnout", values: ["DRAW", "DRAW", "DRAW", "DRAW"], skill_counts: [0, 0, 0, 0], original_values: ["DRAW", "DRAW", "DRAW", "DRAW"] },
        { label: "Ceiling", boss_id: "ceiling", values: ["WIN", "WIN", "WIN", "WIN"], skill_counts: [0, 0, 0, 0], original_values: ["WIN", "WIN", "WIN", "WIN"] },
      ],
      branches: [
        { build_id: "a", career: "Career A", destinations: [] },
        { build_id: "b", career: "Career B", destinations: [] },
        { build_id: "c", career: "Career C", destinations: [] },
        { build_id: "d", career: "Career D", destinations: [] },
      ],
    });
    mockCompareBuilds.mockResolvedValue(fourBuild);

    renderCV(["a", "b", "c", "d"]);

    await waitFor(() => {
      expect(screen.getByTestId("card-character-a")).toBeInTheDocument();
    });
    expect(screen.getByTestId("card-character-d")).toBeInTheDocument();
  });

  // --- P1: branch preview with convergence ---

  it("renders branch preview with convergence badges (P1)", async () => {
    const convergentBranches = makeCompareResult({
      branches: [
        { build_id: "berkeley-cs-001", career: "Software Developers", destinations: [{ to_title: "Tech Lead", to_soc: "15-1299", delta_ern: 2, delta_grw: -1 }] },
        { build_id: "iu-bloom-mkt-001", career: "Marketing Managers", destinations: [{ to_title: "Tech Lead", to_soc: "15-1299", delta_ern: 3, delta_grw: 0 }] },
      ],
    });
    mockCompareBuilds.mockResolvedValue(convergentBranches);

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("card-branch-berkeley-cs-001")).toBeInTheDocument();
    });
    const convergenceBadges = screen.getAllByText(/↔/);
    expect(convergenceBadges.length).toBeGreaterThanOrEqual(2);
  });

  // --- P2: Gemma summary ---

  it("renders the Gemma summary text once compareInsights resolves (P2)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());
    mockCompareInsights.mockResolvedValue(
      makeInsights({
        compare_summary: "Build A optimizes for earnings; Build B for resilience. Neither is wrong.",
      }),
    );

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(
      () => {
        expect(
          screen.getByText(/Build A optimizes for earnings/),
        ).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it("falls back to loading placeholder when insights fail (saboteur)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());
    mockCompareInsights.mockRejectedValue(new Error("model unavailable"));

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await screen.findByTestId("region-gemma-compare");
    expect(screen.getByText(/Reading the tradeoffs/i)).toBeInTheDocument();
  });

  // ===========================================================================
  // Ask Gemma — compare-screen entry point (P0).
  // docs/specs/feature-ask-gemma.md §4 New Tests Required.
  // ===========================================================================

  describe("Ask Gemma compare entry button (P0)", () => {
    it("dispatches a compare scope with all build_ids when btn-ask-compare is clicked", async () => {
      mockCompareBuilds.mockResolvedValue(makeCompareResult());
      // The button only renders when compare_summary is non-null.
      mockCompareInsights.mockResolvedValue(
        makeInsights({
          compare_summary: "The trade-off is real but workable.",
        }),
      );
      mockAskGemma.mockResolvedValue({
        response: "DePaul costs more per year, but earnings catch up by year 5.",
        tool_calls: [],
      });

      render(
        <MemoryRouter>
          <CompareView
            buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]}
            onBack={() => {}}
          />
        </MemoryRouter>,
      );

      // The summary must resolve before the button renders.
      await waitFor(() => {
        expect(
          screen.getByText(/trade-off is real but workable/),
        ).toBeInTheDocument();
      });

      // Chat dialog is hidden initially.
      expect(screen.queryByTestId("dialog-chat")).toBeNull();

      // Click the entry button.
      const askButton = screen.getByTestId("btn-ask-compare");
      fireEvent.click(askButton);

      // Chat dialog opens.
      await waitFor(() => {
        expect(screen.getByTestId("dialog-chat")).toBeInTheDocument();
      });

      // Submit a question — verify the scope routed through askGemma is
      // a compare scope with all build_ids.
      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "Which one wins on cost?" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      await waitFor(() => {
        expect(mockAskGemmaStream).toHaveBeenCalledTimes(1);
      });
      const scope = mockAskGemmaStream.mock.calls[0]![0] as {
        kind: string;
        build_ids: string[];
      };
      expect(scope.kind).toBe("compare");
      expect(scope.build_ids).toEqual([
        "berkeley-cs-001",
        "iu-bloom-mkt-001",
      ]);
    });

    it("renders the compare scope chip in the chat header when opened", async () => {
      mockCompareBuilds.mockResolvedValue(makeCompareResult());
      mockCompareInsights.mockResolvedValue(
        makeInsights({ compare_summary: "Tradeoffs are real." }),
      );

      render(
        <MemoryRouter>
          <CompareView
            buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]}
            onBack={() => {}}
          />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Tradeoffs are real.")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("btn-ask-compare"));

      // The chat scope chip carries the "Comparing: …" prefix per the
      // §3 alias table. School names are passed through.
      await waitFor(() => {
        const chip = screen.getByTestId("chip-chat-scope");
        expect(chip).toBeInTheDocument();
        expect(chip.textContent).toContain("Comparing");
        expect(chip.textContent).toContain("UC Berkeley");
        expect(chip.textContent).toContain("IU Bloomington");
      });
    });
  });
});
