import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TreeNodeDetailPanel } from "./TreeNodeDetailPanel";
import type { PositionedNode } from "@/data/treeLayout";

/**
 * TreeNodeDetailPanel.test.tsx
 *
 * Tests the detail panel that appears when a user clicks a tree node.
 * This component has real logic:
 * - Stat delta computation (node stat - root stat)
 * - Positive deltas show green with "+"
 * - Negative deltas show orange
 * - Zero deltas show dash
 * - Boss fight results map to colored pills
 * - "unknown" boss results are hidden
 * - Close button fires onClose callback
 * - Salary formatting with toLocaleString
 * - Education block only renders when present
 */

function makeNode(overrides: Partial<PositionedNode> = {}): PositionedNode {
  return {
    id: "career-11-3031-0",
    soc_code: "11-3031",
    title: "Financial Manager",
    level: 1,
    x: 420,
    y: 200,
    stats: { ern: 85, roi: 74, res: 42, grw: 55, hmn: 52 },
    bosses: {
      ai: "win",
      loans: "win",
      market: "draw",
      burnout: "lose",
      ceiling: "win",
    },
    median_wage: 139790,
    education: "Bachelor's degree + experience",
    parentId: "root-13-2051",
    branchColor: "#F2D477",
    branchLabel: "Go Management",
    ...overrides,
  };
}

function makeRootNode(overrides: Partial<PositionedNode> = {}): PositionedNode {
  return {
    id: "root-13-2051",
    soc_code: "13-2051",
    title: "Financial Analyst",
    level: 0,
    x: 80,
    y: 300,
    stats: { ern: 72, roi: 68, res: 45, grw: 61, hmn: 38 },
    bosses: {
      ai: "draw",
      loans: "win",
      market: "win",
      burnout: "lose",
      ceiling: "draw",
    },
    median_wage: 95570,
    education: "Bachelor's degree",
    parentId: null,
    branchColor: "#7DD4A3",
    branchLabel: null,
    ...overrides,
  };
}

