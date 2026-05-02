/**
 * Menu (Screen 10) API client.
 *
 * Endpoints (resolved by architect 2026-04-16):
 *   GET  /builds?profile_name=X        → { builds: BuildSummary[] }
 *   POST /builds/compare               → { builds, stats, bosses }
 *   POST /build/{build_id}/chat        → { response }   (guidance_router.py:19)
 *
 * Mock fallback via VITE_USE_MOCK_API.
 */

import { apiGet, apiPost } from "@/api/client";
import {
  mockListBuilds,
  mockCompareBuilds,
  mockChat,
} from "@/api/mockMenu";
import type { GemmaTraceEvent } from "@/types/gemmaTrace";

const USE_MOCK = import.meta.env.VITE_USE_MOCK_API === "true";
const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface BuildSummary {
  build_id: string;
  created_at: string;
  school_name: string;
  major_text: string;
  career_title: string;
  ern: number | null;
  roi: number | null;
  res: number | null;
  grw: number | null;
  aura: number | null;
  wins: number;
  losses: number;
  draws: number;
  profile_name: string;
  animal_emoji: string | null;
}

export interface CompareBuild {
  build_id: string;
  label: string;
  career: string;
  soc_code: string;
  profile_name: string;
  animal_emoji: string | null;
  school_name: string;
  major_text: string;
  effort: string;
  loan_pct: number;
  median_annual_wage: number | null;
  net_price_annual: number | null;
  modeled_total_debt: number | null;
  tuition_annual: number | null;
  is_out_of_state: boolean;
  institution_control: string | null;
}

export interface CompareStatRow {
  label: string;
  values: (number | null)[];
}

export interface CompareBossRow {
  label: string;
  boss_id: string;
  values: string[];
  skill_counts: number[];
  original_values: string[];
}

export interface CompareBranchBuild {
  build_id: string;
  career: string;
  destinations: {
    to_title: string;
    to_soc: string;
    delta_ern: number | null;
    delta_grw: number | null;
  }[];
}

export interface CompareResult {
  builds: CompareBuild[];
  stats: CompareStatRow[];
  bosses: CompareBossRow[];
  branches: CompareBranchBuild[];
}

export interface BuildProsCons {
  build_id: string;
  pros: string[];
  cons: string[];
}

export interface ComparePivotal {
  meta_tradeoff: string;
  meta_explanation: string;
  decade_projection: string;
  pivot_question: string;
}

export interface CompareInsights {
  money_insight: string | null;
  compare_summary: string | null;
  pros_cons: BuildProsCons[] | null;
  pivotal: ComparePivotal | null;
}

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

// ---------------------------------------------------------------------------
// Ask Gemma — scope-aware chat (POST /chat/ask).
// Mirrors the backend AskScope discriminated union (models/api.py).
// ---------------------------------------------------------------------------

export type AskStatTarget = "ERN" | "ROI" | "RES" | "GRW" | "AURA";
export type AskBossTarget =
  | "ai"
  | "loans"
  | "market"
  | "burnout"
  | "ceiling";

export type AskScope =
  | { kind: "stat"; build_ids: [string]; target_id: AskStatTarget }
  | { kind: "boss"; build_ids: [string]; target_id: AskBossTarget }
  | { kind: "skill"; build_ids: [string]; target_id: string }
  | { kind: "build"; build_ids: [string]; target_id?: null }
  | { kind: "compare"; build_ids: string[]; target_id?: null }
  | { kind: "branch"; build_ids: [string]; target_id: string };

/**
 * One enriched tool-call entry on `AskResponse.tool_calls` — mirrors
 * the backend `TraceEventPayload` (`backend/app/models/api.py`). The
 * `turn` field carries the per-dispatch `dispatch_index`. Powers the
 * `<GemmaTrace>` post-hoc fallback render when SSE is unavailable.
 */
export interface TraceEventPayload {
  turn: number;
  tool: string;
  args: Record<string, unknown>;
  result_preview: string;
  duration_ms: number;
  error: string | null;
}

export interface AskResponse {
  response: string;
  tool_calls: TraceEventPayload[];
}

