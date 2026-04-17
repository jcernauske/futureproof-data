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
import type { BuildSummary } from "@/api/menu";

const mockSendChat = vi.fn();
vi.mock("@/api/menu", async () => {
  const actual =
    await vi.importActual<typeof import("@/api/menu")>("@/api/menu");
  return {
    ...actual,
    sendChat: (...args: unknown[]) => mockSendChat(...args),
  };
});

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
    hmn: 5,
    wins: 4,
    losses: 0,
    draws: 1,
    profile_name: "Wandering Otter",
    ...overrides,
  };
}

beforeEach(() => {
  mockSendChat.mockReset();
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
    expect(input.value).toBe("What internships should I look for?");
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
    // (1 user + 1 assistant — exactly 2 entries per the spec table).
    const secondCallArgs = mockSendChat.mock.calls[1]!;
    expect(secondCallArgs[0]).toBe("berkeley-cs-001");
    expect(secondCallArgs[1]).toBe("Q2");
    const history = secondCallArgs[2] as Array<{ role: string; content: string }>;
    expect(history).toHaveLength(2);
    expect(history[0]).toEqual({ role: "user", content: "Q1" });
    expect(history[1]).toEqual({ role: "assistant", content: "A1" });
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
});
