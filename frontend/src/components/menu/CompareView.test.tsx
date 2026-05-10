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
    cost_of_attendance_annual: cost ? cost * 1.5 : null,
    published_cost_4yr: cost ? cost * 4 * 1.5 : null,
    room_board_on_campus: 10500,
    tuition_in_state: cost,
    tuition_out_of_state: cost ? cost * 2.5 : null,
    earnings_1yr_median: wage,
    earnings_1yr_p25: wage ? wage * 0.7 : null,
    earnings_1yr_p75: wage ? wage * 1.3 : null,
    state_abbr: "IN",
    fte_enrollment: 35000,
    endowment_per_fte: 45000,
    marketing_ratio: 0.1,
    athletic_spend_per_fte: 2000,
    athletic_revenue_per_fte: 3000,
    athletic_subsidy_ratio: 0.15,
    aura_score_basis: "ipeds_finance+eada",
    coverage_tier: "full",
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

  it("uses Gemma's pivotal tradeoff as the top Big Choice headline", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());
    mockCompareInsights.mockResolvedValue(
      makeInsights({
        compare_summary: "The surface tradeoff is simple.",
        pivotal: {
          meta_tradeoff: "Big Debt, Big Brand, or High Pay",
          meta_explanation: "Pick the pressure you are willing to carry.",
          decade_projection: "The ten-year path depends on execution.",
          pivot_question: "Which tradeoff still feels worth it?",
        },
      }),
    );

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getAllByText("Big Debt, Big Brand, or High Pay").length).toBeGreaterThanOrEqual(2);
    });

    expect(screen.getAllByText("Big Choice").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText(/lowers pressure/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/raises upside/i)).not.toBeInTheDocument();
  });

  it("falls back to loading placeholder when insights fail (saboteur)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());
    mockCompareInsights.mockRejectedValue(new Error("model unavailable"));

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await screen.findByTestId("region-gemma-compare");
    expect(screen.getByText(/Reading the tradeoffs/i)).toBeInTheDocument();
  });

  it("shows a Big Choice loading state instead of fallback copy while Gemma is thinking", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());
    mockCompareInsights.mockReturnValue(new Promise(() => {}));

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await screen.findByTestId("region-compare");

    expect(screen.getByRole("status", { name: /loading big choice/i })).toBeInTheDocument();
    expect(screen.queryByText(/lowers pressure/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/raises upside/i)).not.toBeInTheDocument();
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

  // ===========================================================================
  // Compare Screen Redesign — feature-compare-screen-redesign §4
  // ===========================================================================

  // --- P0: CompareWinners rendered before Character Cards ---

  it("renders CompareWinners before Character Cards in the DOM (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("region-compare-winners")).toBeInTheDocument();
    });

    // Verify DOM order: region-compare-winners appears before the first character card.
    const winnersSection = screen.getByTestId("region-compare-winners");
    const characterCard = screen.getByTestId("card-character-berkeley-cs-001");

    // compareDocumentPosition returns a bitmask; bit 4 (DOCUMENT_POSITION_FOLLOWING)
    // means the argument node follows the reference node in the document.
    const position = winnersSection.compareDocumentPosition(characterCard);
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  // --- P0: Cost Breakdown accordion collapsed by default ---

  it("renders Cost Breakdown accordion collapsed by default (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("accordion-cost-breakdown")).toBeInTheDocument();
    });

    // The toggle button should indicate collapsed state.
    const toggle = screen.getByTestId("btn-toggle-accordion-cost-breakdown");
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    // The cost detail content should NOT be visible when collapsed.
    expect(screen.queryByText("Sticker Price vs Avg After-Aid Cost")).not.toBeInTheDocument();
  });

  // --- P0: School Profile accordion collapsed by default ---

  it("renders School Profile accordion collapsed by default (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("accordion-school-profile")).toBeInTheDocument();
    });

    // The toggle button should indicate collapsed state.
    const toggle = screen.getByTestId("btn-toggle-accordion-school-profile");
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    // The school profile content should NOT be visible when collapsed.
    expect(screen.queryByText("Institutional X-Ray")).not.toBeInTheDocument();
  });

  // --- P1: Cost accordion expands and shows cost table ---

  it("expands Cost Breakdown accordion to reveal cost table (P1)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("accordion-cost-breakdown")).toBeInTheDocument();
    });

    // Click the toggle to expand.
    const toggle = screen.getByTestId("btn-toggle-accordion-cost-breakdown");
    fireEvent.click(toggle);

    // After expanding, the cost detail content should be visible.
    await waitFor(() => {
      expect(toggle).toHaveAttribute("aria-expanded", "true");
    });

    // The cost table should show line items.
    await waitFor(() => {
      expect(screen.getByText("Sticker Price vs Avg After-Aid Cost")).toBeInTheDocument();
    });
    expect(screen.getByText(/reported average annual net price for eligible aid-recipient undergraduates/i)).toBeInTheDocument();
    expect(screen.getByText("Cost Detail")).toBeInTheDocument();
  });

  // --- P1: School Profile accordion expands and shows AURA breakdown ---

  it("expands School Profile accordion to reveal AURA breakdown (P1)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("accordion-school-profile")).toBeInTheDocument();
    });

    // Click the toggle to expand.
    const toggle = screen.getByTestId("btn-toggle-accordion-school-profile");
    fireEvent.click(toggle);

    // After expanding, the AURA breakdown content should be visible.
    await waitFor(() => {
      expect(toggle).toHaveAttribute("aria-expanded", "true");
    });

    await waitFor(() => {
      expect(screen.getByText("Institutional X-Ray")).toBeInTheDocument();
    });

    // The school identity cards should show enrollment for both builds.
    // Both builds have fte_enrollment=35000, so there will be two "35,000" texts.
    const enrollmentTexts = screen.getAllByText("35,000");
    expect(enrollmentTexts.length).toBe(2);
  });

  // --- P1: Salary section shows p25/p75 range ---

  it("renders p25/p75 salary range bars in MoneySection (P1)", async () => {
    // The default makeBuild sets earnings_1yr_p25 and p75 to non-null values
    // (wage * 0.7 and wage * 1.3), so the range bars should render.
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    renderCV(["berkeley-cs-001", "iu-bloom-mkt-001"]);

    await waitFor(() => {
      expect(screen.getByTestId("salary-berkeley-cs-001")).toBeInTheDocument();
    });

    // The salary bar for Berkeley should expose a peer-band aria-label.
    // Berkeley: wage=130000, p25=91000, p75=169000
    const berkeleySalary = screen.getByTestId("salary-berkeley-cs-001");
    const rangeLabel = berkeleySalary.querySelector('[aria-label*="Peer Year-1 band"]');
    expect(rangeLabel).not.toBeNull();

    // The p25/p75 formatted values should appear as range labels.
    // p25 = 130000 * 0.7 = 91000 -> "$91K", p75 = 130000 * 1.3 = 169000 -> "$169K"
    expect(screen.getByText("$91K")).toBeInTheDocument();
    expect(screen.getByText("$169K")).toBeInTheDocument();
  });

  // --- P2: Cost accordion handles null cost data ---

  it("renders em-dash for null cost data in expanded Cost Breakdown (P2)", async () => {
    // Create builds with null cost data.
    const nullCostResult = makeCompareResult({
      builds: [
        makeBuild("null-cost-001", "School A", "Major A", "Career A", "11-0001", 80000, null, null),
        makeBuild("null-cost-002", "School B", "Major B", "Career B", "11-0002", 90000, null, null),
      ],
    });
    mockCompareBuilds.mockResolvedValue(nullCostResult);

    renderCV(["null-cost-001", "null-cost-002"]);

    await waitFor(() => {
      expect(screen.getByTestId("accordion-cost-breakdown")).toBeInTheDocument();
    });

    // Expand the accordion.
    fireEvent.click(screen.getByTestId("btn-toggle-accordion-cost-breakdown"));

    await waitFor(() => {
      expect(screen.getByText("Cost Detail")).toBeInTheDocument();
    });

    // With null net_price_annual and null published_cost_4yr, the component
    // should show "Cost data unavailable" for each build.
    // makeBuild sets cost=null -> net_price_annual=null, cost_of_attendance_annual=null,
    // published_cost_4yr=null, room_board_on_campus still defaults to 10500.
    // But the bar section checks published_cost_4yr OR net_price_annual.
    // With both null, it should show the fallback message.
    const unavailableMessages = screen.getAllByText("Cost data unavailable");
    expect(unavailableMessages.length).toBe(2);
  });

  // --- P2: School profile handles missing AURA data ---

  it("renders fallback when all AURA data is missing in School Profile (P2)", async () => {
    // Create builds with all institution profile fields nulled out.
    const noAuraBuilds = [
      {
        ...makeBuild("no-aura-001", "School A", "Major A", "Career A", "11-0001"),
        endowment_per_fte: null,
        marketing_ratio: null,
        athletic_spend_per_fte: null,
        athletic_revenue_per_fte: null,
        athletic_subsidy_ratio: null,
        fte_enrollment: null,
        aura_score_basis: null,
        coverage_tier: null,
      },
      {
        ...makeBuild("no-aura-002", "School B", "Major B", "Career B", "11-0002"),
        endowment_per_fte: null,
        marketing_ratio: null,
        athletic_spend_per_fte: null,
        athletic_revenue_per_fte: null,
        athletic_subsidy_ratio: null,
        fte_enrollment: null,
        aura_score_basis: null,
        coverage_tier: null,
      },
    ];
    const noAuraResult = makeCompareResult({ builds: noAuraBuilds });
    mockCompareBuilds.mockResolvedValue(noAuraResult);

    renderCV(["no-aura-001", "no-aura-002"]);

    await waitFor(() => {
      expect(screen.getByTestId("accordion-school-profile")).toBeInTheDocument();
    });

    // Expand the School Profile accordion.
    fireEvent.click(screen.getByTestId("btn-toggle-accordion-school-profile"));

    // The CompareSchoolProfile component renders a fallback message
    // when all builds lack institution profile data.
    await waitFor(() => {
      expect(
        screen.getByText("Institution profile data is not available for these schools."),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // PDF Report Exports — comparison export trigger.
  // docs/specs/feature-pdf-report-exports.md §4 New Tests Required (P1).
  // ===========================================================================

  describe("Export comparison PDF button (P1)", () => {
    it("enables the button for cross-major comparisons", async () => {
      // Cross-major comparison is SUPPORTED — the in-app CompareView
      // shows them, the PDF matches that contract.
      const crossMajor = makeCompareResult({
        builds: [
          makeBuild("a", "School A", "Mechanical Engineering", "Mech Eng", "17-2141"),
          makeBuild("b", "School B", "Computer Science", "Software Dev", "15-1252"),
        ],
      });
      mockCompareBuilds.mockResolvedValue(crossMajor);

      renderCV(["a", "b"]);

      await waitFor(() => {
        expect(screen.getByTestId("btn-export-pdf-compare")).toBeInTheDocument();
      });

      const btn = screen.getByTestId(
        "btn-export-pdf-compare",
      ) as HTMLButtonElement;
      expect(btn.disabled).toBe(false);
    });

    it("disables the button when 5 builds are selected", async () => {
      const fiveBuild = makeCompareResult({
        builds: [
          makeBuild("a", "School A", "Major A", "Career A", "11-0001"),
          makeBuild("b", "School B", "Major A", "Career B", "11-0002"),
          makeBuild("c", "School C", "Major A", "Career C", "11-0003"),
          makeBuild("d", "School D", "Major A", "Career D", "11-0004"),
          makeBuild("e", "School E", "Major A", "Career E", "11-0005"),
        ],
        stats: [
          { label: "ERN", values: [7, 6, 8, 5, 4] },
          { label: "ROI", values: [6, 7, 5, 8, 3] },
          { label: "RES", values: [5, 4, 6, 7, 5] },
          { label: "GRW", values: [8, 9, 7, 6, 5] },
          { label: "AURA", values: [4, 5, 3, 9, 6] },
        ],
        bosses: [
          { label: "AI", boss_id: "ai", values: ["WIN", "DRAW", "LOSE", "WIN", "WIN"], skill_counts: [0, 0, 0, 0, 0], original_values: ["WIN", "DRAW", "LOSE", "WIN", "WIN"] },
          { label: "Loans", boss_id: "loans", values: ["WIN", "WIN", "WIN", "WIN", "WIN"], skill_counts: [0, 0, 0, 0, 0], original_values: ["WIN", "WIN", "WIN", "WIN", "WIN"] },
          { label: "Market", boss_id: "market", values: ["WIN", "WIN", "WIN", "WIN", "WIN"], skill_counts: [0, 0, 0, 0, 0], original_values: ["WIN", "WIN", "WIN", "WIN", "WIN"] },
          { label: "Burnout", boss_id: "burnout", values: ["DRAW", "DRAW", "DRAW", "DRAW", "DRAW"], skill_counts: [0, 0, 0, 0, 0], original_values: ["DRAW", "DRAW", "DRAW", "DRAW", "DRAW"] },
          { label: "Ceiling", boss_id: "ceiling", values: ["WIN", "WIN", "WIN", "WIN", "WIN"], skill_counts: [0, 0, 0, 0, 0], original_values: ["WIN", "WIN", "WIN", "WIN", "WIN"] },
        ],
        branches: [
          { build_id: "a", career: "Career A", destinations: [] },
          { build_id: "b", career: "Career B", destinations: [] },
          { build_id: "c", career: "Career C", destinations: [] },
          { build_id: "d", career: "Career D", destinations: [] },
          { build_id: "e", career: "Career E", destinations: [] },
        ],
      });
      mockCompareBuilds.mockResolvedValue(fiveBuild);

      renderCV(["a", "b", "c", "d", "e"]);

      await waitFor(() => {
        expect(screen.getByTestId("btn-export-pdf-compare")).toBeInTheDocument();
      });

      const btn = screen.getByTestId(
        "btn-export-pdf-compare",
      ) as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
      // Tooltip mentions the 4-school cap.
      const tooltip = btn.getAttribute("title") ?? "";
      expect(tooltip.toLowerCase()).toMatch(/4|four|deselect/);
    });

    it("enables the button for 3 same-major builds", async () => {
      // Same major across all 3 implies same career (CIP → SOC is
      // deterministic in this app), so the (major_text + career)
      // signature is identical → button enabled.
      const threeSameMajor = makeCompareResult({
        builds: [
          makeBuild("a", "School A", "Mechanical Engineering", "Mechanical Engineers", "17-2141"),
          makeBuild("b", "School B", "Mechanical Engineering", "Mechanical Engineers", "17-2141"),
          makeBuild("c", "School C", "Mechanical Engineering", "Mechanical Engineers", "17-2141"),
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
          { build_id: "a", career: "Mech Eng A", destinations: [] },
          { build_id: "b", career: "Mech Eng B", destinations: [] },
          { build_id: "c", career: "Mech Eng C", destinations: [] },
        ],
      });
      mockCompareBuilds.mockResolvedValue(threeSameMajor);

      renderCV(["a", "b", "c"]);

      await waitFor(() => {
        expect(screen.getByTestId("btn-export-pdf-compare")).toBeInTheDocument();
      });

      const btn = screen.getByTestId(
        "btn-export-pdf-compare",
      ) as HTMLButtonElement;
      // Button is enabled — no disabled flag and no title-tooltip explainer.
      expect(btn.disabled).toBe(false);
    });
  });
});
