import { describe, it, expect } from "vitest";
import {
  eduRank,
  relatednessTier,
  sortBranchesInLane,
  bucketBranches,
  dominantStatDelta,
  socRollup,
  truncateTitle,
} from "./horizonLayout";
import type { CareerBranch } from "@/types/build";

/**
 * horizonLayout.test.ts — Tests for the pure-function lane assignment
 * module that powers the /branch-tree horizon map.
 *
 * Every assertion here calls real production code with real fixtures.
 * No mocks, no spies — these are pure-function tests in the strictest
 * sense: input → output, deterministic, side-effect-free.
 *
 * Hunting for:
 *  - eduRank correctness across all 8 known education levels + null
 *  - relatednessTier derivation per D#17 (boundaries 1, 5, 6, 10, 11, 20, null)
 *  - sortBranchesInLane (tier ASC, relatedness ASC tiebreak — most-related-first)
 *  - bucketBranches lane cap (6) + totalBeforeCap reporting
 *  - bucketBranches hideSupplemental filter
 *  - bucketBranches stable sort within identical tier+relatedness
 *  - dominantStatDelta picks largest abs(delta), preserves sign
 *  - truncateTitle word-boundary aware truncation
 */

// --- Test fixtures ---

function makeBranch(overrides: Partial<CareerBranch> = {}): CareerBranch {
  return {
    from_soc: "13-2051",
    to_soc: "11-3031",
    to_title: "Financial Manager",
    delta_ern: null,
    delta_roi: null,
    delta_res: null,
    delta_grw: null,
    delta_hmn: null,
    unlock: null,
    relatedness: null,
    experience_years: null,
    experience_tier: null,
    experience_delta: null,
    related_education_level: null,
    ...overrides,
  };
}

// --- eduRank ---

describe("eduRank", () => {
  it("test_eduRank_returns_correct_ranks_for_all_8_known_education_levels", () => {
    expect(eduRank("High school diploma or equivalent")).toBe(0);
    expect(eduRank("No formal educational credential")).toBe(1);
    expect(eduRank("Postsecondary nondegree award")).toBe(1);
    expect(eduRank("Some college, no degree")).toBe(1);
    expect(eduRank("Associate's degree")).toBe(2);
    expect(eduRank("Bachelor's degree")).toBe(3);
    expect(eduRank("Master's degree")).toBe(4);
    expect(eduRank("Doctoral or professional degree")).toBe(5);
  });

  it("test_eduRank_null_returns_null", () => {
    expect(eduRank(null)).toBeNull();
    expect(eduRank(undefined)).toBeNull();
  });

  it("test_eduRank_unknown_string_returns_null", () => {
    expect(eduRank("Some bizarre custom level")).toBeNull();
    expect(eduRank("")).toBeNull();
  });
});

// --- relatednessTier (D#17 derivation) ---

describe("relatednessTier", () => {
  it("test_relatednessTier_boundaries_1_through_5_are_PrimaryShort", () => {
    expect(relatednessTier(1)).toBe("Primary-Short");
    expect(relatednessTier(5)).toBe("Primary-Short");
  });

  it("test_relatednessTier_boundaries_6_through_10_are_PrimaryLong", () => {
    expect(relatednessTier(6)).toBe("Primary-Long");
    expect(relatednessTier(10)).toBe("Primary-Long");
  });

  it("test_relatednessTier_boundaries_11_and_above_are_Supplemental", () => {
    expect(relatednessTier(11)).toBe("Supplemental");
    expect(relatednessTier(20)).toBe("Supplemental");
    expect(relatednessTier(99)).toBe("Supplemental");
  });

  it("test_relatednessTier_null_returns_null", () => {
    expect(relatednessTier(null)).toBeNull();
    expect(relatednessTier(undefined)).toBeNull();
  });
});

// --- sortBranchesInLane ---

