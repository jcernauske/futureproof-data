import { create } from "zustand";

export type GauntletPhase =
  | "intro"
  | "fighting"
  | "final_boss"
  | "next_steps_loading"
  | "next_steps"
  | "complete";

export type FightPhase =
  | "entrance"
  | "result"
  | "reroll"
  | "structural_loss"
  | "resolved";

interface GauntletState {
  phase: GauntletPhase;
  currentFightIndex: number;
  fightPhase: FightPhase;
  setPhase: (phase: GauntletPhase) => void;
  setCurrentFightIndex: (index: number) => void;
  setFightPhase: (phase: FightPhase) => void;
  advanceFight: () => void;

  selectedSkillIds: Set<string>;
  isRescoring: boolean;
  toggleSkill: (skillId: string) => void;
  clearSelectedSkills: () => void;
  setIsRescoring: (rescoring: boolean) => void;

  nextStepsContent: string | null;
  nextStepsError: boolean;
  setNextStepsContent: (content: string) => void;
  setNextStepsError: (error: boolean) => void;

  resetGauntlet: () => void;
}

export const useGauntletStore = create<GauntletState>()((set, get) => ({
  phase: "intro",
  currentFightIndex: 0,
  fightPhase: "entrance",
  setPhase: (phase) => set({ phase }),
  setCurrentFightIndex: (currentFightIndex) => set({ currentFightIndex }),
  setFightPhase: (fightPhase) => set({ fightPhase }),
  advanceFight: () => {
    const { currentFightIndex } = get();
    if (currentFightIndex < 4) {
      set({
        currentFightIndex: currentFightIndex + 1,
        fightPhase: "entrance",
        selectedSkillIds: new Set(),
      });
    } else {
      set({ phase: "final_boss" });
    }
  },

  selectedSkillIds: new Set(),
  isRescoring: false,
  toggleSkill: (skillId) =>
    set((state) => {
      const next = new Set(state.selectedSkillIds);
      if (next.has(skillId)) {
        next.delete(skillId);
      } else {
        next.add(skillId);
      }
      return { selectedSkillIds: next };
    }),
  clearSelectedSkills: () => set({ selectedSkillIds: new Set() }),
  setIsRescoring: (isRescoring) => set({ isRescoring }),

  nextStepsContent: null,
  nextStepsError: false,
  setNextStepsContent: (nextStepsContent) =>
    set({ nextStepsContent, nextStepsError: false }),
  setNextStepsError: (nextStepsError) => set({ nextStepsError }),

  resetGauntlet: () =>
    set({
      phase: "intro",
      currentFightIndex: 0,
      fightPhase: "entrance",
      selectedSkillIds: new Set(),
      isRescoring: false,
      nextStepsContent: null,
      nextStepsError: false,
    }),
}));
