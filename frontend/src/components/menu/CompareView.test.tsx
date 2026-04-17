/**
 * CompareView.test.tsx
 *
 * Covers:
 * - Renders one Risk Headline card per boss (P0)
 * - Highlights divergence — caution kicker text "Your builds disagree here." (P0)
 * - Gemma summary text renders after sendChat resolves (P2)
 *
 * The @/api/menu module is mocked at module boundary so we control
 * compareBuilds and sendChat resolution timing.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { CompareView } from "./CompareView";
import type { CompareResult } from "@/api/menu";

const mockCompareBuilds = vi.fn();
const mockSendChat = vi.fn();
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    compareBuilds: (...args: unknown[]) => mockCompareBuilds(...args),
    sendChat: (...args: unknown[]) => mockSendChat(...args),
  };
});

function makeCompareResult(overrides: Partial<CompareResult> = {}): CompareResult {
  return {
    builds: [
      {
        build_id: "berkeley-cs-001",
        label: "UC Berkeley — Computer Science",
        career: "Software Developers",
      },
      {
        build_id: "iu-bloom-mkt-001",
        label: "IU Bloomington — Marketing",
        career: "Marketing Managers",
      },
    ],
    stats: [
      { label: "ERN", values: [8, 6] },
      { label: "ROI", values: [7, 6] },
      { label: "RES", values: [4, 7] },
      { label: "GRW", values: [9, 5] },
      { label: "HMN", values: [5, 8] },
    ],
    bosses: [
      // Divergent: Berkeley LOSES AI, IU WINS — should trigger divergence treatment.
      { label: "AI", values: ["LOSE", "WIN"] },
      // Both win — should NOT show divergence kicker.
      { label: "Loans", values: ["WIN", "WIN"] },
      { label: "Market", values: ["WIN", "WIN"] },
      // Both same outcome — agreement.
      { label: "Burnout", values: ["DRAW", "DRAW"] },
      { label: "Ceiling", values: ["WIN", "WIN"] },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  mockCompareBuilds.mockReset();
  mockSendChat.mockReset();
  // Default sendChat to a never-resolving promise — tests that care override.
  mockSendChat.mockReturnValue(new Promise(() => {}));
});

describe("CompareView", () => {
  // --- P0: renders one card per boss ---

  it("renders one Risk Headline card per boss in the result (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    render(
      <CompareView buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]} onBack={() => {}} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("card-risk-ai")).toBeInTheDocument();
    });
    expect(screen.getByTestId("card-risk-loans")).toBeInTheDocument();
    expect(screen.getByTestId("card-risk-market")).toBeInTheDocument();
    expect(screen.getByTestId("card-risk-burnout")).toBeInTheDocument();
    expect(screen.getByTestId("card-risk-ceiling")).toBeInTheDocument();
  });

  it("calls compareBuilds with the supplied buildIds (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    render(
      <CompareView
        buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]}
        onBack={() => {}}
      />,
    );

    await waitFor(() => {
      expect(mockCompareBuilds).toHaveBeenCalledWith([
        "berkeley-cs-001",
        "iu-bloom-mkt-001",
      ]);
    });
  });

  // --- P0: divergence highlighting ---

  it('shows "Your builds disagree here." on a divergent boss row (P0)', async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    render(
      <CompareView
        buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]}
        onBack={() => {}}
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("card-risk-ai")).toBeInTheDocument();
    });

    // Divergent kicker — only present on AI (LOSE vs WIN), not on Loans (WIN/WIN).
    const aiCard = screen.getByTestId("card-risk-ai");
    expect(aiCard).toHaveTextContent("Your builds disagree here.");

    const loansCard = screen.getByTestId("card-risk-loans");
    expect(loansCard).not.toHaveTextContent("Your builds disagree here.");
  });

  it("divergent card carries the accent-caution left border class (P0)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());

    render(
      <CompareView
        buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]}
        onBack={() => {}}
      />,
    );

    const aiCard = await screen.findByTestId("card-risk-ai");
    expect(aiCard.className).toMatch(/border-l-accent-caution/);

    const loansCard = screen.getByTestId("card-risk-loans");
    // Agreement rows render the transparent border placeholder, NOT the caution color.
    expect(loansCard.className).not.toMatch(/border-l-accent-caution/);
  });

  // --- P2: Gemma summary renders after sendChat resolves ---

  it("renders the Gemma summary text once sendChat resolves (P2)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());
    mockSendChat.mockResolvedValue(
      "Build A optimizes for earnings; Build B for resilience. Neither is wrong.",
    );

    render(
      <CompareView
        buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]}
        onBack={() => {}}
      />,
    );

    await waitFor(
      () => {
        expect(
          screen.getByText(/Build A optimizes for earnings/),
        ).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it("falls back to the loading placeholder when summary chat fails (saboteur)", async () => {
    mockCompareBuilds.mockResolvedValue(makeCompareResult());
    mockSendChat.mockRejectedValue(new Error("model unavailable"));

    render(
      <CompareView
        buildIds={["berkeley-cs-001", "iu-bloom-mkt-001"]}
        onBack={() => {}}
      />,
    );

    // Compare result still renders, summary region present, but no narrative text.
    await screen.findByTestId("region-gemma-compare");
    // The placeholder text — not blow-up — should still be visible.
    expect(screen.getByText(/Reading the tradeoffs/i)).toBeInTheDocument();
  });
});
