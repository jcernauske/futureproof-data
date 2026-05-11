import { describe, it, expect, beforeEach } from "vitest";
import { useBuildStore } from "./buildStore";
import type { Build, CareerOutcome, TieredCareers } from "@/types/build";

/**
 * buildStore tests
 *
 * Covers the two contracts that matter:
 *   1. setTieredCareers accepts null (regression guard — used to be non-null)
 *   2. resetBuild clears build state
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
    wage_p10: null,
    wage_p25: null,
    wage_p75: null,
    wage_p90: null,
    earnings_1yr_median: null,
    earnings_1yr_p25: null,
    earnings_1yr_p75: null,
    debt_median: null,
    debt_to_earnings_annual: null,
    education_level_name: null,
    growth_category: null,
    work_experience_code: null,
    net_price_annual: null,
    cost_of_attendance_annual: null,
    published_cost_4yr: null,
    modeled_total_debt: null,
    debt_median_reference: null,
    institution_control: null,
    tuition_in_state: null,
    tuition_out_of_state: null,
    room_board_on_campus: null,
    stats: { ern: 8, roi: 7, res: 4, grw: 9, aura: 5 },
    bosses: { ai: 6, loans: 3, market: 2, burnout: 5, ceiling: 3 },
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
  };
}

beforeEach(() => {
  useBuildStore.setState({
    tieredCareers: null,
    selectedCareer: null,
    isBuilding: false,
    buildingStage: 0,
    buildingTotal: 0,
    completedSteps: new Set<string>(),
    build: null,
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
    it("clears build/selectedCareer/tieredCareers/isBuilding/buildingStage and progress fields", () => {
      const store = useBuildStore.getState();
      store.setTieredCareers({
        common: [makeCareer("15-1252")],
        less_common: [],
        stretch: [],
      });
      store.setSelectedCareer(makeCareer("15-1252"));
      store.setIsBuilding(true);
      store.setBuildingStage(3);
      store.setBuildingTotal(9);
      store.addCompletedStep("skeleton");
      store.setBuild({ build_id: "b-1" } as Build);

      store.resetBuild();

      const after = useBuildStore.getState();
      expect(after.tieredCareers).toBeNull();
      expect(after.selectedCareer).toBeNull();
      expect(after.build).toBeNull();
      expect(after.isBuilding).toBe(false);
      expect(after.buildingStage).toBe(0);
      expect(after.buildingTotal).toBe(0);
      expect(after.completedSteps.size).toBe(0);
    });
  });

  describe("setBuildingStage — function updater", () => {
    it("accepts a number directly", () => {
      useBuildStore.getState().setBuildingStage(5);
      expect(useBuildStore.getState().buildingStage).toBe(5);
    });

    it("accepts a function updater for safe concurrent increments", () => {
      useBuildStore.getState().setBuildingStage(3);
      useBuildStore.getState().setBuildingStage((prev) => prev + 1);
      useBuildStore.getState().setBuildingStage((prev) => prev + 1);
      expect(useBuildStore.getState().buildingStage).toBe(5);
    });
  });

  describe("addCompletedStep", () => {
    it("accumulates steps into the set", () => {
      const store = useBuildStore.getState();
      store.addCompletedStep("skeleton");
      store.addCompletedStep("boss_ai");
      store.addCompletedStep("boss_loans");
      const steps = useBuildStore.getState().completedSteps;
      expect(steps.has("skeleton")).toBe(true);
      expect(steps.has("boss_ai")).toBe(true);
      expect(steps.has("boss_loans")).toBe(true);
      expect(steps.size).toBe(3);
    });

    it("deduplicates — adding same step twice does not increase size", () => {
      const store = useBuildStore.getState();
      store.addCompletedStep("skeleton");
      store.addCompletedStep("skeleton");
      expect(useBuildStore.getState().completedSteps.size).toBe(1);
    });
  });

  describe("localStorage", () => {
    it("does not carry the legacy hasSeenStatTutorial key after store mutations", () => {
      // Regression guard: hasSeenStatTutorial was previously the sole
      // partialized field on this store. After removing the persist
      // middleware, no buildStore mutation should write the legacy key
      // back into localStorage under the old "futureproof-build" name.
      const store = useBuildStore.getState();
      store.setTieredCareers({
        common: [makeCareer()],
        less_common: [],
        stretch: [],
      });
      store.setBuild({ build_id: "b-persist-test" } as Build);

      const raw = localStorage.getItem("futureproof-build");
      if (raw === null) {
        expect(raw).toBeNull();
        return;
      }
      const parsed = JSON.parse(raw) as { state?: Record<string, unknown> };
      expect(parsed.state ?? {}).not.toHaveProperty("hasSeenStatTutorial");
    });
  });
});
