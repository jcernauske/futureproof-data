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
import { getOutcomes } from "@/api/build";
import { fireCheckpoint } from "@/lib/checkpoint";
import { useProfileStore } from "@/store/profileStore";
import { useDebouncedTrigger } from "@/hooks/useDebouncedTrigger";
import type { IntentResult, Suggestion, GradCredentialNoticePayload } from "@/types/buildInput";
import type { CareerOutcome } from "@/types/build";

const MAJOR_DEBOUNCE_MS = 300;
const CAREER_FETCH_DEBOUNCE_MS = 250;

export type SocRevealState =
  | { kind: "idle" }
  | { kind: "outcomes-loading" }
  | { kind: "outcomes-loaded"; outcomes: CareerOutcome[] }
  | { kind: "error"; message: string };

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
  /** Commit the current resolution, write the log, navigate to /my-build. */
  commit: () => Promise<void>;
  /** Swap an alternative CIP into the primary position and refetch outcomes. */
  onPickAlternative: (index: number) => void;

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
   * When a chip dispatch returns intent_divergence with a confirmed_focus,
   * this holds the suggested new major text (e.g., "Computer Science").
   * The screen should offer to re-search with this value. Null otherwise.
   */
  suggestedMajor: string | null;

  /**
   * What callers should route to /build/outcomes to match the semantics of
   * CareerPickScreen.tsx line 62. When parent_cip is present (IU reports
   * 52.01 for Kelley but Gemma matched 52.14), use the broad parent so the
   * substitution branch fires; otherwise fall back to the matched leaf.
   */
  parentCipOrMatched: string | null;

  /** Outcomes-first paint state machine for the SOC reveal. */
  socReveal: SocRevealState;

  /** Register the career card the student clicked (for commit metadata). */
  setCommittedClick: (click: CommittedClick) => void;

  /**
   * Non-null when the chip dispatch or pre-flag short-circuit determined
   * that the student's target career requires graduate school. The
   * SetYourCourseScreen renders the GradCredentialNotice tile from this.
   */
  gradCredentialNotice: GradCredentialNoticePayload | null;
}

