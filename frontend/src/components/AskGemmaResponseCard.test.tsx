import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AskGemmaResponseCard } from "./AskGemmaResponseCard";

/**
 * AskGemmaResponseCard tests (P0/P1)
 *
 * - Loading state shows the GemmaThinking indicator.
 * - Answer renders when loaded (not loading).
 * - Regenerate button fires onRegenerate.
 * - Close button fires onClose.
 * - Card has role=region + aria-live=polite so screen readers announce
 *   the answer when it lands.
 */

describe("AskGemmaResponseCard", () => {
  it("renders loading state with GemmaThinking when loading=true", () => {
    render(
      <AskGemmaResponseCard
        loading={true}
        answer={null}
        onRegenerate={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    // GemmaThinking is role=status with "Gemma is answering…" copy.
    expect(screen.getByText(/Gemma is answering/i)).toBeInTheDocument();
    // The answer paragraph must NOT render while loading — the production
    // component branches: loading ? <GemmaThinking /> : <p>{answer}</p>.
    expect(screen.queryByText(/biology/i)).not.toBeInTheDocument();
  });

  it("disables Regenerate while loading (prevents double-fires)", () => {
    render(
      <AskGemmaResponseCard
        loading={true}
        answer={null}
        onRegenerate={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    const regen = screen.getByRole("button", { name: /Regenerate answer/i });
    expect(regen).toBeDisabled();
  });

  it("renders the answer when loading=false and answer is present", () => {
    render(
      <AskGemmaResponseCard
        loading={false}
        answer="Biology is the standard pre-med path."
        onRegenerate={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(
      screen.getByText("Biology is the standard pre-med path."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Gemma is answering/i)).not.toBeInTheDocument();
  });

  it("regenerate button fires onRegenerate callback once per click", () => {
    const onRegenerate = vi.fn();
    render(
      <AskGemmaResponseCard
        loading={false}
        answer="something"
        onRegenerate={onRegenerate}
        onClose={vi.fn()}
      />,
    );
    const regen = screen.getByRole("button", { name: /Regenerate answer/i });
    fireEvent.click(regen);
    expect(onRegenerate).toHaveBeenCalledTimes(1);
  });

  it("close button fires onClose callback once per click", () => {
    const onClose = vi.fn();
    render(
      <AskGemmaResponseCard
        loading={false}
        answer="something"
        onRegenerate={vi.fn()}
        onClose={onClose}
      />,
    );
    const close = screen.getByRole("button", { name: /Close answer/i });
    fireEvent.click(close);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("has role=region, aria-live=polite, and aria-label='Gemma answer'", () => {
    render(
      <AskGemmaResponseCard
        loading={false}
        answer="something"
        onRegenerate={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    const region = screen.getByRole("region", { name: "Gemma answer" });
    expect(region).toHaveAttribute("aria-live", "polite");
  });

  it("regenerate button is enabled when loading=false", () => {
    render(
      <AskGemmaResponseCard
        loading={false}
        answer="something"
        onRegenerate={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    const regen = screen.getByRole("button", { name: /Regenerate answer/i });
    expect(regen).not.toBeDisabled();
  });
});
