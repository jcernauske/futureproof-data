/**
 * chat.test.ts — Zod schema tests for ExplainStatReceipt.
 *
 * Validates the runtime schema boundary behavior for the
 * score_provenance field added in the AURA explain-stat receipt.
 */

import { describe, it, expect } from "vitest";
import { explainStatReceiptSchema } from "./chat";

// ---------------------------------------------------------------------------
// Minimal valid receipt payload — AURA shape
// ---------------------------------------------------------------------------

function makeMinimalAURAPayload(): Record<string, unknown> {
  return {
    kind: "receipt",
    stat_code: "AURA",
    stat_name: "Brand Gravity",
    score: 8,
    score_max: 10,
    one_liner: "Brand Gravity measures institutional weight.",
    components: [
      {
        weight_pct: 100,
        label: "your school's brand gravity",
        explainer: "Endowment, marketing, and athletics per student.",
        value_pct: null,
        anchor_text: "IU Bloomington institutional signals",
        anchor_dollars: null,
        missing_reason: null,
      },
    ],
    math_line: "composite 0.72 → AURA score 8/10",
    sources: [
      {
        label: "Endowment + marketing",
        name: "IPEDS, U.S. Department of Education",
      },
    ],
    why_mix_paragraph:
      "Prestige matters for networking and recruiter shortlists.",
  };
}

// ---------------------------------------------------------------------------
// score_provenance Zod validation
// ---------------------------------------------------------------------------

describe("explainStatReceiptSchema — score_provenance", () => {
  it("test_zod_parser_accepts_score_provenance_string", () => {
    const payload = {
      ...makeMinimalAURAPayload(),
      score_provenance: "endowment + marketing + athletics",
    };
    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.score_provenance).toBe(
        "endowment + marketing + athletics",
      );
    }
  });

  it("test_zod_parser_accepts_score_provenance_null", () => {
    const payload = {
      ...makeMinimalAURAPayload(),
      score_provenance: null,
    };
    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.score_provenance).toBeNull();
    }
  });

  it("test_zod_parser_accepts_omitted_score_provenance", () => {
    const payload = makeMinimalAURAPayload();
    // score_provenance is NOT in the payload
    expect(payload).not.toHaveProperty("score_provenance");

    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(true);
    if (result.success) {
      // Optional field should be undefined when omitted
      expect(result.data.score_provenance).toBeUndefined();
    }
  });

  it("rejects score_provenance longer than 200 chars", () => {
    const payload = {
      ...makeMinimalAURAPayload(),
      score_provenance: "x".repeat(201),
    };
    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(false);
  });

  it("accepts score_provenance exactly 200 chars (boundary)", () => {
    const payload = {
      ...makeMinimalAURAPayload(),
      score_provenance: "a".repeat(200),
    };
    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(true);
  });

  it("rejects score_provenance of wrong type (number)", () => {
    const payload = {
      ...makeMinimalAURAPayload(),
      score_provenance: 42,
    };
    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Verify AURA is accepted as a stat_code value
// ---------------------------------------------------------------------------

describe("explainStatReceiptSchema — AURA stat_code", () => {
  it("accepts AURA as stat_code", () => {
    const payload = makeMinimalAURAPayload();
    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.stat_code).toBe("AURA");
    }
  });

  it("rejects unknown stat_code", () => {
    const payload = {
      ...makeMinimalAURAPayload(),
      stat_code: "XYZ",
    };
    const result = explainStatReceiptSchema.safeParse(payload);
    expect(result.success).toBe(false);
  });
});
