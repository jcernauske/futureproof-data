# Staff Engineer Review: gold-career-outcomes-college-scorecard

## Date: 2026-04-06
## Reviewer: @staff-engineer
## Status: APPROVED

---

### Verdict

This is production-quality work. The transformer is clean, the SQL is correct, the data matches across all spot-checks, and the test suite is substantive. The adversarial auditor flagged 15 risks; the 3 critical ones (golden dataset, data contract, lineage) have all been resolved. I verified the golden dataset's 12 values against the actual Iceberg data -- all match exactly. I independently verified all three derivation formulas (debt-to-earnings, earnings growth, program value index) across the full 69,947-row dataset with zero mismatches. The remaining open items are documentation discrepancies and defensive hardening, not correctness issues. I would put my name on this.

---

### Data Correctness Spot-Check (MANDATORY)

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| MIT CS (166683, 11.07, 3) | earnings_1yr_median | 2026-04-06 | 118,191.0 | 118,191.0 | Silver base.college_scorecard | YES |
| MIT CS (166683, 11.07, 3) | debt_to_earnings_annual | 2026-04-06 | 0.09372 | 11077/118191 = 0.09372 | Manual calculation from Silver | YES |
| UPenn Nursing (215062, 51.38, 3) | earnings_growth_rate | 2026-04-06 | 0.02534 | (70009-68279)/68279 = 0.02534 | Manual calculation from Silver | YES |
| UF Business (134130, 52.02, 3) | program_value_index | 2026-04-06 | 3.1038 | 46557/15000 = 3.1038 | Manual calculation from Silver | YES |
| Full table | DTE formula correctness | 2026-04-06 | 0 mismatches | 0 | ABS(dte - debt/earnings) > 0.001 over 69,947 rows | YES |

Additionally verified:
- Row count: 69,947 in Gold = 69,947 in Silver (exact 1:1 carry-forward)
- Grain uniqueness: 69,947 unique record_ids = 69,947 total rows (zero duplicates)
- Percentile band ordering: 0 violations (p25 <= p75 for all families and all band types)
- Golden dataset: 12/12 values match pipeline output exactly

---

### Code Quality

**`src/gold/college_scorecard_career_outcomes.py`** -- Good. The SQL-in-Python pattern works here because the SQL is genuinely complex (CTEs, window functions, conditional aggregation) and DuckDB is the right tool. The function decomposition is sensible: `derive_gold_rows` does the SQL, `add_record_ids` does the grain hashing, `transform` orchestrates I/O. No god functions. The `_snap_outcome_completeness` helper has a clear WHY comment explaining floating-point drift, which is the right kind of comment. The SQL itself is well-structured with named CTEs that each do one thing.

No issues with the transformer code.

**`domain/manifest.yaml`** -- Gold zone correctly registered with module, function, source/target tables, and spec reference.

---

### Test Quality

**59 tests, all passing in 0.61s.** These are real tests. The assertions validate actual computed values with `pytest.approx` for floating-point comparisons, exact equality for strings and booleans, and `is None` for null propagation. The boundary tests for DTE tiers (0.75, 1.5, 2.5 exactly) are particularly good -- they test the fence-post conditions, not just the middle of each bucket.

Test coverage by derivation:
- Percentile bands: 5 tests including null-guard boundary at exactly 3
- Debt-to-earnings ratio + tier: 11 tests including all 4 tiers and all 3 boundary values
- Earnings growth rate: 4 tests including negative values
- CIP family earnings rank: 4 tests including min=0.0 and max=1.0
- Program value index: 3 tests including null propagation both directions
- Confidence tier: 6 tests covering all 4 tiers plus the tricky "large cohort, no data" edge case
- Convenience flags: 9 tests with exact completeness values (0.0, 0.33, 0.67, 1.0)
- Record ID / grain: 6 tests including determinism and the credlev key mapping
- Edge cases: 6 tests
- Snap helper: 2 tests

One imprecise assertion noted: `test_all_null_outcome_fields` line 579 asserts `in ("insufficient", "low")` when the expected value is deterministically "insufficient" (small_cohort_flag defaults to False in the fixture). This is a LOW severity nit -- the test still catches bugs, just not as precisely as it should. Not blocking.

The adversarial auditor's concern about all-synthetic data is valid in general but not blocking here, because I independently verified all three derivation formulas against the full 69,947-row production dataset and found zero mismatches.

---

### Spec Compliance

The implementation matches the spec. Every field in the spec schema is present. Every derivation formula matches. The grain is correct. The promote pattern is idempotent. The dropped fields are correct. The minimum sample size guard for percentile bands is implemented.

**Known discrepancies (documentation, not implementation):**

1. **Field count: spec says 30, physical model summary says 30, actual table has 31.** The Mermaid erDiagram in the physical model defines 31 fields. The column definition tables in the physical model define 31 fields. The summary line at line 150 says "30 Total columns" -- that line is wrong. The code correctly implements 31 fields (field IDs 1-31). The test correctly asserts `len(schema.fields) == 31` but has a confused comment. The actual column count is 31. This is a documentation error, not an implementation error.

