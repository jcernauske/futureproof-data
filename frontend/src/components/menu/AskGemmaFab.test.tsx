/**
 * AskGemmaFab.test.tsx — sticky FAB on /my-build.
 *
 * Spec: docs/specs/feature-ask-gemma.md §3 entry point #4 + §4 P1.
 *
 * What's tested:
 *   - When `visible={false}`, the FAB renders no interactive element.
 *   - When `visible={true}`, the FAB renders a button with the
 *     localized `aria-label` for "Ask Gemma about your whole build".
 *   - Clicking the FAB invokes `onOpen` exactly once.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AskGemmaFab } from "./AskGemmaFab";

describe("AskGemmaFab (P1)", () => {
  it("hides the FAB button when visible={false}", () => {
    render(<AskGemmaFab visible={false} onOpen={() => {}} />);
    // The FAB button must not be in the DOM when hidden — the parent
    // sets `visible={!chatOpen && build !== null}` and the FAB is
    // expected to disappear so it never overlaps the chat dialog.
    expect(screen.queryByTestId("btn-ask-build")).toBeNull();
    // Defensive: no button at all renders.
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders a button with the localized aria-label when visible={true}", () => {
    render(<AskGemmaFab visible={true} onOpen={() => {}} />);
    const button = screen.getByTestId("btn-ask-build");
    expect(button).toBeInTheDocument();
    // The aria-label is the i18n string `chat.askAboutBuild`. The
    // localized English value is "Ask the Guide about your whole build".
    // Locking it here means a future copy change to the UI string
    // forces a paired update to the test — which is exactly the
    // behavior we want for an accessibility-critical label.
    expect(button).toHaveAttribute(
      "aria-label",
      "Ask the Guide about your whole build",
    );
  });

  it("invokes onOpen exactly once when clicked (saboteur: double-fire)", () => {
    const onOpen = vi.fn();
    render(<AskGemmaFab visible={true} onOpen={onOpen} />);
    fireEvent.click(screen.getByTestId("btn-ask-build"));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });
});
