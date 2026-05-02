import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  askGemmaStream,
  parseSSEFrame,
  type AskScope,
} from "@/api/menu";
import type { GemmaTraceEvent } from "@/types/gemmaTrace";

const SCOPE: AskScope = { kind: "build", build_ids: ["bid-1"] };

function makeStreamResponse(frames: string[]): Response {
  // Concatenate frames into one body. Each frame already ends with
  // "\n\n" per the SSE wire format (sse_event helper).
  const body = frames.join("");
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(body));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

beforeEach(() => {
  // Ensure mock mode is off (test exercises the real fetch path).
  vi.stubEnv("VITE_USE_MOCK_API", "false");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("parseSSEFrame", () => {
  it("parses a turn_start frame", () => {
    const frame =
      'event: turn_start\ndata: {"type":"turn_start","turn":0,"tool":"get_career_paths","args":{"unitid":1}}';
    const ev = parseSSEFrame(frame);
    expect(ev).toEqual({
      type: "turn_start",
      turn: 0,
      tool: "get_career_paths",
      args: { unitid: 1 },
    });
  });

  it("parses a turn_complete frame", () => {
    const frame =
      'event: turn_complete\ndata: {"type":"turn_complete","turn":0,"tool":"get_career_paths","args":{},"result_preview":"ok","duration_ms":42,"error":null}';
    const ev = parseSSEFrame(frame);
    expect(ev?.type).toBe("turn_complete");
    if (ev?.type === "turn_complete") {
      expect(ev.duration_ms).toBe(42);
      expect(ev.error).toBeNull();
    }
  });

  it("parses final_text and done frames", () => {
    expect(
      parseSSEFrame(
        'event: final_text\ndata: {"type":"final_text","response":"hi"}',
      ),
    ).toEqual({ type: "final_text", response: "hi" });
    expect(
      parseSSEFrame('event: done\ndata: {"type":"done"}'),
    ).toEqual({ type: "done" });
  });

  it("test_unknown_event_type_returns_null_not_throw", () => {
    // Decision #15 / Item B forward-compat seam. A future backend that
    // emits a new event type (e.g. "thinking", "final_text_delta")
    // must NOT break the older frontend bundle.
    const frame =
      'event: thinking\ndata: {"type":"thinking","text":"reasoning..."}';
    let result: GemmaTraceEvent | null | "threw" = "threw";
    try {
      result = parseSSEFrame(frame);
    } catch {
      result = "threw";
    }
    expect(result).toBeNull();
  });

  it("returns null on malformed JSON", () => {
    const frame = "event: turn_start\ndata: not-valid-json";
    expect(parseSSEFrame(frame)).toBeNull();
  });

  it("returns null when event/data lines are missing", () => {
    expect(parseSSEFrame("malformed")).toBeNull();
    expect(parseSSEFrame("event: turn_start\n(no data)")).toBeNull();
  });
});

describe("askGemmaStream", () => {
  it("test_askGemmaStream_happy_path_parses_sse_frames", async () => {
    const frames = [
      'event: turn_start\ndata: {"type":"turn_start","turn":0,"tool":"get_career_paths","args":{}}\n\n',
      'event: turn_complete\ndata: {"type":"turn_complete","turn":0,"tool":"get_career_paths","args":{},"result_preview":"ok","duration_ms":50,"error":null}\n\n',
      'event: final_text\ndata: {"type":"final_text","response":"Final answer."}\n\n',
      'event: done\ndata: {"type":"done"}\n\n',
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeStreamResponse(frames)),
    );

    const received: GemmaTraceEvent[] = [];
    const result = await askGemmaStream(
      SCOPE,
      "anything",
      [],
      (e) => received.push(e),
    );

    expect(received.map((e) => e.type)).toEqual([
      "turn_start",
      "turn_complete",
      "final_text",
      "done",
    ]);
    expect(result.response).toBe("Final answer.");
  });

  it("test_askGemmaStream_falls_back_on_http_error", async () => {
    // First call (stream endpoint) returns 500.
    // Second call (apiPost via askGemma) is intercepted in apiPost — we
    // mock fetch to return both an error then a clean response.
    const fetchMock = vi.fn();
    fetchMock.mockResolvedValueOnce(
      new Response("server error", { status: 500 }),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          response: "Fallback answer.",
          tool_calls: [
            {
              turn: 0,
              tool: "get_career_paths",
              args: {},
              result_preview: "ok",
              duration_ms: 30,
              error: null,
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const received: GemmaTraceEvent[] = [];
    const result = await askGemmaStream(
      SCOPE,
      "anything",
      [],
      (e) => received.push(e),
    );

    expect(result.response).toBe("Fallback answer.");
    // Synthesized turn_start + turn_complete from the single tool_call,
    // then final_text + done.
    expect(received.map((e) => e.type)).toEqual([
      "turn_start",
      "turn_complete",
      "final_text",
      "done",
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("test_askGemmaStream_falls_back_on_thrown_error", async () => {
    const fetchMock = vi.fn();
    fetchMock.mockRejectedValueOnce(new Error("network down"));
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          response: "Recovered.",
          tool_calls: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const received: GemmaTraceEvent[] = [];
    const result = await askGemmaStream(
      SCOPE,
      "anything",
      [],
      (e) => received.push(e),
    );

    expect(result.response).toBe("Recovered.");
    // No tool_calls → no synthesized turn events; only final_text + done.
    expect(received.map((e) => e.type)).toEqual(["final_text", "done"]);
  });

  it("silently skips unknown event types in the live stream", async () => {
    // Mid-stream "thinking" frame must not crash the consumer; known
    // events around it must still dispatch.
    const frames = [
      'event: turn_start\ndata: {"type":"turn_start","turn":0,"tool":"get_career_paths","args":{}}\n\n',
      'event: thinking\ndata: {"type":"thinking","text":"hmm"}\n\n',
      'event: final_text\ndata: {"type":"final_text","response":"OK."}\n\n',
      'event: done\ndata: {"type":"done"}\n\n',
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(makeStreamResponse(frames)),
    );

    const received: GemmaTraceEvent[] = [];
    await askGemmaStream(SCOPE, "anything", [], (e) => received.push(e));

    expect(received.map((e) => e.type)).toEqual([
      "turn_start",
      "final_text",
      "done",
    ]);
  });
});
