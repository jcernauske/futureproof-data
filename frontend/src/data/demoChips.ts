/**
 * Demo chip slate — 10 (school, major) combos verified to return full
 * pentagons (non-null ERN, ROI, RES, GRW, AURA) through the production
 * intent → build flow.
 *
 * Each entry carries a full SchoolSelection so a chip click can skip the
 * SchoolSearch step. The cost fields were captured from
 * consumable_program_career_paths at the time of verification — they
 * track the same source the live SchoolSearch returns, so they shouldn't
 * drift mid-cycle.
 *
 * Picked for variety: 5 STEM, 2 social sciences, 1 business, 1 healthcare,
 * 1 arts (deliberately low-ROI tradeoff case to show the pentagon tells
 * an honest story even when the numbers don't flatter the choice).
 *
 * Verification methodology + raw output: /tmp/verify_demo_combos.py +
 * /tmp/verified_combos.json (kept out of the repo on purpose — re-run
 * the script after any gold-pipeline regen).
 */

import type { SchoolSelection } from "@/types/buildInput";

export interface DemoChip {
  school: SchoolSelection;
  /** What gets typed into the major input — drives the live intent stream. */
  majorText: string;
  /** Short display label for the chip (school + major in compact form). */
  label: string;
}

/**
 * A two-school pair where everything is equal except the price tag.
 * Drives the "same major, different cost" section of the demo drawer.
 * Both pentagons are populated; ROI gap is meaningful (>=2 points).
 * Each side renders as a normal DemoChip — clicking it follows the
 * same intent → build flow as a single pick.
 */
export interface ComparisonPair {
  major: string;
  better: DemoChip;
  worse: DemoChip;
}

export const DEMO_CHIPS: DemoChip[] = [
  {
    school: {
      unitid: 110635,
      name: "University of California-Berkeley",
      institutionControl: "Public",
      stateAbbr: "CA",
      netPriceAnnual: 14979,
      costOfAttendanceAnnual: 42708,
      tuitionInState: 14850,
      tuitionOutOfState: 45627,
    },
    majorText: "Computer Science",
    label: "UC Berkeley · Computer Science",
  },
  {
    school: {
      unitid: 243744,
      name: "Stanford University",
      institutionControl: "Private nonprofit",
      stateAbbr: "CA",
      netPriceAnnual: 12136,
      costOfAttendanceAnnual: 82162,
      tuitionInState: 62484,
      tuitionOutOfState: 62484,
    },
    majorText: "Computer Science",
    label: "Stanford · Computer Science",
  },
  {
    school: {
      unitid: 166683,
      name: "Massachusetts Institute of Technology",
      institutionControl: "Private nonprofit",
      stateAbbr: "MA",
      netPriceAnnual: 19813,
      costOfAttendanceAnnual: 79850,
      tuitionInState: 60156,
      tuitionOutOfState: 60156,
    },
    majorText: "Electrical Engineering",
    label: "MIT · Electrical Engineering",
  },
  {
    school: {
      unitid: 139755,
      name: "Georgia Institute of Technology-Main Campus",
      institutionControl: "Public",
      stateAbbr: "GA",
      netPriceAnnual: 13289,
      costOfAttendanceAnnual: 27797,
      tuitionInState: 11764,
      tuitionOutOfState: 32876,
    },
    majorText: "Industrial Engineering",
    label: "Georgia Tech · Industrial Engineering",
  },
  {
    school: {
      unitid: 170976,
      name: "University of Michigan-Ann Arbor",
      institutionControl: "Public",
      stateAbbr: "MI",
      netPriceAnnual: 14832,
      costOfAttendanceAnnual: 33345,
      tuitionInState: 17228,
      tuitionOutOfState: 58072,
    },
    majorText: "Mechanical Engineering",
    label: "Michigan · Mechanical Engineering",
  },
  {
    school: {
      unitid: 228778,
      name: "The University of Texas at Austin",
      institutionControl: "Public",
      stateAbbr: "TX",
      netPriceAnnual: 19678,
      costOfAttendanceAnnual: 29842,
      tuitionInState: 11678,
      tuitionOutOfState: 42778,
    },
    majorText: "Nursing",
    label: "UT Austin · Nursing",
  },
  {
    school: {
      unitid: 151351,
      name: "Indiana University-Bloomington",
      institutionControl: "Public",
      stateAbbr: "IN",
      netPriceAnnual: 15342,
      costOfAttendanceAnnual: 27361,
      tuitionInState: 11790,
      tuitionOutOfState: 40482,
    },
    majorText: "Marketing",
    label: "Indiana · Marketing",
  },
  {
    school: {
      unitid: 110662,
      name: "University of California-Los Angeles",
      institutionControl: "Public",
      stateAbbr: "CA",
      netPriceAnnual: 14013,
      costOfAttendanceAnnual: 36643,
      tuitionInState: 13747,
      tuitionOutOfState: 44524,
    },
    majorText: "Psychology",
    label: "UCLA · Psychology",
  },
  {
    school: {
      unitid: 166027,
      name: "Harvard University",
      institutionControl: "Private nonprofit",
      stateAbbr: "MA",
      netPriceAnnual: 16816,
      costOfAttendanceAnnual: 82842,
      tuitionInState: 59076,
      tuitionOutOfState: 59076,
    },
    majorText: "Economics",
    label: "Harvard · Economics",
  },
  {
    school: {
      unitid: 193900,
      name: "New York University",
      institutionControl: "Private nonprofit",
      stateAbbr: "NY",
      netPriceAnnual: 35035,
      costOfAttendanceAnnual: 79121,
      tuitionInState: 60438,
      tuitionOutOfState: 60438,
    },
    majorText: "Film",
    label: "NYU · Film",
  },
];

