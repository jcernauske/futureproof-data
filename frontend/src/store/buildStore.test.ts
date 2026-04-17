import { describe, it, expect, beforeEach } from "vitest";
import { useBuildStore } from "./buildStore";
import type { Build, CareerOutcome, TieredCareers } from "@/types/build";

/**
 * buildStore tests
 *
 * Covers the three contracts that matter:
 *   1. setTieredCareers accepts null (regression guard — used to be non-null)
 *   2. resetBuild clears build state but preserves hasSeenStatTutorial
 *   3. hasSeenStatTutorial persists to localStorage
 */

function makeCareer(soc = "15-1252"): CareerOutcome {
  return {
    unitid: 1,
    institution_name: "Test U",
    cipcode: "11.0701",
    program_name: "CS",
    soc_code: soc,
    occupation_title: "Software Developer",
    soc_major_group_name: null,
    median_annual_wage: 100000,
    earnings_1yr_median: null,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    net_price_annual: null,
    cost_of_attendance_annual: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    room_board_on_campus: null,
    stats: { ern: 8, roi: 7, res: 4, grw: 9, hmn: 5 },
    bosses: { ai: 6, loans: 3, market: 2, burnout: 5, ceiling: 3 },
    top_5_activities: [],
    top_human_activities: [],
    burnout_drivers: [],
    stats_available_count: 5,
    overall_confidence: "high",
    substitution_applied: false,
    reported_cipcode: null,
    substituted_cipcode: null,
    data_caveat: null,
    loan_pct: 0.5,
  };
}

beforeEach(() => {
  // Hard reset so tests are independent
  useBuildStore.setState({
    tieredCareers: null,
    selectedCareer: null,
    isBuilding: false,
    buildingStage: 0,
    build: null,
    hasSeenStatTutorial: false,
  });
  localStorage.clear();
});

describe("buildStore", () => {
  describe("setTieredCareers nullability", () => {
    it("accepts null without type error and exposes null to consumers", () => {
      const tiers: TieredCareers = {
        common: [makeCareer("15-1252")],
        less_common: [],
        stretch: [],
      };
      useBuildStore.getState().setTieredCareers(tiers);
      expect(useBuildStore.getState().tieredCareers).not.toBeNull();

      // The reason this test exists: CareerPickScreen's "Try Again"
      // passes null to reset the list. Must be supported at type + runtime.
      useBuildStore.getState().setTieredCareers(null);
      expect(useBuildStore.getState().tieredCareers).toBeNull();
    });

    it("subscribers re-render when tieredCareers flips to null", () => {
      const snapshots: (TieredCareers | null)[] = [];
      const unsub = useBuildStore.subscribe((s) => {
        snapshots.push(s.tieredCareers);
      });
      try {
        useBuildStore.getState().setTieredCareers({
          common: [makeCareer()],
          less_common: [],
          stretch: [],
        });
        useBuildStore.getState().setTieredCareers(null);
      } finally {
        unsub();
      }
      // Two distinct notifications — non-null followed by null
      expect(snapshots.length).toBe(2);
      expect(snapshots[0]).not.toBeNull();
      expect(snapshots[1]).toBeNull();
    });
  });

  describe("resetBuild", () => {
    it("clears build/selectedCareer/tieredCareers/isBuilding/buildingStage", () => {
      const store = useBuildStore.getState();
      store.setTieredCareers({
        common: [makeCareer("15-1252")],
        less_common: [],
        stretch: [],
      });
      store.setSelectedCareer(makeCareer("15-1252"));
      store.setIsBuilding(true);
      store.setBuildingStage(3);
      store.setBuild({ build_id: "b-1" } as Build);

      store.resetBuild();

      const after = useBuildStore.getState();
      expect(after.tieredCareers).toBeNull();
      expect(after.selectedCareer).toBeNull();
      expect(after.build).toBeNull();
      expect(after.isBuilding).toBe(false);
      expect(after.buildingStage).toBe(0);
    });

    it("preserves hasSeenStatTutorial across resetBuild", () => {
      const store = useBuildStore.getState();
      store.setHasSeenStatTutorial(true);
      expect(useBuildStore.getState().hasSeenStatTutorial).toBe(true);

      store.resetBuild();

      // Critical: resetBuild is called on every "new build" flow — if it
      // wiped hasSeenStatTutorial, returning students would be re-tutored
      // on every build.
      expect(useBuildStore.getState().hasSeenStatTutorial).toBe(true);
    });
  });

  describe("hasSeenStatTutorial localStorage persistence", () => {
    it("writes hasSeenStatTutorial=true to localStorage when set", () => {
      useBuildStore.getState().setHasSeenStatTutorial(true);

      const raw = localStorage.getItem("futureproof-build");
      expect(raw).not.toBeNull();
      const parsed = JSON.parse(raw!);
      // Zustand persist shape: { state: {...}, version: N }
      expect(parsed.state.hasSeenStatTutorial).toBe(true);
    });

    it("does NOT persist transient state (tieredCareers/build) to localStorage", () => {
      const store = useBuildStore.getState();
      store.setTieredCareers({
        common: [makeCareer()],
        less_common: [],
        stretch: [],
      });
      store.setBuild({ build_id: "b-persist-test" } as Build);
      store.setHasSeenStatTutorial(true);

      const parsed = JSON.parse(localStorage.getItem("futureproof-build")!);
      // partialize() should filter to ONLY hasSeenStatTutorial.
      // Persisting tieredCareers/build would stale-fill the store on refresh.
      expect(parsed.state.tieredCareers).toBeUndefined();
      expect(parsed.state.build).toBeUndefined();
      expect(parsed.state.hasSeenStatTutorial).toBe(true);
    });
  });
});
