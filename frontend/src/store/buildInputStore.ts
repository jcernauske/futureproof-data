import { create } from "zustand";
import type {
  SchoolSelection,
  MajorSelection,
  EffortSelection,
  LoanSelection,
  ProgramResult,
} from "@/types/buildInput";

type Phase = "school" | "major" | "sliders";

interface BuildInputState {
  phase: Phase;
  school: SchoolSelection | null;
  programs: ProgramResult[];
  major: MajorSelection | null;
  effort: EffortSelection;
  loans: LoanSelection;

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
}

const DEFAULT_EFFORT: EffortSelection = {
  level: "balanced",
  percentile: 50,
  ernShift: 0,
};

const DEFAULT_LOANS: LoanSelection = { percentage: 50 };

export const useBuildInputStore = create<BuildInputState>((set) => ({
  phase: "school",
  school: null,
  programs: [],
  major: null,
  effort: DEFAULT_EFFORT,
  loans: DEFAULT_LOANS,

  setPhase: (phase) => set({ phase }),
  setSchool: (school) => set({ school, phase: "major" }),
  setPrograms: (programs) => set({ programs }),
  setMajor: (major) => set({ major, phase: "sliders" }),
  setEffort: (effort) => set({ effort }),
  setLoans: (loans) => set({ loans }),
  clearSchool: () =>
    set({ school: null, programs: [], major: null, phase: "school" }),
  clearMajor: () => set({ major: null, phase: "major" }),
  reset: () =>
    set({
      phase: "school",
      school: null,
      programs: [],
      major: null,
      effort: DEFAULT_EFFORT,
      loans: DEFAULT_LOANS,
    }),
  resetInputs: () =>
    set({
      phase: "school",
      school: null,
      programs: [],
      major: null,
      effort: DEFAULT_EFFORT,
      loans: DEFAULT_LOANS,
    }),
}));
