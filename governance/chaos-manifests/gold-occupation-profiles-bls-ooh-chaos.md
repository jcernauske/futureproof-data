# After-Action Report: gold-occupation-profiles-bls-ooh

**Date:** 2026-04-07T20:40:00Z
**Agent:** @chaos-monkey
**Spec:** gold-occupation-profiles-bls-ooh
**Table:** consumable.occupation_profiles (Gold zone)
**Shadow Table:** shadow_consumable.occupation_profiles
**Source Rows:** 832
**Cycles Completed:** 5 of 5
**DQ Rules Tested:** 53 (54 defined, 1 deferred: GLD-OP-048)

## Executive Summary

Five adversarial hardening cycles were executed against `consumable.occupation_profiles` at escalating corruption rates (5%, 6%, 7%, 8%, 10%). Corruptions were injected across all 10 DQ dimensions targeting the Gold zone schema: nullified required fields, invalid GRW/market/wage values, duplicate soc_codes, contradictory derived-field combinations (grw_score_rounded vs grw_score, confidence_tier vs flags, data_completeness vs null counts, growth_category vs grw_score), plausible-but-wrong values, extreme outliers, temporal anomalies, volume inflation, orphan keys, and removal of SOC major group coverage.

**Overall Detection Rate: 67.9% - 77.4% (36-42 of 53 rules fired across cycles)**

Of 53 executable DQ rules, 26 fired consistently across all 5 cycles. 18 rules fired intermittently (seed-dependent). 8 rules remained silent across all 5 cycles. 1 rule (GLD-OP-039) errored consistently due to a SQL execution issue.

## Corruption Strategies Applied

### Per Dimension

| Dimension | Strategy | Target Fields | Corruptions (Cycle 5) |
|-----------|----------|---------------|----------------------|
| Completeness | Null required fields | record_id, soc_code, occupation_title, soc_major_group, soc_major_group_name, broad_occupation_flag, catchall_flag, growth_category, wage_available, confidence_tier, data_completeness, backs_stats, backs_bosses, source_load_date, promoted_at | 27 |
| Validity | Invalid formats/values | soc_code (bad format), growth_category (invalid enum), grw_score (out of 1-10), grw_score_rounded (out of 1-10), wage_tier (invalid enum), confidence_tier (invalid enum), data_completeness (outside {0.75,1.0}), education_code (out of 1-8), soc_major_group (invalid code), backs_stats (wrong constant), backs_bosses (wrong constant), wage_percentile (out of 0-1), negative employment, wage out of range, employment_change_pct extreme | 27 |
| Uniqueness | Exact row duplication | soc_code (full grain duplicate with identical record_id) | 16 |
| Consistency | Contradictory combinations | grw_score_rounded != ROUND(grw_score), market_score_rounded != ROUND(market_score), soc_major_group != soc_code[:2], confidence_tier contradicts wage_available/broad/catchall flags, wage_tier non-null with wage_available=False, wage_percentile non-null with wage_available=False, data_completeness contradicts actual null counts, growth_category contradicts grw_score range, broad+catchall both True | 27 |
| Accuracy | Plausible but wrong | Swapped employment_current/projected, wrong soc_major_group_name, wage off by factor (10x, 0.1x), wrong market_score formula, wrong grw_score for employment_change_pct | 20 |
| Reasonableness | Extreme outliers | Negative wages (-500K), extreme wages (50M), extreme employment (100M+), extreme openings (50M+), extreme grw_score (0.001, 99.9, -50), extreme market_score (0.001, -5, 99.9), negative openings | 27 |
| Freshness | Temporal anomalies | Future source_load_date (2030), stale source_load_date (2015), future promoted_at (2035), epoch promoted_at (1970) | 20 |
| Referential Integrity | Orphan keys | record_id set to non-hash values (op-ORPHAN*), soc_code set to non-existent codes (99-9999, 00-0001) | 20 |
| Volume | Row count inflation | Mass duplication (~10% of rows) | 83+ duplicates |
| Coverage | Missing combinations | Remove all rows for 3 SOC major groups per cycle, remove subset of confidence tier rows | ~150-300 rows removed |

## Per-Cycle Results

| Cycle | Rate | Corruptions | Final Rows | Rules Failed | Rules Passed | Rules Errored | Detection Rate |
|-------|------|-------------|------------|-------------|-------------|---------------|----------------|
| 1 | 5% | 95 | 735 | 38 | 15 | 1 | 69.8% |
| 2 | 6% | 113 | 523 | 38 | 15 | 1 | 69.8% |
| 3 | 7% | 134 | 598 | 37 | 16 | 1 | 67.9% |
| 4 | 8% | 153 | 687 | 42 | 11 | 1 | 77.4% |
| 5 | 10% | 189 | 586 | 39 | 14 | 1 | 71.7% |

## DQ Rule Performance

