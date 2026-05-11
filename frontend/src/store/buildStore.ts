import { create } from "zustand";
import type { Build, CareerOutcome, TieredCareers } from "@/types/build";

interface BuildState {
  // Screen 5 — Career Pick
  tieredCareers: TieredCareers | null;
  selectedCareer: CareerOutcome | null;
  setTieredCareers: (tiers: TieredCareers | null) => void;
  setSelectedCareer: (career: CareerOutcome | null) => void;

  // Loading + progress
  isBuilding: boolean;
  buildingStage: number;
  buildingTotal: number;
  completedSteps: Set<string>;
  setIsBuilding: (building: boolean) => void;
  setBuildingStage: (stageOrFn: number | ((prev: number) => number)) => void;
  setBuildingTotal: (total: number) => void;
  addCompletedStep: (step: string) => void;

  // Screen 6 — Reveal
  build: Build | null;
  setBuild: (build: Build) => void;
  updateBuild: (fn: (prev: Build) => Build) => void;

  // Reset
  resetBuild: () => void;

  hydrateFromSession: (data: {
    build?: Build | null;
    tieredCareers?: TieredCareers | null;
    selectedCareer?: CareerOutcome | null;
  }) => void;
}

export const useBuildStore = create<BuildState>()((set) => ({
  tieredCareers: null,
  selectedCareer: null,
  setTieredCareers: (tieredCareers) => set({ tieredCareers }),
  setSelectedCareer: (selectedCareer) => set({ selectedCareer }),

  isBuilding: false,
  buildingStage: 0,
  buildingTotal: 0,
  completedSteps: new Set<string>(),
  setIsBuilding: (isBuilding) => set({ isBuilding }),
  setBuildingStage: (stageOrFn) =>
    set((state) => ({
      buildingStage:
        typeof stageOrFn === "function"
          ? stageOrFn(state.buildingStage)
          : stageOrFn,
    })),
  setBuildingTotal: (buildingTotal) => set({ buildingTotal }),
  addCompletedStep: (step) =>
    set((state) => ({
      completedSteps: new Set(state.completedSteps).add(step),
    })),

  build: null,
  setBuild: (build) => set({ build }),
  updateBuild: (fn) =>
    set((state) => ({ build: state.build ? fn(state.build) : state.build })),

  resetBuild: () =>
    set({
      tieredCareers: null,
      selectedCareer: null,
      isBuilding: false,
      buildingStage: 0,
      buildingTotal: 0,
      completedSteps: new Set<string>(),
      build: null,
    }),

  hydrateFromSession: (data) =>
    set({
      build: data.build ?? null,
      tieredCareers: data.tieredCareers ?? null,
      selectedCareer: data.selectedCareer ?? null,
      isBuilding: false,
      buildingStage: 0,
      buildingTotal: 0,
      completedSteps: new Set<string>(),
    }),
}));
