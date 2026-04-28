/**
 * useSetYourCourse.test.ts
 *
 * Covers the P0 contracts of the unified Set Your Course screen hook:
 *   - Debounced resolution: rapid keystrokes fire exactly one stream.
 *   - In-flight cancellation: a mid-stream edit aborts the prior
 *     controller.
 *   - Chip dispatch: not_expected opens the clarifier surface and, on
 *     submit, calls dispatchChip; show_less_common toggles state with
 *     NO network call; change_major resets the major field with NO
 *     network call.
 *   - Commit: correction payload is sent when current ≠ initial;
 *     commit still goes through (with or without the log) when the
 *     resolution is unchanged.
 *   - Confirmed focus persistence across chip response + clearing on
 *     major edit (P1).
 *
 * Every test mocks @/api/intent and @/api/build so no fetch escapes
 * the test process.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import React from "react";

import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import type { IntentResult } from "@/types/buildInput";
import type { StreamEvent } from "@/api/intent";

// ---------------------------------------------------------------------------
// Module mocks — every fetch path is stubbed.
// ---------------------------------------------------------------------------

vi.mock("@/api/intent", () => ({
  streamIntent: vi.fn(),
  dispatchChip: vi.fn(),
  commitResolution: vi.fn(),
}));
vi.mock("@/api/build", () => ({
  getOutcomes: vi.fn(),
  getTieredCareers: vi.fn(),
}));

import { streamIntent, dispatchChip, commitResolution } from "@/api/intent";
import { getOutcomes } from "@/api/build";
import { useSetYourCourse } from "./useSetYourCourse";
import type { CareerOutcome } from "@/types/build";

const CAREER_FETCH_DEBOUNCE_MS = 250;

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function wrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(MemoryRouter, null, children);
}

function makeResolution(overrides: Partial<IntentResult> = {}): IntentResult {
  return {
    matched_cip: "52.1401",
    matched_title: "Marketing",
    confidence: "high",
    reasoning: "Marketing maps to 52.1401.",
    careers_preview: ["Marketing Manager"],
    audit_flag: null,
    audit_message: null,
    needs_clarification: false,
    alternatives: [],
    parent_cip: "",
    confirmed_focus: null,
    ...overrides,
  };
}

/**
 * Build a streamIntent mock that yields the given events. Returns the
 * async-generator factory that the hook awaits on.
 */
function stubStream(events: StreamEvent[]) {
  return vi.fn(async function* (): AsyncGenerator<StreamEvent, void, unknown> {
    for (const ev of events) {
      yield ev;
    }
  });
}

function seedSchool() {
  useBuildInputStore.setState({
    phase: "major",
    school: {
      unitid: 151351,
      name: "Indiana University",
      institutionControl: null,
      stateAbbr: "IN",
      netPriceAnnual: null,
      costOfAttendanceAnnual: null,
      tuitionInState: null,
      tuitionOutOfState: null,
    },
    programs: [
      {
        unitid: 151351,
        institution_name: "Indiana University",
        cipcode: "52.14",
        program_name: "Marketing",
        cip_family_name: "Business",
        earnings_1yr_median: null,
        debt_median: null,
      },
    ],
    major: null,
    effort: { level: "balanced", percentile: 50, ernShift: 0 },
    loans: { percentage: 50 },
    initialResolution: null,
    currentResolution: null,
    hasCorrected: false,
    debugTrace: null,
  });
}

