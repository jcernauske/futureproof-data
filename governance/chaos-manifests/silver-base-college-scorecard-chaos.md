# After-Action Report: silver-base-college-scorecard

**Date:** 2026-04-07T01:05:59Z
**Agent:** @chaos-monkey
**Spec:** silver-base-college-scorecard
**Table:** base.college_scorecard (Silver zone)
**Shadow Table:** shadow_base.college_scorecard
**Source Rows:** 69,947
**Cycles Completed:** 5 of 5
**DQ Rules Tested:** 35

## Executive Summary

Five adversarial hardening cycles were executed against `base.college_scorecard` at escalating corruption rates (5%, 6%, 7%, 8%, 10%). Corruptions were injected across all 10 DQ dimensions targeting the Silver zone schema: nullified required fields, invalid CIP codes, duplicate grain rows, contradictory field combinations, plausible-but-wrong values, extreme outliers, temporal anomalies, volume inflation, orphan unitids, and removal of CIP family coverage.

**Overall Detection Rate: 71-74% (25-27 of 35 rules fired across cycles)**

Of 35 DQ rules, 26 fired consistently across all 5 cycles. One rule (SLV-CS-028) errored every cycle. Eight rules remained silent across all cycles, representing potential gaps or rules that check dimensions not targeted by these corruptions.

## Corruption Strategies Applied

### Per Dimension

| Dimension | Strategy | Target Fields | Corruptions (Cycle 5) |
|-----------|----------|---------------|----------------------|
| Completeness | Null required fields | record_id, unitid, cipcode, institution_name, program_name, cip_family, cip_family_name, credential_level, credential_description, small_cohort_flag, source_load_date, ingested_at | 233 |
| Validity | Invalid formats/values | cipcode (bad format), credential_level (0, -1, 99), cip_family (00, 99, XX), institution_control (invalid enum) | 233 |
| Uniqueness | Exact row duplication | record_id (full grain duplicate) | 139 |
| Consistency | Contradictory combinations | cipcode vs cip_family mismatch, credential_level vs credential_description mismatch, cip_family vs cip_family_name mismatch, small_cohort_flag vs completions_count_1 contradiction | 174 |
| Accuracy | Plausible but wrong | Swapped earnings_1yr/2yr, wrong unitid in valid range, earnings off by 10x | 98 |
| Reasonableness | Extreme outliers | Negative earnings (-500K), extreme earnings (50M), extreme debt (10M), negative debt, impossible completions (-1, 999999) | 233 |
| Freshness | Temporal anomalies | Future source_load_date (2030), stale source_load_date (2015), future ingested_at (2035), epoch ingested_at (1970) | 174 |
| Volume | Row count inflation | Mass duplication (~10% of rows) | 6,995+ duplicates |
| Referential Integrity | Orphan keys | unitid set to 900M-999M range (impossible IPEDS IDs) | 174 |
| Coverage | Missing combinations | Remove all rows for 3 common CIP families per cycle | ~6,000-11,000 rows removed |

## Per-Cycle Results

| Cycle | Rate | Corruptions | Final Rows | Rules Failed | Rules Passed | Detection Rate |
|-------|------|-------------|------------|-------------|-------------|----------------|
| 1 | 5% | 727 | 58,279 | 27 | 8 | 74.3% |
| 2 | 6% | 877 | 63,586 | 26 | 9 | 71.4% |
| 3 | 7% | 1,023 | 65,491 | 26 | 9 | 71.4% |
| 4 | 8% | 1,175 | 61,726 | 25 | 10 | 68.6% |
| 5 | 10% | 1,462 | 63,606 | 26 | 9 | 71.4% |

## DQ Rule Performance

### Rules That Fired (Caught Corruption) -- 26 rules

These rules detected corruptions in at least one cycle:

