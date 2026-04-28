import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Build, CareerOutcome, TieredCareers } from "@/types/build";

interface BuildState {
  // Screen 5 — Career Pick
  tieredCareers: TieredCareers | null;
  selectedCareer: CareerOutcome | null;
  setTieredCareers: (tiers: TieredCareers | null) => void;
  setSelectedCareer: (career: CareerOutcome | null) => void;

  // Loading
  isBuilding: boolean;
  buildingStage: number;
  setIsBuilding: (building: boolean) => void;
  setBuildingStage: (stage: number) => void;

  // Screen 6 — Reveal
  build: Build | null;
  setBuild: (build: Build) => void;
  updateBuild: (fn: (prev: Build) => Build) => void;

  // Tutorial
  hasSeenStatTutorial: boolean;
  setHasSeenStatTutorial: (seen: boolean) => void;

  // Reset
  resetBuild: () => void;

  hydrateFromSession: (data: {
    build?: Build | null;
    tieredCareers?: TieredCareers | null;
    selectedCareer?: CareerOutcome | null;
  }) => void;
}

export const useBuildStore = create<BuildState>()(
  persist(
    (set) => ({
      tieredCareers: null,
      selectedCareer: null,
      setTieredCareers: (tieredCareers) => set({ tieredCareers }),
      setSelectedCareer: (selectedCareer) => set({ selectedCareer }),

      isBuilding: false,
      buildingStage: 0,
      setIsBuilding: (isBuilding) => set({ isBuilding }),
      setBuildingStage: (buildingStage) => set({ buildingStage }),

      build: null,
      setBuild: (build) => set({ build }),
      updateBuild: (fn) =>
        set((state) => ({ build: state.build ? fn(state.build) : state.build })),

      hasSeenStatTutorial: false,
      setHasSeenStatTutorial: (hasSeenStatTutorial) =>
        set({ hasSeenStatTutorial }),

      resetBuild: () =>
        set({
          tieredCareers: null,
          selectedCareer: null,
          isBuilding: false,
          buildingStage: 0,
          build: null,
        }),

      hydrateFromSession: (data) =>
        set({
          build: data.build ?? null,
          tieredCareers: data.tieredCareers ?? null,
          selectedCareer: data.selectedCareer ?? null,
          isBuilding: false,
          buildingStage: 0,
        }),
    }),
    {
      name: "futureproof-build",
      partialize: (state) => ({
        hasSeenStatTutorial: state.hasSeenStatTutorial,
      }),
    },
  ),
);