/**
 * Three cost-comparison pairs. Same major across both schools; the only
 * meaningful difference is the cost-of-attendance, which propagates to a
 * visibly different ROI score on the pentagon. Both schools genuinely
 * teach the listed major (no crosswalk artifacts), both pentagons are
 * fully populated, and the ROI gap is at least 2 points.
 *
 * Verified via /tmp/verify_comparison_pairs.py against the live intent
 * → build flow at the time of authoring.
 */
export const DEMO_COMPARISONS: ComparisonPair[] = [
  // CS — UC Berkeley public ($43k) vs Boston University private ($83k).
  // Same matched_cip (11.0701), identical ERN (10) — ROI gap of 4 is
  // entirely the cost story.
  {
    major: "Computer Science",
    better: {
      school: {
        unitid: 110635,
        name: "University of California-Berkeley",
        institutionControl: "Public",
        stateAbbr: "CA",
        netPriceAnnual: 14979,
        costOfAttendanceAnnual: 42708,
        tuitionInState: 14850,
        tuitionOutOfState: 45627,
      },
      majorText: "Computer Science",
      label: "UC Berkeley · CS",
    },
    worse: {
      school: {
        unitid: 164988,
        name: "Boston University",
        institutionControl: "Private nonprofit",
        stateAbbr: "MA",
        netPriceAnnual: 26996,
        costOfAttendanceAnnual: 82694,
        tuitionInState: 65168,
        tuitionOutOfState: 65168,
      },
      majorText: "Computer Science",
      label: "Boston University · CS",
    },
  },
  // Industrial Engineering — Georgia Tech ($28k) vs Northwestern ($88k).
  // Both top-tier IE programs, same ERN, 3-point ROI gap from 3.2x cost.
  {
    major: "Industrial Engineering",
    better: {
      school: {
        unitid: 139755,
        name: "Georgia Institute of Technology-Main Campus",
        institutionControl: "Public",
        stateAbbr: "GA",
        netPriceAnnual: 13289,
        costOfAttendanceAnnual: 27797,
        tuitionInState: 11764,
        tuitionOutOfState: 32876,
      },
      majorText: "Industrial Engineering",
      label: "Georgia Tech · Industrial Eng",
    },
    worse: {
      school: {
        unitid: 147767,
        name: "Northwestern University",
        institutionControl: "Private nonprofit",
        stateAbbr: "IL",
        netPriceAnnual: 27143,
        costOfAttendanceAnnual: 87804,
        tuitionInState: 65997,
        tuitionOutOfState: 65997,
      },
      majorText: "Industrial Engineering",
      label: "Northwestern · Industrial Eng",
    },
  },
  // Marketing — Indiana Kelley ($27k) vs Northwestern ($88k).
  // Northwestern's career list is a 100% subset of IU's, so a judge
  // clicking both lands on the same destination SOCs and the only
  // visible delta is the cost-driven pentagon. (Boston University was
  // the original "worse" side but its CIP→SOC crosswalk diverged from
  // IU's, breaking the apples-to-apples read.)
  {
    major: "Marketing",
    better: {
      school: {
        unitid: 151351,
        name: "Indiana University-Bloomington",
        institutionControl: "Public",
        stateAbbr: "IN",
        netPriceAnnual: 15342,
        costOfAttendanceAnnual: 27361,
        tuitionInState: 11790,
        tuitionOutOfState: 40482,
      },
      majorText: "Marketing",
      label: "Indiana · Marketing",
    },
    worse: {
      school: {
        unitid: 147767,
        name: "Northwestern University",
        institutionControl: "Private nonprofit",
        stateAbbr: "IL",
        netPriceAnnual: 27143,
        costOfAttendanceAnnual: 87804,
        tuitionInState: 65997,
        tuitionOutOfState: 65997,
      },
      majorText: "Marketing",
      label: "Northwestern · Marketing",
    },
  },
];