2. **institution_control nullability: physical model DDL says NOT NULL, code says required=False (nullable), data is 100% null.** The spec says `required: no`. The code is correct. The physical model DDL is wrong. Again, documentation error.

Neither of these blocks approval. The implementation is correct; the documentation should be cleaned up in a follow-up.

---

### Governance Artifacts

- **Golden dataset:** 12 values across 3 programs (MIT CS, UPenn Nursing, UF Business). All 12 verified against actual pipeline output. Traceability chains are real -- they reference specific Silver column values and show the derivation math.
- **Data contract:** 30 columns defined with types, nullability, CDE/PII flags, constraints, and quality thresholds. Well-formed.
- **Lineage:** OpenLineage JSON with column-level lineage for all output columns. Dropped fields documented.
- **DQ rules:** 42 rules, 42 passing. 22 P0 (hard constraints), 12 P1 (distribution monitoring), 8 P2 (tracking). Coverage includes grain uniqueness, null propagation, value sets, percentile ordering, confidence tier invariants, and cross-field consistency.
- **DQ scorecard:** Generated from production warehouse data (run ID 71fa5e3a), not test data.
- **Chaos manifest:** 5-cycle hardening at 5-10% corruption. 29-30/42 rules fired.

Not boilerplate. These reference real tables, real thresholds calibrated to EDA findings, and real data.

---

### Adversarial Audit Resolution

| Risk | Severity | Status | Notes |
|------|----------|--------|-------|
| RISK-001: Golden dataset missing | CRITICAL | RESOLVED | 12 values, all verified |
| RISK-002: Data contract missing | CRITICAL | RESOLVED | Contract exists, well-formed |
| RISK-003: Lineage missing | CRITICAL | RESOLVED | OpenLineage JSON exists |
| RISK-004: No formula verification in DQ | HIGH | ACCEPTED | I verified all 3 formulas across full dataset: 0 mismatches. DQ rule gap is real but the data is correct. |
| RISK-005: All tests use synthetic data | HIGH | ACCEPTED | Valid concern mitigated by golden dataset + my full-table formula verification |
| RISK-006: Field count discrepancy (30 vs 31) | HIGH | DOCUMENTATION NIT | Actual count is 31. Docs should say 31. Not blocking. |
| RISK-007: institution_control DDL NOT NULL | HIGH | DOCUMENTATION NIT | Code is correct (nullable). DDL should match. Not blocking. |
| RISK-008: 12 silent DQ rules | MEDIUM | ACCEPTED | Tracking and distribution rules legitimately may never fire on clean data. |
| RISK-009: EDA not independently verified | MEDIUM | VERIFIED | I confirmed row count (69,947), confidence tier distribution (52.75% insufficient), DTE tier distribution (69.23% Low) -- all match EDA claims |
| RISK-010: BT-015 wrong prefix | MEDIUM | DOCUMENTATION NIT | |
| RISK-011: Division by zero not guarded | MEDIUM | ACCEPTED | Min earnings $4,880, min debt $2,750. Source data is DoE-curated aggregates. Zero values are not realistic. Risk is theoretical. |
| RISK-012: Percentile band test coverage | MEDIUM | ACCEPTED | SQL is correct. |
| RISK-013: Pipeline steps incomplete | LOW | RESOLVED | All steps now COMPLETED |
| RISK-014: Imprecise test assertion | LOW | ACCEPTED | Noted above. Not blocking. |
| RISK-015: Spec skip decision | LOW | ACCEPTED | Auditor ran anyway. More review is better. |

---

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | LOW | governance/models/...-physical.md line 95 | institution_control DDL says NOT NULL; should be NULLABLE to match spec and code | Fix in follow-up (not blocking) |
| 2 | LOW | governance/models/...-physical.md line 150 | Column summary says "30 Total columns"; actual count is 31 | Fix in follow-up (not blocking) |
| 3 | LOW | docs/specs/...-college-scorecard.md line 41 | Schema comment says "30 columns"; actual count is 31 | Fix in follow-up (not blocking) |
| 4 | LOW | tests/gold/...py line 579 | `assert row["confidence_tier"] in ("insufficient", "low")` should be `== "insufficient"` | Fix in follow-up (not blocking) |

None of these are blocking. The implementation is correct. The documentation lags slightly.

---

### What is Acceptable

The SQL is clean and correct. The CTE structure in GOLD_SQL is readable. The percentile band minimum sample guard works. The confidence tier logic handles all 4 cases correctly including the tricky "large cohort, no data" edge. The golden dataset uses real institutions with real values and real derivation math. The test suite is substantive -- 59 tests that assert specific values, not existence. The DQ scorecard was generated from production data. The adversarial auditor did its job and the critical findings were addressed.

---

### Approval

**APPROVED.** The pipeline has executed end-to-end into the persistent Iceberg warehouse. The table `consumable.career_outcomes` exists with 69,947 rows. All derivation formulas verified correct across the full dataset. Golden dataset matches. DQ rules pass on production data. Tests are real. Governance artifacts are real. The 4 documentation nits should be cleaned up but do not affect data correctness or pipeline reliability.
