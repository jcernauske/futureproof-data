/**
 * FrameProgressDots.test.tsx
 *
 * Tests the 4px→20px pill + past/future color split on the progress
 * dot row. Framer Motion's `animate` prop doesn't apply inline styles
 * in jsdom, so we capture its `animate` payload via a local mock of
 * `motion.span`. That lets us assert on what the component SENDS to
 * the animation layer — which is the closest to observable behavior
 * we can get without a real browser.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

// Captured animate payloads per rendered span, in mount order.
const capturedAnimate: Array<Record<string, unknown>> = [];

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<object>("framer-motion");
  const React = await import("react");
  return {
    ...actual,
    motion: new Proxy(
      {},
      {
        get: (_target, tag: string) => {
          return (props: Record<string, unknown>) => {
            if (props.animate && typeof props.animate === "object") {
              capturedAnimate.push(props.animate as Record<string, unknown>);
            }
            const {
              animate: _animate,
              initial: _initial,
              exit: _exit,
              transition: _transition,
              variants: _variants,
              whileTap: _whileTap,
              whileHover: _whileHover,
              custom: _custom,
              ...rest
            } = props;
            return React.createElement(tag, rest);
          };
        },
      },
    ),
  };
});

// Import AFTER the mock so the component picks up the mocked motion.
import { FrameProgressDots } from "./FrameProgressDots";

describe("FrameProgressDots", () => {
  beforeEach(() => {
    capturedAnimate.length = 0;
  });

  it("renders exactly `total` dot elements", () => {
    const { container } = render(<FrameProgressDots total={6} current={0} />);
    const dots = container.querySelectorAll('[aria-hidden="true"]');
    expect(dots.length).toBe(6);
  });

  it("renders three dots for total=3", () => {
    const { container } = render(<FrameProgressDots total={3} current={0} />);
    expect(
      container.querySelectorAll('[aria-hidden="true"]').length,
    ).toBe(3);
  });

  it("navigation aria-label includes the 1-indexed current frame", () => {
    render(<FrameProgressDots total={6} current={2} />);
    const nav = screen.getByTestId("nav-frame-progress");
    // current=2 (0-indexed) surfaces as "frame 3 of 6"
    expect(nav).toHaveAttribute(
      "aria-label",
      "Story progress: frame 3 of 6",
    );
  });

  it("aria-label updates for the final frame", () => {
    render(<FrameProgressDots total={6} current={5} />);
    expect(screen.getByTestId("nav-frame-progress")).toHaveAttribute(
      "aria-label",
      "Story progress: frame 6 of 6",
    );
  });

  // --- Styling via captured animate payloads ---

  it("current dot animates to width 20 (pill); others stay at width 4", () => {
    render(<FrameProgressDots total={6} current={2} />);
    // capturedAnimate[i] corresponds to dot i, in mount order
    expect(capturedAnimate).toHaveLength(6);
    expect(capturedAnimate[2]!.width).toBe(20);
    for (const i of [0, 1, 3, 4, 5]) {
      expect(capturedAnimate[i]!.width).toBe(4);
    }
  });

  it("current dot animates to the thrive accent color", () => {
    render(<FrameProgressDots total={6} current={3} />);
    expect(capturedAnimate[3]!.backgroundColor).toBe(
      "var(--color-accent-thrive)",
    );
  });

  it("past dots animate to a different color than future dots", () => {
    /* Past = text-secondary, future = bg-surface. They MUST differ or
     * the user can't tell where they are in the sequence. */
    render(<FrameProgressDots total={6} current={3} />);
    const past0 = capturedAnimate[0]!.backgroundColor;
    const past2 = capturedAnimate[2]!.backgroundColor;
    const future4 = capturedAnimate[4]!.backgroundColor;
    const future5 = capturedAnimate[5]!.backgroundColor;

    expect(past0).toBe("var(--color-text-secondary)");
    expect(past2).toBe("var(--color-text-secondary)");
    expect(future4).toBe("var(--color-bg-surface)");
    expect(future5).toBe("var(--color-bg-surface)");
    expect(past0).not.toBe(future4);
  });

  it("current=0 marks only the first dot active; rest are 'future'", () => {
    render(<FrameProgressDots total={4} current={0} />);
    expect(capturedAnimate[0]!.backgroundColor).toBe(
      "var(--color-accent-thrive)",
    );
    for (const i of [1, 2, 3]) {
      expect(capturedAnimate[i]!.backgroundColor).toBe(
        "var(--color-bg-surface)",
      );
    }
  });

  it("current=total-1 marks last dot active and all prior as 'past'", () => {
    render(<FrameProgressDots total={4} current={3} />);
    for (const i of [0, 1, 2]) {
      expect(capturedAnimate[i]!.backgroundColor).toBe(
        "var(--color-text-secondary)",
      );
    }
    expect(capturedAnimate[3]!.backgroundColor).toBe(
      "var(--color-accent-thrive)",
    );
  });

  it("zero total renders an empty nav without crashing", () => {
    /* Saboteur: what if we get called with total=0? The component uses
     * Array.from({length: total}), which handles 0 cleanly. */
    const { container } = render(<FrameProgressDots total={0} current={0} />);
    expect(
      container.querySelectorAll('[aria-hidden="true"]').length,
    ).toBe(0);
    expect(capturedAnimate).toHaveLength(0);
  });
});
