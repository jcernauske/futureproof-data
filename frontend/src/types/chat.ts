/**
 * Chat-history-item types and the structured-receipt schema.
 *
 * Mirrors the backend Pydantic models in `backend/app/models/api.py`.
 * Spec: `docs/specs/feature-explain-stat-receipt.md`.
 *
 * The Zod schema is the single source of truth for the runtime shape;
 * the TypeScript types are inferred from it. Use `explainStatReceiptSchema.parse`
 * (or `.safeParse`) at the SSE boundary to validate incoming JSON.
 */
import { z } from "zod";

// ---------------------------------------------------------------------------
// ExplainStatReceipt — structured JSON receipt for the "Explain this stat"
// affordance. v1.0 ships ERN only; the schema fits ERN, ROI, RES, GRW.
// AURA is out of scope for v1.0 (spec Decision 10).
// ---------------------------------------------------------------------------

export const scoringTierSchema = z
  .object({
    label: z.string(),
    range: z.string(),
    score: z.string(),
  })
  .strict();

export const receiptSourceSchema = z
  .object({
    label: z.string(),
    name: z.string(),
  })
  .strict();

export const statComponentSchema = z
  .object({
    weight_pct: z.number().int().min(0).max(100),
    label: z.string(),
    explainer: z.string(),
    value_pct: z.number().int().min(0).max(100).nullable(),
    anchor_text: z.string(),
    anchor_dollars: z.number().int().min(0).nullable(),
    missing_reason: z.string().nullable(),
    evidence_bullets: z.array(z.string()).max(6).nullable().optional(),
  })
  .strict();

export const explainStatReceiptSchema = z
  .object({
    kind: z.literal("receipt"),
    stat_code: z.enum(["ERN", "ROI", "RES", "GRW", "AURA"]),
    stat_name: z.string(),
    score: z.number().int().min(1).max(10).nullable(),
    score_max: z.number().int().default(10),
    one_liner: z.string(),
    components: z.array(statComponentSchema).min(1).max(5),
    math_line: z.string(),
    sources: z.array(receiptSourceSchema).min(1),
    why_mix_paragraph: z.string().max(800),
    scoring_scale: z.array(scoringTierSchema).nullable().optional(),
  })
  .strict();

export type ScoringTier = z.infer<typeof scoringTierSchema>;
export type ReceiptSource = z.infer<typeof receiptSourceSchema>;
export type StatComponent = z.infer<typeof statComponentSchema>;
export type ExplainStatReceipt = z.infer<typeof explainStatReceiptSchema>;

// ---------------------------------------------------------------------------
// ChatHistoryItem — discriminated union for the in-memory chat history.
// "text" carries plain prose for every existing scope; "receipt" carries
// the structured ExplainStatReceipt payload for the explain-this-stat path.
// The dispatch is exhaustive in TypeScript so future kinds (if any) are
// forced through the type system.
// ---------------------------------------------------------------------------

export type ChatHistoryItem =
  | { role: "user" | "assistant"; kind: "text"; content: string }
  | { role: "assistant"; kind: "receipt"; payload: ExplainStatReceipt };

/**
 * Convenience guard for the receipt branch of an SSE final_text payload.
 * Use after a successful `explainStatReceiptSchema.safeParse(...)` to keep
 * the discriminator narrowing co-located with the validation.
 */
export function isExplainStatReceipt(
  value: unknown,
): value is ExplainStatReceipt {
  return explainStatReceiptSchema.safeParse(value).success;
}
