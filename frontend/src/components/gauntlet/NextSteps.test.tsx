import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// Mock framer-motion to bypass animation state (initial="hidden" keeps
// stagger children invisible in jsdom since animations never fire).
// Use a factory mock that creates stable component references.
vi.mock("framer-motion", async () => {
  const React = await import("react");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function makeMotionComponent(tag: string): React.FC<any> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Comp: React.FC<any> = ({ children, initial: _a, animate: _b, exit: _c, transition: _d, variants: _e, whileTap: _f, whileHover: _g, whileFocus: _h, whileInView: _i, layout: _j, layoutId: _k, ...domProps }) => {
      return React.createElement(tag, domProps, children);
    };
    Comp.displayName = `motion.${tag}`;
    return Comp;
  }

  const motionProxy = new Proxy(
    {} as Record<string, React.FC>,
    {
      get: (cache, prop: string) => {
        if (!cache[prop]) {
          cache[prop] = makeMotionComponent(prop);
        }
        return cache[prop];
      },
    },
  );

  return {
    motion: motionProxy,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => children,
  };
});

import { NextSteps } from "./NextSteps";

/**
 * NextSteps tests
 *
 * The NextSteps component renders Gemma-generated action checklist content
 * in four sections parsed from markdown (## headings). It handles three states:
 * loading, error, and content.
 *
 * Key behaviors:
 * - parseNextStepsSections splits markdown by "## " headings
 * - Each section gets an icon from SECTION_ICONS lookup
 * - Loading state shows bouncing emoji
 * - Error state shows retry + continue buttons
 * - Content state renders section cards with CTA buttons
 */

const MOCK_NEXT_STEPS_MARKDOWN = `## Questions to Ask Your Guidance Counselor
- Is this program accredited?
- What's the placement rate?

## Questions to Ask College Recruiters
- What internship programs exist?
- How do graduates do in the job market?

## Things to Verify on Your Own
- Look up salary data on BLS.gov
- Check Glassdoor reviews

## Points to Discuss with Your Parents
- How will we handle loans?
- Is the ROI worth the investment?`;

const defaultProps = {
  content: MOCK_NEXT_STEPS_MARKDOWN,
  error: false,
  loading: false,
  profileEmoji: "\u{1F43B}",
  onRetry: vi.fn(),
  onBranches: vi.fn(),
  onSave: vi.fn(),
  onBackToBuild: vi.fn(),
};

