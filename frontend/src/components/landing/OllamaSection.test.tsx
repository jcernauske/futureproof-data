import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { OllamaSection } from "./OllamaSection";
import { resetReducedMotion } from "@/test/mocks/prefers-reduced-motion";

/**
 * Section E — Run It Yourself (Gemma + Ollama) tests.
 *
 * Two high-stakes assertions live here:
 *
 *  1. The scoped Ollama claim ("When a school runs FutureProof on Ollama,
 *     no student data leaves the building...") — this is the architect
 *     re-review hand-off from §5 Condition 8. The bare standalone phrase
 *     "No student data leaves the building." MUST NOT ship, because the
 *     live demo runs OpenRouter and it would be an overclaim.
 *
 *  2. Terminal commands render as real text (per §2 Decision 7) — copy-pasteable
 *     and zoomable, not a PNG screenshot of iTerm2.
 *
 * The third test exercises the plush-laptop fallback per §2 Decision 10.
 */

describe("OllamaSection", () => {
  beforeEach(() => {
    resetReducedMotion();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the headline with both sentences per §3.8 copy ground truth", () => {
    render(<OllamaSection />);
    expect(
      screen.getByText(/Any school can run this on their own hardware\./),
    ).toBeInTheDocument();
    expect(screen.getByText(/Forever\. At zero cost\./)).toBeInTheDocument();
  });

  it("terminal commands are real text nodes, not images", () => {
    render(<OllamaSection />);

    // Terminal figure is addressable by spec identifier.
    const terminal = document.getElementById("landing-ollama-terminal");
    expect(terminal).not.toBeNull();
    expect(terminal?.tagName).toBe("FIGURE");

    // Commands exist as live text — `getByText` would throw if they were SVG
    // images or data attributes.
    expect(screen.getByText(/ollama pull gemma4:e4b/)).toBeInTheDocument();
    expect(
      screen.getByText(/INFERENCE_BACKEND=ollama npm run dev/),
    ).toBeInTheDocument();
    expect(screen.getByText(/ready at :5173/)).toBeInTheDocument();

    // And the "complete" confirmation line from the first command.
    expect(screen.getByText(/complete/)).toBeInTheDocument();
  });

  it("terminal has the a11y label naming both commands", () => {
    render(<OllamaSection />);
    const terminal = document.getElementById("landing-ollama-terminal");
    expect(terminal?.getAttribute("aria-label")).toBe(
      "Terminal showing ollama pull gemma4:e4b and local launch commands",
    );
  });

  it("scoped Ollama claim ships with the 'when a school runs' clause (ARCHITECT RE-REVIEW gate)", () => {
    const { container } = render(<OllamaSection />);

    // Critical full sentence per §2 Decision 8 + §3.8 architect hand-off.
    const fullText = container.textContent ?? "";
    expect(fullText).toContain(
      "When a school runs FutureProof on Ollama, no student data leaves the building. No cloud bill. No ongoing cost.",
    );

    // Negative assertion: the bare phrase must NEVER appear as a standalone
    // sentence (i.e. preceded by a period or at the start of a block). If a
    // future edit strips the "When a school runs..." clause, this fires.
    //
    // We scan for `. No student data leaves the building.` (period + space + bare claim)
    // or the claim at the start of a paragraph.
    const bareStandalone = /(?:^|\.\s+|\.\s*\n\s*)No student data leaves the building\./;
    expect(bareStandalone.test(fullText)).toBe(false);

    // And the specific preceding clause must always come right before the claim.
    const scopedPattern = /When a school runs FutureProof on Ollama,\s*no student data leaves the building\./;
    expect(scopedPattern.test(fullText)).toBe(true);
  });

  it("body paragraphs ship with the 'flip one environment variable' framing", () => {
    render(<OllamaSection />);
    expect(
      screen.getByText(
        /FutureProof runs on Gemma 4 through Ollama\. Flip one environment variable and the whole stack — stats, fights, the Guide's coaching, the branch tree — works on a school's own server\./,
      ),
    ).toBeInTheDocument();
  });

  it("plush-laptop illustration slot is not rendered (replaced by spec callout)", () => {
    render(<OllamaSection />);
    // Per visual critique §3 item 15 option (b): rather than ship an empty
    // third column waiting for an illustration that didn't land this cycle,
    // the slot now carries a receipt-styled hardware-spec callout. The
    // `landing-ollama-laptop` id returns if/when the SVG ships (spec §11
    // follow-up tracks the re-add).
    expect(document.getElementById("landing-ollama-laptop")).toBeNull();
  });

  it("hardware-spec callout renders in place of the laptop slot", () => {
    render(<OllamaSection />);
    const specs = document.getElementById("landing-ollama-specs");
    expect(specs).not.toBeNull();
    expect(specs?.tagName).toBe("ASIDE");
    // Confirm the key hardware-claim data points render — these are the
    // receipts that carry the credibility the illustration would have.
    expect(screen.getByText(/Runs locally on/i)).toBeInTheDocument();
    expect(screen.getByText("Apple Silicon")).toBeInTheDocument();
    expect(screen.getByText(/M1 · M2 · M3 · M4/)).toBeInTheDocument();
    expect(screen.getByText(/8.*GB minimum/)).toBeInTheDocument();
    // "gemma4:e4b" appears in both the terminal and the callout — scope
    // to the callout to avoid multi-match.
    expect(specs?.textContent).toContain("gemma4:e4b");
  });
});
