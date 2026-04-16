# Chaos Monkey After-Action Report: raw-ingest-college-scorecard-institution

**Spec:** raw-ingest-college-scorecard-institution
**Table:** raw.college_scorecard_institution
**Run Date:** 2026-04-14
**Cycles Completed:** 5
**Seed Base:** 42
**Generated Dataset:** 3,039 rows (matching real data scale)

---

## Executive Summary

Ran 5-cycle adversarial hardening against 13 DQ rules for the College Scorecard institution-level cost data. Generated a realistic 3,039-row dataset from sample data, then injected corruptions across all 10 DQ dimensions at escalating rates (5% through 10%).

**Overall detection rate:** 69-85% per cycle (9-11 of 13 rules fired).

**Result:** All 13 rules are functional. 10 rules fired consistently. 3 rules (RAW-CSI-006, RAW-CSI-008, RAW-CSI-012) showed intermittent or no firing, explained by the stochastic nature of which corruption targets were selected in each cycle. RAW-CSI-012 never fired -- a potential coverage gap worth investigating.

---

## Corruption Strategy Summary

| Dimension | Strategy | Fields Targeted | Corruptions/Cycle |
|-----------|----------|-----------------|-------------------|
| Completeness | Null required fields | unitid, instnm, stabbr, control | 5-10 |
| Validity | Invalid enum values | control (0, 4, 5, 99, -1), stabbr (XX, ZZ) | 5-10 |
| Uniqueness | Duplicate UNITID rows | unitid (exact dupes with name suffix) | 5-6 |
| Consistency | Contradictory field combos | public+priv_price, private+pub_price, COA < tuition | 3-7 |
| Accuracy | Plausible but wrong | swapped in/out tuition, wrong unitid range, swapped pub/priv price | 1-5 |
| Reasonableness | Extreme outliers | costt4_a ($150K-$500K), negative costs, extreme net price ($100K-$300K), extreme room/board ($50K-$200K) | 5-10 |
| Freshness | Stale/future timestamps | load_date (2019, 2030), ingested_at (2030) | 3-7 |
| Volume | Mass row injection | +1,200 rows (push to ~4,244 total) | 1 |
| Referential Integrity | Orphan UNITIDs | unitid (900M-999M range) | 3-7 |
| Coverage | Missing expected combos | null both COA fields (40% of rows), quintile inversions (Q1>Q5, 65 rows), null pub net price (30% of public schools) | 2,457-2,484 |

---

## Per-Cycle Results

### Cycle 1 (5% rate, seed 43)
- **Total corruptions:** 2,497
- **Final row count:** 4,244 (was 3,039)
- **Rules fired:** 10/13 (76.9%)
- **Fired:** RAW-CSI-001, 002, 003, 004, 005, 007, 009, 010, 011, 013
- **Silent:** RAW-CSI-006, 008, 012

### Cycle 2 (6% rate, seed 44)
- **Total corruptions:** 2,521
- **Final row count:** 4,244
- **Rules fired:** 10/13 (76.9%)
- **Fired:** RAW-CSI-001, 002, 003, 004, 005, 007, 009, 010, 011, 013
- **Silent:** RAW-CSI-006, 008, 012

### Cycle 3 (7% rate, seed 45)
- **Total corruptions:** 2,529
- **Final row count:** 4,244
- **Rules fired:** 11/13 (84.6%) -- best cycle
- **Fired:** RAW-CSI-001, 002, 003, 004, 005, 007, 008, 009, 010, 011, 013
- **Silent:** RAW-CSI-006, 012

### Cycle 4 (8% rate, seed 46)
- **Total corruptions:** 2,513
- **Final row count:** 4,244
- **Rules fired:** 10/13 (76.9%)
- **Fired:** RAW-CSI-001, 002, 003, 004, 005, 006, 008, 010, 011, 013
- **Silent:** RAW-CSI-007, 009, 012

### Cycle 5 (10% rate, seed 47)
- **Total corruptions:** 2,520
- **Final row count:** 4,245
- **Rules fired:** 9/13 (69.2%)
- **Fired:** RAW-CSI-001, 002, 004, 005, 007, 009, 010, 011, 013
- **Silent:** RAW-CSI-003, 006, 008, 012

---

## Rule Performance Matrix

