import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useBuildInputStore } from "@/store/buildInputStore";
import { useBuildStore } from "@/store/buildStore";
import {
  commitResolution,
  dispatchChip,
  streamIntent,
  type ChipId,
  type FeasibilityMode,
} from "@/api/intent";
import type { IntentResult, Suggestion } from "@/types/buildInput";

const MAJOR_DEBOUNCE_MS = 300;

interface CommittedClick {
  soc: string | null;
  title: string | null;
  feasibility: FeasibilityMode | null;
}

interface UseSetYourCourseApi {
  /** Trigger a debounced resolution for a new major string. */
  resolve: (majorText: string) => void;
  /** Dispatch one of the three correction chips. */
  onChip: (chipId: ChipId, clarifier?: string) => Promise<void>;
  /** Commit the current resolution, write the log, navigate to /reveal. */
  commit: () => Promise<void>;

  /** True while a resolve stream is in flight. */
  streaming: boolean;
  /** True while a chip dispatch or commit is in flight. */
  busy: boolean;
  /** Accumulated Gemma delta text for the current stream. */
  streamingText: string;
  /** User-readable error from the most recent op. Null when clean. */
  error: string | null;
  /** Current community-suggestion cards. */
  suggestions: Suggestion[];

  /** Local UI state: less-common / stretch tiers visible. */
  showLessCommon: boolean;
  /** Chips the student has tapped this session (for commit payload). */
  chipsTapped: ChipId[];
  /** Clarifier text the student last submitted (for commit payload). */
  lastClarifier: string | null;
  /** Gemma's full debug_trace prose from the last chip dispatch. */
  debugTrace: string | null;
  /** Character-by-character revealed prefix of debugTrace. */
  revealedTrace: string;
  /** True when revealedTrace has caught up to the full debugTrace. */
  revealDone: boolean;
  /** Bucket classification from the most recent chip dispatch. */
  lastBucket: string | null;
  /**
   * True when the clarifier pointed somewhere the current resolution
   * can't reach and Gemma didn't swap the CIP — career tiles are stale.
   */
  clarifierDiverged: boolean;

  /**
   * What callers should route to /build/outcomes to match the semantics of
   * CareerPickScreen.tsx line 62. When parent_cip is present (IU reports
   * 52.01 for Kelley but Gemma matched 52.14), use the broad parent so the
   * substitution branch fires; otherwise fall back to the matched leaf.
   */
  parentCipOrMatched: string | null;

  /** Register the career card the student clicked (for commit metadata). */
  setCommittedClick: (click: CommittedClick) => void;
}

