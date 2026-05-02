/**
 * Frontend types for the Gemma tool-call trace stream.
 *
 * Mirrors the backend wire-format models in
 * `backend/app/models/api.py`:
 *
 *   TraceTurnStart    → { type: "turn_start", turn, tool, args }
 *   TraceTurnComplete → { type: "turn_complete", turn, tool, args,
 *                         result_preview, duration_ms, error }
 *   TraceFinalText    → { type: "final_text", response }
 *   TraceDone         → { type: "done" }
 *
 * The `turn` field on turn_start / turn_complete carries the backend's
 * per-dispatch monotonic `dispatch_index` (Decision #13). It is the
 * unique row-correlation key — NOT the loop's outer LLM turn_number.
 *
 * See `docs/specs/feature-gemma-trace.md` §3 Row Correlation Key.
 */

export type GemmaTraceEvent =
  | {
      type: "turn_start";
      turn: number;
      tool: string;
      args: Record<string, unknown>;
    }
  | {
      type: "turn_complete";
      turn: number;
      tool: string;
      args: Record<string, unknown>;
      result_preview: string;
      duration_ms: number;
      error: string | null;
    }
  | { type: "final_text"; response: string }
  | { type: "done" };

/**
 * Visual mode for `<GemmaTrace>`. ``"live"`` enables row-entrance
 * animation and the in-progress shimmer on unresolved rows; ``"complete"``
 * mounts everything in resolved state with no entrance animation
 * (used by both State 2 and State 3 / fallback).
 */
export type TraceMode = "live" | "complete";

/**
 * One entry in `TOOL_LABEL_MAP` — the per-tool translation surface
 * that turns the raw tool name into pedagogical copy + iconography.
 *
 * `hint` builds the friendly sentence: takes the raw `args` dict and
 * returns the pedagogical sentence to render in the row's default
 * (collapsed) view.
 */
export type ToolLabel = {
  /** Short, judge-readable name. Surfaced in screen-reader announcements. */
  label: string;
  /** Identifier of the in-house SVG icon component (see icons/). */
  icon: string;
  /** Builder for the pedagogical sentence shown in the row's default view. */
  hint: (args: Record<string, unknown>) => string;
};