export function useSetYourCourse(liveMajorText: string = ""): UseSetYourCourseApi {
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
  const homeState = useProfileStore((s) => s.homeState);

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
  const [suggestedMajor, setSuggestedMajor] = useState<string | null>(null);
  const [gradCredentialNotice, setGradCredentialNotice] =
    useState<GradCredentialNoticePayload | null>(null);
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

  // Compute parentCipOrMatched early — the state machine needs it.
  const parentCipOrMatched = useMemo(() => {
    if (!currentResolution) return null;
    return currentResolution.parent_cip || currentResolution.matched_cip || null;
  }, [currentResolution]);

  const outcomesCacheRef = useRef<Map<string, CareerOutcome[]>>(new Map());
  const prefetchAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!school || !currentResolution?.alternatives?.length) return;
    prefetchAbortRef.current?.abort();
    const controller = new AbortController();
    prefetchAbortRef.current = controller;

    const capturedSchool = school;
    const capturedMajor = liveMajorText.trim();

    for (const alt of currentResolution.alternatives) {
      const altCip = alt.parent_cip || alt.cip;
      const cacheKey = `${altCip}:${homeState ?? ""}`;
      if (outcomesCacheRef.current.has(cacheKey)) continue;
      getOutcomes(
        capturedSchool.unitid,
        altCip,
        "balanced",
        0.5,
        capturedMajor || undefined,
        alt.cip,
        controller.signal,
        undefined,
        homeState,
      ).then((outcomes) => {
        if (!controller.signal.aborted) {
          outcomesCacheRef.current.set(cacheKey, outcomes);
        }
      }).catch(() => {});
    }

    return () => { controller.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentResolution?.matched_cip, school?.unitid, homeState]);

  // --- Outcomes-first paint state machine ---
  const [socReveal, setSocReveal] = useState<SocRevealState>({ kind: "idle" });
  const outcomeAbortRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0);

  function doCareerFetch() {
    if (!school || !parentCipOrMatched) {
      setSocReveal({ kind: "idle" });
      return;
    }
    const reqId = ++requestIdRef.current;
    outcomeAbortRef.current?.abort();
    const controller = new AbortController();
    outcomeAbortRef.current = controller;

    const capturedSchool = school;
    const capturedCip = parentCipOrMatched;
    const capturedCacheKey = `${capturedCip}:${homeState ?? ""}`;
    const capturedMajor = liveMajorText.trim();
    const capturedMatchedCip = currentResolution?.matched_cip;
    const capturedIntentKeywords = currentResolution?.intent_keywords;

    const cachedOutcomes = outcomesCacheRef.current.get(capturedCacheKey);
    if (cachedOutcomes) {
      setSocReveal({ kind: "outcomes-loaded", outcomes: cachedOutcomes });
      return;
    }

    setSocReveal({ kind: "outcomes-loading" });

    (async () => {
      try {
        const outcomes = await getOutcomes(
          capturedSchool.unitid,
          capturedCip,
          "balanced",
          0.5,
          capturedMajor || undefined,
          capturedMatchedCip || undefined,
          controller.signal,
          capturedIntentKeywords,
          homeState,
        );
        if (requestIdRef.current !== reqId) return;
        outcomesCacheRef.current.set(capturedCacheKey, outcomes);
        setSocReveal({ kind: "outcomes-loaded", outcomes });
      } catch (err) {
        if (controller.signal.aborted) return;
        if (requestIdRef.current !== reqId) return;
        setSocReveal({
          kind: "error",
          message: err instanceof Error ? err.message : "Failed to load careers",
        });
      }
    })();
  }

  const debouncedCareerFetch = useDebouncedTrigger(doCareerFetch, {
    delayMs: CAREER_FETCH_DEBOUNCE_MS,
    immediateOnKeyChange: parentCipOrMatched,
  });

  useEffect(() => {
    if (!school || !parentCipOrMatched) {
      requestIdRef.current++;
      outcomeAbortRef.current?.abort();
      setSocReveal({ kind: "idle" });
      return;
    }
    debouncedCareerFetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [school, parentCipOrMatched, liveMajorText, homeState, debouncedCareerFetch]);

  useEffect(() => {
    return () => { outcomeAbortRef.current?.abort(); };
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
        outcomesCacheRef.current.clear();
        return;
      }

      debounceRef.current = setTimeout(async () => {
        const controller = new AbortController();
        abortRef.current = controller;
        setStreaming(true);
        setStreamingText("");
        setError(null);
        outcomesCacheRef.current.clear();
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
            locale: useProfileStore.getState().locale,
          })) {
            if (controller.signal.aborted) break;
            if (event.type === "delta") {
              setStreamingText((prev) => prev + event.text);
            } else if (event.type === "structured") {
              structured = { ...event.result, confirmed_focus: null };
              setInitialResolution(structured);
              setCurrentResolution(structured);
              // Clear grad notice unless the pre-flag path fills it.
              setGradCredentialNotice(null);
            } else if (event.type === "grad_credential_payload") {
              setGradCredentialNotice(event.payload);
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
          locale: useProfileStore.getState().locale,
        });
        if (controller.signal.aborted) return;

        setDebugTrace(response.debug_trace || null);
        setLastBucket(response.bucket ?? null);
        setLastChipUpdatedResolution(Boolean(response.updated_resolution));

        // Surface grad-credential notice when bucket routes there.
        if (
          response.cta_link?.kind === "grad_credential_notice" &&
          response.cta_link.payload
        ) {
          setGradCredentialNotice(response.cta_link.payload);
        } else {
          setGradCredentialNotice(null);
        }

        if (
          response.bucket === "intent_divergence" &&
          response.confirmed_focus &&
          !response.updated_resolution
        ) {
          setSuggestedMajor(response.confirmed_focus);
        } else {
          setSuggestedMajor(null);
        }

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

    const outcomes = socReveal.kind === "outcomes-loaded" ? socReveal.outcomes : [];
    const fallbackCareer = outcomes[0] ?? null;
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
      // downstream screens (BuildResultsScreen) read the same fields
      // they do from the old flow.
      setMajor({
        cipCode: currentResolution.matched_cip,
        cipTitle: currentResolution.matched_title,
        rawText: major?.rawText ?? "",
        careersPreview: currentResolution.careers_preview ?? [],
        substitutionApplied: Boolean(currentResolution.parent_cip),
        parentCip: currentResolution.parent_cip ?? "",
        studentMajorText: currentResolution.student_major_text ?? "",
        intentKeywords: currentResolution.intent_keywords ?? [],
      });

      fireCheckpoint("/my-build");
      navigate("/my-build");
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
    socReveal,
    selectedCareer,
    chipsTapped,
    lastClarifier,
    committedClick,
    setMajor,
    navigate,
  ]);

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
      "requires_graduate_credential",
    ]);
    return DIVERGENT.has(lastBucket);
  }, [debugTrace, lastBucket, lastChipUpdatedResolution]);

  const onPickAlternative = useCallback(
    (optionIndex: number) => {
      const res = currentResolution;
      const init = initialResolution;
      if (!res || !init?.alternatives) return;

      if (optionIndex === 0) {
        setCurrentResolution({
          ...res,
          matched_cip: init.matched_cip,
          matched_title: init.matched_title,
          parent_cip: init.parent_cip,
        });
        return;
      }

      const altIndex = optionIndex - 1;
      const alt = init.alternatives[altIndex];
      if (!alt) return;

      setCurrentResolution({
        ...res,
        matched_cip: alt.cip,
        matched_title: alt.title,
        parent_cip: alt.parent_cip ?? res.parent_cip,
      });
    },
    [currentResolution, initialResolution, setCurrentResolution],
  );

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
    suggestedMajor,
    parentCipOrMatched,
    onPickAlternative,
    socReveal,
    setCommittedClick,
    gradCredentialNotice,
  };
}
