# Adversarial Audit: gold-career-outcomes-college-scorecard

**Auditor:** @adversarial-auditor
**Date:** 2026-04-06
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Zone:** Gold (Consumable)
**Table:** consumable.career_outcomes
**Verdict:** CONDITIONAL PASS -- 3 Critical, 4 High, 5 Medium, 3 Low findings

---

## Meta-Question

This pipeline was built entirely by AI agents. Every business term definition, every DQ rule threshold, every concept mapping, every derivation formula, every data model was proposed by an AI and approved by a human. The central question is not "did the AI do a good job?" -- it is "can you prove the AI did not hallucinate, and would a regulator accept your evidence?"

---

## Risk Register

### CRITICAL

**RISK-001: Golden dataset is missing -- no independent verification of derivation correctness**

The spec (line 206-209) requires "at least 3 independently verifiable values, selected from programs with high confidence data." The governance artifact checklist (line 222) lists `governance/golden-datasets/gold-career-outcomes-college-scorecard-golden.json`. This file does not exist. No glob match was found.

This is the single most important control against AI hallucination in derivation logic. The golden dataset is supposed to provide hand-verified expected values for specific real programs (e.g., "MIT Computer Science Bachelor's: expected debt_to_earnings_annual = X, expected confidence_tier = Y") where X and Y are independently computed by a human or verified against a known external source.

Without this artifact, the only evidence that the transformer's SQL produces correct outputs is: (a) unit tests with synthetic data authored by the same AI that wrote the transformer, and (b) DQ rules that check structural properties (not semantic correctness) authored by the same AI. This is the definition of circular validation.

- **Severity:** CRITICAL
- **Evidence demanded:** The golden dataset file with at least 3 real programs, each showing: Silver source values, expected Gold derived values, independent calculation method, and actual Gold output matched against expected.
- **Current control:** MISSING
- **Assessment:** Missing

---

**RISK-002: Data contract is missing -- no consumer-facing schema guarantee**

The spec (line 224) lists `governance/data-contracts/consumable-career-outcomes.yaml`. This file does not exist. The data contract is the formal agreement between the Gold zone producer and downstream consumers (the MCP layer, the product UI) about what fields exist, their types, their nullability semantics, and their freshness guarantees.

Without a data contract, consumers have no stable interface to code against. The MCP layer could be built against today's schema and silently break if a future pipeline run changes column names, types, or nullability.

- **Severity:** CRITICAL
- **Evidence demanded:** The data contract YAML file with schema, SLA, and quality guarantees.
- **Current control:** MISSING
- **Assessment:** Missing

---

**RISK-003: Lineage artifact is missing -- no provenance chain from source to Gold**

The spec (line 223) lists `governance/lineage/gold-career-outcomes-college-scorecard-{timestamp}.json`. No matching file exists. The pipeline state JSON shows lineage-tracker status is NOT_STARTED.

Lineage is the evidence chain that proves data provenance: which Silver rows contributed to which Gold rows, which transformations were applied, and when. Without lineage, if a regulator asks "where did this debt-to-earnings ratio come from?", the answer is "the transformer SQL computed it" -- but there is no machine-readable audit trail connecting a specific Gold row back to its Silver source.

- **Severity:** CRITICAL
- **Evidence demanded:** OpenLineage JSON with run-level and dataset-level facets tracing consumable.career_outcomes back to base.college_scorecard.
- **Current control:** MISSING
- **Assessment:** Missing

---

### HIGH

**RISK-004: No derivation formula verification in DQ rules**

42 DQ rules exist. They are comprehensive for structural properties: null propagation, value set membership, range checks, distribution percentages. However, no DQ rule verifies that the actual computed value matches the expected formula. For example:

- GLD-CO-012/013 verify that debt_to_earnings_annual is null when inputs are null (and non-null when they aren't). But no rule verifies that debt_to_earnings_annual = debt_median / earnings_1yr_median for any specific row.
- GLD-CO-014 verifies earnings_growth_rate null propagation. No rule verifies that earnings_growth_rate = (earnings_2yr_median - earnings_1yr_median) / earnings_1yr_median.
- GLD-CO-037 verifies that program_value_index is the inverse of debt_to_earnings_annual (a cross-field consistency check). This is the closest thing to formula verification, but it only checks that two derived fields are consistent with each other -- not that either is correct relative to the source fields.

The chaos monkey report (lines 126-133) explicitly flagged this gap: "Derivation formula verification: Add rules that spot-check or fully verify debt_to_earnings_annual = debt_median / earnings_1yr_median." This recommendation was not implemented.

- **Severity:** HIGH
- **Evidence demanded:** DQ rules (P0) that sample or fully verify: (a) debt_to_earnings_annual = debt_median / earnings_1yr_median, (b) earnings_growth_rate = (2yr - 1yr) / 1yr, (c) program_value_index = earnings_1yr / debt_median.
- **Current control:** Weak -- GLD-CO-037 provides one cross-check, but all three formulas could be uniformly wrong (e.g., numerator/denominator swapped) and the DQ rules would pass.
- **Assessment:** Weak

---

**RISK-005: Unit tests use exclusively synthetic data -- no real-data validation**

All 59 tests pass. They are well-structured and cover the derivation logic thoroughly. However, every test uses `_make_silver_row()` to construct synthetic input. No test reads from the actual Silver Iceberg table or uses values from the real College Scorecard dataset.

This means the tests prove: "given these hand-crafted inputs, the SQL produces the expected outputs." They do not prove: "given the actual Silver data with its specific edge cases (CIP codes with leading zeros, extremely low earnings like $4,880, privacy-suppressed null patterns), the transformer produces correct results."

The synthetic test fixtures also have a subtle property: the AI that wrote the transformer also wrote the test fixtures. If the AI misunderstood a derivation (e.g., got the confidence tier logic wrong), it would write both the SQL and the test to match the wrong understanding, and all tests would pass.

- **Severity:** HIGH
- **Evidence demanded:** At least 3 tests that use real Silver row values (manually extracted from the Iceberg table or the College Scorecard source CSV) and verify Gold outputs against independently computed expected values.
- **Current control:** Weak -- 59 tests all use synthetic data from the same AI.
- **Assessment:** Weak

---

**RISK-006: Schema field count discrepancy between spec, physical model, and code**

The spec (line 41) says the schema has "30 columns." The physical model (line 149) says "30 Total columns." But the Iceberg schema function `get_gold_schema()` defines 31 NestedField entries (field IDs 1-31). The test `test_schema_field_count` (line 127) asserts `len(schema.fields) == 31` with the comment "30 columns + field IDs are 1-31" -- which is a confused explanation. 31 fields IS 31 columns.

Looking at the spec schema tables: there are exactly 30 data fields listed. But the code has 31 schema fields. The discrepancy appears to be between 30 "user-visible" columns and 31 Iceberg NestedField entries, but both the spec and physical model claim 30. A regulator asking "how many fields does this table have?" would get contradictory answers depending on which document they read.

- **Severity:** HIGH
- **Evidence demanded:** Reconcile the spec, physical model, and code. Identify whether there are 30 or 31 columns and update all documents to agree.
- **Current control:** Weak -- the test passes but its comment admits the discrepancy.
- **Assessment:** Weak

---

**RISK-007: institution_control nullability contradiction between physical model DDL and Iceberg schema**

The physical model's DDL (line 178) declares `institution_control VARCHAR NOT NULL`. But the Iceberg schema (code line 47) declares it as `required=False` (nullable). The physical model's column definition table (line 95) says `NOT NULL`. The spec (line 53) says `required: no`.

This means the physical model's DDL does not match the actual implemented schema. If someone reads the DDL as the source of truth, they would believe institution_control is NOT NULL -- and be wrong. The EDA confirms this field is 100% NULL in reality.

- **Severity:** HIGH
- **Evidence demanded:** Fix the DDL in the physical model to match the actual schema (NULLABLE), or document the intentional deviation with rationale.
- **Current control:** Weak -- the code is correct (nullable) but the physical model DDL is wrong (NOT NULL).
- **Assessment:** Weak

---

### MEDIUM

**RISK-008: 12 DQ rules never fire during chaos monkey testing**

The chaos monkey report identifies 12 rules (GLD-CO-020, 022-027, 034, 035, 039, 040, 042) that returned the same "passing" value across all 5 corruption cycles. This means these 12 rules have never been observed to detect a problem -- they have only ever passed.

A rule that has never failed provides zero evidence of detection capability. It might detect problems if the right corruption were applied, or it might be structurally incapable of failing (e.g., a percentage threshold set so high it can never be exceeded). The chaos monkey report recommends investigating these rules. There is no evidence this investigation was performed.

- **Severity:** MEDIUM
- **Evidence demanded:** For each of the 12 silent rules, either: (a) demonstrate a specific corruption that triggers failure, or (b) acknowledge the rule is a structural invariant and add a complementary rule that provides active detection.
- **Current control:** Adequate for the 29 rules that fire; Weak for the 12 silent rules.
- **Assessment:** Weak

---

**RISK-009: EDA report findings were not independently verified**

The Gold EDA report (`governance/eda/gold-career-outcomes-eda.md`) provides detailed distribution statistics that directly inform DQ rule thresholds. For example: "52.75% of rows will be insufficient confidence tier" (EDA line 253) feeds directly into GLD-CO-025's threshold of "45-60%."

But the EDA was produced by the @data-analyst AI agent. The agent reported analyzing the Silver Iceberg table, but no one independently verified that the Silver table actually contains 69,947 rows, or that 52.75% of them have all three outcome fields null. If the AI misread the data (e.g., queried the wrong table, had a SQL bug in its profiling), all downstream DQ thresholds would be calibrated to wrong numbers.

The EDA report includes specific outlier examples (e.g., "Bloomsburg University of Pennsylvania, Communication Disorders Sciences, DTE ratio 5.328, earnings $4,880, debt $26,000"). These appear plausible but could be fabricated. A human reviewer would need to look up Bloomsburg's Communication Disorders program on the actual College Scorecard website to verify.

- **Severity:** MEDIUM
- **Evidence demanded:** Independent spot-check of at least 3 EDA claims against the actual Silver data (e.g., verify row count, verify Bloomsburg CDS earnings, verify CIP family 28 has exactly 1 non-null earnings row).
- **Current control:** Adequate -- the DQ scorecard confirms rules pass on real data, which provides indirect evidence that distributions match. But "rules pass" only means "rules calibrated to EDA findings agree with data those findings describe" -- circular if EDA was wrong.
- **Assessment:** Adequate (with reservation)

---

**RISK-010: Business glossary term BT-015 (Record ID) has wrong prefix documentation**

BT-015 states: "Prefixed with 'cs' for the College Scorecard domain." But the Gold zone uses prefix 'co' (see code line 37: `GRAIN_PREFIX = "co"` and spec line 43: `prefix='co'`). The Silver zone used 'cs'. BT-015 references only Silver: `used_in_models: ["silver-base-college-scorecard"]` -- it was not updated to include the Gold model, and its definition does not mention the Gold prefix change.

This means the glossary does not accurately describe Gold record_id behavior. A developer reading BT-015 would expect prefix 'cs' but Gold rows have prefix 'co'.

- **Severity:** MEDIUM
- **Evidence demanded:** Update BT-015 to document both prefixes, or create a separate Gold-specific record_id term.
- **Current control:** Weak -- the glossary is stale for this term.
- **Assessment:** Weak

---

**RISK-011: Division by zero not guarded in SQL**

The GOLD_SQL contains three division operations:
1. `debt_median / earnings_1yr_median` (line 174)
2. `(earnings_2yr_median - earnings_1yr_median) / earnings_1yr_median` (line 177)
3. `earnings_1yr_median / debt_median` (line 184)

All three check for null inputs but none check for zero denominators. If earnings_1yr_median = 0.0 (not null, but zero), divisions 1 and 2 would produce infinity or error. If debt_median = 0.0, division 3 would produce infinity or error.

The EDA reports minimum earnings of $4,880 and minimum debt of $2,750, so zero values do not currently exist in the data. However, no DQ rule checks that earnings or debt are strictly positive when non-null. A future data load with a $0 earnings value (perhaps from a data entry error at the source) would cause a runtime failure or produce infinity values that would propagate through the pipeline.

The physical model (line 101) has a CHECK constraint `earnings_1yr_median >= 1000` but this constraint exists only in the reference DDL -- it is not enforced by Iceberg or by any DQ rule at the Gold level.

- **Severity:** MEDIUM
- **Evidence demanded:** Either add explicit zero-guards in the SQL (e.g., `CASE WHEN earnings_1yr_median IS NOT NULL AND earnings_1yr_median > 0 THEN ...`) or add a P0 DQ rule verifying no zero-valued earnings or debt rows exist.
- **Current control:** Weak -- depends on source data never having zeros, with no enforcement.
- **Assessment:** Weak

---

**RISK-012: Percentile band SQL includes null rows in the PERCENTILE_CONT aggregation**

The `cip_bands` CTE (code lines 122-146) computes PERCENTILE_CONT on `earnings_1yr_median` using the `base` table joined with `cip_counts`. DuckDB's PERCENTILE_CONT with `WITHIN GROUP (ORDER BY earnings_1yr_median)` naturally ignores NULL values in the ORDER BY expression. This is correct behavior -- confirmed by the minimum sample count guard using `COUNT(earnings_1yr_median)` which only counts non-nulls.

However, the test for this (`test_percentile_bands_null_when_fewer_than_3`, line 184-193) creates 4 rows where 2 have non-null earnings. The test verifies null bands. But it does not verify the converse: that a CIP family with exactly 2 non-null and 100 null rows still gets null bands (the count should be 2, not 102). This edge case is structurally protected by the COUNT() function, but the test does not explicitly demonstrate it with a large null population.

- **Severity:** MEDIUM
- **Evidence demanded:** Add a test with a CIP family having many null rows and fewer than 3 non-null rows, verifying null bands.
- **Current control:** Adequate -- the SQL is correct and the test covers the boundary, but the test could be stronger.
- **Assessment:** Adequate

---

### LOW

**RISK-013: Pipeline state shows 6 agents NOT_STARTED**

The pipeline state JSON shows pii-scanner, temporal-modeler, lineage-tracker, cde-tagger, doc-generator, governance-reviewer-post, and staff-engineer all at NOT_STARTED status. The spec lists pii-scanner and temporal-modeler as SKIP, but the pipeline state does not reflect these skip decisions (unlike cab-review which is properly SKIPPED).

This means the pipeline is incomplete. The spec's agent workflow (15 steps) has not been fully executed. The remaining agents (lineage-tracker, cde-tagger, doc-generator, governance-reviewer-post, staff-engineer) are required, not skippable.

- **Severity:** LOW (known incomplete state -- this audit is being run before final completion)
- **Evidence demanded:** Complete the remaining pipeline steps or formally document deferral with rationale.
- **Current control:** Adequate -- pipeline state tracking is functioning correctly.
- **Assessment:** Adequate

---

**RISK-014: Test assertion in test_all_null_outcome_fields is imprecise**

Line 579: `assert row["confidence_tier"] in ("insufficient", "low")`. The test allows two possible values when the derivation logic should produce exactly one. With `small_cohort_flag=False` (the default in `_make_silver_row`) and all outcome fields null, the expected tier is "insufficient" (not "low"). The assertion should be `== "insufficient"`, not `in ("insufficient", "low")`.

This imprecision means if the confidence tier logic had a bug that produced "low" instead of "insufficient" for this input, the test would still pass.

- **Severity:** LOW
- **Evidence demanded:** Tighten the assertion to the exact expected value.
- **Current control:** Weak -- test is imprecise.
- **Assessment:** Weak

---

**RISK-015: Spec incorrectly marks adversarial-auditor as SKIP**

The spec (line 185) says: "@adversarial-auditor | SKIP | First Gold spec in pipeline; will audit holistically when cross-source integration specs land." But the pipeline state JSON (line 193-201) lists adversarial-auditor as NOT_STARTED (not SKIPPED), and the pre-review (line 113) flagged this inconsistency. This audit is being run, contradicting the spec's skip decision.

This is a governance process inconsistency. If the adversarial auditor was supposed to be skipped, running it anyway is fine (more review is better). But the spec should be updated to reflect the actual decision.

- **Severity:** LOW
- **Evidence demanded:** Update the spec to remove adversarial-auditor from the SKIP list, or document the override.
- **Current control:** Adequate -- the audit is happening regardless.
- **Assessment:** Adequate

---

## Evidence Demands Summary

| Risk | Evidence Required | Status |
|------|-------------------|--------|
| RISK-001 | Golden dataset with 3+ verified programs | NOT PROVIDED |
| RISK-002 | Data contract YAML | NOT PROVIDED |
| RISK-003 | OpenLineage JSON | NOT PROVIDED |
| RISK-004 | DQ rules verifying derivation formulas | NOT PROVIDED |
| RISK-005 | Tests with real Silver data values | NOT PROVIDED |
| RISK-006 | Reconciled field count (30 vs 31) | NOT PROVIDED |
| RISK-007 | Fix DDL nullability for institution_control | NOT PROVIDED |
| RISK-008 | Investigation of 12 silent DQ rules | NOT PROVIDED |
| RISK-009 | Independent spot-check of 3 EDA claims | NOT PROVIDED |
| RISK-010 | Update BT-015 with Gold prefix | NOT PROVIDED |
| RISK-011 | Zero-guard in SQL or DQ rule | NOT PROVIDED |
| RISK-012 | Test with large null population | NOT PROVIDED |
| RISK-013 | Complete remaining pipeline steps | IN PROGRESS |
| RISK-014 | Tighten imprecise test assertion | NOT PROVIDED |
| RISK-015 | Reconcile spec skip decision | NOT PROVIDED |

---

## Assessment Summary

### What the project does well

1. **Comprehensive DQ rules.** 42 rules covering null propagation, value sets, range checks, distribution monitoring, and cross-field consistency. This is genuinely thorough structural coverage.

2. **Chaos monkey testing.** 5-cycle adversarial hardening at escalating corruption rates. 29 of 42 rules fire consistently. The chaos monkey report honestly identifies gaps rather than claiming perfect coverage.

3. **Thorough EDA.** The Gold EDA profiles every derived field's distribution with specific statistics, identifies outliers with named institutions, and provides threshold recommendations with evidence. The EDA's correction of the spec's "Moderate plurality" expectation to "Low plurality" demonstrates the system's ability to self-correct.

4. **Well-structured transformer code.** The GOLD_SQL is readable, uses CTEs for logical separation, and handles null propagation correctly. The minimum sample size guard for percentile bands is implemented correctly.

5. **Human approval gates.** Three human approvals are documented in the pipeline state (business terms, conceptual model, logical model) with timestamps and notes. The business terms approval includes specific feedback ("BT-021 renamed to Cross-Cohort Earnings Differential") that demonstrates genuine human review, not rubber-stamping.

6. **Honest governance documentation.** The pre-review identifies 6 advisory issues. The chaos monkey report identifies 12 silent rules and 5 potential blind spots. The EDA flags institution_control as a blocking issue. The system does not hide its problems.

### What the project gets wrong

1. **Three required governance artifacts are missing** (golden dataset, data contract, lineage). These are not optional -- they are listed in the spec's success criteria and governance artifact checklist.

2. **No formula verification.** The most important class of hallucination risk -- "the AI computed the wrong formula" -- has no DQ rule coverage. Null propagation and range checks are necessary but not sufficient.

3. **Circular validation.** The same AI wrote the spec, the transformer, the tests, and the DQ rules. Without external validation (golden dataset, real-data tests, independent formula verification), the entire pipeline is a closed loop. Every control was proposed by the entity being controlled.

4. **Physical model DDL contradicts implementation.** The reference DDL says institution_control is NOT NULL; the code says it is nullable. At least one of these is wrong.

### Would a regulator accept this?

**Not yet.** A regulator would note:

- The golden dataset (the primary control against derivation errors) does not exist.
- No data contract exists for consumers to rely on.
- No lineage artifact exists to trace data provenance.
- The DQ rules check structure but not semantic correctness of computed values.
- All tests use synthetic data generated by the same AI that built the pipeline.

The regulator would acknowledge the comprehensive structural controls (42 DQ rules, chaos monkey testing, human approval gates) as strong foundations. But they would require the golden dataset, formula verification rules, and at least one real-data validation test before accepting the pipeline as production-ready.

---

## Recommendations

### Priority 1 -- Must fix before production (CRITICAL)

1. **Create the golden dataset.** Select 3 real programs from Silver data. For each: extract Silver field values, compute all Gold derived fields by hand (or in a separate tool like Excel), write expected values to `governance/golden-datasets/gold-career-outcomes-college-scorecard-golden.json`, and add a DQ rule or test that compares actual Gold output to expected values.

2. **Create the data contract.** Write `governance/data-contracts/consumable-career-outcomes.yaml` specifying schema, quality guarantees, freshness SLA, and breaking change policy.

3. **Complete lineage tracking.** Run the @lineage-tracker agent to produce `governance/lineage/gold-career-outcomes-college-scorecard-{timestamp}.json`.

### Priority 2 -- Should fix before production (HIGH)

4. **Add formula verification DQ rules.** At minimum, add one P0 rule that spot-checks: `SELECT COUNT(*) FROM consumable.career_outcomes WHERE debt_median IS NOT NULL AND earnings_1yr_median IS NOT NULL AND ABS(debt_to_earnings_annual - (debt_median / earnings_1yr_median)) > 0.001`. Repeat for earnings_growth_rate and program_value_index.

5. **Add at least one real-data test.** Query the Silver Iceberg table for a well-known program (e.g., MIT Computer Science). Extract its Silver values. Compute expected Gold values by hand. Add a test that feeds these real values through `derive_gold_rows()` and asserts the expected outputs.

6. **Reconcile field count.** The table has 31 fields, not 30. Update the spec and physical model.

7. **Fix physical model DDL.** Change `institution_control VARCHAR NOT NULL` to `institution_control VARCHAR` (nullable).

### Priority 3 -- Should fix soon (MEDIUM)

8. **Investigate silent DQ rules.** For each of the 12 rules that never fired in chaos testing, document why and either add targeted corruptions or acknowledge the limitation.

9. **Add zero-denomination guard.** Either add `AND earnings_1yr_median > 0` to the SQL CASE expressions, or add a P0 DQ rule: `SELECT COUNT(*) FROM consumable.career_outcomes WHERE earnings_1yr_median = 0 OR debt_median = 0`.

10. **Update BT-015.** Add Gold model to used_in_models and document the 'co' prefix.

11. **Spot-check EDA claims.** Independently verify at least 3 specific values from the EDA report against the actual Silver data.

### Priority 4 -- Minor improvements (LOW)

12. **Tighten test_all_null_outcome_fields assertion** from `in ("insufficient", "low")` to `== "insufficient"`.

13. **Reconcile spec skip decision** for adversarial-auditor.

14. **Complete remaining pipeline agents** (pii-scanner, temporal-modeler, cde-tagger, doc-generator, governance-reviewer-post, staff-engineer).

---

## Audit Trail

- **Artifacts reviewed:** 15 files across governance/, src/gold/, tests/gold/, docs/specs/
- **Tests executed:** 59 tests, 59 passed, 0 failed
- **DQ rules reviewed:** 42 rules (first 20 read in detail, remainder reviewed via scorecard)
- **Pipeline state reviewed:** 20 steps, 12 completed, 1 skipped, 7 not started
- **Missing artifacts found:** 3 (golden dataset, data contract, lineage)
- **Timestamp:** 2026-04-06
- **Auditor:** @adversarial-auditor

---

## Files Referenced

| File | Purpose |
|------|---------|
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/gold-career-outcomes-college-scorecard.md` | Gold spec |
| `/Users/jcernauske/code/bright/futureproof-data/src/gold/college_scorecard_career_outcomes.py` | Transformer code |
| `/Users/jcernauske/code/bright/futureproof-data/tests/gold/test_college_scorecard_career_outcomes.py` | Unit tests |
| `/Users/jcernauske/code/bright/futureproof-data/governance/models/gold-career-outcomes-college-scorecard-physical.md` | Physical model |
| `/Users/jcernauske/code/bright/futureproof-data/governance/business-glossary.json` | Business glossary |
| `/Users/jcernauske/code/bright/futureproof-data/governance/eda/gold-career-outcomes-eda.md` | EDA report |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/gold-career-outcomes-college-scorecard.json` | DQ rules |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-scorecards/gold-career-outcomes-college-scorecard-scorecard.md` | DQ scorecard |
| `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-manifests/gold-career-outcomes-college-scorecard-chaos.md` | Chaos monkey report |
| `/Users/jcernauske/code/bright/futureproof-data/governance/domain-context.md` | Domain context |
| `/Users/jcernauske/code/bright/futureproof-data/governance/reviews/gold-career-outcomes-college-scorecard-pre-review.md` | Pre-implementation review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/pipeline-state/gold-career-outcomes-college-scorecard-pipeline.json` | Pipeline state |