### Rules That ALWAYS Fired (26 rules -- all 5 cycles)

| Rule ID | C1 Val | C2 Val | C3 Val | C4 Val | C5 Val | Inferred Dimension |
|---------|--------|--------|--------|--------|--------|-------------------|
| GLD-OP-001 | 71 | 46 | 47 | 73 | 50 | Uniqueness (grain) |
| GLD-OP-002 | 72 | 48 | 47 | 73 | 49 | Uniqueness (record_id) |
| GLD-OP-003 | 1 | 1 | 1 | 1 | 1 | Volume (row count != 832) |
| GLD-OP-005 | 4 | 4 | 1 | 3 | 2 | Validity (grw_score range) |
| GLD-OP-008 | 7 | 11 | 4 | 3 | 10 | Consistency (grw_rounded != ROUND) |
| GLD-OP-012 | 9 | 1 | 5 | 7 | 7 | Consistency (market_rounded != ROUND) |
| GLD-OP-014 | 1 | 1 | 1 | 1 | 1 | Completeness (wage_pct_overall null count) |
| GLD-OP-016 | 1 | 1 | 1 | 1 | 1 | Completeness (wage_pct_edu null count) |
| GLD-OP-018 | 1 | 1 | 1 | 1 | 1 | Completeness (wage_tier null count) |
| GLD-OP-019 | 1 | 1 | 2 | 4 | 8 | Consistency (wage_tier vs wage_available) |
| GLD-OP-020 | 4 | 1 | 2 | 2 | 2 | Completeness (confidence_tier not null) |
| GLD-OP-022 | 1 | 1 | 1 | 1 | 1 | Validity (confidence_tier low count) |
| GLD-OP-024 | 1 | 3 | 2 | 4 | 8 | Consistency (low iff wage_available=False) |
| GLD-OP-029 | 1 | 1 | 1 | 1 | 1 | Consistency (data_completeness 0.75 count) |
| GLD-OP-030 | 1 | 1 | 2 | 4 | 8 | Consistency (wage_pct null iff wage_available=False) |
| GLD-OP-031 | 4 | 2 | 15 | 8 | 16 | Completeness (NOT NULL identity fields) |
| GLD-OP-036 | 1 | 1 | 1 | 1 | 1 | Validity (confidence tier distribution) |
| GLD-OP-037 | 1 | 1 | 1 | 1 | 1 | Validity (wage tier distribution) |
| GLD-OP-038 | 5 | 6 | 3 | 4 | 10 | Consistency (grw_score vs growth_category) |
| GLD-OP-040 | 10 | 6 | 10 | 11 | 9 | Consistency (soc_major_group derivation) |
| GLD-OP-043 | 5 | 1 | 10 | 6 | 7 | Validity (wage range) |
| GLD-OP-044 | 1 | 2 | 2 | 1 | 2 | Validity (employment_change_pct range) |
| GLD-OP-046 | 1 | 1 | 1 | 1 | 1 | Validity (catchall_flag count) |
| GLD-OP-049 | 1 | 1 | 2 | 4 | 8 | Consistency (wage_available accuracy) |
| GLD-OP-051 | 2 | 1 | 3 | 2 | 2 | Validity (openings non-negative) |
| GLD-OP-053 | 1 | 1 | 1 | 1 | 1 | Coverage (22 SOC groups) |

### Rules That INTERMITTENTLY Fired (18 rules)

| Rule ID | Fires | Pattern (C1-C5) | Inferred Dimension |
|---------|-------|-----------------|-------------------|
| GLD-OP-004 | 3/5 | FAIL FAIL FAIL PASS PASS | Validity (SOC code format) |
| GLD-OP-007 | 3/5 | FAIL PASS FAIL PASS FAIL | Validity (grw_rounded range) |
| GLD-OP-009 | 4/5 | FAIL PASS FAIL FAIL FAIL | Validity (market_score range) |
| GLD-OP-013 | 3/5 | PASS FAIL PASS FAIL FAIL | Validity (wage_pct_overall range) |
| GLD-OP-015 | 2/5 | PASS PASS PASS FAIL FAIL | Validity (wage_pct_edu range) |
| GLD-OP-017 | 2/5 | PASS PASS FAIL FAIL PASS | Validity (wage_tier values) |
| GLD-OP-021 | 2/5 | FAIL PASS PASS PASS FAIL | Validity (confidence_tier values) |
| GLD-OP-025 | 3/5 | PASS FAIL PASS FAIL FAIL | Validity (backs_stats) |
| GLD-OP-026 | 4/5 | PASS FAIL FAIL FAIL FAIL | Validity (backs_bosses) |
| GLD-OP-027 | 4/5 | FAIL FAIL PASS FAIL FAIL | Completeness (data_completeness not null) |
| GLD-OP-028 | 4/5 | FAIL FAIL FAIL FAIL PASS | Validity (data_completeness value set) |
| GLD-OP-041 | 3/5 | PASS PASS FAIL FAIL FAIL | Validity (SOC major group values) |
| GLD-OP-042 | 4/5 | FAIL FAIL FAIL FAIL PASS | Validity (growth_category values) |
| GLD-OP-045 | 4/5 | FAIL FAIL PASS FAIL FAIL | Validity (broad_flag count) |
| GLD-OP-047 | 3/5 | FAIL FAIL PASS FAIL PASS | Validity (education_code range) |
| GLD-OP-050 | 3/5 | PASS FAIL PASS FAIL FAIL | Validity (employment positivity) |
| GLD-OP-052 | 4/5 | FAIL PASS FAIL FAIL FAIL | Consistency (no broad+catchall overlap) |
| GLD-OP-054 | 4/5 | FAIL FAIL FAIL FAIL PASS | Consistency (data_completeness derivation) |

