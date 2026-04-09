# After-Action Report: gold-career-outcomes-college-scorecard

**Date:** 2026-04-06T23:30:00Z
**Agent:** @chaos-monkey
**Spec:** gold-career-outcomes-college-scorecard
**Table:** consumable.career_outcomes (Gold zone)
**Shadow Table:** shadow_consumable.career_outcomes
**Source Rows:** 69,947
**Cycles Completed:** 5 of 5
**DQ Rules Tested:** 42

## Executive Summary

Five adversarial hardening cycles were executed against `consumable.career_outcomes` at escalating corruption rates (5%, 6%, 7%, 8%, 10%). Corruptions were injected across all 10 DQ dimensions targeting the Gold zone schema: nullified required fields, invalid CIP codes and tier values, duplicate grain rows, contradictory derived-field combinations (confidence tier vs flags, debt-to-earnings tier vs ratio, percentile band ordering violations, has_earnings/has_debt flag contradictions), plausible-but-wrong values, extreme outliers on financial metrics, temporal anomalies, volume inflation, orphan keys, and removal of CIP family and confidence tier coverage.

**Overall Detection Rate: 69-71% (29-30 of 42 rules fired across cycles)**

Of 42 DQ rules, 29 fired consistently across all 5 cycles. One rule (GLD-CO-003) fired intermittently (cycle 2 only). Twelve rules remained silent across all 5 cycles, representing potential gaps or rules checking dimensions not targeted by these corruptions.

## Corruption Strategies Applied

### Per Dimension

| Dimension | Strategy | Target Fields | Corruptions (Cycle 5) |
|-----------|----------|---------------|----------------------|
| Completeness | Null required fields | record_id, unitid, cipcode, institution_name, program_name, cip_family, cip_family_name, credential_level, small_cohort_flag, confidence_tier, has_earnings, has_debt, outcome_completeness, source_load_date, promoted_at | 233 |
| Validity | Invalid formats/values | cipcode (bad format), credential_level (0, -1, 99), confidence_tier (invalid enum), debt_to_earnings_tier (case-wrong, invalid enum), outcome_completeness (non-standard values), cip_family (00, 99, XX) | 233 |
| Uniqueness | Exact row duplication | record_id (full grain duplicate) | 139 |
| Consistency | Contradictory combinations | cipcode vs cip_family mismatch, confidence_tier contradicts has_earnings/has_debt/small_cohort_flag, debt_to_earnings_tier contradicts ratio, has_earnings flag contradicts earnings nulls, has_debt flag contradicts debt null, outcome_completeness contradicts field nulls, percentile band ordering (p25 > p75) | 211 |
| Accuracy | Plausible but wrong | Swapped earnings_1yr/2yr, wrong unitid in valid range, earnings off by 10x, wrong debt_to_earnings_annual (not debt/earnings), wrong earnings_growth_rate | 80 |
| Reasonableness | Extreme outliers | Negative earnings (-500K), extreme earnings (50M), extreme debt (10M), negative debt, extreme DTE ratios (50.0, -5.0), impossible rank values (-0.5, 1.5), extreme growth rates (10.0, -5.0), negative program_value_index | 233 |
| Freshness | Temporal anomalies | Future source_load_date (2030), stale source_load_date (2015), future promoted_at (2035), epoch promoted_at (1970) | 174 |
| Volume | Row count inflation | Mass duplication (~10% of rows) | 6,995+ duplicates |
| Referential Integrity | Orphan keys | unitid set to 900M-999M range (impossible IPEDS IDs), record_id set to non-hash values | 174 |
| Coverage | Missing combinations | Remove all rows for 3 common CIP families per cycle, remove subset of confidence tier rows | ~8,500-12,600 rows removed |

## Per-Cycle Results

| Cycle | Rate | Corruptions | Final Rows | Rules Failed | Rules Passed | Detection Rate |
|-------|------|-------------|------------|-------------|-------------|----------------|
| 1 | 5% | 733 | 63,213 | 29 | 13 | 69.0% |
| 2 | 6% | 891 | 57,352 | 30 | 12 | 71.4% |
| 3 | 7% | 1,042 | 61,132 | 29 | 13 | 69.0% |
| 4 | 8% | 1,179 | 65,066 | 29 | 13 | 69.0% |
| 5 | 10% | 1,482 | 61,380 | 29 | 13 | 69.0% |

## DQ Rule Performance

### Rules That Fired (Caught Corruption) -- 29 rules (consistently)

These rules detected corruptions in every cycle:

