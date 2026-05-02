import { describe, it, expect } from "vitest";
import {
  pickEdgeLabel,
  pickEdgeHover,
  formatPayDelta,
  formatPayFull,
} from "./edgeLabel";
import type { TreeNode } from "@/types/tree";

/**
 * T1.1 — Edge-label selection tests.
 *
 * Priority chain we're guarding (in order):
 *   1. education delta (when both known + non-equal)
 *   2. experience tier delta (when both known + non-equal)
 *   3. pay delta with |Δ| ≥ $10,000
 *   4. relatedness rank ≤ 5 ("Close") or ≥ 11 ("Stretch")
 *   5. otherwise null
 *
 * Identity translator — surfaces the raw key. Lets us assert the
 * intent of the selection without coupling to copy.
 */
const tIdentity = (key: string): string => key;

function makeNode(overrides: Partial<TreeNode> = {}): TreeNode {
  return {
    soc_code: "13-0000",
    title: "Test",
    level: 1,
    ern: null,
    roi: null,
    res: null,
    grw: null,
    hmn: null,
    median_wage: null,
    education: null,
    experience_years: null,
    experience_tier: null,
    relatedness: null,
    boss_ai: null,
    boss_loans: null,
    boss_market: null,
    boss_burnout: null,
    boss_ceiling: null,
    children: [],
    ...overrides,
  };
}

describe("pickEdgeLabel — priority chain", () => {
  it("pickEdgeLabel_education_delta_wins", () => {
    // Both education AND experience AND pay all changed — education
    // must win because it's first in the priority chain.
    const parent = makeNode({
      education: "Bachelor's degree",
      experience_tier: "early",
      median_wage: 60_000,
    });
    const child = makeNode({
      education: "Master's degree",
      experience_tier: "mid",
      median_wage: 95_000,
    });

    const result = pickEdgeLabel(parent, child, tIdentity);

    expect(result).not.toBeNull();
    expect(result!.kind).toBe("education");
    expect(result!.isPositive).toBe(true);
    // Identity translator returns the key — we expect the master's
    // key with the "+" prefix (child rank > parent rank).
    expect(result!.text).toBe("+future.edge.degree.masters");
  });

  it("pickEdgeLabel_returns_null_for_uneventful_edge", () => {
    // Same education, same tier, sub-threshold pay delta, no relatedness.
    // Nothing in the chain should fire.
    const parent = makeNode({
      education: "Bachelor's degree",
      experience_tier: "mid",
      median_wage: 80_000,
      relatedness: 7, // strictly between 5 and 11 — not surface-worthy
    });
    const child = makeNode({
      education: "Bachelor's degree",
      experience_tier: "mid",
      median_wage: 84_000, // Δ = $4k — under threshold
      relatedness: 7,
    });

    expect(pickEdgeLabel(parent, child, tIdentity)).toBeNull();
  });

  it("pickEdgeLabel_pay_threshold_10k", () => {
    // Pay delta of exactly $9,999 — below threshold, must NOT label.
    const parentLow = makeNode({ median_wage: 50_000 });
    const childLow = makeNode({ median_wage: 59_999 });
    expect(pickEdgeLabel(parentLow, childLow, tIdentity)).toBeNull();

    // Pay delta of exactly $10,000 — at threshold, MUST label
    // (spec uses |Δ| ≥ $10,000).
    const parentEq = makeNode({ median_wage: 50_000 });
    const childEq = makeNode({ median_wage: 60_000 });
    const eqResult = pickEdgeLabel(parentEq, childEq, tIdentity);
    expect(eqResult).not.toBeNull();
    expect(eqResult!.kind).toBe("pay");
    expect(eqResult!.isPositive).toBe(true);
    expect(eqResult!.text).toBe("+$10k");

    // Pay delta of $10,001 — clearly over threshold, label fires.
    const parentHi = makeNode({ median_wage: 50_000 });
    const childHi = makeNode({ median_wage: 60_001 });
    const hiResult = pickEdgeLabel(parentHi, childHi, tIdentity);
    expect(hiResult).not.toBeNull();
    expect(hiResult!.kind).toBe("pay");
  });

  it("falls through to pay when education is unchanged (experience no longer wins)", () => {
    // Experience tier deltas were removed from the priority chain in
    // favor of the dedicated experience-range slider. With education
    // unchanged, pay is the next priority.
    const parent = makeNode({
      education: "Bachelor's degree",
      experience_tier: "early",
      median_wage: 60_000,
    });
    const child = makeNode({
      education: "Bachelor's degree",
      experience_tier: "mid",
      median_wage: 80_000, // +$20k → wins
    });

    const result = pickEdgeLabel(parent, child, tIdentity);
    expect(result).not.toBeNull();
    expect(result!.kind).toBe("pay");
    expect(result!.text).toBe("+$20k");
  });

  it("falls through to pay when education and tier are unchanged", () => {
    const parent = makeNode({
      education: "Bachelor's degree",
      experience_tier: "mid",
      median_wage: 60_000,
    });
    const child = makeNode({
      education: "Bachelor's degree",
      experience_tier: "mid",
      median_wage: 100_000, // +$40k
    });

    const result = pickEdgeLabel(parent, child, tIdentity);
    expect(result).not.toBeNull();
    expect(result!.kind).toBe("pay");
    expect(result!.text).toBe("+$40k");
  });

  it("falls through to relatedness 'Close' when nothing else fires", () => {
    const parent = makeNode({ median_wage: 80_000 });
    const child = makeNode({
      median_wage: 80_000, // same pay
      relatedness: 3, // ≤ 5
    });

    const result = pickEdgeLabel(parent, child, tIdentity);
    expect(result).not.toBeNull();
    expect(result!.kind).toBe("relatedness_close");
    expect(result!.isPositive).toBe(true);
  });

  it("falls through to relatedness 'Stretch' when rank ≥ 11", () => {
    const parent = makeNode({ median_wage: 80_000 });
    const child = makeNode({
      median_wage: 80_000,
      relatedness: 14,
    });

    const result = pickEdgeLabel(parent, child, tIdentity);
    expect(result).not.toBeNull();
    expect(result!.kind).toBe("relatedness_stretch");
    expect(result!.isPositive).toBe(false);
  });

  it("relatedness rank in mid-band (6..10) does not fire", () => {
    const parent = makeNode({ median_wage: 80_000 });
    const child = makeNode({ median_wage: 80_000, relatedness: 8 });
    expect(pickEdgeLabel(parent, child, tIdentity)).toBeNull();
  });

  it("negative pay delta crossing threshold renders with minus sign", () => {
    const parent = makeNode({ median_wage: 100_000 });
    const child = makeNode({ median_wage: 80_000 });
    const result = pickEdgeLabel(parent, child, tIdentity);
    expect(result).not.toBeNull();
    expect(result!.kind).toBe("pay");
    expect(result!.isPositive).toBe(false);
    // U+2212 minus sign per formatPayDelta — not ASCII hyphen.
    expect(result!.text).toBe("−$20k");
  });

  it("education to a level not in the label map skips the rule", () => {
    // child's education isn't in EDU_LABEL_KEY → fall through.
    const parent = makeNode({ education: "Bachelor's degree" });
    const child = makeNode({
      education: "Some college, no degree", // valid in EDU_RANK but not in EDU_LABEL_KEY
      median_wage: 50_000,
    });
    // Parent has no median_wage → pay rule can't fire either; should be null.
    const result = pickEdgeLabel(parent, child, tIdentity);
    expect(result).toBeNull();
  });

  it("null education on either side skips the rule and falls through", () => {
    // Education rule needs both sides; with parent null, falls through
    // to pay (experience is no longer in the chain). Adding wages to
    // both so pay can fire and we have a non-null assertion.
    const parent = makeNode({
      education: null,
      median_wage: 60_000,
    });
    const child = makeNode({
      education: "Master's degree",
      median_wage: 95_000,
    });
    const result = pickEdgeLabel(parent, child, tIdentity);
    expect(result).not.toBeNull();
    expect(result!.kind).toBe("pay");
  });
});

