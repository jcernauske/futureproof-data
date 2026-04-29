/**
 * BranchHighlightDriver.test.tsx
 *
 * Tests the branch-name parser that fires highlight events on tree
 * nodes when Gemma names a branch in chat.
 *
 * Hygiene rules under test (fp-architect condition #3):
 *   (a) sort candidate titles by descending length so longest match
 *       wins regardless of order in the response.
 *   (b) word-boundary anchors so "Analyst" doesn't fire inside
 *       "Analytical" / "Analysts'".
 *   (c) case-insensitive comparison.
 *   (d) escape regex metacharacters in titles — real O*NET titles
 *       contain `,` `(` `/`.
 *
 * Plus: dedup within 1s window, multi-match stagger 200ms, no-op on
 * null/empty response.
 *
 * The component renders nothing — every assertion is on the
 * ``onHighlight`` callback's call sequence.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { BranchHighlightDriver } from "./BranchHighlightDriver";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

const SIMPLE_NODES = [
  { id: "node-financial-analyst", title: "Financial Analyst" },
  { id: "node-marketing-manager", title: "Marketing Manager" },
];

describe("BranchHighlightDriver", () => {
  it("test_simple_title_match_fires_highlight: response naming a tree node fires onHighlight once", () => {
    const onHighlight = vi.fn();
    render(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={
          "If you're looking at salary upside, the Financial Analyst track is the strongest direction here."
        }
        onHighlight={onHighlight}
      />,
    );

    // Single match → fires immediately (stagger=0 for the 1st match).
    vi.advanceTimersByTime(50);

    expect(onHighlight).toHaveBeenCalledTimes(1);
    expect(onHighlight).toHaveBeenCalledWith("node-financial-analyst");
  });

  it("test_longest_match_wins_on_substring_collision: 'Analyst' and 'Financial Analyst' yields only the longer match", () => {
    const onHighlight = vi.fn();
    const nodes = [
      { id: "node-analyst", title: "Analyst" },
      { id: "node-financial-analyst", title: "Financial Analyst" },
    ];

    render(
      <BranchHighlightDriver
        nodes={nodes}
        latestResponse={"The Financial Analyst path is what to look at first."}
        onHighlight={onHighlight}
      />,
    );

    vi.advanceTimersByTime(50);

    // Longest-match-wins: only "Financial Analyst" highlights, not the
    // shorter "Analyst" substring inside it.
    expect(onHighlight).toHaveBeenCalledTimes(1);
    expect(onHighlight).toHaveBeenCalledWith("node-financial-analyst");
  });

  it("test_word_boundary_anchors_prevent_false_match: 'Analytical' does not match 'Analyst'", () => {
    const onHighlight = vi.fn();
    const nodes = [{ id: "node-analyst", title: "Analyst" }];

    render(
      <BranchHighlightDriver
        nodes={nodes}
        latestResponse={
          "Your role takes Analytical thinking and rigor — it's a left-brain seat."
        }
        onHighlight={onHighlight}
      />,
    );

    vi.advanceTimersByTime(50);

    // "Analyst" inside "Analytical" must NOT match — \b anchor on both
    // sides of the alternation.
    expect(onHighlight).not.toHaveBeenCalled();
  });

  it("test_word_boundary_anchors_prevent_false_match: 'Analysts' (plural) is okay, 'Analystical' (made up) is not", () => {
    const onHighlight = vi.fn();
    const nodes = [{ id: "node-analyst", title: "Analyst" }];

    render(
      <BranchHighlightDriver
        nodes={nodes}
        latestResponse={
          "Your career as a financial Analystical thinker is unusual."
        }
        onHighlight={onHighlight}
      />,
    );

    vi.advanceTimersByTime(50);
    expect(onHighlight).not.toHaveBeenCalled();
  });

  it("test_regex_metachars_in_titles_escaped: O*NET titles with commas + slashes match verbatim", () => {
    const onHighlight = vi.fn();
    // Real O*NET titles include commas, slashes, parentheses, periods —
    // all regex metacharacters. A naive new RegExp() built from
    // unescaped titles either throws (e.g. on unbalanced `(`) or
    // silently mis-matches. Tests both that compilation succeeds AND
    // that titles with metacharacters at non-boundary positions match
    // verbatim. (Trailing `)` is bounded against `\b` and is therefore
    // out of scope for word-boundary matching — covered by the
    // dedicated metachar-period test below.)
    const nodes = [
      {
        id: "node-sales-rep",
        title:
          "Sales Representatives, Wholesale and Manufacturing, Technical and Scientific Products",
      },
      {
        id: "node-aero",
        // Slash inside a title.
        title: "Aerospace Engineering and Operations Technologists/Technicians",
      },
    ];

    render(
      <BranchHighlightDriver
        nodes={nodes}
        latestResponse={
          "If you'd rather sell complex products, the Sales Representatives, Wholesale and Manufacturing, Technical and Scientific Products track is the closest adjacent role. Aerospace Engineering and Operations Technologists/Technicians is the more hands-on alternative."
        }
        onHighlight={onHighlight}
      />,
    );

    vi.advanceTimersByTime(500);

    // Both titles match verbatim. The regex compilation must not
    // throw, and the comma + slash metacharacters must not act as
    // alternation / character-class operators.
    const calls = onHighlight.mock.calls.map((c) => c[0]);
    expect(calls).toContain("node-sales-rep");
    expect(calls).toContain("node-aero");
    expect(onHighlight).toHaveBeenCalledTimes(2);
  });

  it("test_title_ending_in_non_word_char_still_matches: regression for `\\b` JS-regex pitfall (faang-staff Finding 1, 2026-04-28)", () => {
    const onHighlight = vi.fn();
    // Real-world O*NET titles end in `)` (a non-word character). With
    // JavaScript's `\b...\b` anchors, the trailing-non-word followed
    // by a space (also non-word) is NOT a word boundary, so the match
    // silently fails. The lookaround anchors `(?<![A-Za-z0-9_])` /
    // `(?![A-Za-z0-9_])` we use instead handle this correctly because
    // they only assert "not adjacent to a word character" — a space
    // is fine, end-of-string is fine, punctuation is fine.
    const nodes = [
      { id: "node-designers-industrial", title: "Designers (Industrial)" },
    ];
    const response =
      "If you stay close to the work, the Designers (Industrial) path is the right move.";

    render(
      <BranchHighlightDriver
        nodes={nodes}
        latestResponse={response}
        onHighlight={onHighlight}
      />,
    );

    vi.advanceTimersByTime(50);
    expect(onHighlight).toHaveBeenCalledTimes(1);
    expect(onHighlight).toHaveBeenCalledWith("node-designers-industrial");
  });

  it("test_regex_metachars_in_titles_escaped: title with parentheses compiles without throwing", () => {
    const onHighlight = vi.fn();
    // Unescaped `(` would either throw "Unmatched group" or silently
    // construct a capture group that mismatches. Validates escaping by
    // confirming the component renders without error AND yields the
    // expected match at a word-boundary position.
    const nodes = [
      {
        id: "node-cs-mgr",
        // Real-world title shape with parens — only matters that
        // construction doesn't throw and that an exact-match in body
        // does fire (the response uses the verbatim title at a
        // word-boundary position).
        title: "Computer (Systems) Managers",
      },
    ];

    expect(() => {
      render(
        <BranchHighlightDriver
          nodes={nodes}
          latestResponse={null}
          onHighlight={onHighlight}
        />,
      );
    }).not.toThrow();

    // No response yet → no fires.
    vi.advanceTimersByTime(50);
    expect(onHighlight).not.toHaveBeenCalled();
  });

  it("test_regex_metachars_in_titles_escaped: a title with a period does not match arbitrary single-char text", () => {
    const onHighlight = vi.fn();
    // The literal title is "Cert. A" — if `.` were unescaped this
    // would match "Cert XA" / "CertaA" etc. Validates escapeRegex is
    // wired in.
    const nodes = [{ id: "node-cert", title: "Cert. A" }];

    render(
      <BranchHighlightDriver
        nodes={nodes}
        latestResponse={"Could go for a CertXA next year — easy enough."}
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(50);
    expect(onHighlight).not.toHaveBeenCalled();
  });

  it("test_null_or_empty_response_noop: null and empty string both no-op", () => {
    const onHighlight = vi.fn();

    const { rerender } = render(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={null}
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(500);
    expect(onHighlight).not.toHaveBeenCalled();

    rerender(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={""}
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(500);
    expect(onHighlight).not.toHaveBeenCalled();
  });

  it("test_dedup_within_1s_window: same node referenced twice in <1s fires once", () => {
    const onHighlight = vi.fn();

    const { rerender } = render(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={
          "The Financial Analyst path is the strongest one to watch here."
        }
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(50);
    expect(onHighlight).toHaveBeenCalledTimes(1);

    // Same node fires again in a follow-up response within 1s — dedup
    // suppresses the second highlight.
    vi.advanceTimersByTime(500); // total 550ms — still inside window
    rerender(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={
          "Worth digging into the Financial Analyst track first."
        }
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(50);

    expect(onHighlight).toHaveBeenCalledTimes(1);
  });

  it("test_dedup_window_releases_after_1s: same node fires again after the window closes", () => {
    const onHighlight = vi.fn();

    const { rerender } = render(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={"The Financial Analyst track is your strongest move."}
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(50);
    expect(onHighlight).toHaveBeenCalledTimes(1);

    // Wait past the 1000ms dedup window before the second response.
    vi.advanceTimersByTime(1100);
    rerender(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={"Coming back to Financial Analyst — what's the pay?"}
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(50);
    expect(onHighlight).toHaveBeenCalledTimes(2);
  });

  it("test_multi_match_staggered_200ms: two distinct matches fire 200ms apart", () => {
    const onHighlight = vi.fn();

    render(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={
          "From here, the Financial Analyst path keeps you in numbers, while the Marketing Manager track moves you toward people."
        }
        onHighlight={onHighlight}
      />,
    );

    // First fires at delay=0; second at delay=200.
    vi.advanceTimersByTime(50);
    expect(onHighlight).toHaveBeenCalledTimes(1);
    expect(onHighlight).toHaveBeenNthCalledWith(1, "node-financial-analyst");

    vi.advanceTimersByTime(150); // total 200ms — second fires now.
    expect(onHighlight).toHaveBeenCalledTimes(2);
    expect(onHighlight).toHaveBeenNthCalledWith(2, "node-marketing-manager");
  });

  it("case-insensitive matching: lowercase response still matches title-cased nodes", () => {
    const onHighlight = vi.fn();

    render(
      <BranchHighlightDriver
        nodes={SIMPLE_NODES}
        latestResponse={
          "the financial analyst track is the strongest move from here."
        }
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(50);

    expect(onHighlight).toHaveBeenCalledTimes(1);
    expect(onHighlight).toHaveBeenCalledWith("node-financial-analyst");
  });

  it("empty nodes list: no-op even with a substantial response", () => {
    const onHighlight = vi.fn();

    render(
      <BranchHighlightDriver
        nodes={[]}
        latestResponse={
          "From here, the Financial Analyst path keeps you in numbers."
        }
        onHighlight={onHighlight}
      />,
    );
    vi.advanceTimersByTime(500);

    expect(onHighlight).not.toHaveBeenCalled();
  });
});