describe("sortBranchesInLane", () => {
  it("test_sortBranchesInLane_respects_derived_tier_order_then_relatedness_ASC", () => {
    // Build a mixed-tier list. Expected order after sort:
    //   Primary-Short (1, 5) → Primary-Long (6, 10) → Supplemental (11, 20) → null
    // Within tier: relatedness ASC (most-related first since 1 = best_index).
    const input: CareerBranch[] = [
      makeBranch({ to_soc: "supp-20", relatedness: 20 }),
      makeBranch({ to_soc: "ps-5", relatedness: 5 }),
      makeBranch({ to_soc: "null-rel", relatedness: null }),
      makeBranch({ to_soc: "pl-10", relatedness: 10 }),
      makeBranch({ to_soc: "ps-1", relatedness: 1 }),
      makeBranch({ to_soc: "pl-6", relatedness: 6 }),
      makeBranch({ to_soc: "supp-11", relatedness: 11 }),
    ];

    const out = sortBranchesInLane(input);
    const ids = out.map((b) => b.to_soc);

    expect(ids).toEqual([
      "ps-1",
      "ps-5",
      "pl-6",
      "pl-10",
      "supp-11",
      "supp-20",
      "null-rel",
    ]);
  });

  it("test_sortBranchesInLane_does_not_mutate_input", () => {
    const input: CareerBranch[] = [
      makeBranch({ to_soc: "a", relatedness: 10 }),
      makeBranch({ to_soc: "b", relatedness: 1 }),
    ];
    const inputBefore = input.map((b) => b.to_soc);
    sortBranchesInLane(input);
    expect(input.map((b) => b.to_soc)).toEqual(inputBefore);
  });

  it("test_sortBranchesInLane_empty_array_returns_empty", () => {
    expect(sortBranchesInLane([])).toEqual([]);
  });
});

// --- bucketBranches ---

