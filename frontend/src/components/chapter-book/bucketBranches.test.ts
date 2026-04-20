/**
 * bucketBranches — smoke tests covering each Bucketing Rule.
 *
 * Spec: docs/specs/feature-chapter-book.md §4 Service Changes + §4 New
 * Tests Required. Full P0/P1/P2 matrix is expanded by @test-writer in
 * spec step 4.
 */
import { describe, expect, it } from "vitest";
import { bucketBranches } from "./bucketBranches";
import { chapterCopy } from "./chapterCopy";
import { makeBranch, makeCareer, branchesFullArc } from "./__fixtures__/branches";

describe("bucketBranches", () => {
  it("buckets four tiers into four chapters when all present", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, branchesFullArc);
    expect(chapters.map((c) => c.tier)).toEqual([
      "entry",
      "early",
      "mid",
      "senior",
    ]);
    expect(chapters.map((c) => c.number)).toEqual([1, 2, 3, 4]);
    expect(chapters[0]!.kind).toBe("anchor");
    expect(chapters[1]!.kind).toBe("role");
    expect(chapters[2]!.kind).toBe("locked"); // Master's degree gate
    expect(chapters[3]!.kind).toBe("role");
  });

  it("drops branches with null experience_tier", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, [
      ...branchesFullArc,
      makeBranch({
        to_soc: "99-9999",
        to_title: "Rare Occupation",
        experience_tier: null,
      }),
    ]);
    // Full-arc plus the null-tier branch still produces four chapters —
    // the null-tier branch cannot appear anywhere.
    expect(chapters).toHaveLength(4);
    expect(chapters.some((c) => c.soc === "99-9999")).toBe(false);
  });

  it("filters self-referencing branches before bucketing", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, [
      makeBranch({
        to_soc: career.soc_code,
        to_title: career.occupation_title,
        experience_tier: "early",
        relatedness: 0.99,
      }),
      ...branchesFullArc,
    ]);
    // Self-reference MUST NOT appear as chapter 2 even though its
    // relatedness would win the sort.
    expect(chapters[1]!.soc).toBe("19-1022"); // Microbiologist
  });

  it("synthesizes terminating ceiling when senior tier missing", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, branchesFullArc.slice(0, 2));
    // early + mid present, senior absent → chapter 4 is terminating ceiling.
    expect(chapters).toHaveLength(4);
    expect(chapters[3]!.kind).toBe("ceiling");
    expect(chapters[3]!.soc).toBeNull();
  });

  it("produces two-chapter book when every non-anchor tier is empty", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, []);
    expect(chapters).toHaveLength(2);
    expect(chapters[0]!.kind).toBe("anchor");
    expect(chapters[1]!.kind).toBe("ceiling");
    expect(chapters[1]!.tier).toBe("early");
    expect(chapters[1]!.years_label).toBe("1+ yr");
  });

  it("bridges a middle-tier gap with a ceiling but continues the arc", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, [branchesFullArc[0]!, branchesFullArc[2]!]);
    // early + senior present, mid absent → chapter 3 is bridge ceiling.
    expect(chapters).toHaveLength(4);
    expect(chapters[2]!.kind).toBe("ceiling");
    expect(chapters[2]!.tier).toBe("mid");
    // And the senior chapter still renders.
    expect(chapters[3]!.kind).toBe("role");
    expect(chapters[3]!.soc).toBe("11-9121");
  });

  it("detects grad-degree via related_education_level (primary path)", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, [
      makeBranch({
        to_soc: "19-1042",
        to_title: "Medical Scientist",
        experience_tier: "early",
        related_education_level: "Master's degree",
        unlock: null,
      }),
    ]);
    expect(chapters[1]!.kind).toBe("locked");
    expect(chapters[1]!.requires_grad_degree).toBe(true);
  });

  it("falls back to unlock-regex when related_education_level is null", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, [
      makeBranch({
        to_soc: "11-1011",
        to_title: "Chief Executive",
        experience_tier: "early",
        related_education_level: null,
        unlock: "Master's preferred · 10+ yrs",
      }),
    ]);
    expect(chapters[1]!.kind).toBe("locked");
  });

  it("tie-breaks on to_soc lexicographic ascending at equal relatedness", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, [
      makeBranch({
        to_soc: "11-9121",
        to_title: "Later SOC",
        experience_tier: "mid",
        relatedness: 0.8,
      }),
      makeBranch({
        to_soc: "11-9041",
        to_title: "Earlier SOC",
        experience_tier: "mid",
        relatedness: 0.8,
      }),
    ]);
    expect(chapters[2]!.soc).toBe("11-9041");
  });

  it("anchor inherits requires_grad_degree from parent education_level_name", () => {
    const career = makeCareer({
      education_level_name: "Doctoral or professional degree",
    });
    const chapters = bucketBranches(career, []);
    expect(chapters[0]!.kind).toBe("anchor");
    expect(chapters[0]!.requires_grad_degree).toBe(true);
  });

  it("strips zero and null deltas from the pill row", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, [
      makeBranch({
        to_soc: "19-1022",
        to_title: "Microbiologist",
        experience_tier: "early",
        delta_ern: 1,
        delta_roi: 0,
        delta_res: null,
        delta_grw: 0,
        delta_hmn: -1,
      }),
    ]);
    expect(chapters[1]!.deltas).toEqual({ ern: 1, hmn: -1 });
  });

  it("anchor snapshot uses parent stats, not deltas", () => {
    const career = makeCareer({
      stats: { ern: 4, roi: 3, res: 2, grw: null, hmn: 3 },
    });
    const chapters = bucketBranches(career, []);
    expect(chapters[0]!.stats_snapshot).toEqual({ ern: 4, roi: 3, res: 2, hmn: 3 });
  });

  it("uses canonical year-label copy for populated chapters", () => {
    const career = makeCareer();
    const chapters = bucketBranches(career, branchesFullArc);
    expect(chapters[0]!.years_label).toBe(chapterCopy.years.entry);
    expect(chapters[1]!.years_label).toBe(chapterCopy.years.early);
    expect(chapters[2]!.years_label).toBe(chapterCopy.years.mid);
    expect(chapters[3]!.years_label).toBe(chapterCopy.years.senior);
  });
});