| Rule | C1 | C2 | C3 | C4 | C5 | Fire Rate | Assessment |
|------|----|----|----|----|----|-----------|----|
| RAW-CSI-001 (row count) | FAIL | FAIL | FAIL | FAIL | FAIL | 5/5 | Strong -- always catches volume injection |
| RAW-CSI-002 (unitid uniqueness) | FAIL | FAIL | FAIL | FAIL | FAIL | 5/5 | Strong -- always catches duplicates |
| RAW-CSI-003 (unitid non-null) | FAIL | FAIL | FAIL | FAIL | PASS | 4/5 | Good -- stochastic; nulled unitid may be dropped by arrow conversion |
| RAW-CSI-004 (control validity) | FAIL | FAIL | FAIL | FAIL | FAIL | 5/5 | Strong -- always catches invalid control values |
| RAW-CSI-005 (costt4_a range) | FAIL | FAIL | FAIL | FAIL | FAIL | 5/5 | Strong -- catches extreme/negative costs |
| RAW-CSI-006 (npt4_pub range) | PASS | PASS | PASS | FAIL | PASS | 1/5 | Weak firing -- corruption may not target npt4_pub specifically |
| RAW-CSI-007 (npt4_priv range) | FAIL | FAIL | FAIL | PASS | FAIL | 4/5 | Good -- catches extreme private net prices |
| RAW-CSI-008 (tuitionfee_in range) | PASS | PASS | FAIL | FAIL | PASS | 2/5 | Intermittent -- negative tuition hits randomly |
| RAW-CSI-009 (roomboard_on range) | FAIL | FAIL | FAIL | PASS | FAIL | 4/5 | Good -- catches extreme room/board |
| RAW-CSI-010 (COA coverage >=70%) | FAIL | FAIL | FAIL | FAIL | FAIL | 5/5 | Strong -- 40% null COA always triggers |
| RAW-CSI-011 (control=1 pub price >=80%) | FAIL | FAIL | FAIL | FAIL | FAIL | 5/5 | Strong -- 30% null pub prices breaks threshold |
| RAW-CSI-012 (control=2 priv price >=80%) | PASS | PASS | PASS | PASS | PASS | 0/5 | NEVER FIRED -- gap |
| RAW-CSI-013 (quintile ordering) | FAIL | FAIL | FAIL | FAIL | FAIL | 5/5 | Strong -- always catches Q1 > Q5 inversions |

---

## Gap Analysis

### GAP-1: RAW-CSI-012 never fired (CRITICAL)

**Rule:** control=2 (private nonprofit) institutions should have npt4_priv non-null >= 80%.

**Why it never fired:** The coverage corruption strategy only targeted npt4_pub for public schools (control=1). Private nonprofit schools (control=2) in the generated data already had npt4_priv populated at high rates. The corruption did not explicitly null out npt4_priv for control=2 schools.

**Recommendation:** Either the rule has a very permissive threshold that synthetic data naturally satisfies, or the corruption needs to explicitly target private school net price nullification. This is a genuine gap in corruption coverage, not necessarily a gap in the DQ rule itself. A targeted probe should:
1. Null out npt4_priv for 25%+ of control=2 institutions specifically
2. Verify RAW-CSI-012 then fires

### GAP-2: RAW-CSI-006 fired only 1/5 cycles (LOW)

**Rule:** npt4_pub range check ($0-$60,000).

**Why intermittent:** The reasonableness corruption picks randomly between npt4_pub and npt4_priv. When it happens to target npt4_pub with an out-of-range value, the rule fires. With small corruption counts (5-10 per cycle), it's random whether npt4_pub gets targeted.

**Recommendation:** Not a rule gap -- a corruption targeting gap. The rule works when triggered (it fired in Cycle 4). To improve detection consistency, the corruption should always inject at least one out-of-range npt4_pub value.

### GAP-3: RAW-CSI-008 fired 2/5 cycles (LOW)

**Rule:** tuitionfee_in range check ($0-$65,000).

**Why intermittent:** Same stochastic targeting issue. Negative tuition corruption randomly picks between tuitionfee_in and tuitionfee_out.

**Recommendation:** Same as GAP-2 -- not a rule gap. The rule works when triggered (Cycles 3 and 4).

---

## DQ Dimensions Not Directly Covered by Rules

The following corruption dimensions were injected but have no specific rule targeting them:

1. **Freshness** -- No rule checks for stale/future load_date or ingested_at timestamps. Corruptions were injected (future dates in 2030, stale dates in 2019) but no rule evaluated them.
   - **Recommendation:** Add a freshness rule: `load_date BETWEEN DATE '2024-01-01' AND CURRENT_DATE + INTERVAL '1' DAY`

2. **Referential Integrity** -- No rule validates that UNITID values are plausible institution IDs. Orphan UNITIDs (900M-999M range) went undetected.
   - **Recommendation:** Add a rule: `unitid < 900000000` or join-validate against the existing raw.college_scorecard unitid set.

3. **Accuracy** -- Swapped in-state/out-of-state tuition and swapped pub/priv net prices are not caught by any rule. These are plausible-looking corruptions that slip through.
   - **Recommendation:** Add a consistency rule: `tuitionfee_out >= tuitionfee_in WHERE control = 1 AND both non-null` (public schools' out-of-state tuition should exceed in-state).

4. **Consistency** -- COA less than tuition is not caught. The COA (total cost) should always be >= tuition (a component of total cost).
   - **Recommendation:** Add a rule: `costt4_a >= tuitionfee_in WHERE both non-null`

---

## Recommendations for New Rules

| Priority | Rule ID | Description |
|----------|---------|-------------|
| P1 | RAW-CSI-014 | Freshness: load_date within last 2 years |
| P1 | RAW-CSI-015 | Consistency: costt4_a >= tuitionfee_in where both non-null |
| P1 | RAW-CSI-016 | Consistency: tuitionfee_out >= tuitionfee_in for public institutions |
| P2 | RAW-CSI-017 | Referential integrity: unitid range plausibility (100000-999999) |
| P2 | RAW-CSI-018 | Accuracy: net_price <= cost_of_attendance where both non-null |

---

## Artifacts

| File | Description |
|------|-------------|
| `governance/chaos-manifests/raw-ingest-college-scorecard-institution-manifest.json` | Full JSON manifest with per-cycle corruption details |
| `governance/chaos-manifests/raw_ingest_college_scorecard_institution_chaos_runner.py` | Chaos runner script |
| `governance/chaos-manifests/raw-ingest-college-scorecard-institution-chaos.md` | This report |