function makeOutcome(overrides: Partial<CareerOutcome> = {}): CareerOutcome {
  return {
    unitid: 151351,
    institution_name: "Indiana University",
    cipcode: "52.14",
    program_name: "Marketing",
    soc_code: "11-2021",
    occupation_title: "Marketing Manager",
    soc_major_group_name: "Management",
    median_annual_wage: 133380,
    earnings_1yr_median: 55000,
    earnings_1yr_p25: 42000,
    earnings_1yr_p75: 68000,
    debt_median: 24000,
    debt_to_earnings_annual: 0.44,
    education_level_name: "Bachelor's degree",
    growth_category: "Average",
    net_price_annual: 18000,
    cost_of_attendance_annual: 26000,
    modeled_total_debt: 72000,
    debt_median_reference: 24000,
    institution_control: "Public",
    tuition_in_state: 10000,
    tuition_out_of_state: 22000,
    room_board_on_campus: 11000,
    stats: { ern: 4, roi: 3, res: 3, grw: 3, hmn: 3 },
    bosses: { ai: 2, loans: 1, market: 2, burnout: 2, ceiling: 2 },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: 5,
    overall_confidence: "high",
    match_quality: null,
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    is_out_of_state: false,
    loan_pct: 0.5,
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function seedResolution() {
  useBuildInputStore.setState({
    initialResolution: makeResolution(),
    currentResolution: makeResolution(),
  });
}

beforeEach(() => {
  mockNavigate.mockReset();
  vi.mocked(streamIntent).mockReset();
  vi.mocked(dispatchChip).mockReset();
  vi.mocked(commitResolution).mockReset();
  vi.mocked(getOutcomes).mockReset().mockResolvedValue([]);
  useBuildStore.setState({
    selectedCareer: null,
  });
  seedSchool();
});

afterEach(() => {
  vi.useRealTimers();
});

// ---------------------------------------------------------------------------
// TestDebounce
// ---------------------------------------------------------------------------

describe("TestDebounce", () => {
  it("debounces_major_input — rapid keystrokes produce one resolution call after settle", async () => {
    vi.useFakeTimers();
    const mock = stubStream([
      { type: "delta", text: "Marketing." },
      { type: "structured", result: makeResolution() },
      { type: "suggestions", suggestions: [] },
      { type: "done" },
    ]);
    vi.mocked(streamIntent).mockImplementation(mock);

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    act(() => {
      result.current.resolve("m");
      result.current.resolve("ma");
      result.current.resolve("mar");
      result.current.resolve("mark");
      result.current.resolve("marketing");
    });
    // Nothing has fired yet — still inside the 300ms debounce window.
    expect(streamIntent).toHaveBeenCalledTimes(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(305);
    });

    // Exactly one request fired, with the final (most recent) value.
    expect(streamIntent).toHaveBeenCalledTimes(1);
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    const firstCallArgs = vi.mocked(streamIntent).mock.calls[0]![0];
    expect(firstCallArgs.majorText).toBe("marketing");
  });

  it("cancels_in_flight_on_edit — editing mid-stream aborts the prior request", async () => {
    vi.useFakeTimers();
    // First stream: yields one delta and then hangs until aborted.
    const abortSignalsSeen: Array<AbortSignal | undefined> = [];
    let firstStreamAborted = false;
    const firstStream = vi.fn(async function* (args: { signal?: AbortSignal }): AsyncGenerator<StreamEvent, void, unknown> {
      abortSignalsSeen.push(args.signal);
      yield { type: "delta" as const, text: "Still thinking..." };
      // Wait for the signal to abort; never resolve the structured event.
      await new Promise<void>((resolve) => {
        args.signal?.addEventListener("abort", () => {
          firstStreamAborted = true;
          resolve();
        });
        // Safety net so the test never hangs even if abort misfires.
        setTimeout(resolve, 5000);
      });
    });
    const secondStream = stubStream([
      { type: "delta", text: "Biology." },
      {
        type: "structured",
        result: makeResolution({
          matched_cip: "26.0101",
          matched_title: "Biology",
        }),
      },
      { type: "suggestions", suggestions: [] },
      { type: "done" },
    ]);
    vi.mocked(streamIntent)
      .mockImplementationOnce(firstStream)
      .mockImplementationOnce(secondStream);

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    // First keystroke → first debounce.
    act(() => {
      result.current.resolve("marketing");
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(305);
    });
    // First request in flight.
    expect(streamIntent).toHaveBeenCalledTimes(1);

    // Mid-stream edit → must abort the first controller + schedule a
    // second debounced call.
    act(() => {
      result.current.resolve("biology");
    });
    // Abort is synchronous (the hook calls abortRef.current.abort() on
    // the new resolve).
    expect(firstStreamAborted).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(305);
    });
    // The second request fired AFTER the debounce window elapsed.
    expect(streamIntent).toHaveBeenCalledTimes(2);
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    const secondArgs = vi.mocked(streamIntent).mock.calls[1]![0];
    expect(secondArgs.majorText).toBe("biology");
    // Each request carries its own AbortSignal.
    expect(abortSignalsSeen[0]).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// TestChip
// ---------------------------------------------------------------------------

describe("TestChip", () => {
  it("not_expected_opens_clarifier_then_dispatches — the Gemma-heavy chip calls /intent/chip with clarifier", async () => {
    // Seed initial + current resolutions so the chip path has context.
    useBuildInputStore.setState({
      initialResolution: makeResolution(),
      currentResolution: makeResolution(),
    });
    vi.mocked(dispatchChip).mockResolvedValue({
      debug_trace: "trace",
      updated_resolution: null,
      cta_link: null,
      bucket: "no_issue_found",
      confirmed_focus: null,
    });

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    await act(async () => {
      await result.current.onChip(
        "not_expected",
        "I wanted marketing-manager jobs, not general business.",
      );
    });

    expect(dispatchChip).toHaveBeenCalledTimes(1);
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    const args = vi.mocked(dispatchChip).mock.calls[0]![0];
    expect(args.chipId).toBe("not_expected");
    expect(args.clarifier).toBe(
      "I wanted marketing-manager jobs, not general business.",
    );
    // lastClarifier surfaced on the hook state for the commit payload.
    expect(result.current.lastClarifier).toBe(
      "I wanted marketing-manager jobs, not general business.",
    );
    // chipsTapped records the tap for the commit payload.
    expect(result.current.chipsTapped).toEqual(["not_expected"]);
  });

  it("updated_resolution_replaces_current — a chip response with updated_resolution swaps currentResolution in the store", async () => {
    const initial = makeResolution();
    useBuildInputStore.setState({
      initialResolution: initial,
      currentResolution: initial,
    });
    const replacement = makeResolution({
      matched_cip: "51.3801",
      matched_title: "Nursing",
      confidence: "high",
    });
    vi.mocked(dispatchChip).mockResolvedValue({
      debug_trace: "re-resolving",
      updated_resolution: replacement,
      cta_link: null,
      bucket: "semantic_drift",
      confirmed_focus: null,
    });

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });
    await act(async () => {
      await result.current.onChip("not_expected", "nursing please");
    });

    const state = useBuildInputStore.getState();
    expect(state.currentResolution?.matched_cip).toBe("51.3801");
    expect(state.currentResolution?.matched_title).toBe("Nursing");
    // Initial is untouched (this is the correction record's baseline).
    expect(state.initialResolution?.matched_cip).toBe("52.1401");
    expect(state.hasCorrected).toBe(true);
  });

  it("show_less_common_toggles_tiers_no_fetch — chip tap mutates local state only", async () => {
    useBuildInputStore.setState({
      initialResolution: makeResolution(),
      currentResolution: makeResolution(),
    });
    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    expect(result.current.showLessCommon).toBe(false);
    await act(async () => {
      await result.current.onChip("show_less_common");
    });

    expect(dispatchChip).not.toHaveBeenCalled();
    expect(streamIntent).not.toHaveBeenCalled();
    expect(result.current.showLessCommon).toBe(true);

    // Toggling again flips it back.
    await act(async () => {
      await result.current.onChip("show_less_common");
    });
    expect(result.current.showLessCommon).toBe(false);
    expect(dispatchChip).not.toHaveBeenCalled();
  });

  it("change_major_resets_major_field — chip tap clears the major input with NO network request", async () => {
    useBuildInputStore.setState({
      initialResolution: makeResolution(),
      currentResolution: makeResolution(),
      major: {
        cipCode: "52.1401",
        cipTitle: "Marketing",
        rawText: "marketing",
        careersPreview: [],
        substitutionApplied: false,
        parentCip: "",
      },
    });
    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    await act(async () => {
      await result.current.onChip("change_major");
    });

    expect(dispatchChip).not.toHaveBeenCalled();
    expect(streamIntent).not.toHaveBeenCalled();

    const state = useBuildInputStore.getState();
    expect(state.major).toBeNull();
    expect(state.currentResolution).toBeNull();
    expect(state.initialResolution).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// TestCommit
// ---------------------------------------------------------------------------

describe("TestCommit", () => {
  it("commits_and_logs_correction_when_resolved_cip_changed — current ≠ initial sends the correction payload", async () => {
    const initial = makeResolution({
      matched_cip: "52.0201",
      matched_title: "Business",
    });
    const current = makeResolution({
      matched_cip: "52.1401",
      matched_title: "Marketing",
    });
    useBuildInputStore.setState({
      initialResolution: initial,
      currentResolution: current,
      major: {
        cipCode: "52.0201",
        cipTitle: "Business",
        rawText: "marketing",
        careersPreview: [],
        substitutionApplied: false,
        parentCip: "",
      },
    });
    vi.mocked(commitResolution).mockResolvedValue({
      committed: true,
      logged: true,
    });

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });
    await act(async () => {
      await result.current.commit();
    });

    expect(commitResolution).toHaveBeenCalledTimes(1);
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    const args = vi.mocked(commitResolution).mock.calls[0]![0];
    expect(args.currentResolution.matched_cip).toBe("52.1401");
    expect(args.initialResolution.matched_cip).toBe("52.0201");
    expect(args.inputNormalized).toBe("marketing");
    expect(args.schoolName).toBe("Indiana University");
    expect(args.unitid).toBe(151351);
    expect(mockNavigate).toHaveBeenCalledWith("/my-build");
  });

  it("commits_without_correction_when_resolution_unchanged — current == initial still commits (backend no-ops the log)", async () => {
    // When current == initial, the backend's record_commit returns
    // logged=False (no correction learned). The hook still calls
    // commitResolution and still navigates — the log decision is
    // server-side.
    const shared = makeResolution();
    useBuildInputStore.setState({
      initialResolution: shared,
      currentResolution: shared,
      major: {
        cipCode: shared.matched_cip,
        cipTitle: shared.matched_title,
        rawText: "marketing",
        careersPreview: [],
        substitutionApplied: false,
        parentCip: "",
      },
    });
    vi.mocked(commitResolution).mockResolvedValue({
      committed: true,
      logged: false,
    });

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });
    await act(async () => {
      await result.current.commit();
    });

    expect(commitResolution).toHaveBeenCalledTimes(1);
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    const args = vi.mocked(commitResolution).mock.calls[0]![0];
    expect(args.currentResolution.matched_cip).toBe(
      args.initialResolution.matched_cip,
    );
    expect(mockNavigate).toHaveBeenCalledWith("/my-build");
  });
});

// ---------------------------------------------------------------------------
// TestConfirmedFocus (P1)
// ---------------------------------------------------------------------------

describe("TestConfirmedFocus", () => {
  it("confirmed_focus_persists_on_resolution_state — chip response with confirmed_focus updates currentResolution.confirmed_focus", async () => {
    useBuildInputStore.setState({
      initialResolution: makeResolution(),
      currentResolution: makeResolution(),
    });
    vi.mocked(dispatchChip).mockResolvedValue({
      debug_trace: "confirmed sub-focus",
      updated_resolution: null,
      cta_link: null,
      bucket: "crosswalk_mismatch",
      confirmed_focus: "Deaf Education",
    });

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });
    await act(async () => {
      await result.current.onChip("not_expected", "deaf ed please");
    });

    const state = useBuildInputStore.getState();
    expect(state.currentResolution?.confirmed_focus).toBe("Deaf Education");
  });

  it("major_edit_clears_confirmed_focus — re-resolving from a new major input drops any prior sub-focus", async () => {
    // NB: don't use fake timers + waitFor in the same test — waitFor
    // schedules retry via real setTimeout, which never fires when fake
    // timers are active. Use real timers and wait past the 300ms
    // debounce organically.
    // Prime the store with a prior confirmed_focus.
    useBuildInputStore.setState({
      initialResolution: makeResolution({ confirmed_focus: null }),
      currentResolution: makeResolution({ confirmed_focus: "Deaf Education" }),
    });
    const mock = stubStream([
      { type: "delta", text: "Biology." },
      {
        type: "structured",
        result: makeResolution({
          matched_cip: "26.0101",
          matched_title: "Biology",
          confirmed_focus: null,
        }),
      },
      { type: "suggestions", suggestions: [] },
      { type: "done" },
    ]);
    vi.mocked(streamIntent).mockImplementation(mock);

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });
    act(() => {
      result.current.resolve("biology");
    });

    await waitFor(
      () => {
        const state = useBuildInputStore.getState();
        expect(state.currentResolution?.matched_title).toBe("Biology");
      },
      { timeout: 2000 },
    );
    const finalState = useBuildInputStore.getState();
    // New resolution replaces the prior currentResolution entirely —
    // the old sub-focus cannot survive a topic change.
    expect(finalState.currentResolution?.confirmed_focus).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// TestSocRevealStateMachine (P0)
// ---------------------------------------------------------------------------

describe("TestSocRevealStateMachine", () => {
  it("socReveal transitions idle -> outcomes-loading -> outcomes-loaded", async () => {
    vi.useFakeTimers();
    seedResolution();
    const outcomes = [makeOutcome()];

    const outcomesDef = deferred<CareerOutcome[]>();
    vi.mocked(getOutcomes).mockReturnValue(outcomesDef.promise);

    const { result } = renderHook(() => useSetYourCourse("marketing"), { wrapper });

    expect(result.current.socReveal.kind).toBe("idle");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });
    expect(result.current.socReveal.kind).toBe("outcomes-loading");

    await act(async () => {
      outcomesDef.resolve(outcomes);
      await Promise.resolve();
    });
    // Flush React state updates.
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.socReveal.kind).toBe("outcomes-loaded");
    if (result.current.socReveal.kind === "outcomes-loaded") {
      expect(result.current.socReveal.outcomes).toHaveLength(1);
    }
  });

  it("cache hit from prior CIP skips loading state", async () => {
    vi.useFakeTimers();
    seedResolution();
    const outcomes1 = [makeOutcome({ soc_code: "11-2021" })];

    const outcomesDef1 = deferred<CareerOutcome[]>();
    vi.mocked(getOutcomes).mockReturnValueOnce(outcomesDef1.promise);

    const { result, rerender } = renderHook(
      ({ text }) => useSetYourCourse(text),
      { wrapper, initialProps: { text: "marketing" } },
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });
    expect(result.current.socReveal.kind).toBe("outcomes-loading");

    await act(async () => {
      outcomesDef1.resolve(outcomes1);
      await Promise.resolve();
    });
    await act(async () => { await Promise.resolve(); });
    expect(result.current.socReveal.kind).toBe("outcomes-loaded");

    rerender({ text: "marketing strategy" });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });
    expect(result.current.socReveal.kind).toBe("outcomes-loaded");
  });

  it("superseded outcomes request is aborted", async () => {
    vi.useFakeTimers();
    seedResolution();

    const abortSpy = vi.spyOn(AbortController.prototype, "abort");

    vi.mocked(getOutcomes).mockReturnValue(new Promise(() => {}));

    const { rerender } = renderHook(
      ({ text }) => useSetYourCourse(text),
      { wrapper, initialProps: { text: "marketing" } },
    );

    // Fire first debounce.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });
    expect(getOutcomes).toHaveBeenCalledTimes(1);
    abortSpy.mockClear();

    // Trigger second fetch.
    rerender({ text: "biology" });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });

    expect(abortSpy).toHaveBeenCalled();
    abortSpy.mockRestore();
  });

  it("keystrokes inside debounce window do not fire fetch", async () => {
    vi.useFakeTimers();
    seedResolution();

    vi.mocked(getOutcomes).mockResolvedValue([makeOutcome()]);

    const { rerender } = renderHook(
      ({ text }) => useSetYourCourse(text),
      { wrapper, initialProps: { text: "m" } },
    );

    // 5 rapid keystrokes, each before debounce fires.
    for (const char of ["ma", "mar", "mark", "marke"]) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(50);
      });
      rerender({ text: char });
    }

    // Nothing fired yet.
    expect(getOutcomes).not.toHaveBeenCalled();

    // Now let the debounce complete.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });

    expect(getOutcomes).toHaveBeenCalledTimes(1);
  });

  it("resolved CIP change fires immediately, bypassing debounce", async () => {
    vi.useFakeTimers();

    vi.mocked(getOutcomes).mockResolvedValue([makeOutcome()]);

    // Seed with one CIP, then change it.
    useBuildInputStore.setState({
      initialResolution: makeResolution({ matched_cip: "52.1401" }),
      currentResolution: makeResolution({ matched_cip: "52.1401" }),
    });

    renderHook(
      ({ text }) => useSetYourCourse(text),
      { wrapper, initialProps: { text: "marketing" } },
    );

    // Let the initial effect fire.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });
    const firstCallCount = vi.mocked(getOutcomes).mock.calls.length;

    // Change the resolved CIP — this should fire immediately.
    act(() => {
      useBuildInputStore.setState({
        currentResolution: makeResolution({
          matched_cip: "26.0101",
          matched_title: "Biology",
        }),
      });
    });

    // Do NOT advance timers — the CIP change should fire synchronously
    // via the immediateOnKeyChange override.
    await act(async () => {
      await Promise.resolve();
    });

    expect(vi.mocked(getOutcomes).mock.calls.length).toBeGreaterThan(firstCallCount);
  });
});

