import { describe, it, expect, beforeEach } from "vitest";
import { useGauntletStore } from "./gauntletStore";

/**
 * gauntletStore tests
 *
 * Tests the Zustand store that manages boss gauntlet sequencing:
 * - Fight index advancement (0-4, then final_boss transition)
 * - Skill selection toggle (add/remove from Set)
 * - Phase transitions
 * - State reset
 *
 * These tests call production store methods directly and assert on
 * observable state changes. No mocking of the store itself.
 */

// Reset store to initial state before each test so they're independent
beforeEach(() => {
  useGauntletStore.getState().resetGauntlet();
});

describe("gauntletStore", () => {
  // ----- advanceFight -----

  describe("advanceFight", () => {
    it("increments currentFightIndex from 0 to 1", () => {
      const store = useGauntletStore.getState();
      expect(store.currentFightIndex).toBe(0);

      store.advanceFight();

      const updated = useGauntletStore.getState();
      expect(updated.currentFightIndex).toBe(1);
    });

    it("resets fightPhase to entrance on advance", () => {
      const store = useGauntletStore.getState();
      store.setFightPhase("resolved");
      store.advanceFight();

      expect(useGauntletStore.getState().fightPhase).toBe("entrance");
    });

    it("clears selectedSkillIds on advance", () => {
      const store = useGauntletStore.getState();
      store.toggleSkill("sk-cloud");
      store.toggleSkill("sk-lead");
      expect(useGauntletStore.getState().selectedSkillIds.size).toBe(2);

      store.advanceFight();

      expect(useGauntletStore.getState().selectedSkillIds.size).toBe(0);
    });

    it("advances through all 5 fights sequentially (indices 0-4)", () => {
      const store = useGauntletStore.getState();

      for (let i = 0; i < 4; i++) {
        store.advanceFight();
      }

      // After 4 advances we should be at index 4 (fight 5 of 5)
      expect(useGauntletStore.getState().currentFightIndex).toBe(4);
      // Phase should still NOT be final_boss yet -- we haven't advanced past fight 5
      expect(useGauntletStore.getState().phase).toBe("intro");
    });

    it("transitions to final_boss phase when advancing past fight 5 (index 4)", () => {
      const store = useGauntletStore.getState();

      // Advance to index 4
      for (let i = 0; i < 4; i++) {
        store.advanceFight();
      }
      expect(useGauntletStore.getState().currentFightIndex).toBe(4);

      // One more advance should trigger final_boss
      store.advanceFight();
      expect(useGauntletStore.getState().phase).toBe("final_boss");
    });

    it("does NOT increment index past 4 when transitioning to final_boss", () => {
      const store = useGauntletStore.getState();

      for (let i = 0; i < 5; i++) {
        store.advanceFight();
      }

      // Index stays at 4 -- final_boss is a phase change, not an index change
      expect(useGauntletStore.getState().currentFightIndex).toBe(4);
    });
  });

  // ----- toggleSkill -----

  describe("toggleSkill", () => {
    it("adds a skill id to selectedSkillIds", () => {
      useGauntletStore.getState().toggleSkill("sk-cloud");

      expect(useGauntletStore.getState().selectedSkillIds.has("sk-cloud")).toBe(
        true,
      );
      expect(useGauntletStore.getState().selectedSkillIds.size).toBe(1);
    });

    it("removes a skill id when toggled twice", () => {
      const store = useGauntletStore.getState();
      store.toggleSkill("sk-cloud");
      store.toggleSkill("sk-cloud");

      expect(useGauntletStore.getState().selectedSkillIds.has("sk-cloud")).toBe(
        false,
      );
      expect(useGauntletStore.getState().selectedSkillIds.size).toBe(0);
    });

    it("supports multiple concurrent selections", () => {
      const store = useGauntletStore.getState();
      store.toggleSkill("sk-cloud");
      store.toggleSkill("sk-lead");
      store.toggleSkill("sk-oss");

      const ids = useGauntletStore.getState().selectedSkillIds;
      expect(ids.size).toBe(3);
      expect(ids.has("sk-cloud")).toBe(true);
      expect(ids.has("sk-lead")).toBe(true);
      expect(ids.has("sk-oss")).toBe(true);
    });

    it("only removes the toggled skill, leaving others intact", () => {
      const store = useGauntletStore.getState();
      store.toggleSkill("sk-cloud");
      store.toggleSkill("sk-lead");
      store.toggleSkill("sk-cloud"); // remove cloud

      const ids = useGauntletStore.getState().selectedSkillIds;
      expect(ids.size).toBe(1);
      expect(ids.has("sk-lead")).toBe(true);
      expect(ids.has("sk-cloud")).toBe(false);
    });
  });

  // ----- clearSelectedSkills -----

  describe("clearSelectedSkills", () => {
    it("empties the selectedSkillIds set", () => {
      const store = useGauntletStore.getState();
      store.toggleSkill("sk-cloud");
      store.toggleSkill("sk-lead");
      store.clearSelectedSkills();

      expect(useGauntletStore.getState().selectedSkillIds.size).toBe(0);
    });
  });

  // ----- setPhase -----

  describe("setPhase", () => {
    it("transitions between gauntlet phases", () => {
      const phases = [
        "fighting",
        "final_boss",
        "next_steps_loading",
        "next_steps",
        "complete",
      ] as const;

      for (const phase of phases) {
        useGauntletStore.getState().setPhase(phase);
        expect(useGauntletStore.getState().phase).toBe(phase);
      }
    });
  });

  // ----- setFightPhase -----

  describe("setFightPhase", () => {
    it("transitions between fight sub-phases", () => {
      const phases = [
        "entrance",
        "result",
        "reroll",
        "structural_loss",
        "resolved",
      ] as const;

      for (const phase of phases) {
        useGauntletStore.getState().setFightPhase(phase);
        expect(useGauntletStore.getState().fightPhase).toBe(phase);
      }
    });
  });

  // ----- next steps state -----

  describe("nextSteps state", () => {
    it("setNextStepsContent stores content and clears error", () => {
      const store = useGauntletStore.getState();
      store.setNextStepsError(true);
      store.setNextStepsContent("## Questions\n- Item 1");

      const state = useGauntletStore.getState();
      expect(state.nextStepsContent).toBe("## Questions\n- Item 1");
      expect(state.nextStepsError).toBe(false);
    });

    it("setNextStepsError sets error flag", () => {
      useGauntletStore.getState().setNextStepsError(true);
      expect(useGauntletStore.getState().nextStepsError).toBe(true);
    });
  });

  // ----- resetGauntlet -----

  describe("resetGauntlet", () => {
    it("restores all state to initial values", () => {
      const store = useGauntletStore.getState();
      // Dirty every piece of state
      store.setPhase("complete");
      store.setCurrentFightIndex(3);
      store.setFightPhase("resolved");
      store.toggleSkill("sk-cloud");
      store.setIsRescoring(true);
      store.setNextStepsContent("some content");

      store.resetGauntlet();

      const reset = useGauntletStore.getState();
      expect(reset.phase).toBe("intro");
      expect(reset.currentFightIndex).toBe(0);
      expect(reset.fightPhase).toBe("entrance");
      expect(reset.selectedSkillIds.size).toBe(0);
      expect(reset.isRescoring).toBe(false);
      expect(reset.nextStepsContent).toBeNull();
      expect(reset.nextStepsError).toBe(false);
    });
  });
});
