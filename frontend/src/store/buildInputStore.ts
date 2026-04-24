import { create } from "zustand";
import type {
  SchoolSelection,
  MajorSelection,
  EffortSelection,
  LoanSelection,
  ProgramResult,
  IntentResult,
} from "@/types/buildInput";

type Phase = "school" | "major" | "sliders";

interface BuildInputState {
  phase: Phase;
  school: SchoolSelection | null;
  programs: ProgramResult[];
  major: MajorSelection | null;
  effort: EffortSelection;
  loans: LoanSelection;

  // Set Your Course resolution state — see
  // docs/specs/feature-set-your-course.md §4. The fields are additive and
  // default to null/false so the existing /school flow writes partial
  // payloads the store still accepts.
  initialResolution: IntentResult | null;
  currentResolution: IntentResult | null;
  hasCorrected: boolean;
  debugTrace: string | null;

  setPhase: (phase: Phase) => void;
  setSchool: (school: SchoolSelection) => void;
  setPrograms: (programs: ProgramResult[]) => void;
  setMajor: (major: MajorSelection) => void;
  setEffort: (effort: EffortSelection) => void;
  setLoans: (loans: LoanSelection) => void;
  clearSchool: () => void;
  clearMajor: () => void;
  reset: () => void;
  resetInputs: () => void;

  // Set Your Course setters.
  setInitialResolution: (result: IntentResult | null) => void;
  setCurrentResolution: (result: IntentResult | null) => void;
  setDebugTrace: (trace: string | null) => void;
  clearResolution: () => void;

  hydrateFromSession: (data: Record<string, unknown>) => void;
}

const DEFAULT_EFFORT: EffortSelection = {
  level: "balanced",
  percentile: 50,
  ernShift: 0,
};

const DEFAULT_LOANS: LoanSelection = { percentage: 50 };

const EMPTY_RESOLUTION_SLICE = {
  initialResolution: null as IntentResult | null,
  currentResolution: null as IntentResult | null,
  hasCorrected: false,
  debugTrace: null as string | null,
};

function deriveHasCorrected(
  initial: IntentResult | null,
  current: IntentResult | null,
): boolean {
  if (!initial || !current) return false;
  return initial.matched_cip !== current.matched_cip;
}

export const useBuildInputStore = create<BuildInputState>((set, get) => ({
  phase: "school",
  school: null,
  programs: [],
  major: null,
  effort: DEFAULT_EFFORT,
  loans: DEFAULT_LOANS,

  ...EMPTY_RESOLUTION_SLICE,

  setPhase: (phase) => set({ phase }),
  setSchool: (school) => set({ school, phase: "major" }),
  setPrograms: (programs) => set({ programs }),
  setMajor: (major) => set({ major, phase: "sliders" }),
  setEffort: (effort) => set({ effort }),
  setLoans: (loans) => set({ loans }),
  clearSchool: () =>
    set({
      school: null,
      programs: [],
      major: null,
      phase: "school",
      ...EMPTY_RESOLUTION_SLICE,
    }),
  clearMajor: () =>
    set({ major: null, phase: "major", ...EMPTY_RESOLUTION_SLICE }),
  reset: () =>
    set({
      phase: "school",
      school: null,
      programs: [],
      major: null,
      effort: DEFAULT_EFFORT,
      loans: DEFAULT_LOANS,
      ...EMPTY_RESOLUTION_SLICE,
    }),
  resetInputs: () =>
    set({
      phase: "school",
      school: null,
      programs: [],
      major: null,
      effort: DEFAULT_EFFORT,
      loans: DEFAULT_LOANS,
      ...EMPTY_RESOLUTION_SLICE,
    }),

  setInitialResolution: (result) =>
    set({
      initialResolution: result,
      hasCorrected: deriveHasCorrected(result, get().currentResolution),
    }),
  setCurrentResolution: (result) =>
    set({
      currentResolution: result,
      hasCorrected: deriveHasCorrected(get().initialResolution, result),
    }),
  setDebugTrace: (trace) => set({ debugTrace: trace }),
  clearResolution: () => set({ ...EMPTY_RESOLUTION_SLICE }),

  hydrateFromSession: (data) =>
    set({
      phase: (data.phase as Phase) ?? "school",
      school: (data.school as SchoolSelection | null) ?? null,
      programs: (data.programs as ProgramResult[]) ?? [],
      major: (data.major as MajorSelection | null) ?? null,
      effort: (data.effort as EffortSelection) ?? DEFAULT_EFFORT,
      loans: (data.loans as LoanSelection) ?? DEFAULT_LOANS,
      initialResolution: (data.initialResolution as IntentResult | null) ?? null,
      currentResolution: (data.currentResolution as IntentResult | null) ?? null,
      hasCorrected: deriveHasCorrected(
        (data.initialResolution as IntentResult | null) ?? null,
        (data.currentResolution as IntentResult | null) ?? null,
      ),
    }),
}));
