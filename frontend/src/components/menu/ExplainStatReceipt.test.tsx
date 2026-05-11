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

  // -------------------------------------------------------------------------
  // Score-null state — server can't honestly produce a score; the card
  // renders with an open-ring callout instead of a number.
  // Spec: docs/specs/bugfix-explain-stat-trigger-null-score-guard.md
  // -------------------------------------------------------------------------

  it("renders an open-ring score callout when score is null", () => {
    const payload = makeHappyPayload({
      score: null,
      math_line: "0.6 × n/a + 0.4 × 0.92 → no score available",
      components: [
        {
          weight_pct: 60,
          label: "your school's program rank",
          explainer:
            "How Millikin University's Chemistry graduates' median earnings would rank against peers in the same field of study — if this number were reported.",
          value_pct: null,
          anchor_text: "Millikin University Chemistry grads",
          anchor_dollars: null,
          missing_reason:
            "College Scorecard doesn't report median earnings for Millikin University's Chemistry graduates yet — usually because the cohort is small enough that publishing earnings would identify individual students.",
        },
        {
          weight_pct: 40,
          label: "this career's pay rank",
          explainer:
            "How Food Science Technicians' median wage ranks against all U.S. occupations.",
          value_pct: 45,
          anchor_text: "Food Science Technicians",
          anchor_dollars: 50_300,
          missing_reason: null,
        },
      ],
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const scoreEl = screen.getByTestId("receipt-score");
    expect(scoreEl.getAttribute("data-score-missing")).toBe("true");
    // No fabricated number — only the open ring + em-dash + score_max.
    expect(scoreEl.textContent ?? "").not.toMatch(/\d{1,2}\/10/);
    expect(scoreEl.textContent ?? "").toContain("/10");
    expect(scoreEl.getAttribute("aria-label") ?? "").toMatch(
      /not available for this combination yet/i,
    );

    // The 60% bullet renders the missing_reason; the 40% bullet shows
    // its values normally.
    expect(screen.getByTestId("receipt-missing-60")).toBeInTheDocument();
    expect(screen.queryByTestId("receipt-missing-40")).toBeNull();

    // Math line names the missing input + the no-score outcome.
    const mathCard = screen.getByTestId("receipt-math-line");
    expect(mathCard.textContent ?? "").toContain("n/a");
    expect(mathCard.textContent ?? "").toContain("no score available");
  });
});

// ---------------------------------------------------------------------------
// ROI / RES / GRW receipt rendering (feature-explain-stat-receipt-roi-res-grw)
// ---------------------------------------------------------------------------

function makeROIPayload(): ExplainStatReceipt {
  return {
    kind: "receipt",
    stat_code: "ROI",
    stat_name: "Return on Investment",
    score: 4,
    score_max: 10,
    one_liner: "ROI divides your school's full published cost by your starting salary.",
    components: [
      {
        weight_pct: 100,
        label: "your debt-to-earnings ratio",
        explainer: "Indiana University CS costs $112,400 over 4 years. Grads earn $78,400.",
        value_pct: null,
        anchor_text: "Indiana University Computer Science 4-year published cost",
        anchor_dollars: 112400,
        missing_reason: null,
      },
    ],
    math_line: "$112,400 / $78,400 = 1.43 → ROI score 4/10",
    sources: [
      { label: "Published cost", name: "College Scorecard (U.S. Department of Education)" },
      { label: "Graduate earnings", name: "College Scorecard (U.S. Department of Education)" },
    ],
    why_mix_paragraph: "Same degree, different costs, different payoff timelines.",
  };
}