describe("bucketBranches", () => {
  it("test_bucketBranches_caps_lanes_at_6_and_reports_totalBeforeCap", () => {
    // 21 branches all bucketing to Business by SOC major group.
    const branches: CareerBranch[] = Array.from({ length: 21 }, (_, i) =>
      makeBranch({
        to_soc: `11-300${i}`,
        relatedness: i + 1,
        related_education_level: "Bachelor's degree",
      }),
    );

    const out = bucketBranches(branches, "Bachelor's degree", false);

    expect(out.business.branches.length).toBe(6);
    expect(out.business.totalBeforeCap).toBe(21);
    expect(out.technical.branches.length).toBe(0);
    expect(out.technical.totalBeforeCap).toBe(0);
    expect(out.arts.branches.length).toBe(0);
    expect(out.arts.totalBeforeCap).toBe(0);
  });

  it("test_bucketBranches_with_hideSupplemental_excludes_supplemental_tier", () => {
    // Mix: 2 PS, 2 PL, 4 Supp — all Business.
    const branches: CareerBranch[] = [
      makeBranch({ to_soc: "11-1001", relatedness: 1, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1002", relatedness: 4, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1003", relatedness: 7, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1004", relatedness: 9, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1005", relatedness: 12, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1006", relatedness: 15, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1007", relatedness: 18, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1008", relatedness: 21, related_education_level: "Bachelor's degree" }),
    ];

    const out = bucketBranches(branches, "Bachelor's degree", true);

    // Supplementals removed across all lanes
    expect(out.business.branches.length).toBe(4);
    expect(out.business.totalBeforeCap).toBe(4);
    for (const b of out.business.branches) {
      expect(relatednessTier(b.relatedness)).not.toBe("Supplemental");
    }
  });

  it("test_bucketBranches_hideSupplemental_off_includes_supplementals", () => {
    const branches: CareerBranch[] = [
      makeBranch({ to_soc: "11-1011", relatedness: 1, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "11-1012", relatedness: 15, related_education_level: "Bachelor's degree" }),
    ];

    const out = bucketBranches(branches, "Bachelor's degree", false);
    expect(out.business.branches.length).toBe(2);
  });

  it("test_bucketBranches_distributes_across_soc_taxonomy_lanes", () => {
    const branches: CareerBranch[] = [
      makeBranch({ to_soc: "11-3031", relatedness: 1, related_education_level: "Bachelor's degree" }),
      makeBranch({ to_soc: "15-2051", relatedness: 2, related_education_level: "Master's degree" }),
      makeBranch({
        to_soc: "27-1024",
        relatedness: 3,
        related_education_level: "Doctoral or professional degree",
      }),
    ];

    const out = bucketBranches(branches, "Bachelor's degree", false);

    expect(out.business.branches.map((b) => b.to_soc)).toEqual(["11-3031"]);
    expect(out.technical.branches.map((b) => b.to_soc)).toEqual(["15-2051"]);
    expect(out.arts.branches.map((b) => b.to_soc)).toEqual(["27-1024"]);
  });

  it("test_bucketBranches_preserves_stable_sort_within_identical_tier_and_relatedness", () => {
    // Two branches with identical tier+relatedness — input order should be preserved.
    const branches: CareerBranch[] = [
      makeBranch({
        to_soc: "11-1001",
        relatedness: 3,
        related_education_level: "Bachelor's degree",
      }),
      makeBranch({
        to_soc: "11-1002",
        relatedness: 3,
        related_education_level: "Bachelor's degree",
      }),
      makeBranch({
        to_soc: "11-1003",
        relatedness: 3,
        related_education_level: "Bachelor's degree",
      }),
    ];

    const out = bucketBranches(branches, "Bachelor's degree", false);
    expect(out.business.branches.map((b) => b.to_soc)).toEqual([
      "11-1001",
      "11-1002",
      "11-1003",
    ]);
  });

  it("test_bucketBranches_totalBeforeCap_reflects_post_filter_count", () => {
    // 10 supplementals + 3 primary-short, all Business.
    // With hideSupplemental=true: filtered list is 3, so totalBeforeCap=3.
    const branches: CareerBranch[] = [
      ...Array.from({ length: 10 }, (_, i) =>
        makeBranch({
          to_soc: `11-20${i}`,
          relatedness: 12 + i,
          related_education_level: "Bachelor's degree",
        }),
      ),
      ...Array.from({ length: 3 }, (_, i) =>
        makeBranch({
          to_soc: `11-30${i}`,
          relatedness: i + 1,
          related_education_level: "Bachelor's degree",
        }),
      ),
    ];

    const out = bucketBranches(branches, "Bachelor's degree", true);
    expect(out.business.totalBeforeCap).toBe(3);
    expect(out.business.branches.length).toBe(3);
  });

  it("test_bucketBranches_custom_laneCap_option", () => {
    // Pass a custom cap (used by the expand-all path in BranchHorizonMap).
    const branches: CareerBranch[] = Array.from({ length: 10 }, (_, i) =>
      makeBranch({
        to_soc: `11-40${i}`,
        relatedness: i + 1,
        related_education_level: "Bachelor's degree",
      }),
    );

    const out = bucketBranches(branches, "Bachelor's degree", false, {
      laneCap: Number.MAX_SAFE_INTEGER,
    });
    expect(out.business.branches.length).toBe(10);
    expect(out.business.totalBeforeCap).toBe(10);
  });

  it("test_bucketBranches_empty_input_returns_all_taxonomy_lanes_empty", () => {
    const out = bucketBranches([], "Bachelor's degree", false);
    for (const lane of Object.values(out)) {
      expect(lane.branches).toEqual([]);
      expect(lane.totalBeforeCap).toBe(0);
    }
  });
});

// --- dominantStatDelta ---

describe("dominantStatDelta", () => {
  it("test_dominantStatDelta_picks_largest_abs_delta_preserves_sign", () => {
    const branch = makeBranch({
      delta_ern: 5,
      delta_grw: -8,
      delta_hmn: 3,
      delta_res: null,
    });
    const out = dominantStatDelta(branch);
    expect(out).toEqual({ stat: "grw", value: -8 });
  });

  it("test_dominantStatDelta_all_null_returns_null", () => {
    const branch = makeBranch({});
    expect(dominantStatDelta(branch)).toBeNull();
  });

  it("test_dominantStatDelta_all_zero_returns_null", () => {
    const branch = makeBranch({
      delta_ern: 0,
      delta_grw: 0,
      delta_hmn: 0,
      delta_res: 0,
    });
    expect(dominantStatDelta(branch)).toBeNull();
  });

  it("test_dominantStatDelta_excludes_roi_per_spec", () => {
    // delta_roi is intentionally NOT considered. If only delta_roi is set,
    // result is null; if delta_roi has a much larger magnitude than the
    // other stats, it still doesn't win.
    const branchOnlyRoi = makeBranch({ delta_roi: 99 });
    expect(dominantStatDelta(branchOnlyRoi)).toBeNull();

    const branchRoiVsErn = makeBranch({ delta_roi: 99, delta_ern: 2 });
    expect(dominantStatDelta(branchRoiVsErn)).toEqual({ stat: "ern", value: 2 });
  });

  it("test_dominantStatDelta_positive_value_returned_correctly", () => {
    const branch = makeBranch({ delta_ern: 12, delta_grw: 3 });
    expect(dominantStatDelta(branch)).toEqual({ stat: "ern", value: 12 });
  });

  it("test_dominantStatDelta_first_match_wins_on_tie", () => {
    // Iteration order is ern → grw → hmn → res; on equal abs values, first wins.
    const branch = makeBranch({ delta_ern: 5, delta_grw: -5 });
    expect(dominantStatDelta(branch)).toEqual({ stat: "ern", value: 5 });
  });
});

// --- truncateTitle ---

describe("truncateTitle", () => {
  it("test_truncateTitle_short_string_unchanged", () => {
    expect(truncateTitle("Financial Analyst")).toBe("Financial Analyst");
  });

  it("test_truncateTitle_at_max_length_unchanged", () => {
    const exactly32 = "A".repeat(32);
    expect(truncateTitle(exactly32)).toBe(exactly32);
  });

  it("test_truncateTitle_word_boundary_aware_truncation", () => {
    // "Postsecondary Education Administrators" = 38 chars, exceeds 32.
    // Last space before idx 31 is at "Postsecondary Education " — should cut there.
    const title = "Postsecondary Education Administrators";
    const out = truncateTitle(title);
    expect(out.length).toBeLessThanOrEqual(33); // allow ellipsis byte
    expect(out.endsWith("…")).toBe(true);
    // Should NOT cut mid-word — last char before … should be a non-space letter
    // and the prefix should be a clean word boundary.
    expect(out).toMatch(/^[A-Za-z ]+…$/);
  });

  it("test_truncateTitle_long_single_word_falls_through_to_hard_cut", () => {
    // No spaces at all → the word-boundary check fails (lastSpace = -1) and
    // we fall through to the hard cut at maxLen-1 + ellipsis.
    const long = "A".repeat(50);
    const out = truncateTitle(long);
    expect(out.length).toBe(32);
    expect(out.endsWith("…")).toBe(true);
  });

  it("test_truncateTitle_custom_maxLen", () => {
    expect(truncateTitle("Hello World Foo", 8)).toMatch(/…$/);
    const out = truncateTitle("Hello World Foo", 8);
    expect(out.length).toBeLessThanOrEqual(9);
  });

  it("test_truncateTitle_50_char_input_returns_at_most_33_chars_with_ellipsis", () => {
    const fifty = "Senior Information Security Specialist Position!"; // 49 chars
    const out = truncateTitle(fifty);
    expect(out.length).toBeLessThanOrEqual(33);
    expect(out.endsWith("…")).toBe(true);
  });
});

describe("socRollup", () => {
  it("returns null for null/undefined/empty soc", () => {
    expect(socRollup(null)).toBeNull();
    expect(socRollup(undefined)).toBeNull();
    expect(socRollup("")).toBeNull();
  });

  it("returns null for unknown major group", () => {
    expect(socRollup("99-9999")).toBeNull();
    expect(socRollup("55-1010")).toBeNull(); // 55 = Military, intentionally not mapped
    expect(socRollup("ab-cdef")).toBeNull();
  });

  it("buckets all 5 Business major groups (11/13/23/41/43)", () => {
    expect(socRollup("11-9121")).toBe("business"); // Natural Sciences Managers
    expect(socRollup("13-2051")).toBe("business"); // Financial Analyst
    expect(socRollup("23-1011")).toBe("business"); // Lawyers
    expect(socRollup("41-2031")).toBe("business"); // Retail Salespersons
    expect(socRollup("43-9111")).toBe("business"); // Statistical Assistants
  });

  it("buckets all 3 Technical major groups (15/17/19)", () => {
    expect(socRollup("15-2051")).toBe("technical"); // Data Scientists
    expect(socRollup("17-2051")).toBe("technical"); // Civil Engineers
    expect(socRollup("19-3033")).toBe("technical"); // Industrial-Organizational Psychologists
  });

  it("buckets Arts & Creativity (27)", () => {
    expect(socRollup("27-1024")).toBe("arts"); // Graphic Designers
    expect(socRollup("27-2042")).toBe("arts"); // Musicians and Singers
  });

  it("buckets Education & Community (21/25)", () => {
    expect(socRollup("21-1023")).toBe("education"); // Mental Health Counselors
    expect(socRollup("25-1011")).toBe("education"); // Business Teachers, Postsecondary
  });

  it("buckets Care (29/31/33)", () => {
    expect(socRollup("29-1141")).toBe("care"); // Registered Nurses
    expect(socRollup("31-9092")).toBe("care"); // Medical Assistants
    expect(socRollup("33-2011")).toBe("care"); // Firefighters
  });

  it("buckets Service (35/37/39)", () => {
    expect(socRollup("35-1011")).toBe("service"); // Chefs and Head Cooks
    expect(socRollup("37-2011")).toBe("service"); // Janitors
    expect(socRollup("39-5012")).toBe("service"); // Hairdressers
  });

  it("buckets Trades (45/47/49/51/53)", () => {
    expect(socRollup("45-1011")).toBe("trades"); // First-Line Supervisors of Farming
    expect(socRollup("47-2031")).toBe("trades"); // Carpenters
    expect(socRollup("49-9021")).toBe("trades"); // HVAC Mechanics and Installers
    expect(socRollup("51-1011")).toBe("trades"); // First-Line Supervisors of Production
    expect(socRollup("53-3032")).toBe("trades"); // Heavy and Tractor-Trailer Truck Drivers
  });

  it("uses only the first 2 chars (ignores remainder)", () => {
    expect(socRollup("15-9999")).toBe("technical");
    expect(socRollup("11-1234.56")).toBe("business");
    expect(socRollup("11")).toBe("business"); // Just the major group prefix
  });

  it("handles a real DePaul Data-Scientist build's branches end-to-end", () => {
    // Mirrors the distribution observed at runtime: 7 Computer/Math + 4 Business
    // + 2 Mgmt + 2 Sciences + 1 Office Admin → expected 9 technical + 7 business.
    const fixtureSocs = [
      "11-9121", "11-3021",                                   // 2 Mgmt
      "15-2041", "15-1211", "15-2051", "15-1252", "15-1244", "15-1232", "15-2031", // 7 CompMath
      "13-1161", "13-2051", "13-1031", "13-1071",            // 4 Business/Finance
      "19-3033", "19-3011",                                   // 2 Sciences
      "43-9111",                                              // 1 Office Admin
    ];
    const buckets = fixtureSocs.map(socRollup);
    const technical = buckets.filter((b) => b === "technical").length;
    const business = buckets.filter((b) => b === "business").length;
    expect(technical).toBe(9); // 15* + 19* = 7 + 2
    expect(business).toBe(7);  // 11* + 13* + 43* = 2 + 4 + 1
    expect(buckets.every((b) => b !== null)).toBe(true);
  });
});
