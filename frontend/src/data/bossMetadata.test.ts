import { describe, it, expect } from "vitest";
import {
  BOSS_ORDER,
  BOSS_METADATA,
  RESULT_COLORS,
  getVerdictColor,
} from "./bossMetadata";

/**
 * bossMetadata tests
 *
 * Tests the static boss configuration and the getVerdictColor helper.
 * getVerdictColor extracts the first word from a verdict string, uppercases it,
 * and maps it to a Tailwind class. This is the function most likely to break
 * if someone changes the verdict format or color mapping.
 */

describe("BOSS_ORDER", () => {
  it("contains exactly 5 bosses in correct sequence", () => {
    expect(BOSS_ORDER).toEqual(["ai", "loans", "market", "burnout", "ceiling"]);
  });
});

describe("BOSS_METADATA", () => {
  it("has metadata for every boss in BOSS_ORDER", () => {
    for (const bossId of BOSS_ORDER) {
      const meta = BOSS_METADATA[bossId];
      expect(meta).toBeDefined();
      expect(meta.id).toBe(bossId);
      expect(meta.label).toBeTruthy();
      expect(meta.emoji).toBeTruthy();
      expect(meta.subtitle).toBeTruthy();
      expect(meta.colorToken).toMatch(/^text-boss-/);
      expect(meta.glowToken).toMatch(/^shadow-glow-/);
    }
  });

  it("each boss has a unique label", () => {
    const labels = BOSS_ORDER.map((id) => BOSS_METADATA[id].label);
    expect(new Set(labels).size).toBe(labels.length);
  });
});

describe("RESULT_COLORS", () => {
  it("maps all four outcomes to color tokens", () => {
    expect(RESULT_COLORS.win).toBe("accent-thrive");
    expect(RESULT_COLORS.lose).toBe("accent-alert");
    expect(RESULT_COLORS.draw).toBe("accent-caution");
    expect(RESULT_COLORS.unknown).toBe("accent-info");
  });
});

describe("getVerdictColor", () => {
  it('returns thrive color for "DOMINANT" verdict', () => {
    expect(getVerdictColor("DOMINANT — crushed it")).toBe("text-accent-thrive");
  });

  it('returns thrive color for "SOLID" verdict', () => {
    expect(getVerdictColor("SOLID build overall")).toBe("text-accent-thrive");
  });

  it('returns caution color for "MIXED" verdict', () => {
    expect(getVerdictColor("MIXED results across the board")).toBe(
      "text-accent-caution",
    );
  });

  it('returns alert color for "VULNERABLE" verdict', () => {
    expect(getVerdictColor("VULNERABLE to market shifts")).toBe(
      "text-accent-alert",
    );
  });

  it("is case-insensitive on the first word (lowercased input)", () => {
    // The function uppercases the first word, so "solid build" should work
    expect(getVerdictColor("solid build")).toBe("text-accent-thrive");
  });

  it("falls back to secondary text color for unknown verdict", () => {
    expect(getVerdictColor("AMAZING performance")).toBe("text-text-secondary");
  });

  it("falls back for empty string", () => {
    expect(getVerdictColor("")).toBe("text-text-secondary");
  });

  it("handles single-word verdict", () => {
    expect(getVerdictColor("MIXED")).toBe("text-accent-caution");
  });

  it("handles verdict with extra whitespace", () => {
    // split(" ")[0] handles leading content fine, but what about leading spaces?
    // "  MIXED" -> split(" ")[0] = "" -> toUpperCase = "" -> no match -> fallback
    expect(getVerdictColor("  MIXED")).toBe("text-text-secondary");
  });
});