export async function listBuilds(profileName?: string): Promise<BuildSummary[]> {
  if (USE_MOCK) return mockListBuilds(profileName ?? "");
  const query = profileName
    ? `?profile_name=${encodeURIComponent(profileName)}`
    : "";
  const res = await apiGet<{ builds: BuildSummary[] }>(`/builds${query}`);
  return res.builds;
}

export async function compareBuilds(buildIds: string[]): Promise<CompareResult> {
  if (USE_MOCK) return mockCompareBuilds(buildIds);
  return apiPost<CompareResult>("/builds/compare", { build_ids: buildIds });
}

export async function compareInsights(buildIds: string[]): Promise<CompareInsights> {
  if (USE_MOCK) return { money_insight: null, compare_summary: null, pros_cons: null, pivotal: null };
  return apiPost<CompareInsights>("/builds/compare-insights", { build_ids: buildIds });
}

export async function sendChat(
  buildId: string,
  message: string,
  history: ChatHistoryItem[],
  locale?: string,
): Promise<string> {
  if (USE_MOCK) return mockChat(message, history);
  const res = await apiPost<{ response: string }>(
    `/build/${encodeURIComponent(buildId)}/chat`,
    { message, history, locale: locale ?? undefined },
  );
  return res.response;
}

export async function askGemma(
  scope: AskScope,
  message: string,
  history: ChatHistoryItem[],
  locale?: string,
): Promise<AskResponse> {
  if (USE_MOCK) {
    const text = await mockChat(message, history);
    return { response: text, tool_calls: [] };
  }
  return apiPost<AskResponse>("/chat/ask", {
    scope,
    message,
    history,
    locale: locale ?? undefined,
  });
}

// ---------------------------------------------------------------------------
// Ask Gemma streaming variant — POST /chat/ask/stream.
//
// Surfaces Gemma's multi-turn function-calling chain as live SSE events
// for `<GemmaTrace>`. See docs/specs/feature-gemma-trace.md §4.
//
// Failure modes (all silent — the chat never shows an error toast):
// 1. Streaming endpoint HTTP error or thrown — falls back to askGemma
//    and synthesizes turn_start + turn_complete events from the
//    enriched tool_calls list. Final shape is identical to the live
//    path so <GemmaTrace> renders both feeds the same way (Decision #7).
// 2. Unknown SSE event type — parser returns null, reader loop skips
//    it, stream continues. This is the forward-compat seam (Decision
//    #15) — adding new event types in the backend later doesn't break
//    older frontend bundles.
// ---------------------------------------------------------------------------

/**
 * Parse one SSE frame text block into a `GemmaTraceEvent`, or `null`
 * if the frame is malformed OR carries an unknown `type` value.
 *
 * **Forward-compat contract (Decision #15 / Item B):** MUST return null
 * (never throw, never propagate) on any frame whose JSON `type` field
 * is not in the known discriminated union. The reader loop calls this
 * for every frame; an unknown type is silently skipped.
 */
export function parseSSEFrame(frame: string): GemmaTraceEvent | null {
  const eventMatch = frame.match(/^event:\s*(.+)$/m);
  const dataMatch = frame.match(/^data:\s*(.+)$/m);
  if (!eventMatch || !dataMatch) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(dataMatch[1]!);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) return null;
  const obj = parsed as Record<string, unknown>;
  const type = obj.type;

  switch (type) {
    case "turn_start":
      return {
        type: "turn_start",
        turn: typeof obj.turn === "number" ? obj.turn : 0,
        tool: typeof obj.tool === "string" ? obj.tool : "",
        args:
          typeof obj.args === "object" && obj.args !== null
            ? (obj.args as Record<string, unknown>)
            : {},
      };
    case "turn_complete":
      return {
        type: "turn_complete",
        turn: typeof obj.turn === "number" ? obj.turn : 0,
        tool: typeof obj.tool === "string" ? obj.tool : "",
        args:
          typeof obj.args === "object" && obj.args !== null
            ? (obj.args as Record<string, unknown>)
            : {},
        result_preview:
          typeof obj.result_preview === "string" ? obj.result_preview : "",
        duration_ms:
          typeof obj.duration_ms === "number" ? obj.duration_ms : 0,
        error: typeof obj.error === "string" ? obj.error : null,
      };
    case "final_text":
      return {
        type: "final_text",
        response: typeof obj.response === "string" ? obj.response : "",
      };
    case "done":
      return { type: "done" };
    default:
      // Unknown event type — silently skip. This is the forward-compat
      // seam: a future backend version that emits a new event type
      // (e.g. "thinking", "final_text_delta") doesn't break this
      // older frontend bundle.
      return null;
  }
}

