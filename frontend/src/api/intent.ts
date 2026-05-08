/**
 * Intent API client for the Set Your Course flow.
 *
 * Exposes three functions that the unified screen calls:
 *   - streamIntent:      POST /intent/stream — SSE stream of deltas +
 *                        a final structured resolution + community signal.
 *   - dispatchChip:      POST /intent/chip — one stateless chip tap.
 *   - commitResolution:  POST /intent/commit — append one correction log
 *                        record when the student commits.
 *
 * See docs/specs/feature-set-your-course.md §4 "Architecture Overview"
 * + "Service Changes" for the on-the-wire contract.
 */

import { apiPost } from "@/api/client";
import type { IntentResult, Suggestion, GradCredentialNoticePayload } from "@/types/buildInput";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type ChipId = "not_expected" | "show_less_common" | "change_major";

// Feasibility mode for the clicked career, when any. See spec §4
// "Feasibility Classification (the 5 Modes)". We don't render this
// directly in the committed flow — it lands on the correction log.
export type FeasibilityMode =
  | "direct_hit"
  | "crosswalk_quirk"
  | "adjacent_reachable"
  | "school_gap"
  | "genuinely_impossible"
  | "requires_grad_school";

export interface CtaLink {
  href: string;
  label: string;
  kind?: "school_discovery_v05" | "grad_credential_notice";
  payload?: GradCredentialNoticePayload | null;
}

export interface ChipResponse {
  debug_trace: string;
  updated_resolution: IntentResult | null;
  cta_link: CtaLink | null;
  bucket: string | null;
  confirmed_focus: string | null;
}

export type StreamEvent =
  | { type: "delta"; text: string }
  | { type: "structured"; result: IntentResult }
  | { type: "suggestions"; suggestions: Suggestion[] }
  | { type: "grad_credential_payload"; payload: GradCredentialNoticePayload }
  | { type: "done" };

interface StreamIntentArgs {
  majorText: string;
  schoolName: string;
  unitid: number;
  programs: Array<Record<string, unknown>>;
  signal?: AbortSignal;
  locale?: string;
}

/**
 * Async-iterate over Server-Sent Events from /intent/stream. Yields typed
 * events as they arrive. Throws a generic Error on AbortSignal trigger.
 *
 * SSE wire format:
 *   event: delta
 *   data: {"text": "..."}
 *
 *   event: structured
 *   data: {"result": {...IntentResult}}
 *
 *   event: suggestions
 *   data: {"suggestions": [...]}
 *
 *   event: done
 *   data: {}
 *
 * Events are separated by \n\n. Each event may carry multiple `data:` lines
 * (concatenated with a newline per the SSE spec). We tolerate missing
 * `event:` lines (treat as `message`) and ignore unknown event types.
 */
export async function* streamIntent({
  majorText,
  schoolName,
  unitid,
  programs,
  signal,
  locale,
}: StreamIntentArgs): AsyncIterableIterator<StreamEvent> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/intent/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        major_text: majorText,
        school_name: schoolName,
        unitid,
        programs,
        locale: locale ?? "en",
      }),
      signal,
    });
  } catch (err) {
    if (signal?.aborted) throw new Error("stream aborted");
    throw err instanceof Error ? err : new Error("stream request failed");
  }

  if (!response.ok) {
    throw new Error(`intent stream error: ${response.status}`);
  }
  if (!response.body) {
    throw new Error("intent stream produced no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        throw new Error("stream aborted");
      }
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line — "\n\n". Network
      // buffers may split anywhere, so parse greedily.
      let sep = buffer.indexOf("\n\n");
      while (sep !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const parsed = parseSseFrame(frame);
        if (parsed) yield parsed;
        sep = buffer.indexOf("\n\n");
      }
    }
    // Final partial frame (no trailing \n\n) — SSE spec allows it.
    if (buffer.trim().length > 0) {
      const parsed = parseSseFrame(buffer);
      if (parsed) yield parsed;
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // reader may already be closed; ignore.
    }
  }
}

function parseSseFrame(raw: string): StreamEvent | null {
  const lines = raw.split("\n");
  let eventName = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
    // Lines without a known prefix are ignored per SSE spec.
  }
  if (dataLines.length === 0) return null;
  const dataStr = dataLines.join("\n");
  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(dataStr) as Record<string, unknown>;
  } catch {
    return null;
  }

  switch (eventName) {
    case "delta": {
      const text = typeof payload.text === "string" ? payload.text : "";
      return { type: "delta", text };
    }
    case "structured": {
      const result = (payload.result ?? payload) as IntentResult;
      return { type: "structured", result };
    }
    case "suggestions": {
      const suggestions = (payload.suggestions ?? []) as Suggestion[];
      return { type: "suggestions", suggestions };
    }
    case "grad_credential_payload": {
      const gcPayload = payload as unknown as GradCredentialNoticePayload;
      return { type: "grad_credential_payload", payload: gcPayload };
    }
    case "done":
      return { type: "done" };
    default:
      return null;
  }
}

interface DispatchChipArgs {
  chipId: ChipId;
  clarifier?: string;
  currentResolution: IntentResult;
  initialResolution: IntentResult;
  schoolName: string;
  unitid: number;
  programs: Array<Record<string, unknown>>;
  signal?: AbortSignal;
  locale?: string;
}

export async function dispatchChip({
  chipId,
  clarifier,
  currentResolution,
  initialResolution,
  schoolName,
  unitid,
  programs,
  signal,
  locale,
}: DispatchChipArgs): Promise<ChipResponse> {
  // apiPost does not accept an AbortSignal, so we call fetch directly for
  // the chip path — aborts are load-bearing per the spec's chip-stream
  // abort policy.
  const res = await fetch(`${API_BASE}/intent/chip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chip_id: chipId,
      clarifier: clarifier ?? null,
      current_resolution: currentResolution,
      initial_resolution: initialResolution,
      school_name: schoolName,
      unitid,
      programs,
      locale: locale ?? "en",
    }),
    signal,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail =
      typeof (body as { detail?: unknown }).detail === "string"
        ? (body as { detail: string }).detail
        : `chip dispatch error: ${res.status}`;
    throw new Error(detail);
  }
  return (await res.json()) as ChipResponse;
}

interface CommitResolutionArgs {
  currentResolution: IntentResult;
  initialResolution: IntentResult;
  schoolName: string;
  unitid: number;
  inputNormalized: string;
  clickedSoc: string | null;
  clickedCareerTitle: string | null;
  feasibilityMode: FeasibilityMode | null;
  chipsTapped: ChipId[];
  clarifier: string | null;
}

export async function commitResolution(
  args: CommitResolutionArgs,
): Promise<{ committed: boolean; logged: boolean }> {
  return apiPost<{ committed: boolean; logged: boolean }>("/intent/commit", {
    current_resolution: args.currentResolution,
    initial_resolution: args.initialResolution,
    school_name: args.schoolName,
    unitid: args.unitid,
    major_text: args.inputNormalized,
    clicked_soc: args.clickedSoc,
    clicked_career_title: args.clickedCareerTitle,
    feasibility_mode: args.feasibilityMode,
    chips_tapped: args.chipsTapped,
    clarifier: args.clarifier,
  });
}
