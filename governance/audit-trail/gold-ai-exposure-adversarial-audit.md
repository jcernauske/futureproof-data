# Adversarial Audit: gold-ai-exposure

**Date:** 2026-04-09
**Auditor:** @data-analyst (acting as @adversarial-auditor)
**Spec:** gold-ai-exposure
**Table:** consumable.ai_exposure (389 rows, 9 columns)
**Audit Method:** Code review of transformer, DQ rule inspection, chaos monkey results review, derivation formula verification

---

## 1. Executive Summary

This is a simple, well-constrained Gold derivation table. The transformer reads 419 Silver rows, filters to 389 where bls_match=true, derives two integer fields (stat_res, boss_ai_score) from exposure_score, and promotes to Gold. The derivation math is trivially correct. The DQ rule suite (15 rules, all human-approved) is comprehensive. The chaos monkey found 13 of 15 rules fire reliably, with 2 cross-table rules erroring in shadow mode due to an environmental limitation.

**Verdict: PASS with minor caveat** (cross-table shadow testing limitation is documented but not blocking).

---

## 2. Transformer Code Review

**File:** `src/gold/ai_exposure_transformer.py` (198 lines)

### Derivation Formula Verification

| Formula | Code (line) | Correct? | Edge Cases |
|---------|-------------|----------|------------|
| `stat_res = MIN(11 - exposure_score, 10)` | Line 59: `return min(11 - exposure_score, 10)` | Yes | Cap at 10 triggers only when exposure_score=0. No such rows exist in Gold (all bls_match=true rows have exposure_score >= 1). |
| `boss_ai_score = MAX(exposure_score, 1)` | Line 68: `return max(exposure_score, 1)` | Yes | Floor at 1 triggers only when exposure_score=0. Same -- never exercised in current data. |
| `stat_res + boss_ai_score = 11` (invariant) | Follows from (11-x) + x = 11 when x >= 1 | Yes | Holds universally for all 389 rows. |

### Filter Logic

Line 84: `if not row.get("bls_match"): continue` -- correctly filters to bls_match=true. Also skips rows where bls_match is missing (defensive).

Line 88: `if soc_code is None: continue` -- correctly guards against null SOC codes reaching Gold. Redundant with bls_match=true filter (all bls_match=true rows have non-null SOC) but not harmful.

### Grain and Record ID

Lines 114-115: `compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)` where GRAIN_FIELDS=["soc_code"] and GRAIN_PREFIX="aie". Deterministic SHA-256 hash. 389 distinct SOC codes produce 389 distinct record_ids. No collision risk.

### Promote Pattern

Lines 170-176: Uses Brightsmith `promote()` with id_field="record_id". Idempotent -- re-promotion of unchanged data produces no new snapshot. Correct usage.

### Code Quality Assessment

- No mutation of input data (Silver rows are read-only)
- No side effects beyond Iceberg writes
- Clear separation of concerns (derive_gold_rows, add_record_ids, transform)
- Logging at each stage
- Return value includes full accounting (rows_read, rows_filtered, rows_derived, promoted, skipped_dedup)

**Assessment: STRONG.** No issues found in transformer code.

---

## 3. DQ Rule Suite Review

**File:** `governance/dq-rules/gold-ai-exposure.json` (15 rules, all active, all human-approved)

### Rule Coverage by Dimension

| Dimension | Rules | Assessment |
|-----------|-------|-----------|
| Uniqueness | GLD-AIE-001, GLD-AIE-002 | Grain (soc_code) and surrogate key (record_id) both checked. **Strong.** |
| Volume | GLD-AIE-003 | Row count 370-409 (389 +/- 5%). **Strong.** |
| Validity | GLD-AIE-004, GLD-AIE-005, GLD-AIE-006, GLD-AIE-011 | Ranges for all three scores + SOC format. **Strong.** |
| Consistency | GLD-AIE-007, GLD-AIE-013, GLD-AIE-014 | Inverse invariant + both derivation formulas verified. **Strong.** |
| Completeness | GLD-AIE-008, GLD-AIE-009, GLD-AIE-012 | Rationale non-null + min length + all-fields non-null. **Strong.** |
| Referential Integrity | GLD-AIE-010 | Cross-validation with occupation_profiles. **Strong (see caveat below).** |
| Coverage | GLD-AIE-015 | SOC coverage >= 40% of occupation_profiles. **Strong (see caveat below).** |

### Derivation Accuracy Rules

Unlike the gold-futureproof-engine spec (which lacked derivation accuracy rules), this spec has GLD-AIE-013 and GLD-AIE-014, which validate the exact formulas -- not just output ranges. This is the correct approach. The inverse invariant (GLD-AIE-007) provides a third cross-check.

### Notable: No Golden Dataset

