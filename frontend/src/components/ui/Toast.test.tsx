import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { Toast } from "./Toast";

describe("Toast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when open is false", () => {
    render(<Toast open={false} message="hi" onClose={() => {}} />);
    expect(screen.queryByTestId("header-toast")).not.toBeInTheDocument();
  });

  it("renders the message when open is true", () => {
    render(<Toast open={true} message="Saved" onClose={() => {}} />);
    expect(screen.getByTestId("header-toast")).toHaveTextContent("Saved");
  });

  it("renders with role=status and aria-live=polite", () => {
    render(<Toast open={true} message="Saved" onClose={() => {}} />);
    const toast = screen.getByTestId("header-toast");
    expect(toast).toHaveAttribute("role", "status");
    expect(toast).toHaveAttribute("aria-live", "polite");
  });

  it("auto-dismisses after duration", () => {
    const onClose = vi.fn();
    render(
      <Toast
        open={true}
        message="Saved"
        durationMs={1000}
        onClose={onClose}
      />,
    );
    expect(onClose).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("uses default duration of 1000ms when none provided", () => {
    const onClose = vi.fn();
    render(<Toast open={true} message="Saved" onClose={onClose} />);
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(onClose).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("hides the leading spark glyph from screen readers", () => {
    render(<Toast open={true} message="Saved" onClose={() => {}} />);
    const sparkSpan = screen
      .getByTestId("header-toast")
      .querySelector('span[aria-hidden="true"]');
    expect(sparkSpan).not.toBeNull();
    expect(sparkSpan!.textContent).toBe("✦");
  });

  it("resets the dismiss timer when message changes (replace-in-place)", () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <Toast
        open={true}
        message="First"
        durationMs={1000}
        onClose={onClose}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(800);
    });
    rerender(
      <Toast
        open={true}
        message="Second"
        durationMs={1000}
        onClose={onClose}
      />,
    );
    // 800ms more would have triggered the first timer; the new effect resets it.
    act(() => {
      vi.advanceTimersByTime(800);
    });
    expect(onClose).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("supports a custom testId", () => {
    render(
      <Toast
        open={true}
        message="x"
        onClose={() => {}}
        testId="custom-toast"
      />,
    );
    expect(screen.getByTestId("custom-toast")).toBeInTheDocument();
  });
});