// ---------------------------------------------------------------------------
// TestSocRevealErrors (P1)
// ---------------------------------------------------------------------------

describe("TestSocRevealErrors", () => {
  it("error during outcomes settles state to error", async () => {
    vi.useFakeTimers();
    seedResolution();

    vi.mocked(getOutcomes).mockRejectedValue(new Error("Network failure"));

    const { result } = renderHook(() => useSetYourCourse("marketing"), { wrapper });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });
    // Flush the async rejection handler.
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.socReveal.kind).toBe("error");
    if (result.current.socReveal.kind === "error") {
      expect(result.current.socReveal.message).toBe("Network failure");
    }
  });

  it("error during outcomes fetch sets error state", async () => {
    vi.useFakeTimers();
    seedResolution();

    vi.mocked(getOutcomes).mockRejectedValue(new Error("Network failure"));

    const { result } = renderHook(() => useSetYourCourse("marketing"), { wrapper });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CAREER_FETCH_DEBOUNCE_MS + 10);
    });
    await act(async () => { await Promise.resolve(); });
    await act(async () => { await Promise.resolve(); });

    expect(result.current.socReveal.kind).toBe("error");
    if (result.current.socReveal.kind === "error") {
      expect(result.current.socReveal.message).toBe("Network failure");
    }
  });
});