The DQ rule notes state: "CONS-GOLDEN-DATASET rule DEFERRED pending golden dataset creation." For a 389-row table with trivial derivations and 3 formula-verification rules, the absence of a golden dataset is acceptable. The derivation formulas are deterministic and fully verified by GLD-AIE-013 and GLD-AIE-014.

**Assessment: STRONG.** 15 rules cover all relevant dimensions. No gaps identified.

---

## 4. Chaos Monkey Results Review

**Report:** `governance/audit-trail/gold-ai-exposure-chaos-monkey.md`

### Summary

- 5 cycles at escalating corruption rates (5%-10%)
- 301 total corruptions injected across all 10 DQ dimensions
- 13 of 15 rules fire reliably
- 2 rules error in every cycle (GLD-AIE-010, GLD-AIE-015)
- 1 rule intermittent (GLD-AIE-008, seed-dependent -- not a gap)
- 0 dimensions went completely undetected
- Overall detection rate: 80-87%

### Cross-Table Shadow Error (GLD-AIE-010, GLD-AIE-015)

These two rules perform joins to `consumable.occupation_profiles`, which is not available in the shadow catalog used by the chaos monkey. The error is:

```
Catalog Error: Table with name consumable_occupation_profiles does not exist!
```

**This is an environmental limitation of single-table shadow testing, not a rule logic defect.** The rules are correctly written. They would pass in production where both tables exist in the same catalog.

**Recommendation:** The shadow testing framework should either:
1. Register companion tables read-only from the production catalog, or
2. Skip cross-table rules gracefully with a diagnostic message rather than an error.

This is a framework improvement item, not a blocking issue for this spec.

### GLD-AIE-008 Intermittent Detection

GLD-AIE-008 (rationale non-null) passed at some corruption rates and fired at others. This is seed-dependent -- at some seeds the random corruption mix does not null out or empty the rationale field. The rule itself is functional. No action needed.

**Assessment: STRONG.** Detection rate is appropriate for the rule count and corruption strategies. No gaps.

---

## 5. Risk Register

### RISK-001: Cross-Table Rules Unverified in Shadow Mode (LOW)

GLD-AIE-010 and GLD-AIE-015 error in shadow mode. These rules validate referential integrity (every soc_code exists in occupation_profiles) and coverage (ai_exposure covers >= 40% of occupation_profiles SOCs). Both are important for downstream joins but cannot be adversarially tested in the current shadow framework.

**Mitigation:** The EDA report confirms 100% cross-validation pass and 46.8% coverage. The rules pass in production DQ runs. The gap is limited to adversarial hardening, not production monitoring.

**Severity:** LOW. The rules work in production. The shadow limitation is documented.

### RISK-002: Exposure Score 0 Edge Case Untested in Production Data (LOW)

The derivation formulas handle exposure_score=0 (stat_res capped at 10, boss_ai_score floored at 1), but no rows with exposure_score=0 exist in the current data. The chaos monkey does inject out-of-range values, and the range rules catch them. The specific edge case where exposure_score=0 is valid but triggers floor/cap logic has been tested only through the chaos monkey, not with real data.

**Mitigation:** DQ rules GLD-AIE-004, GLD-AIE-005, and GLD-AIE-006 defensively allow 0-10 range. If future data includes exposure_score=0 rows, the formulas will handle them correctly (verified by code inspection).

**Severity:** LOW. Edge case is handled correctly in code and covered by defensive DQ rules.

---

## 6. Controls That Work Well

1. **Derivation formula verification (GLD-AIE-013, GLD-AIE-014):** These rules check the exact computation, not just the output range. This is stronger than the gold-futureproof-engine approach and should be the standard for all derivation tables. **Assessment: STRONG**

2. **Inverse invariant (GLD-AIE-007):** Mathematical proof that stat_res + boss_ai_score = 11 when exposure_score >= 1. Holds for all 389 rows. Any violation is a guaranteed bug. **Assessment: STRONG**

3. **Grain uniqueness (GLD-AIE-001, GLD-AIE-002):** 389 distinct soc_codes, 389 distinct record_ids. Zero duplicates. **Assessment: STRONG**

4. **Completeness (GLD-AIE-008, GLD-AIE-009, GLD-AIE-012):** All 9 columns NOT NULL per schema. Rationale minimum length 100 chars (actual minimum 297). **Assessment: STRONG**

5. **Idempotent promote pattern:** Re-running the transformer on unchanged Silver data produces no new Iceberg snapshot. Prevents duplicate rows. **Assessment: STRONG**

---

## 7. Recommendations

No blocking issues. No changes requested.

**Minor improvement (non-blocking):**
- Enhance shadow testing framework to support read-only companion table registration for cross-table DQ rules. This would allow GLD-AIE-010 and GLD-AIE-015 to be adversarially tested.

---

**Audit completed:** 2026-04-09
**Auditor:** @data-analyst
**Recommendation:** PASS
