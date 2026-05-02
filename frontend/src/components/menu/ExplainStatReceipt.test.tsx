/**
 * ExplainStatReceipt.test.tsx — structured receipt card for the
 * "Explain this stat" affordance on /my-build.
 *
 * Spec: docs/specs/feature-explain-stat-receipt.md (DRAFT v1.3) §3
 * (visual contract) + §4 New Tests Required (P0/P1 rows).
 *
 * The component is "dumb" rendering — all logic (score override,
 * label normalization, math line server-rendering, missing-reason
 * stamping) happens server-side. These tests bind the visual contract:
 *
 *   - Default state renders all four sections (callout, components,
 *     math card, sources, why-mix).
 *   - Missing-reason rows render the note + dim the row's text styling.
 *   - The score callout colors use `var(--color-stat-{stat_code})`.
 *   - The effort line surfaces as a separate visual element below the
 *     math card when `math_line` carries a `\n`-separated second line.
 *   - Accessibility attributes per §3 accessibility table.
 *   - Component does not overflow at the narrow (480px) breakpoint.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExplainStatReceiptCard } from "./ExplainStatReceipt";
import type { ExplainStatReceipt } from "@/types/chat";

// ---------------------------------------------------------------------------
// Fixtures — happy path + four state variants per §3 mockups
// ---------------------------------------------------------------------------

function makeHappyPayload(
  overrides: Partial<ExplainStatReceipt> = {},
): ExplainStatReceipt {
  return {
    kind: "receipt",
    stat_code: "ERN",
    stat_name: "Earning Power",
    score: 7,
    score_max: 10,
    one_liner:
      "Earning Power tells you how much your degree usually pays right after graduation.",
    components: [
      {
        weight_pct: 60,
        label: "your school's program rank",
        explainer:
          "IU Bloomington's Computer Science grads earn $94,200 — the 87th percentile (out of 100 programs, this one ranks higher than about 86) of all CS programs.",
        value_pct: 87,
        anchor_text: "Indiana University Computer Science grads",
        anchor_dollars: 94_200,
        missing_reason: null,
      },
      {
        weight_pct: 40,
        label: "this career's pay rank",
        explainer:
          "Software Developer pays a median of $132,270, which sits at the 92nd percentile.",
        value_pct: 92,
        anchor_text: "Software Developer",
        anchor_dollars: 132_270,
        missing_reason: null,
      },
    ],
    math_line: "0.6 × 0.87 + 0.4 × 0.92 → score 9/10",
    sources: [
      {
        label: "Graduate earnings",
        name: "College Scorecard (U.S. Department of Education)",
      },
      {
        label: "Occupation wages",
        name: "Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)",
      },
    ],
    why_mix_paragraph:
      "Picture a top CS program at a regional school vs. a top Philosophy program at a flagship. School rank alone would mislead. Mixing in occupation pay grounds the score in real salaries.",
    ...overrides,
  };
}

function makeMissingSchoolRankPayload(): ExplainStatReceipt {
  const base = makeHappyPayload();
  // The 60% component is the school-rank piece per the spec.
  base.components[0] = {
    ...base.components[0]!,
    value_pct: null,
    anchor_dollars: null,
    missing_reason: "no median earnings reported for this program yet",
  };
  base.math_line = "0.6 × n/a + 0.4 × 0.92 → score 7/10";
  return base;
}

// ---------------------------------------------------------------------------
// State 1 — default (both percentiles present, balanced effort)
// ---------------------------------------------------------------------------

describe("ExplainStatReceiptCard", () => {
  it("test_renders_default_state — all sections render with expected content (P0)", () => {
    const payload = makeHappyPayload();
    render(<ExplainStatReceiptCard payload={payload} />);

    // Score callout — stat name + score / score_max.
    expect(screen.getByText("Earning Power")).toBeInTheDocument();
    expect(screen.getByText(/^7$/)).toBeInTheDocument();
    expect(screen.getByText("/10")).toBeInTheDocument();

    // The one-liner.
    expect(
      screen.getByText(
        /Earning Power tells you how much your degree usually pays/,
      ),
    ).toBeInTheDocument();

    // Section headings render. Each label appears twice (sr-only h2 +
    // visible decorative div per §3 accessibility pattern), so use
    // getAllByText. The eyebrow text was changed to "Sources" by the
    // visionary's design audit (was "Where the data comes from").
    expect(screen.getAllByText("How it works").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sources").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Why we mix both pieces").length,
    ).toBeGreaterThan(0);

    // Components: both rows render with their labels + explainers.
    expect(screen.getByText("your school's program rank")).toBeInTheDocument();
    expect(screen.getByText("this career's pay rank")).toBeInTheDocument();
    // "87th percentile" appears both in the explainer prose AND in the
    // percentile-callout row. Both are intentional; getAllByText asserts
    // at least one is present.
    expect(screen.getAllByText(/87th percentile/).length).toBeGreaterThan(0);
    expect(
      screen.getByText(/Software Developer pays a median of \$132,270/),
    ).toBeInTheDocument();

    // Math line (first/only line) renders inside the receipt-math-line card.
    const mathCard = screen.getByTestId("receipt-math-line");
    expect(mathCard).toHaveTextContent("0.6 × 0.87 + 0.4 × 0.92 → score 9/10");

    // Sources render as 2 pills, identified by slug per §3 spec.
    expect(
      screen.getByTestId("receipt-source-college-scorecard"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("receipt-source-bls-ooh")).toBeInTheDocument();
    expect(
      screen.getByTestId("receipt-source-college-scorecard"),
    ).toHaveAttribute("title", expect.stringContaining("College Scorecard"));

    // why-mix paragraph renders.
    expect(
      screen.getByText(/Picture a top CS program at a regional school/),
    ).toBeInTheDocument();
  });

  // -----------------------------------------------------------------
  // State 2 — missing school rank (60% component)
  // -----------------------------------------------------------------

  it("test_renders_missing_school_rank — missing-reason row + dimmed styling (P0)", () => {
    const payload = makeMissingSchoolRankPayload();
    render(<ExplainStatReceiptCard payload={payload} />);

    // Missing-reason note renders.
    const note = screen.getByTestId("receipt-missing-60");
    expect(note).toBeInTheDocument();
    expect(note).toHaveTextContent(
      "no median earnings reported for this program yet",
    );

    // The 60% row's prose container dims to text-text-muted; the
    // percentage chip and the always-muted percentile callout don't
    // count for "row dimming." We scope to the .flex-1 prose wrapper.
    const row60 = screen.getByTestId("receipt-component-ern-60");
    const proseWrapper60 = row60.querySelector(".flex-1");
    expect(proseWrapper60).not.toBeNull();
    expect(proseWrapper60!.className).toContain("text-text-muted");

    // Math line carries n/a in the 60% slot.
    expect(screen.getByTestId("receipt-math-line")).toHaveTextContent(
      "0.6 × n/a",
    );
    // 40% row's prose wrapper is NOT dimmed (text-text-secondary).
    const row40 = screen.getByTestId("receipt-component-ern-40");
    const proseWrapper40 = row40.querySelector(".flex-1");
    expect(proseWrapper40).not.toBeNull();
    expect(proseWrapper40!.className).toContain("text-text-secondary");
    expect(proseWrapper40!.className).not.toContain("text-text-muted");
  });

  // -----------------------------------------------------------------
  // State color token — score callout colored via stat-code CSS var
  // -----------------------------------------------------------------

  it("test_renders_score_color_token — accent uses var(--color-stat-{code}) (P0)", () => {
    const payload = makeHappyPayload({ stat_code: "ERN" });
    render(<ExplainStatReceiptCard payload={payload} />);

    // The score callout's inline color style references the stat-code
    // CSS variable (lowercase). The component renders the score
    // value as the text "7" — find the element whose style.color is
    // the var.
    const region = screen.getByTestId("explain-stat-receipt");
    const styleString = region.getAttribute("style") ?? "";
    expect(styleString).toContain("var(--color-stat-ern)");
  });

  // -----------------------------------------------------------------
  // State 5 — effort line variant (Decision 13)
  // -----------------------------------------------------------------

  it("test_renders_effort_line_when_non_balanced — effort line below math card (P0)", () => {
    const payload = makeHappyPayload({
      math_line:
        "0.6 × 0.70 + 0.4 × 0.80 → score 8/10\nYour **Focused** effort setting lifts this to 9/10",
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    // Math card carries only the first (arithmetic) line.
    const mathCard = screen.getByTestId("receipt-math-line");
    expect(mathCard).toHaveTextContent(
      "0.6 × 0.70 + 0.4 × 0.80 → score 8/10",
    );
    // The effort line lives in a separate dedicated element.
    const effortLine = screen.getByTestId("receipt-effort-line");
    expect(effortLine).toBeInTheDocument();
    expect(effortLine).toHaveTextContent(/Focused/);
    expect(effortLine).toHaveTextContent(/lifts this to 9\/10/);
    // The arithmetic must NOT also appear in the effort line element.
    expect(effortLine.textContent ?? "").not.toContain("0.6 × 0.70");
    // **Focused** rendered as <strong>, not as raw asterisks.
    expect(effortLine.querySelector("strong")).not.toBeNull();
    expect(effortLine.textContent ?? "").not.toContain("**");
  });

  it("does NOT render the effort line for balanced effort (saboteur)", () => {
    const payload = makeHappyPayload({
      math_line: "0.6 × 0.87 + 0.4 × 0.92 → score 9/10",
    });
    render(<ExplainStatReceiptCard payload={payload} />);
    expect(screen.queryByTestId("receipt-effort-line")).toBeNull();
  });

  // -----------------------------------------------------------------
  // Accessibility attributes (P1)
  // -----------------------------------------------------------------

  it("test_accessibility_attributes — region role, aria-label, data-testids (P1)", () => {
    const payload = makeHappyPayload();
    render(<ExplainStatReceiptCard payload={payload} />);

    const region = screen.getByTestId("explain-stat-receipt");
    expect(region).toHaveAttribute("role", "region");
    expect(region).toHaveAttribute(
      "aria-label",
      expect.stringContaining("Earning Power"),
    );
    expect(region).toHaveAttribute(
      "aria-label",
      expect.stringContaining("explanation receipt"),
    );

    // Component rows both have data-testids.
    expect(screen.getByTestId("receipt-component-ern-60")).toBeInTheDocument();
    expect(screen.getByTestId("receipt-component-ern-40")).toBeInTheDocument();

    // Source pills each carry data-testid (slug-based) + aria-label + title.
    const src0 = screen.getByTestId("receipt-source-college-scorecard");
    expect(src0).toHaveAttribute("aria-label", expect.stringContaining("Source"));
    expect(src0).toHaveAttribute("title");
  });

  // -----------------------------------------------------------------
  // Responsive — narrow viewport (480px) does not overflow (P1)
  // -----------------------------------------------------------------

  it("test_renders_responsive_narrow — no overflow at 480px viewport (P1)", () => {
    // Resize the jsdom viewport. window.innerWidth/innerHeight are
    // writable in jsdom; emit a resize event so any matchMedia listeners
    // re-evaluate. The component itself uses Tailwind responsive classes
    // and percentage-based widths — assert it renders cleanly and
    // the root element's style does not impose a fixed width.
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 480,
    });
    window.dispatchEvent(new Event("resize"));

    const payload = makeHappyPayload();
    const { container } = render(<ExplainStatReceiptCard payload={payload} />);

    const region = screen.getByTestId("explain-stat-receipt");
    // The component sets max-width to 100% of its container; verify.
    const styleString = region.getAttribute("style") ?? "";
    expect(styleString).toContain("max-width: 100%");
    // Sanity: the render produced an actual DOM tree (not a React error
    // boundary fallback or null).
    expect(container.firstChild).not.toBeNull();
  });

  // -----------------------------------------------------------------
  // Both percentiles missing (degenerate state) — sanity render check
  // -----------------------------------------------------------------

  it("renders both-missing degenerate state without throwing", () => {
    const payload = makeHappyPayload();
    payload.components = payload.components.map((c) => ({
      ...c,
      value_pct: null,
      anchor_dollars: null,
      missing_reason: "missing data",
    }));
    payload.math_line = "0.6 × n/a + 0.4 × n/a → score 7/10";
    render(<ExplainStatReceiptCard payload={payload} />);

    // Both rows have a missing-reason note.
    expect(screen.getByTestId("receipt-missing-60")).toBeInTheDocument();
    expect(screen.getByTestId("receipt-missing-40")).toBeInTheDocument();
    // Math card shows two n/a placeholders.
    const mathCard = screen.getByTestId("receipt-math-line");
    expect(mathCard.textContent ?? "").toContain("n/a");
    expect((mathCard.textContent ?? "").match(/n\/a/g)?.length).toBe(2);
  });
});