function makeRESPayload(): ExplainStatReceipt {
  return {
    kind: "receipt",
    stat_code: "RES",
    stat_name: "AI Resilience",
    score: 8,
    score_max: 10,
    one_liner: "AI Resilience blends automation exposure with human-essential signals.",
    components: [
      {
        weight_pct: 50,
        label: "AI exposure",
        explainer: "Software Developers score 8/10 on AI exposure.",
        value_pct: 80,
        anchor_text: "AI-exposure rating: 8/10",
        anchor_dollars: null,
        missing_reason: null,
        evidence_bullets: [
          "Drafting code from a clear specification",
          "Finding patterns in logs and test failures",
        ],
      },
      {
        weight_pct: 50,
        label: "human-essential skills",
        explainer: "Software Developers score 7/10 on human-essential skills.",
        value_pct: 70,
        anchor_text: "Human-essential rating: 7/10",
        anchor_dollars: null,
        missing_reason: null,
        evidence_bullets: [
          "Choosing the right product tradeoff",
          "Coordinating with teammates and users",
        ],
      },
    ],
    math_line: "0.5 × 8 + 0.5 × 7 → score 8/10",
    sources: [
      { label: "AI exposure composite", name: "Karpathy AI Exposure Index + Anthropic Economic Index" },
      { label: "Human-essential skills", name: "O*NET (Occupational Information Network)" },
    ],
    why_mix_paragraph: "Two signals blended 50/50 to hedge against either being too generous.",
  };
}

function makeGRWPayload(): ExplainStatReceipt {
  return {
    kind: "receipt",
    stat_code: "GRW",
    stat_name: "Growth Outlook",
    score: 8,
    score_max: 10,
    one_liner: "Growth Outlook reads the BLS 10-year employment projection.",
    components: [
      {
        weight_pct: 100,
        label: "this career's projected employment change",
        explainer: "BLS expects Software Developer jobs to grow 15% over the next decade.",
        value_pct: null,
        anchor_text: "+15.2% projected change over 10 years",
        anchor_dollars: null,
        missing_reason: null,
      },
    ],
    math_line: "+15.2% employment change → GRW score 8/10",
    sources: [
      { label: "Employment projections", name: "Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)" },
    ],
    why_mix_paragraph: "We use a projection because you care about the world you'll enter.",
  };
}

describe("ExplainStatReceiptCard — ROI (value_pct=null, no missing_reason)", () => {
  it("test_renders_roi_receipt_no_percentile_callout_when_value_pct_null_and_no_missing_reason", () => {
    render(<ExplainStatReceiptCard payload={makeROIPayload()} />);

    // Should NOT render the open-ring glyph (◦ —)
    const article = screen.getByTestId("explain-stat-receipt");
    expect(article.textContent).not.toContain("◦ —");

    // Should render the anchor_dollars instead
    expect(article.textContent).toContain("$112,400");

    // Score callout uses the stat color
    expect(screen.getByText("Return on Investment")).toBeInTheDocument();
    expect(screen.getByText(/^4$/)).toBeInTheDocument();
  });

  it("test_renders_roi_missing_reason_still_shows_glyph", () => {
    const payload = makeROIPayload();
    payload.components[0]!.missing_reason = "no published cost data for this institution yet";
    payload.components[0]!.anchor_dollars = null;
    render(<ExplainStatReceiptCard payload={payload} />);

    // When missing_reason IS set, the open-ring glyph DOES render
    const article = screen.getByTestId("explain-stat-receipt");
    expect(article.textContent).toContain("◦ —");
    expect(screen.getByTestId("receipt-missing-100")).toBeInTheDocument();
  });
});

describe("ExplainStatReceiptCard — GRW (value_pct=null, anchor_text only)", () => {
  it("test_renders_grw_receipt_no_percentile_callout", () => {
    render(<ExplainStatReceiptCard payload={makeGRWPayload()} />);

    const article = screen.getByTestId("explain-stat-receipt");
    // No open-ring glyph
    expect(article.textContent).not.toContain("◦ —");
    // anchor_text is rendered
    expect(article.textContent).toContain("+15.2% projected change over 10 years");
    // Score renders
    expect(screen.getByText(/^8$/)).toBeInTheDocument();
  });
});

