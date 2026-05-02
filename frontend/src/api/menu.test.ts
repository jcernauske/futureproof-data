/**
 * menu.test.ts — `parseSSEFrame` Zod-union parsing for the
 * final_text frame's `response` discriminated union.
 *
 * Spec: docs/specs/feature-explain-stat-receipt.md (DRAFT v1.3) §4 New
 * Tests Required (P0 rows for `frontend/src/api/menu.test.ts`).
 *
 * The contract:
 *   - String response → returned as-is (the prose-bubble path).
 *   - Object response that matches the receipt Zod schema → returned
 *     as the typed ExplainStatReceipt.
 *   - Object response that fails the Zod schema (missing fields,
 *     wrong types, unsanctioned extras) → falls back to
 *     `String(value)` so the chat renders something rather than
 *     throws.
 */

import { describe, it, expect } from "vitest";
import { parseSSEFrame } from "./menu";
import type { ExplainStatReceipt } from "@/types/chat";

function frame(eventName: string, data: unknown): string {
  return `event: ${eventName}\ndata: ${JSON.stringify(data)}`;
}

function goodReceipt(): ExplainStatReceipt {
  return {
    kind: "receipt",
    stat_code: "ERN",
    stat_name: "Earning Power",
    score: 7,
    score_max: 10,
    one_liner: "How much your degree usually pays right after graduation.",
    components: [
      {
        weight_pct: 60,
        label: "your school's program rank",
        explainer: "School rank explainer here.",
        value_pct: 87,
        anchor_text: "IU CS grads",
        anchor_dollars: 94_200,
        missing_reason: null,
      },
      {
        weight_pct: 40,
        label: "this career's pay rank",
        explainer: "Career pay rank explainer.",
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
        name: "Occupational Outlook Handbook (BLS)",
      },
    ],
    why_mix_paragraph:
      "Two students at different schools — different programs, different careers, different ranks. Mixing both grounds the score.",
  };
}

describe("parseSSEFrame final_text Zod union", () => {
  it("test_zod_parser_distinguishes_string_vs_receipt — string branch (P0)", () => {
    const event = parseSSEFrame(
      frame("final_text", { type: "final_text", response: "plain prose answer" }),
    );
    expect(event).not.toBeNull();
    expect(event!.type).toBe("final_text");
    if (event!.type === "final_text") {
      expect(event!.response).toBe("plain prose answer");
      expect(typeof event!.response).toBe("string");
    }
  });

  it("test_zod_parser_distinguishes_string_vs_receipt — receipt branch (P0)", () => {
    const receipt = goodReceipt();
    const event = parseSSEFrame(
      frame("final_text", { type: "final_text", response: receipt }),
    );
    expect(event).not.toBeNull();
    if (event!.type === "final_text") {
      expect(typeof event!.response).toBe("object");
      const resp = event!.response as ExplainStatReceipt;
      expect(resp.kind).toBe("receipt");
      expect(resp.stat_code).toBe("ERN");
      expect(resp.score).toBe(7);
      expect(resp.components).toHaveLength(2);
      expect(resp.components[0]!.weight_pct).toBe(60);
      expect(resp.sources).toHaveLength(2);
    }
  });

  it("test_zod_parser_falls_back_to_string_on_invalid_object — missing fields (P0)", () => {
    // Object with the receipt's `kind` discriminator but missing
    // required fields (no components, no math_line). Zod rejects;
    // parser falls back to String(value) instead of throwing.
    const broken = {
      kind: "receipt",
      stat_code: "ERN",
      // ...missing everything else
    };
    const event = parseSSEFrame(
      frame("final_text", { type: "final_text", response: broken }),
    );
    expect(event).not.toBeNull();
    if (event!.type === "final_text") {
      // Falls back to String(value) — the value is "[object Object]"
      // for plain JSON objects. The contract is "doesn't throw," not
      // "produces meaningful output" — the prose render of
      // "[object Object]" is the gracefully-degrade path.
      expect(typeof event!.response).toBe("string");
    }
  });

  it("falls back to string when object has wrong-type fields (saboteur)", () => {
    // `score` as a string instead of number — Zod rejects.
    const broken = { ...goodReceipt(), score: "seven" as unknown as number };
    const event = parseSSEFrame(
      frame("final_text", { type: "final_text", response: broken }),
    );
    expect(event).not.toBeNull();
    if (event!.type === "final_text") {
      expect(typeof event!.response).toBe("string");
    }
  });

  it("falls back to string when object has score out of range (saboteur)", () => {
    const broken = { ...goodReceipt(), score: 99 };
    const event = parseSSEFrame(
      frame("final_text", { type: "final_text", response: broken }),
    );
    expect(event).not.toBeNull();
    if (event!.type === "final_text") {
      expect(typeof event!.response).toBe("string");
    }
  });

  it("falls back to string when object has unsanctioned extra field (saboteur)", () => {
    // Zod schemas use .strict() — extra keys are rejected.
    const broken = { ...goodReceipt(), confidence: 0.8 };
    const event = parseSSEFrame(
      frame("final_text", { type: "final_text", response: broken }),
    );
    expect(event).not.toBeNull();
    if (event!.type === "final_text") {
      expect(typeof event!.response).toBe("string");
    }
  });

  it("falls back to empty string when response is missing (saboteur)", () => {
    // No `response` key at all on the SSE frame's data object. The
    // parser should not throw; it should produce String(undefined) ==
    // "undefined" or the empty-string fallback.
    const event = parseSSEFrame(frame("final_text", { type: "final_text" }));
    expect(event).not.toBeNull();
    if (event!.type === "final_text") {
      // String(undefined) is "undefined" but parseFinalTextResponse
      // uses `value ?? ""` so it produces "".
      expect(typeof event!.response).toBe("string");
      expect(event!.response).toBe("");
    }
  });
});