**Intermittent firing is expected.** These rules fire based on whether random corruption targets happen to hit specific fields or combinations. With 832 rows and corruption targeting different rows per seed, stochastic variation means certain corruptions may miss the exact conditions a rule checks. At 10% corruption rate (cycle 5), more rules fire because more rows are targeted.

### Rules That NEVER Fired (8 rules -- always passed)

| Rule ID | All Values | Analysis |
|---------|-----------|----------|
| GLD-OP-006 | [0,0,0,0,0] | grw_score null count = 0. Our corruptions set grw_score to wrong values but do not null it. Volume/coverage removal drops rows but nulling grw_score specifically requires targeting it in completeness -- rare because it shares pool with 15 other required fields. |
| GLD-OP-010 | [0,0,0,0,0] | market_score null count = 0. Same as GLD-OP-006 -- market_score is corrupted to wrong values, not null. Not targeted by completeness because it is not in the required fields list (it is nullable in schema). |
| GLD-OP-011 | [0,0,0,0,0] | market_score_rounded range 1-10. Consistency strategy for market_score_rounded clamps to [1,10], so out-of-range values are never produced. The clamping is intentional in the corruption function to keep values plausible. |
| GLD-OP-023 | [0,0,0,0,0] | confidence_tier 'high' is majority. Even with corruption (changing confidence_tier on ~3% of rows, removing ~30% rows via coverage), 'high' still dominates because the base is 735/832 = 88.3%. Our corruptions cannot flip enough rows to make medium or low the majority. |
| GLD-OP-032 | [0,0,0,0,0] | GRW score mean within 4.5-6.5. Statistical aggregate check. Individual extreme grw_score values on ~3% of rows do not shift the mean outside [4.5, 6.5] because the 832-row population absorbs outliers. Even with row removals, the mean stays centered. |
| GLD-OP-033 | [0,0,0,0,0] | GRW score bucket coverage >= 8 of 10. Our corruptions add/modify GRW values but don't systematically empty entire buckets. All 10 buckets remain populated because most rows are uncorrupted. |
| GLD-OP-034 | [0,0,0,0,0] | Market score std dev > 1.0. Statistical check. Original std dev = 1.607. Corruption does not compress the distribution enough to drop below 1.0. |
| GLD-OP-035 | [0,0,0,0,0] | Market score bucket coverage >= 7 of 10. Same rationale as GLD-OP-033 -- buckets stay populated because most rows are uncorrupted. |

### Rule That ALWAYS Errored (1 rule)

| Rule ID | Error | Analysis |
|---------|-------|----------|
| GLD-OP-039 | SQL execution error | Market score formula consistency rule uses a correlated subquery with PERCENT_RANK() inside a WHERE clause. DuckDB does not support correlated subqueries with window functions in this pattern. **This is a rule definition bug, not a data problem.** The SQL needs to be restructured to use a CTE or JOIN pattern. |

## Gap Analysis

### Confirmed Gaps

1. **GLD-OP-039 (Market score formula consistency) -- BROKEN RULE.** The SQL is syntactically invalid for DuckDB. It uses a correlated subquery with `PERCENT_RANK() OVER (ORDER BY o2.openings_annual_avg) FROM ... WHERE o2.soc_code = op.soc_code`. This never executes successfully. The rule provides zero detection value and must be rewritten using a CTE-based approach.

2. **GLD-OP-006 (GRW null count) and GLD-OP-010 (market_score null count) -- UNCHALLENGED.** These completeness rules check for nulls in grw_score and market_score. Our corruption strategies never null these fields because they are not in the "required fields" list for completeness injection (they are nullable in schema). However, a real-world failure could produce null grw_score if employment_change_pct becomes null. These rules are structurally sound but were not stress-tested.