describe("ExplainStatReceiptCard — RES (2 components)", () => {
  it("test_renders_res_receipt_two_components", () => {
    render(<ExplainStatReceiptCard payload={makeRESPayload()} />);

    // Both component labels render
    expect(screen.getByText("AI exposure")).toBeInTheDocument();
    expect(screen.getByText("human-essential skills")).toBeInTheDocument();

    // Both percentile callouts render (value_pct populated)
    expect(screen.getByText(/80th percentile/)).toBeInTheDocument();
    expect(screen.getByText(/70th percentile/)).toBeInTheDocument();
    expect(screen.getByText("Drafting code from a clear specification")).toBeInTheDocument();
    expect(screen.getByText("Choosing the right product tradeoff")).toBeInTheDocument();

    // Two component rows in the list
    const components = screen.getByTestId("receipt-components");
    expect(components.children).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// AURA receipt + score_provenance rendering
// Spec: docs/specs/feature-explain-stat-receipt-aura.md
// ---------------------------------------------------------------------------

function makeAURAPayload(
  overrides: Partial<ExplainStatReceipt> = {},
): ExplainStatReceipt {
  return {
    kind: "receipt",
    stat_code: "AURA",
    stat_name: "Brand Gravity",
    score: 8,
    score_max: 10,
    one_liner:
      "Brand Gravity measures how much weight your school's name carries for networking, alumni access, and recruiter shortlists.",
    components: [
      {
        weight_pct: 100,
        label: "your school's brand gravity",
        explainer:
          "Indiana University-Bloomington's per-student endowment, marketing reach, and athletic spending combine into one composite signal.",
        value_pct: null,
        anchor_text:
          "IU Bloomington's endowment, marketing, and athletics per student",
        anchor_dollars: null,
        missing_reason: null,
        evidence_bullets: [
          "Endowment: $85,000/student — how much savings the school holds per student",
          "Marketing: 0.045 ratio — how much the school spends getting its name out there, per student",
          "Athletics: $3,200/student — how much the school puts into sports programs per student",
        ],
      },
    ],
    math_line: "composite 0.72 → AURA score 8/10",
    sources: [
      {
        label: "Endowment + marketing",
        name: "Integrated Postsecondary Education Data System (IPEDS), U.S. Department of Education",
      },
      {
        label: "Athletics",
        name: "Equity in Athletics Disclosure Act (EADA), U.S. Department of Education",
      },
    ],
    why_mix_paragraph:
      "Most college tools pretend prestige doesn't matter but it absolutely does for networking, alumni access, and recruiter shortlists.",
    scoring_scale: [
      { label: "Elite brand", range: "9 – 10", score: "9 – 10" },
      { label: "Strong brand", range: "7 – 8", score: "7 – 8" },
      { label: "Solid brand", range: "5 – 6", score: "5 – 6" },
      { label: "Modest brand", range: "3 – 4", score: "3 – 4" },
      { label: "Low profile", range: "1 – 2", score: "1 – 2" },
    ],
    score_provenance: "endowment + marketing + athletics",
    ...overrides,
  };
}

describe("ExplainStatReceiptCard — AURA + score_provenance", () => {
  it("test_renders_score_provenance_byline_when_present", () => {
    const payload = makeAURAPayload({
      score_provenance: "endowment + marketing + athletics",
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const byline = screen.getByTestId("receipt-score-provenance");
    expect(byline).toBeInTheDocument();
    expect(byline.textContent).toContain(
      "based on endowment + marketing + athletics",
    );
    // Verify it's a <p> tag
    expect(byline.tagName).toBe("P");
  });

  it("test_suppresses_score_provenance_byline_when_null", () => {
    // Use an ERN fixture which has no score_provenance
    const payload = makeHappyPayload();
    // Explicitly ensure score_provenance is absent
    expect(payload.score_provenance).toBeUndefined();
    render(<ExplainStatReceiptCard payload={payload} />);

    // No receipt-score-provenance element should exist
    expect(screen.queryByTestId("receipt-score-provenance")).toBeNull();
  });

  it("test_renders_aura_receipt_full_shape", () => {
    const payload = makeAURAPayload();
    render(<ExplainStatReceiptCard payload={payload} />);

    // Score provenance byline renders
    const byline = screen.getByTestId("receipt-score-provenance");
    expect(byline).toBeInTheDocument();
    expect(byline.textContent).toContain("based on");

    // Single component renders
    expect(
      screen.getByText("your school's brand gravity"),
    ).toBeInTheDocument();
    const components = screen.getByTestId("receipt-components");
    expect(components.children).toHaveLength(1);

    // Math line renders
    const mathCard = screen.getByTestId("receipt-math-line");
    expect(mathCard.textContent).toContain("composite 0.72");
    expect(mathCard.textContent).toContain("AURA score 8/10");

    // Stat name renders
    expect(screen.getByText("Brand Gravity")).toBeInTheDocument();
    // Score renders
    expect(screen.getByText(/^8$/)).toBeInTheDocument();

    // Evidence bullets from the component render
    expect(
      screen.getByText(/Endowment: \$85,000\/student/),
    ).toBeInTheDocument();

    // Sources render — 2 source pills exist. IPEDS and EADA both fall
    // through to the slugified fallback path (no hardcoded short form).
    // The title attribute carries the full name so we check that.
    const allSources = screen.getByTestId("explain-stat-receipt")
      .querySelectorAll('[data-testid^="receipt-source-"]');
    expect(allSources.length).toBe(2);
  });

  it("suppresses score_provenance byline when score_provenance is undefined", () => {
    // Explicitly test the undefined case (Zod marks it optional)
    const payload = makeAURAPayload();
    delete (payload as Record<string, unknown>).score_provenance;
    render(<ExplainStatReceiptCard payload={payload} />);

    expect(screen.queryByTestId("receipt-score-provenance")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Source pill link vs button rendering (pipeline lineage feature)
// Spec: source pills render as <a> when url present, <button> when absent
// ---------------------------------------------------------------------------

describe("ExplainStatReceiptCard — source pill link/button rendering", () => {
  it("test_source_pill_renders_as_link_when_url_present", () => {
    const payload = makeHappyPayload({
      sources: [
        {
          label: "Graduate earnings",
          name: "College Scorecard (U.S. Department of Education)",
          url: "https://collegescorecard.ed.gov/",
        },
        {
          label: "Occupation wages",
          name: "Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)",
          url: "https://www.bls.gov/ooh/",
        },
      ],
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const scorecardPill = screen.getByTestId("receipt-source-college-scorecard");
    expect(scorecardPill.tagName).toBe("A");
    expect(scorecardPill).toHaveAttribute("href", "https://collegescorecard.ed.gov/");
    expect(scorecardPill).toHaveAttribute("target", "_blank");
    expect(scorecardPill).toHaveAttribute("rel", expect.stringContaining("noopener"));

    const blsPill = screen.getByTestId("receipt-source-bls-ooh");
    expect(blsPill.tagName).toBe("A");
    expect(blsPill).toHaveAttribute("href", "https://www.bls.gov/ooh/");
    expect(blsPill).toHaveAttribute("target", "_blank");
  });

  it("test_source_pill_renders_as_button_when_url_absent", () => {
    // Sources without url should render as <button> elements
    const payload = makeHappyPayload({
      sources: [
        {
          label: "Graduate earnings",
          name: "College Scorecard (U.S. Department of Education)",
          // no url field
        },
        {
          label: "Occupation wages",
          name: "Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)",
          // no url field
        },
      ],
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const scorecardPill = screen.getByTestId("receipt-source-college-scorecard");
    expect(scorecardPill.tagName).toBe("BUTTON");
    expect(scorecardPill).not.toHaveAttribute("href");
    expect(scorecardPill).not.toHaveAttribute("target");

    const blsPill = screen.getByTestId("receipt-source-bls-ooh");
    expect(blsPill.tagName).toBe("BUTTON");
  });

  it("test_source_pill_mixed_urls — link and button coexist", () => {
    // One source with url, one without — verifies mixed rendering
    const payload = makeHappyPayload({
      sources: [
        {
          label: "Graduate earnings",
          name: "College Scorecard (U.S. Department of Education)",
          url: "https://collegescorecard.ed.gov/",
        },
        {
          label: "Occupation wages",
          name: "Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)",
          // no url
        },
      ],
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const linkPill = screen.getByTestId("receipt-source-college-scorecard");
    expect(linkPill.tagName).toBe("A");
    expect(linkPill).toHaveAttribute("href", "https://collegescorecard.ed.gov/");

    const buttonPill = screen.getByTestId("receipt-source-bls-ooh");
    expect(buttonPill.tagName).toBe("BUTTON");
  });

  it("test_source_pill_link_shows_external_arrow — visible ↗ glyph", () => {
    const payload = makeHappyPayload({
      sources: [
        {
          label: "Graduate earnings",
          name: "College Scorecard (U.S. Department of Education)",
          url: "https://collegescorecard.ed.gov/",
        },
      ],
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const pill = screen.getByTestId("receipt-source-college-scorecard");
    // The external-link arrow glyph renders when url is present
    expect(pill.textContent).toContain("↗"); // ↗
  });

  it("test_source_pill_button_no_arrow — no ↗ glyph without url", () => {
    const payload = makeHappyPayload({
      sources: [
        {
          label: "Graduate earnings",
          name: "College Scorecard (U.S. Department of Education)",
          // no url
        },
      ],
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const pill = screen.getByTestId("receipt-source-college-scorecard");
    expect(pill.textContent).not.toContain("↗");
  });
});

// ---------------------------------------------------------------------------
// Data Lineage section rendering (collapsible <details> section)
// ---------------------------------------------------------------------------

describe("ExplainStatReceiptCard — lineage section", () => {
  it("test_lineage_section_hidden_when_null", () => {
    // Default makeHappyPayload has no lineage — section must not render
    const payload = makeHappyPayload();
    expect(payload.lineage).toBeUndefined();
    render(<ExplainStatReceiptCard payload={payload} />);

    expect(screen.queryByTestId("receipt-lineage")).toBeNull();
  });

  it("test_lineage_section_hidden_when_explicitly_null", () => {
    const payload = makeHappyPayload({ lineage: null });
    render(<ExplainStatReceiptCard payload={payload} />);

    expect(screen.queryByTestId("receipt-lineage")).toBeNull();
  });

  it("test_lineage_section_hidden_when_empty_array", () => {
    const payload = makeHappyPayload({ lineage: [] });
    render(<ExplainStatReceiptCard payload={payload} />);

    expect(screen.queryByTestId("receipt-lineage")).toBeNull();
  });

  it("test_lineage_section_renders_when_present", () => {
    const payload = makeHappyPayload({
      lineage: [
        {
          component_label: "your school's program rank",
          steps: [
            {
              layer: "gold" as const,
              table_or_file: "consumable.career_outcomes",
              column: "cip_family_earnings_rank",
            },
            {
              layer: "silver" as const,
              table_or_file: "base.college_scorecard",
              column: "earnings_1yr_median",
            },
            {
              layer: "bronze" as const,
              table_or_file: "bronze.college_scorecard",
            },
            {
              layer: "upstream" as const,
              table_or_file: "College Scorecard Field-of-Study CSV",
              url: "https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Field-of-Study.csv",
            },
          ],
        },
        {
          component_label: "this career's pay rank",
          steps: [
            {
              layer: "gold" as const,
              table_or_file: "consumable.occupation_profiles",
              column: "wage_percentile_overall",
            },
            {
              layer: "upstream" as const,
              table_or_file: "BLS Employment Projections",
              url: "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm",
            },
          ],
        },
      ],
    });
    render(<ExplainStatReceiptCard payload={payload} />);

    const lineageEl = screen.getByTestId("receipt-lineage");
    expect(lineageEl).toBeInTheDocument();
    expect(lineageEl.tagName).toBe("DETAILS");

    // Summary text says "Data Lineage"
    const summary = lineageEl.querySelector("summary");
    expect(summary).not.toBeNull();
    expect(summary!.textContent).toContain("Data Lineage");

    // Both component labels render as headings inside the lineage section
    // (they also appear in the components section, so scope to lineage)
    const lineageLabels = lineageEl.querySelectorAll("h3");
    const lineageLabelTexts = Array.from(lineageLabels).map(
      (h) => h.textContent,
    );
    expect(lineageLabelTexts).toContain("your school's program rank");
    expect(lineageLabelTexts).toContain("this career's pay rank");

    // Layer labels render (GOLD, SILVER, BRONZE, UPSTREAM)
    const lineageText = lineageEl.textContent ?? "";
    expect(lineageText).toContain("gold");
    expect(lineageText).toContain("silver");
    expect(lineageText).toContain("bronze");
    expect(lineageText).toContain("upstream");

    // Table/file names render
    expect(lineageText).toContain("consumable.career_outcomes");
    expect(lineageText).toContain("base.college_scorecard");

    // Column names render with dot prefix
    expect(lineageText).toContain(".cip_family_earnings_rank");

    // Upstream step with URL has a link element
    const upstreamLinks = lineageEl.querySelectorAll('a[target="_blank"]');
    expect(upstreamLinks.length).toBeGreaterThan(0);
  });
});