describe("NextSteps", () => {
  // ---- Content rendering ----

  describe("content state", () => {
    it("renders all four section headings", () => {
      render(<NextSteps {...defaultProps} />);

      expect(
        screen.getByText("Questions to Ask Your Guidance Counselor"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Questions to Ask College Recruiters"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Things to Verify on Your Own"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Points to Discuss with Your Parents"),
      ).toBeInTheDocument();
    });

    it("renders section content within each card", () => {
      render(<NextSteps {...defaultProps} />);

      expect(
        screen.getByText(/is this program accredited/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/how will we handle loans/i),
      ).toBeInTheDocument();
    });

    it("renders section articles with aria-labels", () => {
      render(<NextSteps {...defaultProps} />);

      expect(
        screen.getByLabelText("Questions to Ask Your Guidance Counselor"),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText("Points to Discuss with Your Parents"),
      ).toBeInTheDocument();
    });

    it("renders the YOUR NEXT STEPS header", () => {
      render(<NextSteps {...defaultProps} />);

      expect(screen.getByText("YOUR NEXT STEPS")).toBeInTheDocument();
    });

    it("renders CTA buttons", () => {
      render(<NextSteps {...defaultProps} />);

      expect(
        screen.getByLabelText("See where this path leads"),
      ).toBeInTheDocument();
      expect(screen.getByText(/save & share/i)).toBeInTheDocument();
      expect(screen.getByText(/back to my build/i)).toBeInTheDocument();
    });

    it("fires onBranches when primary CTA is clicked", () => {
      const onBranches = vi.fn();
      render(<NextSteps {...defaultProps} onBranches={onBranches} />);

      fireEvent.click(screen.getByLabelText("See where this path leads"));
      expect(onBranches).toHaveBeenCalledTimes(1);
    });

    it("fires onSave when save button is clicked", () => {
      const onSave = vi.fn();
      render(<NextSteps {...defaultProps} onSave={onSave} />);

      fireEvent.click(screen.getByText(/save & share/i));
      expect(onSave).toHaveBeenCalledTimes(1);
    });

    it("fires onBackToBuild when back button is clicked", () => {
      const onBackToBuild = vi.fn();
      render(<NextSteps {...defaultProps} onBackToBuild={onBackToBuild} />);

      fireEvent.click(screen.getByText(/back to my build/i));
      expect(onBackToBuild).toHaveBeenCalledTimes(1);
    });

    it("renders region ids for DOM targeting", () => {
      const { container } = render(<NextSteps {...defaultProps} />);

      expect(container.querySelector("#region-checklist-0")).toBeInTheDocument();
      expect(container.querySelector("#region-checklist-1")).toBeInTheDocument();
      expect(container.querySelector("#region-checklist-2")).toBeInTheDocument();
      expect(container.querySelector("#region-checklist-3")).toBeInTheDocument();
    });
  });

  // ---- Edge cases for markdown parsing ----

  describe("markdown parsing edge cases", () => {
    it("handles markdown with fewer than four sections", () => {
      const twoSections = `## Questions to Ask Your Guidance Counselor
- Is this program accredited?

## Things to Verify on Your Own
- Look up salary data`;

      const { container } = render(
        <NextSteps {...defaultProps} content={twoSections} />,
      );

      // Should render exactly 2 sections, not 4
      expect(
        screen.getByLabelText("Questions to Ask Your Guidance Counselor"),
      ).toBeInTheDocument();
      expect(
        screen.getByLabelText("Things to Verify on Your Own"),
      ).toBeInTheDocument();
      // Only 2 region divs
      expect(container.querySelector("#region-checklist-0")).toBeInTheDocument();
      expect(container.querySelector("#region-checklist-1")).toBeInTheDocument();
      expect(container.querySelector("#region-checklist-2")).not.toBeInTheDocument();
    });

    it("returns null when content is null and not loading or error", () => {
      const { container } = render(
        <NextSteps {...defaultProps} content={null} />,
      );

      // Component returns null -- the wrapper div from RTL has no meaningful content
      expect(container.querySelector(".w-full")).not.toBeInTheDocument();
      expect(screen.queryByText("YOUR NEXT STEPS")).not.toBeInTheDocument();
    });
  });

  // ---- Loading state ----

  describe("loading state", () => {
    it("renders loading indicator with profile emoji", () => {
      render(<NextSteps {...defaultProps} content={null} loading={true} />);

      expect(
        screen.getByLabelText(/generating your action plan/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/gemma is writing your action plan/i),
      ).toBeInTheDocument();
    });

    it("has role=status for screen readers", () => {
      render(<NextSteps {...defaultProps} content={null} loading={true} />);

      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("loading takes priority over content", () => {
      // Even if content exists, loading state should render
      render(
        <NextSteps
          {...defaultProps}
          content={MOCK_NEXT_STEPS_MARKDOWN}
          loading={true}
        />,
      );

      expect(
        screen.getByText(/gemma is writing your action plan/i),
      ).toBeInTheDocument();
      expect(screen.queryByText("YOUR NEXT STEPS")).not.toBeInTheDocument();
    });
  });

  // ---- Error state ----

  describe("error state", () => {
    it("renders error message", () => {
      render(
        <NextSteps {...defaultProps} content={null} error={true} />,
      );

      expect(
        screen.getByText(/couldn't generate your action plan/i),
      ).toBeInTheDocument();
    });

    it("renders retry button that calls onRetry", () => {
      const onRetry = vi.fn();
      render(
        <NextSteps
          {...defaultProps}
          content={null}
          error={true}
          onRetry={onRetry}
        />,
      );

      const retryButton = screen.getByText("Try Again");
      fireEvent.click(retryButton);
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it("renders continue button that calls onBranches", () => {
      const onBranches = vi.fn();
      render(
        <NextSteps
          {...defaultProps}
          content={null}
          error={true}
          onBranches={onBranches}
        />,
      );

      fireEvent.click(screen.getByText(/continue/i));
      expect(onBranches).toHaveBeenCalledTimes(1);
    });

    it("error takes priority over content", () => {
      render(
        <NextSteps
          {...defaultProps}
          content={MOCK_NEXT_STEPS_MARKDOWN}
          error={true}
        />,
      );

      expect(
        screen.getByText(/couldn't generate/i),
      ).toBeInTheDocument();
      expect(screen.queryByText("YOUR NEXT STEPS")).not.toBeInTheDocument();
    });
  });
});