/** Synthesize trace events from a non-streaming AskResponse so the
 *  `<GemmaTrace>` fallback render uses the same event shape as the
 *  live path. One `turn_start` + one `turn_complete` per tool_calls
 *  entry, in array order. */
function synthesizeEventsFromToolCalls(
  toolCalls: TraceEventPayload[],
): GemmaTraceEvent[] {
  const events: GemmaTraceEvent[] = [];
  for (const tc of toolCalls) {
    events.push({
      type: "turn_start",
      turn: tc.turn,
      tool: tc.tool,
      args: tc.args,
    });
    events.push({
      type: "turn_complete",
      turn: tc.turn,
      tool: tc.tool,
      args: tc.args,
      result_preview: tc.result_preview,
      duration_ms: tc.duration_ms,
      error: tc.error,
    });
  }
  return events;
}

export interface AskGemmaStreamResult {
  response: string;
  events: GemmaTraceEvent[];
}

/**
 * Send an Ask Gemma message and consume the trace stream live.
 *
 * `onEvent` is fired for every parsed `GemmaTraceEvent` (turn_start,
 * turn_complete, final_text, done) as it arrives. The returned promise
 * resolves with the final response text + the full event list once the
 * stream closes.
 *
 * On connection failure (HTTP error or thrown error from `fetch`),
 * silently falls back to `askGemma`, synthesizes events from
 * `tool_calls`, and fires `onEvent` for each so the consumer renders
 * the same way it would have in the live path.
 */
export async function askGemmaStream(
  scope: AskScope,
  message: string,
  history: ChatHistoryItem[],
  onEvent: (event: GemmaTraceEvent) => void,
  locale?: string,
): Promise<AskGemmaStreamResult> {
  if (USE_MOCK) {
    // Mock path: just consume mockChat and emit a single final_text +
    // done. Trace is not exercised in mock mode.
    const text = await mockChat(message, history);
    const final: GemmaTraceEvent = { type: "final_text", response: text };
    const done: GemmaTraceEvent = { type: "done" };
    onEvent(final);
    onEvent(done);
    return { response: text, events: [final, done] };
  }

  const collected: GemmaTraceEvent[] = [];
  let response = "";

  try {
    const res = await fetch(`${API_BASE}/chat/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope,
        message,
        history,
        locale: locale ?? undefined,
      }),
    });

    if (!res.ok || !res.body) {
      throw new Error(`stream failed: ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          if (!frame.trim()) continue;
          const event = parseSSEFrame(frame);
          if (event === null) continue; // unknown type or malformed
          collected.push(event);
          onEvent(event);
          if (event.type === "final_text") {
            response = event.response;
          }
        }
      }
    } finally {
      try {
        reader.releaseLock();
      } catch {
        // already closed
      }
    }

    return { response, events: collected };
  } catch (err) {
    // Fallback: SSE failed (HTTP error, network, etc.) → use the non-
    // streaming endpoint and synthesize equivalent events from
    // tool_calls. Silent per Decision #7 — chat keeps working.
    if (typeof console !== "undefined") {
      console.warn("[gemma-trace] stream failed, falling back", err);
    }
    const fallback = await askGemma(scope, message, history, locale);
    const synthetic = synthesizeEventsFromToolCalls(fallback.tool_calls);
    const finalEv: GemmaTraceEvent = {
      type: "final_text",
      response: fallback.response,
    };
    const doneEv: GemmaTraceEvent = { type: "done" };
    for (const ev of synthetic) onEvent(ev);
    onEvent(finalEv);
    onEvent(doneEv);
    return {
      response: fallback.response,
      events: [...synthetic, finalEv, doneEv],
    };
  }
}