| Rule ID | Fired In | Cycle 1 Value | Cycle 5 Value | Trend | Likely Dimension |
|---------|----------|---------------|---------------|-------|-----------------|
| SLV-CS-001 | 5/5 | 5,363 | 5,819 | Increasing | Completeness / Volume |
| SLV-CS-002 | 5/5 | 38 | 120 | Increasing | Completeness |
| SLV-CS-003 | 5/5 | 36 | 54 | Increasing | Completeness |
| SLV-CS-004 | 5/5 | 91 | 199 | Increasing | Validity |
| SLV-CS-005 | 5/5 | 8 | 13 | Increasing | Validity |
| SLV-CS-006 | 5/5 | 13 | 20 | Increasing | Validity |
| SLV-CS-007 | 5/5 | 7 | 23 | Increasing | Validity |
| SLV-CS-008 | 5/5 | 9 | 22 | Increasing | Validity |
| SLV-CS-009 | 5/5 | 9 | 16 | Increasing | Validity |
| SLV-CS-010 | 5/5 | 6 | 21 | Increasing | Validity / Consistency |
| SLV-CS-011 | 5/5 | 13 | 20 | Increasing | Validity / Consistency |
| SLV-CS-012 | 5/5 | 5 | 12 | Increasing | Validity / Consistency |
| SLV-CS-013 | 5/5 | 6 | 16 | Increasing | Consistency |
| SLV-CS-014 | 5/5 | 7 | 11 | Increasing | Consistency |
| SLV-CS-015 | 5/5 | 11 | 23 | Increasing | Consistency |
| SLV-CS-021 | 1/5 | 1 (FAIL) | 0 (PASS) | Seed-dependent | Freshness / Uniqueness |
| SLV-CS-022 | 5/5 | 20 | 53 | Increasing | Reasonableness |
| SLV-CS-023 | 5/5 | 25 | 45 | Increasing | Reasonableness |
| SLV-CS-024 | 5/5 | 38 | 87 | Increasing | Reasonableness |
| SLV-CS-025 | 5/5 | 14 | 30 | Increasing | Reasonableness |
| SLV-CS-026 | 5/5 | 19 | 58 | Increasing | Reasonableness |
| SLV-CS-027 | 5/5 | 32 | 41 | Increasing | Referential Integrity / Accuracy |
| SLV-CS-030 | 5/5 | 12 | 30 | Increasing | Freshness |
| SLV-CS-031 | 5/5 | 5,372 | 5,836 | Increasing | Volume / Coverage |
| SLV-CS-033 | 4/5 | 1 (FAIL) | 1 (FAIL) | Stable | Uniqueness |
| SLV-CS-034 | 5/5 | 69 | 149 | Increasing | Coverage / Referential Integrity |

### Rule SLV-CS-028 -- ERROR in All Cycles

SLV-CS-028 returned `ERROR` with `value=None` across all 5 cycles. This rule has an execution defect that prevents it from producing a pass/fail result against the shadow table. This should be investigated and fixed by @dq-rule-writer.

### Rules That Never Fired (Silent) -- 8 rules

These rules passed in every cycle despite heavy corruption:

| Rule ID | Cycle 1 Value | Cycle 5 Value | Analysis |
|---------|---------------|---------------|----------|
| SLV-CS-016 | 67.9 | 65.7 | Percentage-based metric; threshold likely accommodates corruption-induced drift |
| SLV-CS-017 | 63.7 | 61.4 | Percentage-based metric; threshold likely too generous |
| SLV-CS-018 | 67.0 | 65.3 | Percentage-based metric; threshold likely too generous |
| SLV-CS-019 | 8.4 | 8.8 | Low percentage metric; our corruptions don't push it past threshold |
| SLV-CS-020 | 8.1 | 8.5 | Low percentage metric; similar to SLV-CS-019 |
| SLV-CS-021 | 1 (FAIL C1) | 0 (PASS C2-5) | Intermittent -- fires only with specific seed/rate combo |
| SLV-CS-029 | 0 | 0 | Always zero; may check a condition our corruptions don't create |
| SLV-CS-032 | 0 | 0 | Always zero; may check a condition our corruptions don't create |
| SLV-CS-035 | 0 | 0 | Always zero; may check a condition our corruptions don't create |

## Gap Analysis

### Confirmed Gaps

1. **SLV-CS-028 (ERROR):** This rule cannot execute against shadow tables. It errors every cycle with `value=None`. Either the SQL references a table/column that does not exist in the shadow namespace, or it has a structural defect. **Action required: @dq-rule-writer must fix this rule.**

2. **Percentage-threshold rules (SLV-CS-016, SLV-CS-017, SLV-CS-018):** These appear to use percentage-based thresholds that are too generous. Even with 10% corruption, the values (65-68%) stay within threshold. If these check nullable field null rates (e.g., "earnings_1yr_median null rate"), the thresholds were calibrated against the clean data where ~64% of those fields are already null. Our corruptions add only marginal nulls on top of an already-high baseline. **Recommendation: Tighten thresholds or convert to absolute-count checks for corruption detection.**