export function useSetYourCourse(): UseSetYourCourseApi {
  const navigate = useNavigate();
  const {
    school,
    programs,
    major,
    initialResolution,
    currentResolution,
    debugTrace,
    setMajor,
    setInitialResolution,
    setCurrentResolution,
    setDebugTrace,
    clearResolution,
  } = useBuildInputStore();
  const selectedCareer = useBuildStore((s) => s.selectedCareer);
  const tieredCareers = useBuildStore((s) => s.tieredCareers);

  const [streaming, setStreaming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showLessCommon, setShowLessCommon] = useState(false);
  const [chipsTapped, setChipsTapped] = useState<ChipId[]>([]);
  const [lastClarifier, setLastClarifier] = useState<string | null>(null);
  // Bucket classification from the most recent chip dispatch + whether
  // that dispatch actually swapped the CIP. When the clarifier points
  // somewhere the current resolution can't reach (school_gap,
  // intent_divergence, no_issue_found, semantic_drift without a swap),
  // the career list is stale and should be hidden — the reasoning card
  // becomes the honest answer instead.
  const [lastBucket, setLastBucket] = useState<string | null>(null);
  const [lastChipUpdatedResolution, setLastChipUpdatedResolution] =
    useState<boolean>(false);
  // Character-by-character reveal of the chip debug_trace response. The
  // chip dispatch is a single POST (not a stream), so we fake-stream the
  // prose on arrival so the "Gemma is thinking → Gemma said this" read
  // stays consistent with the initial /intent/stream surface.
  const [revealedTrace, setRevealedTrace] = useState("");
  const [revealDone, setRevealDone] = useState(false);
  useEffect(() => {
    if (!debugTrace) {
      setRevealedTrace("");
      setRevealDone(false);
      return;
    }
    setRevealedTrace("");
    setRevealDone(false);
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setRevealedTrace(debugTrace.slice(0, i));
      if (i >= debugTrace.length) {
        window.clearInterval(id);
        setRevealDone(true);
      }
    }, 18);
    return () => window.clearInterval(id);
  }, [debugTrace]);
  const [committedClick, setCommittedClickState] = useState<CommittedClick>({
    soc: null,
    title: null,
    feasibility: null,
  });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Cleanup any pending work on unmount — no dangling fetches.
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
  }, []);

  const resolve = useCallback(
    (majorText: string) => {
      if (!school) return;
      const trimmed = majorText.trim();

      // Cancel any in-flight work — both the debounce and an active stream.
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
      abortRef.current = null;

      // An empty input clears the resolution state entirely.
      if (trimmed.length === 0) {
        clearResolution();
        setStreamingText("");
        setStreaming(false);
        setSuggestions([]);
        setError(null);
        return;
      }

      debounceRef.current = setTimeout(async () => {
        const controller = new AbortController();
        abortRef.current = controller;
        setStreaming(true);
        setStreamingText("");
        setError(null);
        // Every new resolve discards any sub-focus the student accumulated
        // on the previous input — they're talking about a different topic.
        setDebugTrace(null);
        setLastClarifier(null);
        setLastBucket(null);
        setLastChipUpdatedResolution(false);

        const programDicts = programs.map((p) => ({
          cipcode: p.cipcode,
          program_name: p.program_name,
        }));

        try {
          let structured: IntentResult | null = null;
          for await (const event of streamIntent({
            majorText: trimmed,
            schoolName: school.name,
            unitid: school.unitid,
            programs: programDicts,
            signal: controller.signal,
          })) {
            if (controller.signal.aborted) break;
            if (event.type === "delta") {
              setStreamingText((prev) => prev + event.text);
            } else if (event.type === "structured") {
              structured = { ...event.result, confirmed_focus: null };
              // Initial resolution never carries sub-focus — that's only
              // set by the chip dispatch after tool-verified evidence.
              if (!initialResolution) {
                setInitialResolution(structured);
              }
              setCurrentResolution(structured);
            } else if (event.type === "suggestions") {
              setSuggestions(event.suggestions);
            } else if (event.type === "done") {
              break;
            }
          }
          if (!controller.signal.aborted) {
            setStreaming(false);
          }
        } catch (err) {
          if (!controller.signal.aborted) {
            setError(err instanceof Error ? err.message : "Resolve failed");
            setStreaming(false);
          }
        } finally {
          if (abortRef.current === controller) abortRef.current = null;
        }
      }, MAJOR_DEBOUNCE_MS);
    },
    [
      school,
      programs,
      initialResolution,
      setInitialResolution,
      setCurrentResolution,
      setDebugTrace,
      clearResolution,
    ],
  );

  const onChip = useCallback(
    async (chipId: ChipId, clarifier?: string) => {
      setError(null);
      setChipsTapped((prev) =>
        prev.includes(chipId) ? prev : [...prev, chipId],
      );

      if (chipId === "show_less_common") {
        setShowLessCommon((prev) => !prev);
        return;
      }

      if (chipId === "change_major") {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        abortRef.current?.abort();
        abortRef.current = null;
        setStreamingText("");
        setStreaming(false);
        setSuggestions([]);
        clearResolution();
        setMajor(null as unknown as Parameters<typeof setMajor>[0]);
        return;
      }

      // not_expected — the Gemma-heavy chip.
      if (!currentResolution || !initialResolution || !school) return;
      if (clarifier) setLastClarifier(clarifier);

      const programDicts = programs.map((p) => ({
        cipcode: p.cipcode,
        program_name: p.program_name,
      }));

      setBusy(true);
      const controller = new AbortController();
      abortRef.current?.abort();
      abortRef.current = controller;
      try {
        const response = await dispatchChip({
          chipId,
          clarifier,
          currentResolution,
          initialResolution,
          schoolName: school.name,
          unitid: school.unitid,
          programs: programDicts,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;

        setDebugTrace(response.debug_trace || null);
        setLastBucket(response.bucket ?? null);
        setLastChipUpdatedResolution(Boolean(response.updated_resolution));

        if (response.updated_resolution) {
          const merged: IntentResult = {
            ...currentResolution,
            ...response.updated_resolution,
            confirmed_focus: response.confirmed_focus ?? null,
          };
          setCurrentResolution(merged);
        } else if (response.confirmed_focus != null) {
          // No CIP change but Gemma verified a sub-specialty — persist the
          // label on currentResolution so every downstream prose surface
          // interpolates it.
          setCurrentResolution({
            ...currentResolution,
            confirmed_focus: response.confirmed_focus,
          });
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Chip dispatch failed");
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setBusy(false);
      }
    },
    [
      school,
      programs,
      currentResolution,
      initialResolution,
      setCurrentResolution,
      setDebugTrace,
      setMajor,
      clearResolution,
    ],
  );

  const commit = useCallback(async () => {
    if (!school || !currentResolution || !initialResolution) return;

    // The student may have clicked through to an explicit career card from
    // the preview; otherwise we fall back to the first common-tier career
    // so the downstream /reveal has something to render.
    const fallbackCareer =
      tieredCareers?.common[0] ??
      tieredCareers?.less_common[0] ??
      tieredCareers?.stretch[0] ??
      null;
    const committed =
      selectedCareer ??
      (fallbackCareer
        ? { soc_code: fallbackCareer.soc_code, occupation_title: fallbackCareer.occupation_title }
        : null);

    setBusy(true);
    setError(null);
    try {
      await commitResolution({
        currentResolution,
        initialResolution,
        schoolName: school.name,
        unitid: school.unitid,
        // Normalize the raw student text for cache key stability — lower
        // + collapse whitespace. Keeps the hackathon threshold meaningful
        // without getting into stemming territory.
        inputNormalized: (major?.rawText ?? "")
          .trim()
          .toLowerCase()
          .replace(/\s+/g, " "),
        clickedSoc: committedClick.soc ?? committed?.soc_code ?? null,
        clickedCareerTitle:
          committedClick.title ?? committed?.occupation_title ?? null,
        feasibilityMode: committedClick.feasibility,
        chipsTapped,
        clarifier: lastClarifier,
      });

      // Persist the committed CIP into the MajorSelection shape so
      // downstream screens (RevealScreen) read the same fields they do
      // from the old flow.
      setMajor({
        cipCode: currentResolution.matched_cip,
        cipTitle: currentResolution.matched_title,
        rawText: major?.rawText ?? "",
        careersPreview: currentResolution.careers_preview ?? [],
        substitutionApplied: Boolean(currentResolution.parent_cip),
        parentCip: currentResolution.parent_cip ?? "",
      });

      navigate("/reveal");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Commit failed");
    } finally {
      setBusy(false);
    }
  }, [
    school,
    major,
    currentResolution,
    initialResolution,
    tieredCareers,
    selectedCareer,
    chipsTapped,
    lastClarifier,
    committedClick,
    setMajor,
    navigate,
  ]);

  const parentCipOrMatched = useMemo(() => {
    if (!currentResolution) return null;
    return currentResolution.parent_cip || currentResolution.matched_cip || null;
  }, [currentResolution]);

  // True when the most recent chip clarifier pointed somewhere the
  // current resolution can't reach. In that case the career tiles are
  // about the original major and do not answer the clarifier — they
  // should be hidden in favor of the reasoning card.
  const clarifierDiverged = useMemo(() => {
    if (!debugTrace || !lastBucket) return false;
    if (lastChipUpdatedResolution) return false;
    const DIVERGENT: ReadonlySet<string> = new Set([
      "school_gap",
      "intent_divergence",
      "no_issue_found",
      "semantic_drift",
      "crosswalk_mismatch",
    ]);
    return DIVERGENT.has(lastBucket);
  }, [debugTrace, lastBucket, lastChipUpdatedResolution]);

  const setCommittedClick = useCallback((click: CommittedClick) => {
    setCommittedClickState(click);
  }, []);

  return {
    resolve,
    onChip,
    commit,
    streaming,
    busy,
    streamingText,
    error,
    suggestions,
    showLessCommon,
    chipsTapped,
    lastClarifier,
    debugTrace,
    revealedTrace,
    revealDone,
    lastBucket,
    clarifierDiverged,
    parentCipOrMatched,
    setCommittedClick,
  };
}