// ---------------------------------------------------------------------------
// TestMultiCipPick (P1) — onPickAlternative swap behavior
// ---------------------------------------------------------------------------

describe("TestMultiCipPick", () => {
  it("pick_alternative_swaps_resolution — onPickAlternative(1) selects first alternative", async () => {
    vi.useFakeTimers();

    const resWithAlts = makeResolution({
      matched_cip: "14.0901",
      matched_title: "Computer Engineering",
      parent_cip: "14.09",
      alternatives: [
        { cip: "14.1001", title: "Electrical Engineering", why: "Circuits", parent_cip: "14.10" },
        { cip: "14.1901", title: "Mechanical Engineering", why: "Physical", parent_cip: "14.19" },
      ],
      remaining_count: 11,
      narrowing_hint: "Try civil engineering",
    });
    useBuildInputStore.setState({
      initialResolution: resWithAlts,
      currentResolution: resWithAlts,
    });

    vi.mocked(getOutcomes).mockResolvedValue([makeOutcome()]);

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    // Option index 1 = first alternative (index 0 = original primary).
    act(() => {
      result.current.onPickAlternative(1);
    });

    const state = useBuildInputStore.getState();
    expect(state.currentResolution?.matched_cip).toBe("14.1001");
    expect(state.currentResolution?.matched_title).toBe("Electrical Engineering");
    expect(state.currentResolution?.parent_cip).toBe("14.10");
  });

  it("alternatives_stay_stable — swapping does not change the alternatives array", () => {
    const resWithAlts = makeResolution({
      matched_cip: "14.0901",
      matched_title: "Computer Engineering",
      parent_cip: "14.09",
      reasoning: "Closest match for engineering.",
      alternatives: [
        { cip: "14.1001", title: "Electrical Engineering", why: "Circuits", parent_cip: "14.10" },
        { cip: "14.1901", title: "Mechanical Engineering", why: "Physical", parent_cip: "14.19" },
      ],
    });
    useBuildInputStore.setState({
      initialResolution: resWithAlts,
      currentResolution: resWithAlts,
    });

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    act(() => {
      result.current.onPickAlternative(1);
    });

    const state = useBuildInputStore.getState();
    const alts = state.currentResolution?.alternatives;
    expect(alts).not.toBeNull();
    expect(alts!.length).toBe(2);
    // Alternatives array is unchanged — same CIPs in same order.
    expect(alts?.[0]?.cip).toBe("14.1001");
    expect(alts?.[1]?.cip).toBe("14.1901");
  });

  it("pick_original_primary — onPickAlternative(0) restores original primary", () => {
    const resWithAlts = makeResolution({
      matched_cip: "14.0901",
      matched_title: "Computer Engineering",
      parent_cip: "14.09",
      alternatives: [
        { cip: "14.1001", title: "Electrical Engineering", why: "Circuits", parent_cip: "14.10" },
      ],
    });
    useBuildInputStore.setState({
      initialResolution: resWithAlts,
      currentResolution: resWithAlts,
    });

    const { result } = renderHook(() => useSetYourCourse(), { wrapper });

    // First swap to alt.
    act(() => { result.current.onPickAlternative(1); });
    expect(useBuildInputStore.getState().currentResolution?.matched_cip).toBe("14.1001");

    // Now pick index 0 to go back to original primary.
    act(() => { result.current.onPickAlternative(0); });
    expect(useBuildInputStore.getState().currentResolution?.matched_cip).toBe("14.0901");
    expect(useBuildInputStore.getState().currentResolution?.matched_title).toBe("Computer Engineering");
  });
});