3. **GLD-OP-023, GLD-OP-032-035 (Statistical aggregate rules) -- RESILIENT TO ROW-LEVEL CORRUPTION.** These rules check population-level statistics (mean within range, std dev > threshold, bucket coverage). Individual row corruption does not shift these aggregates enough to trigger failure because the uncorrupted majority absorbs the impact. This is actually desirable behavior -- these rules detect wholesale data source changes, not individual row errors.

4. **GLD-OP-011 (Market score rounded range) -- SELF-LIMITING CORRUPTION.** The consistency corruption clamps market_score_rounded to [1,10], which means this range check is never violated by our injection. In production, a transformer bug could produce values outside [1,10], but our corruption approach cannot test this.

### Potential Blind Spots

1. **Freshness rules absent.** There are no DQ rules checking source_load_date or promoted_at for temporal anomalies (future dates, stale dates, epoch values). Our freshness corruptions injected future/stale timestamps but no rules caught them. **Recommendation: Add freshness rules for both fields.**

2. **Referential integrity rules absent.** There are no DQ rules checking that record_id matches `compute_grain_id(soc_code)`. Our orphan record_id injections were not caught by any rule. GLD-OP-002 checks uniqueness of record_id, which fires because duplicate rows have duplicate record_ids, but no rule validates the record_id hash. **Recommendation: Add a grain hash validation rule.**

3. **Accuracy rules absent.** No rules check that grw_score matches the piecewise linear function for the given employment_change_pct. Our wrong_grw_score injections were not specifically caught by a formula-verification rule. GLD-OP-038 (grw vs growth_category monotonic) catches some inversions, but a row with grw_score=7.0 for employment_change_pct=1.0 (correct would be ~5.0) would pass GLD-OP-038 if growth_category is "growing" (which maps to grw 5.0-7.5). **Recommendation: Add a piecewise function verification rule.**

## Stability Assessment

| Metric | Value |
|--------|-------|
| Rules consistently firing (all 5 cycles) | 26 |
| Rules intermittently firing | 18 |
| Rules consistently silent | 8 |
| Rules in error state | 1 (GLD-OP-039) |
| Best detection rate | 77.4% (cycle 4, 8%) |
| Worst detection rate | 67.9% (cycle 3, 7%) |

## Recommendations for @dq-rule-writer

### Priority 1 (Fix Broken Rule)

1. **GLD-OP-039: Rewrite SQL.** The correlated subquery with PERCENT_RANK is unsupported by DuckDB. Restructure using a CTE that pre-computes openings_score via `1.0 + 9.0 * PERCENT_RANK() OVER (ORDER BY openings_annual_avg)`, then join and validate `ABS(market_score - (0.6 * grw_score + 0.4 * openings_score)) < 0.01`.

### Priority 2 (New Rules -- Gap Coverage)

2. **Add freshness rules.** At minimum: `source_load_date <= CURRENT_DATE` (no future dates) and `source_load_date >= '2020-01-01'` (no stale data). Similarly for promoted_at: `promoted_at <= CURRENT_TIMESTAMP` and `promoted_at >= '2020-01-01'`.

3. **Add record_id hash validation.** Verify that record_id is deterministic from soc_code: compute `compute_grain_id({'soc_code': soc_code}, ['soc_code'], prefix='op')` and compare. This prevents orphan record_ids from transformer bugs.

4. **Add grw_score piecewise function spot-check.** Verify at least the boundary conditions: e.g., `employment_change_pct <= -20.0 implies grw_score = 1.0`, `employment_change_pct >= 50.0 implies grw_score = 10.0`.

### Priority 3 (Targeted Stress Tests for Silent Rules)

5. **GLD-OP-006 and GLD-OP-010 (null count rules):** These are structurally sound but untested. Add a chaos monkey strategy that specifically nulls grw_score and market_score to exercise them.

6. **GLD-OP-011 (market_score_rounded range):** Remove the clamping from chaos monkey's consistency corruption so out-of-range values can be injected.

## Information Barrier Compliance

This report was produced without reading DQ rule definitions (`governance/dq-rules/gold-occupation-profiles-bls-ooh.json`) during corruption design. The chaos runner code was written based solely on the Gold zone transformer (`src/gold/bls_ooh_occupation_profiles.py`) and the Iceberg schema. DQ rule definitions were read only to construct this reconciliation report after all 5 cycles completed.

The "Inferred Dimension" column in the rules tables above is an inference based on which corruption functions would logically trigger each rule's failure, cross-referenced against the DQ rule definitions during reconciliation.

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Chaos Runner | `governance/chaos-manifests/gold_occupation_profiles_chaos_runner.py` |
| JSON Manifest | `governance/chaos-manifests/gold-occupation-profiles-bls-ooh-manifest.json` |
| This Report | `governance/chaos-manifests/gold-occupation-profiles-bls-ooh-chaos.md` |
| DQ Results (cycle runs) | `governance/dq-results/gold-occupation-profiles-bls-ooh-*.json` |