3. **Low-signal rules (SLV-CS-019, SLV-CS-020):** Values around 8-9% across all cycles. These likely check a dimension where our corruption volume is insufficient to trigger the threshold. **Recommendation: Review whether these thresholds are appropriate for the data's actual distribution.**

4. **Zero-value rules (SLV-CS-029, SLV-CS-032, SLV-CS-035):** Always return 0 regardless of corruption level. Possible explanations:
   - They check conditions that our corruption strategies don't create (e.g., specific cross-table joins, regex patterns we didn't violate)
   - They check conditions that happen to be unaffected by our corruption approaches
   - They may be checking aspects of data integrity that are structurally maintained even in corrupted data
   **Recommendation: These rules should be reviewed to determine if they provide meaningful detection value. If they check conditions that real-world corruption could violate, new corruption strategies should be added.**

### Potential Blind Spots

Based on our 10-dimension corruption strategy, these areas may lack sufficient DQ coverage:

1. **Cross-field consistency (cipcode prefix vs cip_family):** We injected mismatches but it is unclear which specific rule catches this. If no rule enforces `LEFT(cipcode, 2) = cip_family`, this is a gap.

2. **Credential level/description consistency:** All rows have `credential_level=3` and `credential_description="Bachelor's Degree"`. We injected mismatches but rules may not enforce this 1:1 mapping since the data is currently homogeneous.

3. **institution_control validation:** All values are NULL in the real data. Our injections of invalid enum values ("Government", "Federal") may not be detected if no rule validates the allowed value set for this field.

4. **record_id determinism:** We did not verify whether rules check that `record_id = compute_grain_id(unitid, cipcode, credential_level)`. If someone modifies a grain field without recalculating record_id, this should be caught.

## Stability Assessment

| Metric | Value |
|--------|-------|
| Rules consistently firing (all 5 cycles) | 24 |
| Rules intermittently firing | 2 (SLV-CS-021, SLV-CS-033) |
| Rules consistently silent | 8 |
| Rules in error state | 1 (SLV-CS-028) |
| Stability reached at cycle | 2 (same silent set from cycle 2 onward) |
| Consecutive stable cycles | 4 (cycles 2-5 have identical silent set) |

## Recommendations for @dq-rule-writer

### Priority 1 (Fix)
1. **Fix SLV-CS-028:** Rule errors on every execution. Must be fixed before it can provide any detection value.

### Priority 2 (Tighten)
2. **Review SLV-CS-016/017/018 thresholds:** These percentage-based rules never fire despite 10% corruption. If they check nullable field null rates, the thresholds may be set too loosely relative to the clean data baseline.

### Priority 3 (Investigate)
3. **Verify SLV-CS-029/032/035 utility:** These always return 0. Determine if they check conditions that could realistically be violated by data corruption. If not, consider replacing with more targeted rules.
4. **Review SLV-CS-019/020 sensitivity:** Low-signal rules that stay within threshold at all corruption levels.

### Priority 4 (New Rules -- if not already covered)
5. **Cross-field consistency rule:** Ensure `cipcode[:2] == cip_family` is enforced.
6. **institution_control enum validation:** If/when this field is populated, ensure only valid values are accepted.
7. **record_id determinism check:** Verify `record_id = grain_hash(unitid, cipcode, credential_level)`.
8. **small_cohort_flag consistency:** Ensure `small_cohort_flag = (completions_count_1 IS NULL OR completions_count_1 < 30)`.

## Information Barrier Compliance

This report was produced without reading DQ rule definitions (`governance/dq-rules/silver-base-college-scorecard.json`). All analysis is empirical: we observe which rules fired and which did not, then infer dimension coverage from the pattern of results. Rule IDs are opaque identifiers; we do not know what SQL they execute or what thresholds they use.

The "Likely Dimension" column in the rules table above is an inference based on which corruption functions would logically trigger each rule's failure, not a statement of what the rule actually checks.

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Chaos manifest (JSON) | `governance/chaos-manifests/silver-base-college-scorecard-manifest.json` |
| After-Action Report (this file) | `governance/chaos-manifests/silver-base-college-scorecard-chaos.md` |
| Chaos runner script | `governance/chaos-manifests/silver_chaos_runner.py` |