| Rule ID | Cycle 1 Value | Cycle 5 Value | Trend | Likely Dimension |
|---------|---------------|---------------|-------|-----------------|
| GLD-CO-001 | 5,756 | 5,632 | Stable/Volume-dependent | Completeness / Volume |
| GLD-CO-002 | 5,761 | 5,627 | Stable/Volume-dependent | Completeness / Volume |
| GLD-CO-004 | 2 | 15 | Increasing | Validity |
| GLD-CO-005 | 2 | 4 | Increasing | Validity |
| GLD-CO-006 | 4 | 11 | Increasing | Validity |
| GLD-CO-007 | 8 | 9 | Stable | Validity |
| GLD-CO-008 | 21 | 39 | Increasing | Validity / Consistency |
| GLD-CO-009 | 28 | 57 | Increasing | Validity / Consistency |
| GLD-CO-010 | 31 | 53 | Increasing | Consistency |
| GLD-CO-011 | 20 | 42 | Increasing | Consistency |
| GLD-CO-012 | 14 | 27 | Increasing | Consistency |
| GLD-CO-013 | 1 | 3 | Increasing | Consistency |
| GLD-CO-014 | 14 | 13 | Stable | Reasonableness |
| GLD-CO-015 | 8 | 13 | Increasing | Reasonableness |
| GLD-CO-016 | 9 | 15 | Increasing | Reasonableness |
| GLD-CO-017 | 28 | 53 | Increasing | Reasonableness |
| GLD-CO-018 | 17 | 40 | Increasing | Reasonableness |
| GLD-CO-019 | 14 | 33 | Increasing | Reasonableness |
| GLD-CO-021 | 12 | 20 | Increasing | Freshness |
| GLD-CO-028 | 4 | 4 | Stable | Referential Integrity |
| GLD-CO-029 | 38 | 66 | Increasing | Accuracy / Consistency |
| GLD-CO-030 | 13 | 16 | Increasing | Accuracy / Consistency |
| GLD-CO-031 | 64 | 124 | Increasing | Accuracy / Reasonableness |
| GLD-CO-032 | 73 | 156 | Increasing | Reasonableness |
| GLD-CO-033 | 28 | 43 | Increasing | Reasonableness / Validity |
| GLD-CO-036 | 11 | 34 | Increasing | Consistency / Coverage |
| GLD-CO-037 | 3 | 18 | Increasing | Freshness / Consistency |
| GLD-CO-038 | 22 | 61 | Increasing | Consistency / Accuracy |
| GLD-CO-041 | 1 | 1 | Stable | Volume / Coverage |

### Intermittently Firing Rule -- 1 rule

| Rule ID | Cycles Fired | Analysis |
|---------|-------------|----------|
| GLD-CO-003 | 1/5 (cycle 2 only, value=1) | Seed-dependent; fires only with specific corruption pattern. Likely checks a rare condition our corruptions occasionally trigger. |

### Rules That Never Fired (Silent) -- 12 rules

These rules passed in every cycle despite heavy corruption:

| Rule ID | Cycle 1 Value | Cycle 5 Value | Analysis |
|---------|---------------|---------------|----------|
| GLD-CO-020 | 0 | 0 | Always zero; may check a condition our corruptions don't create |
| GLD-CO-022 | 0 | 0 | Always zero; structural check that holds under corruption |
| GLD-CO-023 | 0 | 0 | Always zero; structural check that holds under corruption |
| GLD-CO-024 | 0 | 0 | Always zero; structural check that holds under corruption |
| GLD-CO-025 | 0 | 0 | Always zero; structural check that holds under corruption |
| GLD-CO-026 | 0 | 0 | Always zero; structural check that holds under corruption |
| GLD-CO-027 | 0 | 0 | Always zero; structural check that holds under corruption |
| GLD-CO-034 | 0 | 0 | Always zero; may check a condition we don't corrupt |
| GLD-CO-035 | 0 | 0 | Always zero; may check a condition we don't corrupt |
| GLD-CO-039 | 100.0 | 100.0 | Percentage metric (100%); our corruptions don't push it below threshold |
| GLD-CO-040 | 0 | 0 | Always zero; structural check that holds under corruption |
| GLD-CO-042 | 0 | 0 | Always zero; structural check that holds under corruption |

## Gap Analysis

### Confirmed Gaps

1. **GLD-CO-039 (Percentage threshold):** Returns 100.0 across all cycles despite corruption. If this is a percentage-based metric, the threshold may be set to allow 100% pass even with corrupted data, OR it checks a dimension where our corruptions don't reduce the pass rate. If it checks a specific data pattern that our corruption strategies don't alter (e.g., "percentage of record_ids matching expected format"), tighter thresholds or complementary absolute-count rules may be needed.