describe("TreeNodeDetailPanel", () => {
  it("renders nothing when node is null", () => {
    const { container } = render(
      <TreeNodeDetailPanel node={null} rootNode={makeRootNode()} onClose={vi.fn()} />,
    );

    expect(screen.queryByTestId("panel-node-detail")).not.toBeInTheDocument();
    // Verify the container has no panel content
    expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument();
  });

  it("renders the node title", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ title: "Financial Manager" })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("Financial Manager")).toBeInTheDocument();
  });

  it("renders SOC code and formatted salary", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ soc_code: "11-3031", median_wage: 139790 })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    // The component renders "SOC 11-3031 · $139,790"
    const socText = screen.getByText(/SOC 11-3031/);
    expect(socText).toBeInTheDocument();
    expect(socText.textContent).toContain("$139,790");
  });

  it("renders SOC code without salary when median_wage is null", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ median_wage: null })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    const socText = screen.getByText(/SOC 11-3031/);
    expect(socText).toBeInTheDocument();
    // Should NOT contain a dollar sign
    expect(socText.textContent).not.toContain("$");
  });

  it("renders education block when education is present", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ education: "Master's preferred" })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("Master's preferred")).toBeInTheDocument();
  });

  it("does NOT render education block when education is null", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ education: null })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    // The education section shouldn't appear at all
    expect(screen.queryByText("Bachelor's degree + experience")).not.toBeInTheDocument();
  });

  // --- Stat deltas ---

  it("shows positive stat deltas with '+' prefix", () => {
    // node.ern=85, root.ern=72, delta = +13
    render(
      <TreeNodeDetailPanel
        node={makeNode({ stats: { ern: 85, roi: 74, res: 42, grw: 55, hmn: 52 } })}
        rootNode={makeRootNode({ stats: { ern: 72, roi: 68, res: 45, grw: 61, hmn: 38 } })}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("+13")).toBeInTheDocument(); // ern: 85-72
    expect(screen.getByText("+6")).toBeInTheDocument();  // roi: 74-68
    expect(screen.getByText("+14")).toBeInTheDocument(); // hmn: 52-38
  });

  it("shows negative stat deltas without '+' prefix", () => {
    // node.res=42, root.res=45, delta = -3
    // node.grw=55, root.grw=61, delta = -6
    render(
      <TreeNodeDetailPanel
        node={makeNode({ stats: { ern: 85, roi: 74, res: 42, grw: 55, hmn: 52 } })}
        rootNode={makeRootNode({ stats: { ern: 72, roi: 68, res: 45, grw: 61, hmn: 38 } })}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("-3")).toBeInTheDocument();  // res: 42-45
    expect(screen.getByText("-6")).toBeInTheDocument();  // grw: 55-61
  });

  it("shows dash for zero delta (stat unchanged from root)", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ stats: { ern: 72, roi: 68, res: 45, grw: 61, hmn: 38 } })}
        rootNode={makeRootNode({ stats: { ern: 72, roi: 68, res: 45, grw: 61, hmn: 38 } })}
        onClose={vi.fn()}
      />,
    );

    // When delta is 0, the component renders an mdash entity
    // All 5 stats have zero delta, so we should see 5 dashes
    const dashes = screen.getAllByText("\u2014");
    expect(dashes.length).toBe(5);
  });

  it("handles null stat values gracefully (shows em-dash for value)", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ stats: { ern: null, roi: null, res: null, grw: null, hmn: null } })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    // When val is null, it renders "\u2014" as the value
    // The component shows the em-dash for null values
    const dashes = screen.getAllByText("\u2014");
    expect(dashes.length).toBeGreaterThan(0);
  });

  // --- Boss fight projection ---

  it("renders boss fight results as pills for known outcomes", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({
          bosses: { ai: "win", loans: "win", market: "draw", burnout: "lose", ceiling: "win" },
        })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("Boss fight projection")).toBeInTheDocument();
    // Should see result pills
    const wins = screen.getAllByText("win");
    expect(wins.length).toBe(3); // ai, loans, ceiling
    expect(screen.getByText("draw")).toBeInTheDocument(); // market
    expect(screen.getByText("lose")).toBeInTheDocument(); // burnout
  });

  it("hides boss rows with 'unknown' result", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({
          bosses: { ai: "unknown", loans: "win", market: null, burnout: "unknown", ceiling: "lose" },
        })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    // ai and burnout are "unknown", market is null — all should be hidden
    expect(screen.queryByText("Fight AI")).not.toBeInTheDocument();
    expect(screen.queryByText("Burnout")).not.toBeInTheDocument();
    expect(screen.queryByText("The Market")).not.toBeInTheDocument();

    // loans and ceiling should render
    expect(screen.getByText(/Student Loans/)).toBeInTheDocument();
    expect(screen.getByText(/The Ceiling/)).toBeInTheDocument();
  });

  it("hides boss rows with null result", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({
          bosses: { ai: null, loans: null, market: null, burnout: null, ceiling: null },
        })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    // No boss rows should appear
    expect(screen.queryByText("Fight AI")).not.toBeInTheDocument();
    expect(screen.queryByText("Student Loans")).not.toBeInTheDocument();
    expect(screen.queryByText("The Market")).not.toBeInTheDocument();
    expect(screen.queryByText("Burnout")).not.toBeInTheDocument();
    expect(screen.queryByText("The Ceiling")).not.toBeInTheDocument();
  });

  // --- Close button ---

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <TreeNodeDetailPanel
        node={makeNode()}
        rootNode={makeRootNode()}
        onClose={onClose}
      />,
    );

    fireEvent.click(screen.getByTestId("btn-close-detail"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // --- Aria ---

  it("sets aria-label with the node title", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ title: "Chief Executive" })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByRole("dialog", { name: "Details for Chief Executive" })).toBeInTheDocument();
  });

  // --- All five stat labels are rendered ---

  it("renders all five stat labels (ERN, ROI, RES, GRW, HMN)", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode()}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("ERN")).toBeInTheDocument();
    expect(screen.getByText("ROI")).toBeInTheDocument();
    expect(screen.getByText("RES")).toBeInTheDocument();
    expect(screen.getByText("GRW")).toBeInTheDocument();
    expect(screen.getByText("HMN")).toBeInTheDocument();
  });

  // --- Stat values are rendered ---

  it("renders actual stat values as numbers", () => {
    render(
      <TreeNodeDetailPanel
        node={makeNode({ stats: { ern: 85, roi: 74, res: 42, grw: 55, hmn: 52 } })}
        rootNode={makeRootNode()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("74")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("55")).toBeInTheDocument();
    expect(screen.getByText("52")).toBeInTheDocument();
  });
});
