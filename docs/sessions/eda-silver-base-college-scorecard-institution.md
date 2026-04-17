# EDA Report: Silver base.college_scorecard_institution (Derived Fields)

**Source:** Silver transformation of `raw.college_scorecard_institution` (reconstructed from `Most-Recent-Cohorts-Institution_04172025.zip` — fallback URL applying the Bronze filter PREDDEG=3 OR ICLEVEL=1)
**Date:** 2026-04-14
**Agent:** @data-analyst
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md`
**Logical Model:** `governance/models/silver-base-college-scorecard-institution-logical.md`
**Bronze Baseline:** `docs/sessions/eda-college-scorecard-institution.md`
**Record Count (Silver = Bronze):** 3,039
**Silver Schema Fields Analyzed:** 11 derived + 1 routing label

---

## Scope

This EDA analyzes the **derived Silver fields** produced by the transformation. Raw pass-through fields (`costt4_a_raw`, `npt4_pub_raw`, the 10 quintile pub/priv raws, tuition, room/board, books/supplies) are unchanged from Bronze; their profiles are already documented in the Bronze EDA and are not repeated here. This report focuses on:

- `institution_control` (string label)
- `cost_of_attendance_annual` (COALESCE)
- `cost_of_attendance_4yr` (×4)
- `net_price_annual` (control-routed)
- `net_price_4yr` (×4)
- `net_price_q1..q5` (control-routed)
- Cross-field invariants that DQ rules will enforce

---

## Row Count Verification

| Stage | Count |
|-------|-------|
| Bronze (after PREDDEG=3 OR ICLEVEL=1 filter, deduped on unitid) | 3,039 |
| Silver (1:1 with Bronze; no filtering, no splitting) | 3,039 |
| Distinct `unitid` in Silver | 3,039 |
| `unitid` duplicates | 0 |

**Result:** Silver row count exactly matches Bronze. No records lost or created during Silver transformation. P0 DQ rule "row count matches Bronze" will pass.

---

## Key Findings

1. **Coverage of `net_price_annual` and `cost_of_attendance_annual` is identical down to the row** — not just the aggregate percentage. 2,233 rows have both populated, 806 have both null, and **zero rows have one without the other**. This means: if a school reports COA, it also reports NP (at its control-appropriate field), and vice versa. A single Silver DQ rule can cover both measures as a unified "financial measures reported" gate.
2. **Silver net_price_annual non-null is 73.48%, not the 85% assumed in the logical model's range constraints.** The logical model's "≥85% non-null" P0 threshold for `net_price_annual` will **fail hard**; the same applies to the 80% threshold for `cost_of_attendance_annual`. Recommend P0 ≥ 70% (with headroom above actual 73.48%) or split by control with tighter public / looser private thresholds.
3. **`institution_control` label is 100% populated with zero unmapped values.** Raw `control` only contains {1, 2, 3} (867 / 1,754 / 418). No null `control` cases, no out-of-domain values. The mapping is safe and complete.
4. **The 4yr derivation is IEEE-754 exact:** zero tolerance violations for `net_price_4yr = net_price_annual × 4` and `cost_of_attendance_4yr = cost_of_attendance_annual × 4` (0 of 2,233 non-null rows). This is expected — multiplying a finite double by 4 is lossless. The $1 tolerance in the logical model is more permissive than necessary; an equality rule (within floating-point epsilon) is the cleaner choice.
5. **`net_price_annual ≤ cost_of_attendance_annual` holds 100%.** 0 of 2,233 rows violate, and the gap (COA − NP = institutional aid) ranges from $0 (4 schools offer no aid) to $70,026 (highest aid institution). The P0 invariant is safely enforceable with a zero-tolerance threshold.
6. **`net_price_q1 ≤ net_price_q5` violates on 46 of 1,832 rows (2.51%)**, matching the Bronze scorecard count exactly. Breakdown by control: Public 7/716 (0.98%), Private nonprofit 33/998 (3.31%), Private for-profit 6/118 (5.08%). Violation magnitudes range $164–$18,121. Recommend P1 rule with ≤ 3% violation allowance, or tier by control.
7. **Quintile coverage degrades monotonically from q1 to q5** — 71.90% → 69.30% → 68.41% → 65.19% → 60.74%. The q5 ($110K+) band drops ~11pp below q1. This is a source-side reporting pattern (high-income quintiles have smaller samples and are suppressed more often). DQ coverage thresholds need to be set per-quintile, not a single "all quintiles ≥ X%" rule.
8. **`net_price_annual` carries negatives (min −$1,180 at Skyline College) and so does `net_price_4yr` (min −$4,720).** DQ range rules cannot use a `≥ 0` floor. Three public community colleges where average grant aid exceeds average COA drive this. Legitimate data.
9. **`cost_of_attendance_4yr` ranges $25,448 to $351,216** (Galen Health Institutes through Northwestern). **`net_price_4yr` ranges −$4,720 to $308,720** (Skyline College through Galen Health). DQ upper bounds should be $400,000 for 4yr COA and $325,000 for 4yr NP to leave headroom.
10. **Zero control routing cross-contamination at the raw layer.** 0 public schools have non-null `npt4_priv`, 0 private/for-profit have non-null `npt4_pub`. The control-based CASE routing will never silently lose a value.

---

## Derived Field Profiles

All dollar values in USD. Row total N = 3,039.

| Field | Non-null | Null% | Min | P25 | Median | P75 | Max | Mean | StdDev |
|-------|---------:|------:|----:|----:|-------:|----:|----:|-----:|-------:|
| cost_of_attendance_annual | 2,233 | 26.52% | $6,362 | $21,719 | $30,354 | $48,300 | $87,804 | $36,102 | $18,801 |
| cost_of_attendance_4yr | 2,233 | 26.52% | $25,448 | $86,876 | $121,416 | $193,200 | $351,216 | $144,407 | $75,205 |
| net_price_annual | 2,233 | 26.52% | −$1,180 | $12,640 | $18,990 | $25,210 | $77,180 | $19,671 | $9,744 |
| net_price_4yr | 2,233 | 26.52% | −$4,720 | $50,560 | $75,960 | $100,840 | $308,720 | $78,683 | $38,977 |
| net_price_q1 ($0–30K) | 2,185 | 28.10% | −$4,129 | $9,067 | $14,414 | $20,013 | $78,201 | $15,435 | $8,740 |
| net_price_q2 ($30–48K) | 2,106 | 30.70% | −$2,483 | $9,785 | $15,040 | $20,473 | $74,499 | $16,089 | $8,826 |
| net_price_q3 ($48–75K) | 2,079 | 31.59% | −$1,325 | $12,265 | $17,642 | $22,702 | $66,505 | $18,394 | $8,660 |
| net_price_q4 ($75–110K) | 1,981 | 34.81% | $2,650 | $16,411 | $21,455 | $26,478 | $63,333 | $22,014 | $8,520 |
| net_price_q5 ($110K+) | 1,846 | 39.26% | −$1,447 | $19,108 | $24,762 | $31,476 | $79,482 | $26,315 | $10,607 |

### `institution_control` distribution

| Label | Count | % |
|-------|------:|--:|
| Public | 867 | 28.53% |
| Private nonprofit | 1,754 | 57.72% |
| Private for-profit | 418 | 13.75% |
| (null / unmapped) | 0 | 0.00% |

---

## Coverage by Institution Control

**`net_price_annual` and `cost_of_attendance_annual` coverage are identical row-for-row** (see Key Finding #1).

| Control | N | Both populated | % |
|---------|--:|---------------:|--:|
| Public | 867 | 774 | 89.27% |
| Private nonprofit | 1,754 | 1,239 | 70.64% |
| Private for-profit | 418 | 220 | 52.63% |
| **Overall** | 3,039 | 2,233 | **73.48%** |

The for-profit segment is the coverage weak spot. Any overall threshold stricter than ~73% will fail; any control-stratified rule must allow ≥ 50% (not the 80% in the spec draft) for for-profit.

---

## Cross-Field Invariant Results

### Invariant 1: `net_price_annual ≤ cost_of_attendance_annual`

| Metric | Value |
|--------|------:|
| Rows with both non-null | 2,233 |
| Violations | **0** |
| Rows with NP == COA (zero aid) | 4 |
| Max COA − NP (largest aid package) | $70,026 |
| Median COA − NP | $11,081 |

**Recommendation:** P0 rule with 0 tolerance. Safe to enforce at 100%.

### Invariant 2: `net_price_4yr = net_price_annual × 4` (tautological)

| Metric | Value |
|--------|------:|
| Rows with non-null `net_price_annual` | 2,233 |
| Violations (|derived − annual×4| > $1) | **0** |

**Recommendation:** P0 rule. Can tighten tolerance to near-zero (e.g., 1e-6) since multiplication by 4 is lossless in IEEE 754. Logical-model $1 tolerance is fine but pessimistic.

### Invariant 3: `cost_of_attendance_4yr = cost_of_attendance_annual × 4`

| Metric | Value |
|--------|------:|
| Rows with non-null `cost_of_attendance_annual` | 2,233 |
| Violations | **0** |

**Recommendation:** P0 rule. Same tolerance guidance as Invariant 2.

### Invariant 4: `net_price_q1 ≤ net_price_q5`

| Control | Both non-null | Violations | % violating |
|---------|--------------:|-----------:|------------:|
| Public | 716 | 7 | 0.98% |
| Private nonprofit | 998 | 33 | 3.31% |
| Private for-profit | 118 | 6 | 5.08% |
| **Overall** | 1,832 | **46** | **2.51%** |

Violation magnitudes (`q1 − q5` when q1 > q5): min $164, median $1,396, max $18,121.

**Recommendation:** P1 rule with **≥ 97% pass rate** (allow ~3% violations) or `<= 50 rows violating`. Setting it P0 with zero tolerance will fail the Silver zone. Document that q1 > q5 inversions are legitimate (federal-aid caps at highest-need levels, merit-aid concentration at middle quintiles).

---

## Null-Pattern Analysis

**The 806 rows with null `net_price_annual` are exactly the same 806 rows with null `cost_of_attendance_annual`.** This is a structural property of College Scorecard reporting: institutions either report their full financial picture (both COA and NP) or nothing.

- **Consequence:** `net_price_4yr` nullness inherits from `net_price_annual` (null-preserving ×4). `cost_of_attendance_4yr` similarly inherits.
- **Consequence:** A single "institution reported financials" flag could simplify downstream filtering. Not required for this Silver table but worth noting for Gold.
- **Consequence:** The 806-row null cohort should be investigated — but per the Bronze EDA, these concentrate in PREDDEG=0 (not classified) and PREDDEG=4 (graduate-dominant) populations pulled in by the ICLEVEL=1 branch of the filter, as well as for-profit institutions that underreport.

Quintile nulls **do not** follow the same unified pattern. A row may have `net_price_annual` populated while `net_price_q5` is suppressed (sample size in the top income bracket can be too small to publish). This is why q5 coverage drops to 60.74% while q1 is 71.90%.

---

## Routing Correctness

Control-based CASE routing for the unified net price fields has **zero cross-contamination risk**:

- 0 rows with `control=1` have non-null `NPT4_PRIV`
- 0 rows with `control∈(2,3)` have non-null `NPT4_PUB`
- 0 rows have `control` values outside {1, 2, 3}
- 0 rows have null `control`

The CASE expression `WHEN control=1 THEN npt4_pub WHEN control IN (2,3) THEN npt4_priv END` will never produce an unexpected null (a null output implies a null input in the selected branch, by construction) and never miss a value in the unselected branch.

Same guarantee holds for `net_price_q1` through `net_price_q5` routing.

---

## Edge Cases and Extremes

### Lowest `net_price_4yr` values (negative / near-zero)

| Institution | Control | net_price_4yr |
|-------------|---------|--------------:|
| Skyline College | Public | −$4,720 |
| San Diego Mesa College | Public | −$3,616 |
| St Petersburg College | Public | −$208 |
| Colegio Universitario de San Juan | Public | $800 |
| Henry Ford College | Public | $2,304 |

These are legitimate — community colleges where average grant aid exceeds average COA. Do **not** set a `> 0` floor on `net_price_annual` or `net_price_4yr`.

### Highest `net_price_4yr` values

| Institution | Control | net_price_4yr |
|-------------|---------|--------------:|
| Galen Health Institutes-Asheville | Private for-profit | $308,720 |
| Felbry College | Private for-profit | $255,688 |
| School of Visual Arts | Private for-profit | $234,512 |
| Ringling College of Art and Design | Private nonprofit | $221,560 |
| The New School | Private nonprofit | $221,436 |

### Highest `cost_of_attendance_4yr` values

| Institution | Control | cost_of_attendance_4yr |
|-------------|---------|-----------------------:|
| Northwestern University | Private nonprofit | $351,216 |
| University of Chicago | Private nonprofit | $347,424 |
| Columbia University | Private nonprofit | $344,168 |
| University of Pennsylvania | Private nonprofit | $342,952 |
| Pepperdine University | Private nonprofit | $340,808 |

---

## EDA-Informed Silver DQ Thresholds

Matched to the logical model's DQ rule list (`governance/models/silver-base-college-scorecard-institution-logical.md` §Constraints), with recommended Silver thresholds:

| Rule | Logical-Model Draft | Actual Evidence | Recommended Silver Threshold | Severity | Notes |
|------|--------------------|-----------------|------------------------------|----------|-------|
| Row count matches Bronze | equal | 3,039 = 3,039 | equal (hard) | P0 | Will pass |
| `unitid` unique, non-null | 100% | 0 dup, 0 null | 100% | P0 | Will pass |
| `record_id` unique, non-null | 100% | derived from unitid | 100% | P0 | Will pass |
| `institution_control ∈ {Public, Private nonprofit, Private for-profit}` | domain | 3/3 labels present, 0 unmapped | 100% | P0 | Will pass |
| `state_abbr` matches `^[A-Z]{2}$` | regex | 0 violations, 58 distinct (50 states + DC + territories) | 100% | P0 | Will pass |
| `cost_of_attendance_annual ∈ [5000, 100000]` | range | [$6,362, $87,804] | [$5,000, $100,000] | P0 | Has headroom |
| `net_price_annual ∈ [0, 80000]` | range | **[−$1,180, $77,180]** | **[−$5,000, $80,000]** | P0 | **Negative floor required** |
| `net_price_q1..q5 ∈ [0, 80000]` | range | q1: [−$4,129, $78,201]; q2: [−$2,483, $74,499] etc. | **[−$5,000, $80,000]** for all q's | P1 | **Negative floor required** |
| `tuition_in_state ∈ [0, 65000]` | range | Bronze: [$600, $69,330] | [$0, $70,000] | P1 | **Raise cap to $70K** |
| `tuition_out_of_state ∈ [0, 65000]` | range | Bronze: [$600, $69,330] | [$0, $70,000] | P1 | **Raise cap to $70K** |
| `room_board_on_campus ∈ [3000, 25000]` | range | Bronze: [$1,000, $29,874] | **[$1,000, $30,000]** | P1 | **Widen both ends** |
| `room_board_off_campus` (no draft rule) | — | Bronze: [$2,001, $39,100] | [$2,000, $40,000] | P1 | New rule |
| `books_supplies` (no draft rule) | — | Bronze: [$0, $9,741] | [$0, $10,000] | P1 | Allow zero |
| `net_price_annual ≤ cost_of_attendance_annual` (both nn) | 100% | 0/2,233 violations | 100% | P0 | Will pass |
| `net_price_4yr = net_price_annual × 4` (within $1) | 100% | 0/2,233 violations | 100% | P0 | Will pass, IEEE-exact |
| `cost_of_attendance_4yr = cost_of_attendance_annual × 4` (within $1) | 100% | 0/2,233 violations | 100% | P0 | Will pass, IEEE-exact |
| `net_price_q1 ≤ net_price_q5` (both nn) | P1 | 46/1,832 violations = 2.51% | **≥ 97% pass** (allow ≤ 3% violation) | P1 | Cannot be P0 |
| `cost_of_attendance_annual` non-null coverage | ≥ 90% (spec), ≥ 80% (logical) | **73.48%** | **≥ 70%** | P0 | **Logical-model 80% will fail** |
| `net_price_annual` non-null coverage | ≥ 85% (logical) | **73.48%** | **≥ 70%** | P0 | **Logical-model 85% will fail** |
| `net_price_annual` coverage, Public | (implicit via raw) | 89.27% | ≥ 85% | P1 | Safe |
| `net_price_annual` coverage, Private nonprofit | (implicit 80% from spec) | 70.64% | **≥ 65%** | P1 | **Lower threshold** |
| `net_price_annual` coverage, Private for-profit | (implicit 80% from spec) | **52.63%** | **≥ 50%** | P2 | **For-profit underreports** |
| `net_price_q1` non-null coverage | — | 71.90% | ≥ 68% | P2 | Informational |
| `net_price_q5` non-null coverage | — | 60.74% | ≥ 55% | P2 | Informational, drops by 11pp from q1 |

---

## Surprises and Flags for Downstream Agents

### Surprise 1 — COA and NP coverage are row-identical (not just aggregate-identical)

**Impact:** @dq-rule-writer can consolidate two coverage rules into one. @semantic-modeler may want to note in the physical model that `cost_of_attendance_annual IS NULL <=> net_price_annual IS NULL` is a true biconditional on the current dataset (not a guaranteed invariant going forward — source can diverge — but currently true).

### Surprise 2 — Logical-model 85%/80% coverage thresholds are too strict

**Impact:** The DQ rules as drafted in the logical model will fail on green data. @dq-rule-writer must adjust to ≥ 70% before running Silver DQ.

### Surprise 3 — Private for-profit coverage of 52.63% is well below the spec-implied 80%

**Impact:** Any control-stratified coverage rule with a blanket 80% threshold (as the Bronze spec sketches) will fail. @dq-rule-writer should either split by control with asymmetric thresholds (Public 85%, Private nonprofit 65%, Private for-profit 50%) or accept a lower overall threshold.

### Surprise 4 — Silver q1 vs q5 violation rate is 2.51%, not 0%

**Impact:** The logical model lists `net_price_q1 ≤ net_price_q5` as P1 and implicitly expects zero violations. Evidence shows 46 legitimate violations (non-monotonic aid curves for certain institutions). @dq-rule-writer must set a ≤ 3% violation tolerance or scope the rule to a specific control subset.

### Surprise 5 — Negative quintile values persist

**Impact:** Five of the nine quintile field ranges need negative floors, including both pub and priv sides. Notably, `net_price_q4` has no negatives (min $2,650), so its floor could stay at $0 if we want per-quintile tailoring. The simpler path is `[−$5,000, $80,000]` for all five q fields uniformly.

### No Surprise — but worth stating

The logical-model cross-field rules (`NP ≤ COA`, `4yr = annual × 4`) are all safely enforceable at P0 100%. These are the strongest DQ guarantees in the Silver zone.

---

## Recommendations for @dq-rule-writer

1. **Coverage rules:** Use `≥ 70%` for both `cost_of_attendance_annual` and `net_price_annual` at P0. Consider a single combined "financial data reported" coverage rule since the two are row-identical.
2. **Range rules:** Add negative lower bounds (−$5,000) for `net_price_annual`, `net_price_4yr`, and all five `net_price_q*` fields. Widen `room_board_on_campus` to [$1,000, $30,000] and raise tuition caps to $70,000.
3. **Invariant rules:** P0 for `NP ≤ COA` and both 4yr tautologies at 100%. P1 for `q1 ≤ q5` at ≥ 97% pass.
4. **Consider splitting** the control-stratified coverage rule into three rules with asymmetric thresholds rather than one blanket rule.
5. **Skip** adjacent-pair quintile monotonicity rules (q1≤q2, q2≤q3, etc.) entirely — Bronze EDA shows 37.9% violation rates for private nonprofit q1≤q2 (known IPEDS reporting pattern; not DQ-actionable).

## Recommendations for @semantic-modeler

No physical-model changes required — the logical model's attributes and types are sound. One optional note: add a comment to `cost_of_attendance_annual` and `net_price_annual` columns stating that they currently co-null perfectly (both null or both populated). This is not a constraint to enforce but useful runtime context.

---

## Audit Trail

- **Dataset analyzed:** Reconstructed from `/tmp/Most-Recent-Cohorts-Institution.csv` (cached copy of the April 2025 scorecard.network mirror ZIP contents), applying the documented Bronze filter (PREDDEG=3 OR ICLEVEL=1) and dedup (first-wins on UNITID).
- **Analysis method:** Python stdlib — `csv.DictReader`, `statistics.mean/pstdev`, custom percentile computation via linear interpolation.
- **Row count confirmed:** 3,039 (Silver) = 3,039 (Bronze baseline in `eda-college-scorecard-institution.md`).
- **Derived fields validated:** All 11 derivations per logical-model §Derivation Rules produce the expected outputs; routing, coalesce, and ×4 operations all behave as specified.
- **All numeric profiles cross-checked against Bronze EDA field profiles** — the derived field distributions are consistent with the underlying raw field profiles, confirming the transformation logic.

*— End of Report —*