2. **Zero-value cluster (GLD-CO-020, 022-027, 034, 035, 040, 042):** Eleven rules consistently return 0. Possible explanations:
   - They check conditions that are structurally impossible in the Gold schema (e.g., cross-table joins that always resolve even with orphan keys in the shadow table)
   - They check conditions where our corruption approach preserves the invariant by accident (e.g., percentile band null-pattern rules that check CIP family sample sizes -- our corruptions don't reduce per-family counts enough to trigger)
   - They may validate conditions that are unaffected because our corruptions target individual rows rather than aggregate statistical properties

### Potential Blind Spots

Based on our 10-dimension corruption strategy and the Gold-specific derived fields, these areas may lack sufficient DQ coverage:

1. **Percentile band null-pattern consistency:** The spec requires p25/p50/p75 to be null when a CIP family has fewer than 3 non-null values for a field. We did not specifically inject violations of this pattern (e.g., non-null percentile bands for a CIP family with only 2 earnings values). If no rule enforces this, it is a gap.

2. **debt_to_earnings_annual derivation correctness:** We injected wrong DTE ratios (values that don't equal debt_median/earnings_1yr_median). Whether rules catch this depends on whether they verify the derivation formula, not just range.

3. **earnings_growth_rate derivation correctness:** Similar concern -- we set growth rates to extreme/wrong values, but whether rules verify `(2yr - 1yr) / 1yr` specifically is unknown.

4. **program_value_index derivation correctness:** We set it to negative/extreme values. Range checks would catch extremes, but formula verification may be missing.

5. **record_id determinism:** We injected orphan record_ids (not matching grain hash). GLD-CO-028 consistently fires with value=4, suggesting it may catch this, but it is unclear if it specifically verifies `record_id = compute_grain_id(unitid, cipcode, credlev)`.

6. **cip_family_earnings_rank range:** We injected impossible values (-0.5, 1.5). Some rules caught extremes, but whether a specific 0.0-1.0 range check exists for this field is unclear.

7. **Cross-field null propagation:** The spec requires `debt_to_earnings_annual IS NULL WHEN debt_median IS NULL OR earnings_1yr_median IS NULL`. We did not specifically inject non-null DTE ratios for rows with null inputs. If no rule enforces this null-propagation invariant, it is a gap.

## Stability Assessment

| Metric | Value |
|--------|-------|
| Rules consistently firing (all 5 cycles) | 29 |
| Rules intermittently firing | 1 (GLD-CO-003) |
| Rules consistently silent | 12 |
| Rules in error state | 0 |
| Stability reached at cycle | 3 (same silent set from cycle 3 onward) |
| Consecutive stable cycles | 3 (cycles 3-5 have identical silent set) |

## Recommendations for @dq-rule-writer

### Priority 1 (New Rules -- if not already covered)

1. **Null-propagation consistency:** Add rules verifying that derived fields (debt_to_earnings_annual, earnings_growth_rate, program_value_index, cip_family_earnings_rank) are null when their input fields are null, and non-null only when inputs are non-null.

2. **Derivation formula verification:** Add rules that spot-check or fully verify:
   - `debt_to_earnings_annual = debt_median / earnings_1yr_median`
   - `earnings_growth_rate = (earnings_2yr_median - earnings_1yr_median) / earnings_1yr_median`
   - `program_value_index = earnings_1yr_median / debt_median`

3. **Percentile band null-pattern:** Add a rule verifying that percentile bands are null when a CIP family has < 3 non-null values for the corresponding field.

### Priority 2 (Investigate Silent Rules)

4. **Review GLD-CO-020, 022-027, 034, 035, 040, 042:** Determine what these 11 rules check. If they validate conditions that real-world corruption could violate, new corruption strategies should be added to stress-test them. If they are structural invariants that are inherently preserved by the schema, they may provide insufficient detection value and could be supplemented with more targeted rules.

5. **Review GLD-CO-039 threshold:** This returns 100.0 across all cycles. If it is a percentage-based rule, the threshold may need tightening, or a complementary absolute-count rule should be added.

### Priority 3 (Tighten Existing)

6. **GLD-CO-003 intermittent firing:** Fires only with specific seed (cycle 2, value=1). If this checks a condition that should trigger more reliably under corruption, its threshold may need adjustment.

## Information Barrier Compliance

This report was produced without reading DQ rule definitions (`governance/dq-rules/gold-career-outcomes-college-scorecard.json`). All analysis is empirical: we observe which rules fired and which did not, then infer dimension coverage from the pattern of results. Rule IDs are opaque identifiers; we do not know what SQL they execute or what thresholds they use.

The "Likely Dimension" column in the rules table above is an inference based on which corruption functions would logically trigger each rule's failure, not a statement of what the rule actually checks.

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Chaos manifest (JSON) | `governance/chaos-manifests/gold-career-outcomes-college-scorecard-manifest.json` |
| After-Action Report (this file) | `governance/chaos-manifests/gold-career-outcomes-college-scorecard-chaos.md` |
| Chaos runner script | `governance/chaos-manifests/gold_chaos_runner.py` |
