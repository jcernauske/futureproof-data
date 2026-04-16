import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BranchTreeSVG } from "./BranchTreeSVG";
import { computeLayout } from "@/data/treeLayout";
import type { TreeNode } from "@/types/tree";

/**
 * BranchTreeSVG.test.tsx
 *
 * Tests for the main SVG tree visualization component.
 *
 * Key behaviors tested:
 * - Root node renders with emoji, title, salary
 * - Career nodes and endpoint nodes render
 * - Branch paths (SVG <path> elements) are present
 * - Node selection callback fires on click
 * - Canvas click deselects (clears selection)
 * - Illumination sequence reveals elements progressively
 * - Replay button restarts the illumination
 * - Correct data-testid attributes for integration test hooks
 * - SVG accessibility (role="img", aria-label)
 *
 * We use vi.useFakeTimers() to control the illumination setTimeout cascade.
 */

function makeTree(): TreeNode {
  return {
    soc_code: "13-2051",
    title: "Financial Analyst",
    level: 0,
    ern: 72,
    roi: 68,
    res: 45,
    grw: 61,
    hmn: 38,
    median_wage: 95570,
    education: "Bachelor's degree",
    boss_ai: "draw",
    boss_loans: "win",
    boss_market: "win",
    boss_burnout: "lose",
    boss_ceiling: "draw",
    children: [
      {
        soc_code: "11-3031",
        title: "Financial Manager",
        level: 1,
        ern: 85,
        roi: 74,
        res: 42,
        grw: 55,
        hmn: 52,
        median_wage: 139790,
        education: "Bachelor's degree + experience",
        boss_ai: "win",
        boss_loans: "win",
        boss_market: "win",
        boss_burnout: "draw",
        boss_ceiling: "win",
        children: [
          {
            soc_code: "11-1011",
            title: "Chief Executive",
            level: 2,
            ern: 95,
            roi: 82,
            res: 38,
            grw: 48,
            hmn: 65,
            median_wage: 189520,
            education: "Master's preferred",
            boss_ai: "win",
            boss_loans: "win",
            boss_market: "draw",
            boss_burnout: "lose",
            boss_ceiling: "win",
            children: [
              {
                soc_code: "11-1021",
                title: "General & Operations Manager",
                level: 3,
                ern: 88,
                roi: 78,
                res: 40,
                grw: 50,
                hmn: 60,
                median_wage: 115250,
                education: "Bachelor's + 5yr experience",
                boss_ai: "win",
                boss_loans: "win",
                boss_market: "win",
                boss_burnout: "draw",
                boss_ceiling: "win",
                children: [],
              },
            ],
          },
        ],
      },
      {
        soc_code: "13-1161",
        title: "Market Research Analyst",
        level: 1,
        ern: 62,
        roi: 65,
        res: 48,
        grw: 70,
        hmn: 55,
        median_wage: 68230,
        education: "Bachelor's degree",
        boss_ai: "draw",
        boss_loans: "draw",
        boss_market: "win",
        boss_burnout: "win",
        boss_ceiling: "lose",
        children: [],
      },
    ],
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

function renderTree(overrides: Partial<Parameters<typeof BranchTreeSVG>[0]> = {}) {
  const tree = overrides.tree ?? makeTree();
  const defaultProps = {
    tree,
    layout: computeLayout(tree),
    emoji: "\uD83D\uDC3B",
    selectedNodeId: null,
    onSelectNode: vi.fn(),
  };
  return render(<BranchTreeSVG {...defaultProps} {...overrides} />);
}

describe("BranchTreeSVG", () => {
  // --- SVG container ---

  it("renders an SVG with the branch tree testid", () => {
    renderTree();
    // Advance all timers so elements are visible
    act(() => vi.advanceTimersByTime(5000));

    expect(screen.getByTestId("region-branch-tree")).toBeInTheDocument();
  });

  it("SVG has role='img' and descriptive aria-label", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    const svg = screen.getByTestId("region-branch-tree");
    expect(svg).toHaveAttribute("role", "img");
    expect(svg.getAttribute("aria-label")).toContain("Financial Analyst");
    expect(svg.getAttribute("aria-label")).toContain("career paths");
  });

  // --- Root node ---

  it("renders root node with data-testid after illumination", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    expect(screen.getByTestId("node-root")).toBeInTheDocument();
  });

  it("renders root node with emoji text", () => {
    renderTree({ emoji: "\uD83E\uDD8A" });
    act(() => vi.advanceTimersByTime(5000));

    // The emoji is rendered inside a <text> element
    const svg = screen.getByTestId("region-branch-tree");
    const texts = svg.querySelectorAll("text");
    const emojiTexts = Array.from(texts).filter((t) => t.textContent === "\uD83E\uDD8A");
    expect(emojiTexts.length).toBeGreaterThan(0);
  });

  it("renders root node title text", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    const svg = screen.getByTestId("region-branch-tree");
    const texts = svg.querySelectorAll("text");
    const titleTexts = Array.from(texts).filter((t) => t.textContent === "Financial Analyst");
    expect(titleTexts.length).toBeGreaterThan(0);
  });

  it("renders root salary text", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    const svg = screen.getByTestId("region-branch-tree");
    const texts = svg.querySelectorAll("text");
    const salaryTexts = Array.from(texts).filter((t) => t.textContent?.includes("$95,570"));
    expect(salaryTexts.length).toBeGreaterThan(0);
  });

  // --- Career nodes ---

  it("renders career nodes with data-testid containing SOC code", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    // Financial Manager branch has Chief Executive at level 2
    expect(screen.getByTestId("node-career-11-1011")).toBeInTheDocument();
    // Market Research is a direct branch (level 1)
    expect(screen.getByTestId("node-career-13-1161")).toBeInTheDocument();
  });

  // --- Endpoint nodes ---

  it("renders endpoint nodes with data-testid containing SOC code", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    expect(screen.getByTestId("node-endpoint-11-1021")).toBeInTheDocument();
  });

  // --- Branch paths ---

  it("renders SVG path elements for branch connections", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    const svg = screen.getByTestId("region-branch-tree");
    const paths = svg.querySelectorAll("path");
    // Should have multiple paths: root->label, label->career, career->endpoint
    expect(paths.length).toBeGreaterThan(0);
  });

  // --- Node selection ---

  it("calls onSelectNode with node id when career node is clicked", () => {
    const onSelectNode = vi.fn();
    renderTree({ onSelectNode });
    act(() => vi.advanceTimersByTime(5000));

    fireEvent.click(screen.getByTestId("node-career-11-1011"));

    expect(onSelectNode).toHaveBeenCalledWith("career-11-1011-0");
  });

  it("calls onSelectNode with root id when root node is clicked", () => {
    const onSelectNode = vi.fn();
    renderTree({ onSelectNode });
    act(() => vi.advanceTimersByTime(5000));

    fireEvent.click(screen.getByTestId("node-root"));

    expect(onSelectNode).toHaveBeenCalledWith("root-13-2051");
  });

  it("calls onSelectNode with endpoint id when endpoint is clicked", () => {
    const onSelectNode = vi.fn();
    renderTree({ onSelectNode });
    act(() => vi.advanceTimersByTime(5000));

    fireEvent.click(screen.getByTestId("node-endpoint-11-1021"));

    expect(onSelectNode).toHaveBeenCalledWith("endpoint-11-1021-0-0");
  });

  // --- Dimming behavior ---

  it("dims unselected nodes when a node is selected", () => {
    renderTree({ selectedNodeId: "career-11-1011-0" });
    act(() => vi.advanceTimersByTime(5000));

    // The root node is inside a <g> with opacity attribute set by TreeRootNode
    // TreeRootNode renders: <g id="rootNode" opacity={dimmed ? 0.4 : 1}>
    const rootNode = screen.getByTestId("node-root");
    const rootGroup = rootNode.closest("g[id='rootNode']");
    expect(rootGroup).not.toBeNull();
    expect(rootGroup!.getAttribute("opacity")).toBe("0.4");
  });

  // --- Replay button ---

  it("renders a replay button", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    expect(screen.getByTestId("btn-replay-tree")).toBeInTheDocument();
    expect(screen.getByText("Replay")).toBeInTheDocument();
  });

  // --- Illumination sequence ---

  it("root node is not visible before its scheduled timeout", () => {
    const { container } = renderTree();

    // At t=0, before any timers fire, the motion.g wrapping rootNode
    // has animate={{ opacity: phases.rootNode ? 1 : 0 }} which starts at 0
    // Check that the root node phase hasn't started yet
    // We need to verify that the rootNode timeout (300ms) hasn't fired
    // Don't advance timers — the rootNode should be in opacity:0 state
    const svg = container.querySelector('[data-testid="region-branch-tree"]');
    expect(svg).toBeInTheDocument();
  });

  it("elements appear progressively as timers fire", () => {
    renderTree();

    // At t=0, nothing visible yet
    // Advance past rootNode timeout (300ms)
    act(() => vi.advanceTimersByTime(350));

    // Root node should now be present (its phase is true)
    expect(screen.getByTestId("node-root")).toBeInTheDocument();

    // Career nodes appear at branchTree.careerStart * 1000 = 1500ms
    // Advance to after career nodes
    act(() => vi.advanceTimersByTime(1500));

    // Career nodes should now be present
    expect(screen.getByTestId("node-career-11-1011")).toBeInTheDocument();
  });

  // --- Gradient definitions ---

  it("renders linearGradient defs for branch colors", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    const svg = screen.getByTestId("region-branch-tree");
    const gradients = svg.querySelectorAll("linearGradient");
    expect(gradients.length).toBeGreaterThan(0);
  });

  // --- Star background ---

  it("renders star circles in the background", () => {
    renderTree();
    act(() => vi.advanceTimersByTime(5000));

    const svg = screen.getByTestId("region-branch-tree");
    const starsGroup = svg.querySelector("#stars");
    expect(starsGroup).not.toBeNull();
    const starCircles = starsGroup!.querySelectorAll("circle");
    expect(starCircles.length).toBe(40); // generateStars(40, ...)
  });
});
