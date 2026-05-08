/**
 * GemmaChat.test.tsx
 *
 * P0:
 *   - Typing + clicking send calls sendChat with message + history
 *   - Renders Gemma's response once the API resolves
 * P1:
 *   - Tapping a starter pill fills the input
 *   - Multi-turn history: second user turn carries the prior 2 entries
 *
 * @/api/menu mocked at the module boundary for deterministic resolution.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { GemmaChat } from "./GemmaChat";
import type { AskScope, BuildSummary } from "@/api/menu";

const mockSendChat = vi.fn();
const mockAskGemma = vi.fn();
const mockAskGemmaStream = vi.fn();
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    sendChat: (...args: unknown[]) => mockSendChat(...args),
    askGemma: (...args: unknown[]) => mockAskGemma(...args),
    askGemmaStream: (...args: unknown[]) => mockAskGemmaStream(...args),
  };
});

// Helper: build the default happy-path stream impl. Fires the supplied
// events in order through onEvent and resolves with the final shape.
type StreamEvent =
  | { type: "turn_start"; turn: number; tool: string; args: Record<string, unknown> }
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

function streamImpl(events: StreamEvent[]) {
  return async (
    _scope: unknown,
    _message: unknown,
    _history: unknown,
    onEvent: (event: StreamEvent) => void,
  ) => {
    for (const ev of events) onEvent(ev);
    const final = events.find(
      (e): e is Extract<StreamEvent, { type: "final_text" }> =>
        e.type === "final_text",
    );
    return { response: final?.response ?? "", events };
  };
}

function makeBuild(overrides: Partial<BuildSummary> = {}): BuildSummary {
  return {
    build_id: "berkeley-cs-001",
    created_at: "2026-04-12T18:30:00Z",
    school_name: "UC Berkeley",
    major_text: "Computer Science",
    career_title: "Software Developers",
    ern: 8,
    roi: 7,
    res: 4,
    grw: 9,
    aura: 5,
    wins: 4,
    losses: 0,
    draws: 1,
    profile_name: "Wandering Otter",
    animal_emoji: "🦦",
    ...overrides,
  };
}

beforeEach(() => {
  mockSendChat.mockReset();
  mockAskGemma.mockReset();
  mockAskGemmaStream.mockReset();
  // Default happy-path stream so existing scope-based tests keep
  // passing without each test wiring the mock up explicitly.
  mockAskGemmaStream.mockImplementation(
    streamImpl([
      { type: "final_text", response: "ok" },
      { type: "done" },
    ]),
  );
});

describe("GemmaChat", () => {
  // --- P0: send message ---

  it("typing + clicking send calls sendChat with message + history (P0)", async () => {
    mockSendChat.mockResolvedValue("Here's a thought on internships.");

    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);

    const input = screen.getByTestId("input-chat") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "What internships?" } });
    fireEvent.click(screen.getByTestId("btn-chat-send"));

    await waitFor(() => {
      expect(mockSendChat).toHaveBeenCalledTimes(1);
    });
    // First turn — empty history, message is what the user typed, build_id is right.
    expect(mockSendChat).toHaveBeenCalledWith(
      "berkeley-cs-001",
      "What internships?",
      [],
      "en",
    );
  });

  it("renders Gemma's response after sendChat resolves (P0)", async () => {
    mockSendChat.mockResolvedValue("Look at health-tech firms first.");

    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);

    fireEvent.change(screen.getByTestId("input-chat"), {
      target: { value: "tell me something" },
    });
    fireEvent.click(screen.getByTestId("btn-chat-send"));

    await waitFor(() => {
      expect(
        screen.getByText("Look at health-tech firms first."),
      ).toBeInTheDocument();
    });
    // The user message also appears in the transcript (assertable user bubble).
    expect(screen.getByText("tell me something")).toBeInTheDocument();
  });

  it("send button is disabled when the input is empty (saboteur: empty submit)", () => {
    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);
    expect(screen.getByTestId("btn-chat-send")).toBeDisabled();
  });

  it("does NOT call sendChat when message is whitespace only (saboteur)", () => {
    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);
    fireEvent.change(screen.getByTestId("input-chat"), {
      target: { value: "    " },
    });
    fireEvent.click(screen.getByTestId("btn-chat-send"));
    expect(mockSendChat).not.toHaveBeenCalled();
  });

  // --- P1: starter questions fill input ---

  it("tapping a starter pill fills the input (P1)", () => {
    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);

    fireEvent.click(screen.getByTestId("btn-starter-0"));

    const input = screen.getByTestId("input-chat") as HTMLInputElement;
    // Chip 0 is the most-likely-tapped multi-tool starter (geography
    // demo). See STARTERS in GemmaChat.tsx — verified to fire 3
    // tool calls when sent.
    expect(input.value).toBe(
      "How would my salary feel in a few different states?",
    );
  });

  it("renders all 7 starter pills (P1)", () => {
    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);
    for (let i = 0; i < 7; i += 1) {
      expect(screen.getByTestId(`btn-starter-${i}`)).toBeInTheDocument();
    }
    // No 8th pill — STARTERS is exactly 7.
    expect(screen.queryByTestId("btn-starter-7")).toBeNull();
  });

  // --- P1: maintains conversation history ---

  it("second user turn passes the prior 2-entry history to sendChat (P1)", async () => {
    // First turn: user "Q1" → assistant "A1". Second turn: user "Q2".
    mockSendChat.mockResolvedValueOnce("A1");

    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);

    // Turn 1.
    fireEvent.change(screen.getByTestId("input-chat"), {
      target: { value: "Q1" },
    });
    fireEvent.click(screen.getByTestId("btn-chat-send"));

    // Wait for the assistant bubble to appear so history reflects [user, assistant].
    await waitFor(() => {
      expect(screen.getByText("A1")).toBeInTheDocument();
    });

    // Turn 2.
    mockSendChat.mockResolvedValueOnce("A2");
    fireEvent.change(screen.getByTestId("input-chat"), {
      target: { value: "Q2" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("btn-chat-send"));
    });

    await waitFor(() => {
      expect(mockSendChat).toHaveBeenCalledTimes(2);
    });

    // Second invocation: build_id, message="Q2", history must contain the prior turn
    // (1 user + 1 assistant — exactly 2 entries per the spec table). The
    // history-item type now widened to a discriminated union with
    // `kind: "text" | "receipt"` per feature-explain-stat-receipt.md
    // §4 (authorized test modification). Existing prose paths emit
    // `kind: "text"` items; the receipt kind is exercised separately
    // by the receipt-dispatch test below.
    const secondCallArgs = mockSendChat.mock.calls[1]!;
    expect(secondCallArgs[0]).toBe("berkeley-cs-001");
    expect(secondCallArgs[1]).toBe("Q2");
    const history = secondCallArgs[2] as Array<{
      role: string;
      kind?: string;
      content?: string;
    }>;
    expect(history).toHaveLength(2);
    expect(history[0]).toEqual({ role: "user", kind: "text", content: "Q1" });
    expect(history[1]).toEqual({
      role: "assistant",
      kind: "text",
      content: "A1",
    });
  });

  // --- Error path (defensive) ---

  it("surfaces an error when sendChat rejects (saboteur: API down)", async () => {
    mockSendChat.mockRejectedValue(new Error("Gemma is napping"));

    render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);

    fireEvent.change(screen.getByTestId("input-chat"), {
      target: { value: "anything" },
    });
    fireEvent.click(screen.getByTestId("btn-chat-send"));

    await waitFor(() => {
      expect(screen.getByText("Gemma is napping")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Ask Gemma — scope-aware path (docs/specs/feature-ask-gemma.md §4 P0).
  // ===========================================================================

  describe("scope prop routes to askGemmaStream() instead of sendChat() (P0)", () => {
    // Per Authorized Test Modifications (§4 / C7) — chat now uses the
    // streaming variant for scope-bound calls. Args: (scope, message,
    // history, onEvent, locale). The onEvent callback is fired once
    // per parsed SSE event.
    it("calls askGemmaStream with the scope when scope is set", async () => {
      const scope: AskScope = {
        kind: "stat",
        build_ids: ["berkeley-cs-001"],
        target_id: "ERN",
      };
      mockAskGemmaStream.mockImplementation(
        streamImpl([
          { type: "final_text", response: "Earnings start strong here." },
          { type: "done" },
        ]),
      );

      render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scope}
          chipText="Asking about: Earning Power"
          onClose={() => {}}
        />,
      );

      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "Why is this so low?" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      await waitFor(() => {
        expect(mockAskGemmaStream).toHaveBeenCalledTimes(1);
      });
      // sendChat and the legacy askGemma must NOT have been called when
      // scope is set — chat now uses askGemmaStream exclusively for
      // scope-bound calls.
      expect(mockSendChat).not.toHaveBeenCalled();
      expect(mockAskGemma).not.toHaveBeenCalled();

      // Args: (scope, message, history, onEvent, locale)
      const args = mockAskGemmaStream.mock.calls[0]!;
      expect(args[0]).toEqual(scope);
      expect(args[1]).toBe("Why is this so low?");
      expect(args[2]).toEqual([]);
      expect(typeof args[3]).toBe("function"); // onEvent callback
      expect(args[4]).toBe("en");

      // Render the response.
      await waitFor(() => {
        expect(screen.getByText("Earnings start strong here.")).toBeInTheDocument();
      });
    });

    it("works for compare scope without a build prop", async () => {
      const scope: AskScope = {
        kind: "compare",
        build_ids: ["berkeley-cs-001", "iu-bloom-mkt-001"],
      };
      mockAskGemmaStream.mockImplementation(
        streamImpl([
          { type: "final_text", response: "Side-by-side, the cost gap is real." },
          { type: "done" },
        ]),
      );

      // No build prop — compare scope is the only one with N>1 build_ids.
      render(
        <GemmaChat
          open={true}
          build={null}
          scope={scope}
          chipText="Comparing: UC Berkeley vs IU Bloomington"
          onClose={() => {}}
        />,
      );

      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "Which one wins on cost?" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      await waitFor(() => {
        expect(mockAskGemmaStream).toHaveBeenCalledTimes(1);
      });
      expect(mockAskGemmaStream.mock.calls[0]![0]).toEqual(scope);
    });
  });

  describe("scope chip renders per kind (P0)", () => {
    const cases: Array<{ kind: AskScope["kind"]; chipText: string; scope: AskScope }> = [
      {
        kind: "stat",
        chipText: "Asking about: AI Resilience",
        scope: { kind: "stat", build_ids: ["b1"], target_id: "RES" },
      },
      {
        kind: "boss",
        chipText: "Asking why this risk did not pass: AI",
        scope: { kind: "boss", build_ids: ["b1"], target_id: "ai" },
      },
      {
        kind: "skill",
        chipText: "Asking about: AI/ML elective track",
        scope: { kind: "skill", build_ids: ["b1"], target_id: "sk1" },
      },
      {
        kind: "build",
        chipText: "Asking about your whole build",
        scope: { kind: "build", build_ids: ["b1"] },
      },
      {
        kind: "compare",
        chipText: "Comparing: UC Berkeley vs IU Bloomington",
        scope: { kind: "compare", build_ids: ["b1", "b2"] },
      },
    ];

    it.each(cases)(
      "renders chip-chat-scope with the chip text for kind=$kind",
      ({ kind, chipText, scope }) => {
        render(
          <GemmaChat
            open={true}
            build={makeBuild()}
            scope={scope}
            chipText={chipText}
            onClose={() => {}}
          />,
        );

        const chip = screen.getByTestId("chip-chat-scope");
        expect(chip).toBeInTheDocument();
        expect(chip).toHaveTextContent(chipText);
        // The legacy "Context: …" line must not also render — the chip
        // replaces it (the spec is binding here, voice-contract aligned).
        expect(chip.textContent ?? "").not.toMatch(/^Context:/);
        // Sanity check: the chip is present for every kind.
        expect(kind).toBeTruthy();
      },
    );
  });

  // ===========================================================================
  // variant prop — feature-tree-as-map.md §4. Embedded variant for
  // /branch-tree, slide-in variant (default) for /menu and /my-build.
  // ===========================================================================

  describe("variant prop (feature-tree-as-map.md §4)", () => {
    it("test_variant_embedded_no_slide_in_no_backdrop: embedded renders inline, no dialog, no backdrop", () => {
      const scope: AskScope = {
        kind: "branch",
        build_ids: ["berkeley-cs-001"],
        target_id: "15-1252",
      };
      // Pending stream — opener fires but never resolves; we're testing
      // the non-async layout, not the response render.
      mockAskGemmaStream.mockReturnValue(new Promise(() => {}));

      const { container } = render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scope}
          chipText="branch · root"
          variant="embedded"
          openerPrompt="Tell me about my career path."
        />,
      );

      // Embedded variant uses panel-branch-chat region; slide-in uses
      // dialog-chat. The two are mutually exclusive.
      expect(screen.getByTestId("panel-branch-chat")).toBeInTheDocument();
      expect(screen.queryByTestId("dialog-chat")).toBeNull();

      // No close-button affordance in embedded mode (chat is always
      // visible, owned by the surrounding screen).
      expect(screen.queryByLabelText("Close chat")).toBeNull();

      // No backdrop element. The slide-in variant mounts a
      // ``fixed inset-0 ... bg-bp-void/60`` backdrop that the embedded
      // variant deliberately omits — the chat lives inside the page
      // grid, not over it.
      const backdrop = container.querySelector(
        "[class*='bg-bp-void/60'][class*='fixed inset-0']",
      );
      expect(backdrop).toBeNull();
    });

    it("test_variant_slide_in_default_unchanged: undefined and explicit 'slide-in' both render the legacy panel", () => {
      // Default (no variant prop).
      const { unmount: unmountA } = render(
        <GemmaChat open={true} build={makeBuild()} onClose={() => {}} />,
      );
      expect(screen.getByTestId("dialog-chat")).toBeInTheDocument();
      expect(screen.queryByTestId("panel-branch-chat")).toBeNull();
      unmountA();

      // Explicit "slide-in".
      render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          variant="slide-in"
          onClose={() => {}}
        />,
      );
      expect(screen.getByTestId("dialog-chat")).toBeInTheDocument();
      expect(screen.queryByTestId("panel-branch-chat")).toBeNull();
    });

    it("embedded variant auto-fires the opener via askGemmaStream when scope is set", async () => {
      const scope: AskScope = {
        kind: "branch",
        build_ids: ["berkeley-cs-001"],
        target_id: "15-1252",
      };
      mockAskGemmaStream.mockImplementation(
        streamImpl([
          {
            type: "final_text",
            response: "You're at the root of your career path.",
          },
          { type: "done" },
        ]),
      );

      render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scope}
          chipText="branch · root"
          variant="embedded"
          openerPrompt="Give me a 3-sentence orientation."
          skeletonHint="Gemma is reading your career path…"
        />,
      );

      await waitFor(() => {
        expect(mockAskGemmaStream).toHaveBeenCalledTimes(1);
      });
      // The opener fires with the openerPrompt as the user message and
      // empty history (this is what triggers the backend's tools-disabled
      // opener path).
      const args = mockAskGemmaStream.mock.calls[0]!;
      expect(args[0]).toEqual(scope);
      expect(args[1]).toBe("Give me a 3-sentence orientation.");
      expect(args[2]).toEqual([]);

      // The opener response renders.
      await waitFor(() => {
        expect(
          screen.getByText("You're at the root of your career path."),
        ).toBeInTheDocument();
      });
    });

    it("embedded variant: scope.target_id change re-fires the opener and clears prior history", async () => {
      const scopeRoot: AskScope = {
        kind: "branch",
        build_ids: ["berkeley-cs-001"],
        target_id: "15-1252",
      };
      const scopeBranch: AskScope = {
        kind: "branch",
        build_ids: ["berkeley-cs-001"],
        target_id: "11-3021",
      };

      mockAskGemmaStream.mockImplementationOnce(
        streamImpl([
          { type: "final_text", response: "Root opener text." },
          { type: "done" },
        ]),
      );

      const { rerender } = render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scopeRoot}
          chipText="branch · root"
          variant="embedded"
          openerPrompt="orient me"
        />,
      );
      await waitFor(() => {
        expect(mockAskGemmaStream).toHaveBeenCalledTimes(1);
      });
      await waitFor(() => {
        expect(screen.getByText("Root opener text.")).toBeInTheDocument();
      });

      // Switch branches → second opener fires; prior history clears.
      mockAskGemmaStream.mockImplementationOnce(
        streamImpl([
          { type: "final_text", response: "Manager-branch opener text." },
          { type: "done" },
        ]),
      );
      rerender(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scopeBranch}
          chipText="branch · Computer and Information Systems Managers"
          variant="embedded"
          openerPrompt="orient me on this branch"
        />,
      );

      await waitFor(() => {
        expect(mockAskGemmaStream).toHaveBeenCalledTimes(2);
      });
      await waitFor(() => {
        expect(screen.getByText("Manager-branch opener text.")).toBeInTheDocument();
      });
      // Prior-branch text is gone (history cleared on scope change).
      expect(screen.queryByText("Root opener text.")).toBeNull();
    });
  });

  describe("legacy no-scope path is unchanged (P0)", () => {
    it("calls sendChat (not askGemma) when scope is undefined", async () => {
      mockSendChat.mockResolvedValue("legacy response");

      render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);

      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "legacy question" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      await waitFor(() => {
        expect(mockSendChat).toHaveBeenCalledTimes(1);
      });
      expect(mockAskGemma).not.toHaveBeenCalled();
    });

    it("renders the legacy contextLine chip (not chip-chat-scope) when scope is undefined", () => {
      render(<GemmaChat open={true} build={makeBuild()} onClose={() => {}} />);

      // The legacy chip carries the "Context: SCHOOL · CAREER · W/L" line.
      // The new scope chip (data-testid=chip-chat-scope) must be absent.
      expect(screen.queryByTestId("chip-chat-scope")).toBeNull();
      // The legacy chip text contains the school name from the build.
      expect(screen.getByText(/UC Berkeley/)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // <GemmaTrace> integration (feature-gemma-trace.md §4 New Tests Required).
  // ===========================================================================

  describe("GemmaTrace integration", () => {
    it("test_chat_renders_trace_when_tool_calls_present", async () => {
      const scope: AskScope = {
        kind: "stat",
        build_ids: ["berkeley-cs-001"],
        target_id: "ERN",
      };
      mockAskGemmaStream.mockImplementation(
        streamImpl([
          {
            type: "turn_start",
            turn: 0,
            tool: "get_career_paths",
            args: { student_major: "Marketing" },
          },
          {
            type: "turn_complete",
            turn: 0,
            tool: "get_career_paths",
            args: { student_major: "Marketing" },
            result_preview: "ok",
            duration_ms: 87,
            error: null,
          },
          { type: "final_text", response: "Earnings start strong here." },
          { type: "done" },
        ]),
      );

      render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scope}
          chipText="Asking about: Earning Power"
          onClose={() => {}}
        />,
      );

      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "Why is this so low?" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      // The trace renders above Gemma's response message.
      await waitFor(() => {
        expect(screen.getByTestId("gemma-trace")).toBeInTheDocument();
      });
      expect(screen.getByTestId("gemma-trace-row-0")).toBeInTheDocument();
      // Pedagogical sentence from TOOL_LABEL_MAP.
      expect(
        screen.getByText(/Looking up career outcomes for Marketing/),
      ).toBeInTheDocument();
      // The chat answer also rendered.
      await waitFor(() => {
        expect(
          screen.getByText("Earnings start strong here."),
        ).toBeInTheDocument();
      });
    });

    it("test_chat_omits_trace_when_no_tool_calls", async () => {
      const scope: AskScope = {
        kind: "stat",
        build_ids: ["berkeley-cs-001"],
        target_id: "ERN",
      };
      // Stream emits only final_text + done (Gemma answered from context).
      mockAskGemmaStream.mockImplementation(
        streamImpl([
          { type: "final_text", response: "Pulled from context." },
          { type: "done" },
        ]),
      );

      render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scope}
          chipText="Asking about: Earning Power"
          onClose={() => {}}
        />,
      );

      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "anything" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      await waitFor(() => {
        expect(screen.getByText("Pulled from context.")).toBeInTheDocument();
      });
      // No trace section in the DOM.
      expect(screen.queryByTestId("gemma-trace")).toBeNull();
    });

    it("test_chat_falls_back_to_post_hoc_trace_on_stream_failure", async () => {
      const scope: AskScope = {
        kind: "stat",
        build_ids: ["berkeley-cs-001"],
        target_id: "ERN",
      };
      // Simulate the askGemmaStream fallback path by having the mock
      // synthesize the same shape it would after catching an HTTP error
      // and re-routing through askGemma. The mocked stream just emits
      // synthesized turn events as if from tool_calls.
      mockAskGemmaStream.mockImplementation(
        streamImpl([
          {
            type: "turn_start",
            turn: 0,
            tool: "get_career_paths",
            args: { student_major: "Marketing" },
          },
          {
            type: "turn_complete",
            turn: 0,
            tool: "get_career_paths",
            args: { student_major: "Marketing" },
            result_preview: "ok",
            duration_ms: 50,
            error: null,
          },
          { type: "final_text", response: "Fallback answer." },
          { type: "done" },
        ]),
      );

      render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scope}
          chipText="Asking about: Earning Power"
          onClose={() => {}}
        />,
      );

      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "anything" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      // Trace renders post-hoc (visually identical to live State 2).
      await waitFor(() => {
        expect(screen.getByTestId("gemma-trace")).toBeInTheDocument();
      });
      // Chat answer arrives. Fallback path is silent — no error toast.
      await waitFor(() => {
        expect(screen.getByText("Fallback answer.")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Explain-this-stat receipt dispatch
  // (docs/specs/feature-explain-stat-receipt.md §4 P0).
  //
  // GemmaChat's renderMessageWithTrace dispatches on `m.kind`:
  //   - kind === "receipt" → <ExplainStatReceiptCard payload={...} />
  //   - kind === "text"    → <ChatMessage message={...} />
  // The streaming path constructs the history item via
  // `assistantHistoryItem(response)`, which discriminates on whether
  // `response` is a string vs. a structured ExplainStatReceipt object.
  // ===========================================================================

  describe("ERN explain-receipt dispatch (P0)", () => {
    it("test_dispatches_receipt_to_explain_stat_component — kind:receipt → ExplainStatReceiptCard", async () => {
      const scope: AskScope = {
        kind: "stat",
        build_ids: ["berkeley-cs-001"],
        target_id: "ERN",
      };
      const receipt = {
        kind: "receipt" as const,
        stat_code: "ERN" as const,
        stat_name: "Earning Power",
        score: 7,
        score_max: 10,
        one_liner:
          "Earning Power tells you how much your degree usually pays right after graduation.",
        components: [
          {
            weight_pct: 60,
            label: "your school's program rank",
            explainer:
              "IU CS grads earn $94,200 — 87th percentile (out of 100 programs, this one ranks higher than about 86) of all CS programs.",
            value_pct: 87,
            anchor_text: "Indiana University Computer Science grads",
            anchor_dollars: 94_200,
            missing_reason: null,
          },
          {
            weight_pct: 40,
            label: "this career's pay rank",
            explainer:
              "Software Developer pays $132,270 — 92nd percentile.",
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
          "Two students at different schools — different programs, different careers, different ranks. Mixing both grounds the score in real salaries.",
      };

      // The streamImpl helper is typed for string responses only;
      // bypass it with a hand-rolled mock that emits a receipt object
      // in the final_text frame.
      mockAskGemmaStream.mockImplementation(
        async (
          _scope: unknown,
          _message: unknown,
          _history: unknown,
          onEvent: (event: unknown) => void,
        ) => {
          const finalEv = { type: "final_text", response: receipt };
          const doneEv = { type: "done" };
          onEvent(finalEv);
          onEvent(doneEv);
          return { response: receipt, events: [finalEv, doneEv] };
        },
      );

      render(
        <GemmaChat
          open={true}
          build={makeBuild()}
          scope={scope}
          chipText="Asking about: Earning Power"
          onClose={() => {}}
        />,
      );

      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "[explain-this:ERN]" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));

      // The receipt card mounts (data-testid from
      // ExplainStatReceipt.tsx). Prose renderer must NOT have rendered
      // the receipt object's stringification.
      await waitFor(() => {
        expect(
          screen.getByTestId("explain-stat-receipt"),
        ).toBeInTheDocument();
      });
      // Math card from the receipt component renders the server-built
      // arithmetic — proof that the structured payload reached the
      // dedicated renderer, not the prose path.
      expect(screen.getByTestId("receipt-math-line")).toHaveTextContent(
        "0.6 × 0.87 + 0.4 × 0.92 → score 9/10",
      );
      // Sanity: the prose-render fallback `[object Object]` MUST NOT
      // appear anywhere — that would mean the receipt was stringified.
      expect(screen.queryByText(/\[object Object\]/)).toBeNull();
    });
  });

  // ===========================================================================
  // feature-career-description-on-pdf.md §4 New Tests Required (P1):
  // career-scope renders a structured "About this career" header card.
  // ===========================================================================

  describe("careerDescription prop renders header card (P1)", () => {
    type CareerDesc = {
      soc_code: string;
      summary: string;
      tasks: string[];
      anchor_tier: "activities" | "description_only" | "title_only";
      generated_at: string;
      model: string;
    };

    function makeCareerDesc(overrides: Partial<CareerDesc> = {}): CareerDesc {
      return {
        soc_code: "13-2051",
        summary:
          "Financial analysts study filings and market data to guide investment decisions.",
        tasks: [
          "Analyze company filings",
          "Assemble valuation models",
          "Brief portfolio managers",
          "Track recommendations and feed lessons back",
        ],
        anchor_tier: "activities",
        generated_at: "2026-05-07T00:00:00+00:00",
        model: "gemma-4-26b-a4b-it",
        ...overrides,
      };
    }

    const careerScope = {
      kind: "career" as const,
      build_ids: [] as [],
      target_id: "13-2051",
    };

    it("career_scope_renders_header_card — populated description renders title, summary, tasks", () => {
      const desc = makeCareerDesc();
      render(
        <GemmaChat
          open={true}
          build={null}
          scope={careerScope}
          chipText="Asking about: Financial and Investment Analysts"
          onClose={() => {}}
          careerDescription={desc}
        />,
      );

      // Header card is mounted.
      expect(screen.getByTestId("card-career-description")).toBeInTheDocument();
      // SOC chip rendered with the SOC code from the scope.
      expect(screen.getByTestId("career-desc-soc")).toHaveTextContent("13-2051");
      // Summary content present.
      expect(
        screen.getByText(
          /Financial analysts study filings and market data/i,
        ),
      ).toBeInTheDocument();
      // Tasks list rendered with all 4 task strings.
      const tasksList = screen.getByTestId("career-desc-tasks");
      expect(tasksList).toBeInTheDocument();
      for (const task of desc.tasks) {
        expect(tasksList).toHaveTextContent(task);
      }
      // Tier A → no disclaimer chip.
      expect(screen.queryByTestId("career-desc-disclaimer")).toBeNull();
    });

    it("career_scope_renders_skeleton_then_content — loading shows skeleton, populated shows content", () => {
      // First render: loading sentinel → skeleton (no real summary text).
      const { rerender } = render(
        <GemmaChat
          open={true}
          build={null}
          scope={careerScope}
          chipText="Asking about: Financial and Investment Analysts"
          onClose={() => {}}
          careerDescription="loading"
        />,
      );
      // Skeleton card mounts with the same testid.
      const loadingCard = screen.getByTestId("card-career-description");
      expect(loadingCard).toBeInTheDocument();
      // a11y attribute present in the loading state.
      expect(loadingCard).toHaveAttribute("role", "status");
      expect(loadingCard).toHaveAttribute("aria-live", "polite");
      // No summary text yet — that lives only in the populated branch.
      expect(
        screen.queryByText(/Financial analysts study filings/i),
      ).toBeNull();

      // Second render: populated → real summary appears, no longer in
      // loading state.
      const desc = makeCareerDesc();
      rerender(
        <GemmaChat
          open={true}
          build={null}
          scope={careerScope}
          chipText="Asking about: Financial and Investment Analysts"
          onClose={() => {}}
          careerDescription={desc}
        />,
      );
      const populated = screen.getByTestId("card-career-description");
      // Now the populated branch — no role="status" on the wrapper.
      expect(populated.getAttribute("role")).toBeNull();
      expect(
        screen.getByText(/Financial analysts study filings/i),
      ).toBeInTheDocument();
    });

    it("career_scope_handles_fetch_error — error sentinel omits the card; freeform chat still works", async () => {
      mockAskGemmaStream.mockImplementation(
        streamImpl([
          { type: "final_text", response: "Talking around the missing card." },
          { type: "done" },
        ]),
      );

      render(
        <GemmaChat
          open={true}
          build={null}
          scope={careerScope}
          chipText="Asking about: Financial and Investment Analysts"
          onClose={() => {}}
          careerDescription="error"
        />,
      );

      // Card omitted on error — neither populated nor loading state renders.
      expect(screen.queryByTestId("card-career-description")).toBeNull();

      // Freeform chat input still mounts and the send path still dispatches.
      fireEvent.change(screen.getByTestId("input-chat"), {
        target: { value: "What does an analyst actually do?" },
      });
      fireEvent.click(screen.getByTestId("btn-chat-send"));
      await waitFor(() => {
        expect(mockAskGemmaStream).toHaveBeenCalledTimes(1);
      });
      // Response renders.
      await waitFor(() => {
        expect(
          screen.getByText("Talking around the missing card."),
        ).toBeInTheDocument();
      });
    });
  });
});
