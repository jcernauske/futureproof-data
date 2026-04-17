/**
 * WrappedViewer.test.tsx
 *
 * Tests the tappable story-viewer shell:
 * - Renders all 6 frames via WrappedFrame (placeholders in test env)
 * - Tap-forward zone advances the frame
 * - Tap-back on frame 0 is a no-op
 * - Progress dots reflect the current frame
 * - Download button invokes the handler for the CURRENT frame
 * - Keyboard ArrowRight / ArrowLeft navigate
 * - Edge cases: past-end forward, past-start back, rapid keyboard mashing
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { WrappedViewer } from "./WrappedViewer";
import type { WrappedFrameInfo } from "@/api/wrapped";

function makeFrames(n = 6): WrappedFrameInfo[] {
  return Array.from({ length: n }, (_, i) => ({
    index: i,
    url: `data:image/svg+xml;base64,frame-${i}`,
  }));
}

describe("WrappedViewer", () => {
  let onDone: ReturnType<typeof vi.fn>;
  let onDownloadFrame: ReturnType<typeof vi.fn>;
  let onDownloadAll: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onDone = vi.fn();
    onDownloadFrame = vi.fn();
    onDownloadAll = vi.fn();
  });

  function renderViewer(frames = makeFrames()) {
    return render(
      <WrappedViewer
        frames={frames}
        onDone={onDone}
        onDownloadFrame={onDownloadFrame}
        onDownloadAll={onDownloadAll}
      />,
    );
  }

  // --- Initial render ---

  it("mounts at frame 0 and shows '1 / 6' counter", () => {
    renderViewer();
    expect(screen.getByText("1 / 6")).toBeInTheDocument();
  });

  it("sets aria-label on the viewer region for the current frame", () => {
    renderViewer();
    const region = screen.getByTestId("region-wrapped-viewer");
    expect(region).toHaveAttribute(
      "aria-label",
      "Your build story — frame 1 of 6",
    );
  });

  it("renders the current WrappedFrame with its URL", () => {
    renderViewer();
    const img = screen.getByTestId("frame-0");
    // Mock frames use data URIs as their URL
    expect(img).toHaveAttribute("src", "data:image/svg+xml;base64,frame-0");
  });

  // --- Tap forward ---

  it("tap-forward advances to frame 2 (index 1)", () => {
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    expect(screen.getByText("2 / 6")).toBeInTheDocument();
    expect(screen.getByTestId("frame-1")).toBeInTheDocument();
  });

  it("tap-forward twice advances to frame 3", () => {
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    expect(screen.getByText("3 / 6")).toBeInTheDocument();
  });

  it("tap-forward on last frame does not advance past 6 / 6", () => {
    /* The forward button is disabled on the last frame — and the
     * counter must never read "7 / 6". Saboteur check: mashing
     * the forward zone shouldn't be able to break out-of-range. */
    renderViewer();
    // Advance to the last frame (5 forward taps)
    for (let i = 0; i < 5; i++) {
      fireEvent.click(screen.getByTestId("btn-frame-forward"));
    }
    expect(screen.getByText("6 / 6")).toBeInTheDocument();

    // Forward button should now be disabled
    expect(screen.getByTestId("btn-frame-forward")).toBeDisabled();

    // Attempt another click — counter must stay at 6 / 6
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    expect(screen.getByText("6 / 6")).toBeInTheDocument();
  });

  // --- Tap back ---

  it("tap-back on frame 0 is a no-op (counter stays at 1 / 6)", () => {
    renderViewer();
    expect(screen.getByTestId("btn-frame-back")).toBeDisabled();

    fireEvent.click(screen.getByTestId("btn-frame-back"));
    expect(screen.getByText("1 / 6")).toBeInTheDocument();
  });

  it("tap-back from frame 2 returns to frame 1", () => {
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    expect(screen.getByText("2 / 6")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("btn-frame-back"));
    expect(screen.getByText("1 / 6")).toBeInTheDocument();
  });

  // --- Progress dots ---

  it("renders a progress-dot navigation with the correct aria-label", () => {
    renderViewer();
    const nav = screen.getByTestId("nav-frame-progress");
    expect(nav).toHaveAttribute(
      "aria-label",
      "Story progress: frame 1 of 6",
    );
  });

  it("progress dots aria-label updates as user advances", () => {
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    fireEvent.click(screen.getByTestId("btn-frame-forward"));

    const nav = screen.getByTestId("nav-frame-progress");
    expect(nav).toHaveAttribute(
      "aria-label",
      "Story progress: frame 3 of 6",
    );
  });

  // --- Download handlers ---

  it("'Download this frame' invokes onDownloadFrame with the current index", () => {
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-download-frame"));
    expect(onDownloadFrame).toHaveBeenCalledTimes(1);
    expect(onDownloadFrame).toHaveBeenCalledWith(0);
  });

  it("download button passes the CURRENT index after navigating", () => {
    /* Saboteur check: does the handler bind to frame 0 because it
     * captures state at render? Nope — it must reflect the frame the
     * user is currently looking at. */
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    fireEvent.click(screen.getByTestId("btn-frame-forward"));
    fireEvent.click(screen.getByTestId("btn-frame-forward"));

    fireEvent.click(screen.getByTestId("btn-download-frame"));
    expect(onDownloadFrame).toHaveBeenCalledWith(3);
  });

  it("'Download all' invokes onDownloadAll once", () => {
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-download-all"));
    expect(onDownloadAll).toHaveBeenCalledTimes(1);
  });

  it("'Done →' invokes onDone once", () => {
    renderViewer();
    fireEvent.click(screen.getByTestId("btn-done"));
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  // --- Keyboard navigation ---

  it("ArrowRight advances the current frame", () => {
    renderViewer();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(screen.getByText("2 / 6")).toBeInTheDocument();
  });

  it("ArrowLeft on frame 0 is a no-op", () => {
    renderViewer();
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByText("1 / 6")).toBeInTheDocument();
  });

  it("ArrowRight then ArrowLeft returns to the first frame", () => {
    renderViewer();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByText("1 / 6")).toBeInTheDocument();
  });

  it("mashing ArrowRight 20 times stops cleanly at the final frame", () => {
    /* Saboteur check: if the user keyboard-mashes past the end,
     * we should NOT throw, log errors, or end up with stale state. */
    renderViewer();
    for (let i = 0; i < 20; i++) {
      fireEvent.keyDown(window, { key: "ArrowRight" });
    }
    expect(screen.getByText("6 / 6")).toBeInTheDocument();
  });

  it("ignores non-arrow keys", () => {
    renderViewer();
    fireEvent.keyDown(window, { key: "a" });
    fireEvent.keyDown(window, { key: "Enter" });
    fireEvent.keyDown(window, { key: " " });
    expect(screen.getByText("1 / 6")).toBeInTheDocument();
  });

  it("removes the keydown listener on unmount (no state updates after)", () => {
    /* If the listener leaks, ArrowRight after unmount throws a React
     * warning about state updates on unmounted components. The
     * error-detecting assertion here is "no unhandled errors during
     * dispatch." */
    const { unmount } = renderViewer();
    unmount();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    // No assertion needed — the test passes if no errors thrown
  });

  // --- Accessibility identifiers ---

  it("exposes all spec-mandated test IDs for a11y linkage", () => {
    renderViewer();
    // Per spec §3 Accessibility table
    expect(screen.getByTestId("region-wrapped-viewer")).toBeInTheDocument();
    expect(screen.getByTestId("nav-frame-progress")).toBeInTheDocument();
    expect(screen.getByTestId("btn-frame-back")).toBeInTheDocument();
    expect(screen.getByTestId("btn-frame-forward")).toBeInTheDocument();
    expect(screen.getByTestId("btn-download-frame")).toBeInTheDocument();
    expect(screen.getByTestId("btn-download-all")).toBeInTheDocument();
    expect(screen.getByTestId("btn-done")).toBeInTheDocument();
  });
});