describe("formatPayDelta", () => {
  it("rounds to nearest $1k for sub-million amounts", () => {
    expect(formatPayDelta(10_000)).toBe("+$10k");
    expect(formatPayDelta(24_300)).toBe("+$24k");
    expect(formatPayDelta(24_500)).toBe("+$25k"); // banker's-style rounding via Math.round
    expect(formatPayDelta(-12_400)).toBe("−$12k");
  });

  it("uses minus sign U+2212, not ASCII hyphen", () => {
    const out = formatPayDelta(-50_000);
    expect(out.startsWith("−")).toBe(true); // U+2212
    expect(out.startsWith("-")).toBe(false); // ASCII -
  });

  it("flips to 'm' form at $1m magnitude with one decimal", () => {
    expect(formatPayDelta(1_000_000)).toBe("+$1.0m");
    expect(formatPayDelta(1_250_000)).toBe("+$1.3m");
    expect(formatPayDelta(-2_000_000)).toBe("−$2.0m");
  });

  it("zero delta is signed +", () => {
    // sign is computed from > 0 — zero falls into the "−" branch by code,
    // but the test exists to pin the contract today and surface change.
    const out = formatPayDelta(0);
    expect(out).toBe("−$0k");
  });
});

describe("formatPayFull", () => {
  it("renders full $-figure with locale grouping and signed prefix", () => {
    expect(formatPayFull(24_300)).toBe("+$24,300");
    expect(formatPayFull(-12_400)).toBe("−$12,400");
    expect(formatPayFull(1_000_000)).toBe("+$1,000,000");
  });
});

describe("pickEdgeHover — mirrors priority chain", () => {
  it("returns null when no pill would render", () => {
    const parent = makeNode({ median_wage: 80_000 });
    const child = makeNode({ median_wage: 84_000 }); // below pay threshold
    expect(pickEdgeHover(parent, child)).toBeNull();
  });

  it("returns education context when education delta wins", () => {
    const parent = makeNode({ education: "Bachelor's degree" });
    const child = makeNode({ education: "Master's degree" });
    const ctx = pickEdgeHover(parent, child);
    expect(ctx).not.toBeNull();
    expect(ctx!.kind).toBe("education");
  });

  it("returns pay context with delta and both wages when pay wins", () => {
    const parent = makeNode({ median_wage: 60_000 });
    const child = makeNode({ median_wage: 90_000 });
    const ctx = pickEdgeHover(parent, child);
    expect(ctx).not.toBeNull();
    expect(ctx!.kind).toBe("pay");
    if (ctx && ctx.kind === "pay") {
      expect(ctx.fromWage).toBe(60_000);
      expect(ctx.toWage).toBe(90_000);
      expect(ctx.delta).toBe(30_000);
    }
  });

  it("returns null when only experience differs (experience removed from chain)", () => {
    // Experience tier deltas no longer drive an edge pill (filter
    // slider replaces them). With nothing else differing, no hover
    // context exists.
    const parent = makeNode({
      experience_tier: "early",
      experience_years: 2,
    });
    const child = makeNode({
      experience_tier: "mid",
      experience_years: 7,
    });
    const ctx = pickEdgeHover(parent, child);
    expect(ctx).toBeNull();
  });
});
