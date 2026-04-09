## Staff Engineer Review

### Date: 2026-04-07
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is production-quality work. The implementation is clean, correct, and well-tested. The GRW piecewise function, market score composition, and null-safe wage percentile computation are all implemented exactly as specified. I verified every derived value against the formula by hand, queried the actual Iceberg tables, and cross-checked against BLS reference data. The numbers are right. 63 tests with real assertions, not theater. The adversarial audit caught a legitimate latent bug (null-openings in PERCENT_RANK) and it was fixed properly in both SQL and Python. I would put my name on this.

### Code Quality

**`src/gold/bls_ooh_occupation_profiles.py`** -- Good.

- Functions do one thing. `compute_grw_score` handles the piecewise math, `derive_gold_rows` runs the SQL + Python derivations, `add_record_ids` stamps the grain hash. No god functions.
- The `_round_half_up` function exists for a real reason (Python banker's rounding vs. DuckDB round-half-up) and the docstring explains WHY, not WHAT. This is the kind of comment I want to see.
- The `GOLD_SQL` CTE pattern for wage percentiles is correct: filter nulls FIRST, PERCENT_RANK on the filtered set, LEFT JOIN back. The comment at line 148-151 explains WHY this matters (DuckDB places nulls at ~0.185, corrupting all positions). Good.
- The `openings_ranked` CTE also correctly excludes null openings (line 208), and the Python side double-checks with `has_openings = row.get("openings_annual_avg") is not None` (line 310). Belt and suspenders. Fine.
- `GRW_BREAKPOINTS` as a module-level constant with typed tuples is clean. The loop in `compute_grw_score` is simple and readable.
- The `openings_score` is popped from the row dict before the final output (line 309), preventing an intermediate computation field from leaking into the Gold table. Good hygiene.
- Schema definition at `get_gold_schema()` matches the physical model exactly: 31 fields, correct types, correct nullability. I verified field-by-field.

No issues.

**`tests/gold/test_bls_ooh_occupation_profiles.py`** -- Good.

- Well-organized test classes by feature area (GRW, market, wage percentile, confidence tier, data completeness, static fields, record ID, schema, dropped fields, end-to-end).
- The `_make_silver_row` factory function with sensible defaults makes tests readable without hiding important setup. It includes ALL Silver fields including the ones that get dropped (employment_change, median_wage_capped, etc.), which correctly exercises the SQL's field selection.
- `_make_multi_rows` builds a curated 8-row dataset that covers: high growth + high wage, moderate growth + high openings, null wage, low wage, broad flag, catchall flag, declining occupation, and a second education_code=3 row for within-tier ranking tests.

### Test Quality

63 tests. All 63 pass (verified: `306 passed in 1.29s` across the full suite, 63 from this file). These are real tests, not theater. Specifics:

**GRW piecewise function (16 tests):** Every segment boundary tested with exact `pytest.approx` values. The `test_boundary_continuity` test iterates all 7 breakpoints and asserts the function is continuous at joints. The three golden dataset values are tested explicitly: Software Developers 15.8% -> 8.37, Registered Nurses 4.9% -> 6.4625, Anesthesiologists 3.2% -> 5.825. Floor at -20 and cap at 50/beyond are tested. This is thorough.

**Market score (5 tests):** Formula verification, null propagation, range validation, rounded consistency, and a comparative test proving high openings boosts market score relative to low openings with same growth. The comparative test is the right kind of test -- it validates the MEANING of the formula, not just the mechanics.

**Wage percentile null handling (4 tests):** The critical test is `test_wage_percentile_excludes_nulls_from_ranking` -- it builds 3 wage rows + 1 null-wage row, asserts null gets None, and asserts the 3 valid rows get exactly 0.0, 0.5, 1.0 from PERCENT_RANK. This directly validates the CTE-based null exclusion pattern that prevents the DuckDB null-positioning bug.

**Confidence tier (7 tests):** Tests all 3 tiers, plus the critical edge case: catchall + null wage -> "low" (not "medium"). This was explicitly called out in the EDA as a 3-occupation edge case (27-2099, 29-1229, 29-1249). Both catchall and broad with null wage are tested for priority.

**Data completeness (5 tests):** Tests all 5 possible values (0.0, 0.25, 0.5, 0.75, 1.0) with exact assertions. Not `> 0`.

**End-to-end (8 tests):** Three golden dataset chain tests validate the full derivation pipeline for Software Developers, Anesthesiologists, and the catchall+null-wage case. Each tests multiple derived fields in the same row, validating cross-column consistency.

Test count exceeds the 15-test minimum for Consumable zone.

### Spec Compliance

Implementation matches the spec. I verified:

- Grain: soc_code, 832 rows, zero duplicates. Confirmed in Iceberg table.
- GRW score: piecewise linear function matches all 8 spec bands exactly. Verified by hand for 3 golden dataset values.
- Market score: formula is `0.6 * grw_score + 0.4 * (1.0 + 9.0 * PERCENT_RANK(openings))`. Verified by independent SQL query against the Gold table -- calculated values match actual values to full floating-point precision.
- Wage percentile: null-safe PERCENT_RANK with exclusion pattern. 23 nulls confirmed.
- Wage tier: 5 tiers with correct percentile thresholds. Distribution: 202/202/202/122/81 -- mathematically consistent with quartile + 90th percentile breakpoints on 809 non-null wages.
- Confidence tier: priority logic correct (low=23, medium=74, high=735). Low count matches null-wage count exactly.
- Static fields: backs_stats="ERN,GRW" and backs_bosses="Market,Ceiling" for all 832 rows.
- Record ID: compute_grain_id with prefix "op" on soc_code grain.
- Promote pattern: idempotent via brightsmith.infra.promote.
- Schema: 31 fields matching physical model.
- Dropped fields: 6 Silver fields correctly excluded (employment_change, median_wage_capped, education_typical, work_experience, training_typical, ingested_at).

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| Software Developers (15-1252) | median_annual_wage | 2024 | $133,080 | $130,160-$133,080 | BLS OOH 2024-2034 | YES |
| Software Developers (15-1252) | grw_score | derived | 8.37 | 8.37 (hand-calc: 7.5 + 5.8/10 * 1.5) | Formula verification | YES |
| Registered Nurses (29-1141) | median_annual_wage | 2024 | $93,600 | $93,600 | BLS OOH 2024-2034 | YES |
| Registered Nurses (29-1141) | grw_score | derived | 6.4625 | 6.4625 (hand-calc: 5.0 + 3.9/4.0 * 1.5) | Formula verification | YES |
| Anesthesiologists (29-1211) | median_annual_wage | 2024 | NULL | Not reported (>$239,200) | BLS OOH 2024-2034 | YES |
| Anesthesiologists (29-1211) | confidence_tier | derived | low | low (wage_available=False) | Spec definition | YES |
| Market score (15-1252) | market_score | derived | 8.8747 | 8.8747 (independent SQL recomputation) | CTE recalculation | YES |
| Total rows | count | - | 832 | 832 | Silver carry-forward | YES |
| Null wage count | count | - | 23 | 23 | Silver source | YES |

All values verified. No discrepancies.

### Governance Artifacts

All required artifacts exist and are substantive:

- **Data models (3):** All APPROVED (conceptual, logical, physical). Physical model matches implementation exactly -- 31 fields, same types, same nullability.
- **DQ rules:** 54 defined, 53 executable, 1 deferred (GLD-OP-048 golden dataset validation still has placeholder SQL).
- **DQ scorecard:** 52/53 passing (98%). P0 gate: PASS. 1 P1 failure (GLD-OP-039).
- **Golden dataset:** 3 verification chains, all traceable from Silver input through derivation formula to expected output. The EDA-identified spec error (29-1215 replaced with 29-1211) is documented.
- **Adversarial audit:** Exists. 14 risks identified, 3 P0. RISK-03 (null-openings bug) was fixed post-audit.
- **Chaos manifest:** 5 adversarial cycles, 67.9%-77.4% detection rate. Gap analysis is honest -- identified broken GLD-OP-039, absent freshness rules, absent record_id hash validation.
- **Data contract:** 31 columns with CDE/PII flags, quality thresholds, consumer documentation. 9 CDE columns flagged with rationale. 0 PII.
- **Lineage:** OpenLineage event with column-level lineage for all 31 output fields. 7 dropped fields documented with justification.
- **Audit trail:** 13 entries covering the full agent workflow.

Not boilerplate. The artifacts reference real tables, real thresholds, real values.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | ADVISORY | `governance/dq-rules/gold-occupation-profiles-bls-ooh.json` | GLD-OP-039 (P1) SQL is broken -- correlated subquery with PERCENT_RANK unsupported by DuckDB. Shows 828 false violations. The market_score formula IS correct (I verified independently), but this DQ rule cannot validate it. | Rewrite using CTE pattern. Non-blocking -- the formula is correct and tested in unit tests. |
| 2 | ADVISORY | `governance/dq-rules/gold-occupation-profiles-bls-ooh.json` | GLD-OP-048 golden dataset validation rule still deferred with placeholder SQL. Golden dataset file exists and verification chains are documented, but automated validation is not wired up. | Update SQL to validate against golden dataset JSON. Non-blocking. |
| 3 | ADVISORY | `docs/specs/gold-occupation-profiles-bls-ooh.md` | Spec status still shows DRAFT (line 3). Should be updated after staff review approval. | Update to COMPLETE. Non-blocking. |

No blocking issues. The three advisory items are legitimate cleanup tasks but do not affect the correctness or quality of the implementation.

### What's Acceptable

- The piecewise GRW function is simple and correct. No over-engineering.
- The null-safe PERCENT_RANK pattern (filter -> rank -> LEFT JOIN) is the right approach for DuckDB's null handling. The CRITICAL comment explaining WHY is warranted.
- The round-half-up function exists for a real reason and the docstring proves the author understood the problem.
- Test coverage is genuine -- 16 tests on the GRW function alone, covering all 8 segments, boundaries, golden values, and edge cases.
- The adversarial audit caught a real bug and it was fixed properly.
- Cross-artifact consistency is verified: spec, physical model, implementation schema, lineage, data contract, and data dictionary all reference the same 31 fields.

### Approval Conditions

APPROVED unconditionally. The three advisory items should be addressed before the next spec begins but do not block this spec's completion.
