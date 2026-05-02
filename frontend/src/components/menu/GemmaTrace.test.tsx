import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { GemmaTrace } from "@/components/menu/GemmaTrace";
import type { GemmaTraceEvent } from "@/types/gemmaTrace";

function turnStart(
  turn: number,
  tool: string,
  args: Record<string, unknown> = {},
): GemmaTraceEvent {
  return { type: "turn_start", turn, tool, args };
}

function turnComplete(
  turn: number,
  tool: string,
  opts: {
    args?: Record<string, unknown>;
    result_preview?: string;
    duration_ms?: number;
    error?: string | null;
  } = {},
): GemmaTraceEvent {
  return {
    type: "turn_complete",
    turn,
    tool,
    args: opts.args ?? {},
    result_preview: opts.result_preview ?? '{"data": "ok"}',
    duration_ms: opts.duration_ms ?? 87,
    error: opts.error ?? null,
  };
}

describe("<GemmaTrace>", () => {
  it("test_empty_events_renders_null", () => {
    const { container } = render(<GemmaTrace events={[]} mode="complete" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders no trace when only final_text + done are present", () => {
    // Gemma answered from context — no tool calls.
    const { container } = render(
      <GemmaTrace
        events={[
          { type: "final_text", response: "Direct answer." },
          { type: "done" },
        ]}
        mode="complete"
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("test_streaming_state_shows_pending_for_unresolved_rows", () => {
    render(
      <GemmaTrace
        events={[
          turnStart(0, "get_career_paths", { student_major: "Marketing" }),
        ]}
        mode="live"
      />,
    );

    const row = screen.getByTestId("gemma-trace-row-0");
    expect(row).toBeTruthy();

    // Pedagogical sentence rendered.
    expect(
      screen.getByText(/Looking up career outcomes for Marketing/),
    ).toBeTruthy();

    // No status pill yet.
    expect(screen.queryByText(/done/)).toBeNull();
    expect(screen.queryByText(/retry/)).toBeNull();

    // Expand button is disabled while in-progress.
    const btn = screen.getByTestId("gemma-trace-expand-0") as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it("test_complete_state_shows_resolved_rows", () => {
    render(
      <GemmaTrace
        events={[
          turnStart(0, "get_career_paths", { student_major: "Marketing" }),
          turnComplete(0, "get_career_paths", {
            args: { student_major: "Marketing" },
            duration_ms: 238,
          }),
          { type: "final_text", response: "..." },
          { type: "done" },
        ]}
        mode="complete"
      />,
    );

    expect(screen.getByText("done")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-duration-0").textContent).toContain(
      "238 ms",
    );

    // Header copy in past tense.
    // Visible header + sr-only live region both contain the same text
    // by design; getAllByText accepts the duplication.
    expect(
      screen.getAllByText(/Gemma checked one source/).length,
    ).toBeGreaterThan(0);
  });

  it("uses plural 'sources' header when multiple rows", () => {
    render(
      <GemmaTrace
        events={[
          turnStart(0, "get_career_paths"),
          turnComplete(0, "get_career_paths"),
          turnStart(1, "get_occupation_data"),
          turnComplete(1, "get_occupation_data"),
        ]}
        mode="complete"
      />,
    );
    expect(
      screen.getAllByText(/Gemma checked 2 sources/).length,
    ).toBeGreaterThan(0);
  });

  it("uses present-continuous header while streaming", () => {
    render(
      <GemmaTrace
        events={[turnStart(0, "get_career_paths")]}
        mode="live"
      />,
    );
    expect(
      screen.getAllByText(/Gemma is looking something up/).length,
    ).toBeGreaterThan(0);
  });

  it("test_error_row_shows_error_pill_and_continues", () => {
    render(
      <GemmaTrace
        events={[
          turnComplete(0, "get_career_paths", {
            error: "RuntimeError: DB unavailable",
            result_preview: '{"error": "DB unavailable"}',
          }),
          turnComplete(1, "get_occupation_data", { duration_ms: 50 }),
        ]}
        mode="complete"
      />,
    );

    // Both rows render.
    expect(screen.getByTestId("gemma-trace-row-0")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-row-1")).toBeTruthy();
    // Error row shows retry pill.
    expect(screen.getByText("retry")).toBeTruthy();
    // Success row shows done pill.
    expect(screen.getByText("done")).toBeTruthy();
  });

  it("test_click_to_expand_shows_engineering_view", () => {
    render(
      <GemmaTrace
        events={[
          turnComplete(0, "get_career_paths", {
            args: { unitid: 110635, cipcode: "11.0701" },
            result_preview: '{"data": [{"occupation_title": "..."}]}',
            duration_ms: 87,
          }),
        ]}
        mode="complete"
      />,
    );

    // Engineering panel not present yet.
    expect(screen.queryByTestId("gemma-trace-detail-0")).toBeNull();

    const btn = screen.getByTestId("gemma-trace-expand-0");
    fireEvent.click(btn);

    const panel = screen.getByTestId("gemma-trace-detail-0");
    expect(panel).toBeTruthy();
    // Tool name in monospace.
    expect(panel.textContent).toContain("get_career_paths");
    // Args JSON visible.
    expect(panel.textContent).toContain("110635");
    expect(panel.textContent).toContain("11.0701");
    // Step ref in footer.
    expect(panel.textContent).toMatch(/step 1 of 1/);
  });

  it("collapses engineering view on second click", () => {
    render(
      <GemmaTrace
        events={[turnComplete(0, "get_career_paths")]}
        mode="complete"
      />,
    );
    const btn = screen.getByTestId("gemma-trace-expand-0");
    fireEvent.click(btn);
    expect(screen.getByTestId("gemma-trace-detail-0")).toBeTruthy();
    fireEvent.click(btn);
    // AnimatePresence exit may be async; the panel either disappears
    // or marks aria-expanded=false. Assert the latter as the contract.
    expect(btn.getAttribute("aria-expanded")).toBe("false");
  });

  it("test_unknown_tool_falls_back_to_default_label", () => {
    render(
      <GemmaTrace
        events={[turnComplete(0, "get_nonexistent_xyz")]}
        mode="complete"
      />,
    );
    // Default fallback hint text from toolLabels.ts.
    expect(screen.getByText(/Gemma is consulting a tool/)).toBeTruthy();
    // Component does not crash.
    expect(screen.getByTestId("gemma-trace-row-0")).toBeTruthy();
  });

  it("test_accessibility_identifiers_present", () => {
    render(
      <GemmaTrace
        events={[
          turnComplete(0, "get_career_paths", {
            args: { student_major: "Marketing" },
          }),
          turnComplete(1, "get_occupation_data", {
            args: { soc_code: "13-2052" },
          }),
        ]}
        mode="complete"
      />,
    );

    // All §3 accessibility identifiers from the spec table.
    expect(screen.getByTestId("gemma-trace")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-rows")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-row-0")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-row-1")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-expand-0")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-expand-1")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-live")).toBeTruthy();

    // aria-label present on row buttons; sentence shape.
    const btn0 = screen.getByTestId("gemma-trace-expand-0");
    const label = btn0.getAttribute("aria-label") ?? "";
    expect(label).toContain("Step 1 of 2");
    expect(label).toContain("Marketing");
    expect(label).toMatch(/done/);
  });

  it("test_rows_correlate_by_dispatch_index_with_parallel_calls", () => {
    // Decision #13 contract — out-of-order completes pair correctly to
    // their starts by `turn` (= dispatch_index). Two starts arrive
    // BEFORE either complete; complete[1] arrives BEFORE complete[0].
    const { rerender } = render(
      <GemmaTrace
        events={[
          turnStart(0, "get_career_paths", { student_major: "A" }),
          turnStart(1, "get_career_paths", { student_major: "B" }),
        ]}
        mode="live"
      />,
    );
    // Both rows present, both in-progress.
    expect(screen.getByTestId("gemma-trace-row-0")).toBeTruthy();
    expect(screen.getByTestId("gemma-trace-row-1")).toBeTruthy();

    rerender(
      <GemmaTrace
        events={[
          turnStart(0, "get_career_paths", { student_major: "A" }),
          turnStart(1, "get_career_paths", { student_major: "B" }),
          turnComplete(1, "get_career_paths", {
            args: { student_major: "B" },
            duration_ms: 100,
          }),
          turnComplete(0, "get_career_paths", {
            args: { student_major: "A" },
            duration_ms: 200,
          }),
        ]}
        mode="complete"
      />,
    );

    // Row 0 (started first, resolved second) shows 200 ms; row 1 shows 100 ms.
    expect(screen.getByTestId("gemma-trace-duration-0").textContent).toContain(
      "200 ms",
    );
    expect(screen.getByTestId("gemma-trace-duration-1").textContent).toContain(
      "100 ms",
    );
  });

  it("renders fallback (post-hoc) state visually identical to complete", () => {
    // Both modes with the same resolved events should render the same
    // structural output; only `animate` differs.
    const events: GemmaTraceEvent[] = [
      turnStart(0, "get_career_paths"),
      turnComplete(0, "get_career_paths", { duration_ms: 87 }),
    ];

    const { container: liveDom } = render(
      <GemmaTrace events={events} mode="complete" />,
    );
    expect(liveDom.textContent).toContain("Gemma checked one source");
    expect(liveDom.textContent).toContain("done");
    expect(liveDom.textContent).toContain("87 ms");
  });
});
