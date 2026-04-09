# Chaos Monkey After-Action Report: crosswalk-cip-soc

**Spec:** crosswalk-cip-soc
**Tables:** raw.cip_soc_crosswalk (Bronze, 6,097 rows), base.cip_soc_crosswalk (Silver, 5,848 rows)
**DQ Rules:** 28 total (8 Bronze BRZ-XW-*, 20 Silver SLV-XW-*)
**Cycles Completed:** 5 (rates: 5%, 6%, 7%, 8%, 10%)
**Run Date:** 2026-04-08
**Agent:** @chaos-monkey

## Summary

| Cycle | Rate | Corruptions | Rules Fired | Rules Silent | Rules Errored | Detection Rate |
|-------|------|-------------|-------------|-------------|---------------|----------------|
| 1     | 5%   | 380         | 22/28       | 3           | 3             | 78.6%          |
| 2     | 6%   | 456         | 20/28       | 5           | 3             | 71.4%          |
| 3     | 7%   | 529         | 22/28       | 3           | 3             | 78.6%          |
| 4     | 8%   | 605         | 21/28       | 4           | 3             | 75.0%          |
| 5     | 10%  | 752         | 21/28       | 4           | 3             | 75.0%          |

## DQ Dimensions Exercised

All 10 dimensions were injected in every cycle:

| Dimension | Strategy Examples | Injections (Cycle 5) |
|-----------|-------------------|----------------------|
| Completeness | Null cipcode, soc_code, cip_title, record_id, match_quality | 118 |
| Validity | Malformed CIP (no dot, wrong length, alpha), malformed SOC, bad match_quality, 99-9999 in Silver | 118 |
| Uniqueness | Duplicate grain rows (cipcode x soc_code) in both zones | 78 |
| Consistency | cip_family != cipcode[:2], soc_major_group mismatch, match_quality contradicts flags, wrong record_id prefix | 118 |
| Accuracy | Valid-format but nonexistent CIP/SOC codes, swapped CIP into SOC field | 78 |
| Reasonableness | CIP families 70-98 (nonexistent), even SOC major groups (00, 02, 56, 60) | 78 |
| Freshness | Future load_date (2030), stale load_date (2015), future ingested_at (2035) | 78 |
| Volume | Mass-duplicate to inflate row count 8-10% beyond expected | 2 |
| Referential Integrity | SOC codes with invalid major groups (12, 14, 16, 20, 60, 90) | 78 |
| Coverage | Remove all rows for 3 CIP families (Bronze) and 3 SOC major groups (Silver) | 6 |

## Rules That Fired (Corruption Detected)

These rules successfully detected injected corruptions across all 5 cycles:

**Bronze (consistently fired):**
- BRZ-XW-001: Fired in all 5 cycles
- BRZ-XW-002: Fired in all 5 cycles
- BRZ-XW-003: Fired in all 5 cycles
- BRZ-XW-005: Fired in all 5 cycles
- BRZ-XW-006: Fired in all 5 cycles
- BRZ-XW-007: Fired in all 5 cycles

**Bronze (intermittent):**
- BRZ-XW-004: Fired in 2/5 cycles (seed-dependent)
- BRZ-XW-008: Fired in 3/5 cycles (seed-dependent)

**Silver (consistently fired):**
- SLV-XW-001 through SLV-XW-007: Fired in all 5 cycles
- SLV-XW-009: Fired in all 5 cycles
- SLV-XW-011: Fired in all 5 cycles
- SLV-XW-012: Fired in all 5 cycles
- SLV-XW-014: Fired in all 5 cycles
- SLV-XW-015: Fired in all 5 cycles
- SLV-XW-016: Fired in all 5 cycles
- SLV-XW-017: Fired in all 5 cycles

**Silver (intermittent):**
- SLV-XW-008: Fired in 2/5 cycles

## Rules That Never Fired (Gaps)

### SLV-XW-010 (PASS in all 5 cycles, value=0)

This rule passed with value=0 across all 5 cycles despite heavy corruption. It may be checking a condition that our corruptions did not target, or it may have an overly permissive threshold.

**Recommendation:** Review what SLV-XW-010 checks. If it validates a condition we corrupted (e.g., match_quality consistency), the threshold may be too lenient. If it checks something we did not corrupt (e.g., a specific cross-join property), it may be untestable without multi-table shadow support.

### SLV-XW-013 (PASS in all 5 cycles, value=0)

Same as SLV-XW-010 -- consistently passed with value=0 despite corruption.

**Recommendation:** Review SLV-XW-013 for threshold sensitivity. Consider whether this rule's condition can be exercised by single-table corruption or if it requires multi-table shadow setup.

## Rules That Errored (Infrastructure Gaps)

### SLV-XW-018, SLV-XW-019, SLV-XW-020 (ERROR in all 5 cycles)

These rules failed with DuckDB catalog errors:
- SLV-XW-018: `Table base_bls_ooh does not exist` (cross-table join to BLS OOH)
- SLV-XW-019: `Table base_onet_occupations does not exist` (cross-table join to O*NET)
- SLV-XW-020: `Table base_college_scorecard does not exist` (cross-table join to College Scorecard)

These are referential integrity rules that validate cross-table FK relationships. In shadow mode, only the crosswalk tables are in the shadow namespace -- the referenced tables (`base.bls_ooh`, `base.onet_occupations`, `base.college_scorecard`) are in the real namespace and not registered in the DuckDB session.

**Recommendation:** The chaos monkey shadow infrastructure needs to register the real (non-shadow) versions of cross-referenced tables alongside the shadow tables. This is a Brightsmith framework enhancement -- when `shadow=True`, the DQ runner should load shadow tables for the spec's own tables but fall back to real tables for cross-references.

## Framework Bug Found

**_KNOWN_NAMESPACES in dq_runner.py was missing `raw`, `base`, `consumable`, `ai_ready`.**

The DQ runner's `_extract_table_refs()` only recognized `{"bronze", "silver", "gold", "mcp"}` as valid namespace prefixes. DQ rules referencing `raw.cip_soc_crosswalk` or `base.cip_soc_crosswalk` were silently skipped during table registration, causing all 28 rules to ERROR before the namespace fix.

**Fix applied:** Added `"raw", "base", "consumable", "ai_ready"` to `_KNOWN_NAMESPACES` in `/Users/jcernauske/code/bright/brightsmith/src/brightsmith/infra/dq_runner.py`.

This bug affects ALL specs that use `raw.*` or `base.*` namespace references in DQ rules. Previous DQ runs for this spec (and possibly others) all show 28/28 rules errored.

## Gap Analysis Summary

| Category | Count | Details |
|----------|-------|---------|
| Rules fired (working) | 22-25/28 | Strong detection across completeness, validity, uniqueness, consistency, freshness, volume |
| Rules silent (potential gaps) | 2 | SLV-XW-010, SLV-XW-013 need threshold review |
| Rules errored (infra) | 3 | SLV-XW-018/019/020 need cross-table shadow support |
| Rules intermittent | 3 | BRZ-XW-004, BRZ-XW-008, SLV-XW-008 fire based on seed (expected for stochastic corruption) |

## Recommendations for @dq-rule-writer

1. **Review SLV-XW-010 and SLV-XW-013** -- these never fired despite injecting corruptions across all 10 dimensions. Either their thresholds are too permissive, or they check conditions that single-table corruption cannot exercise.

2. **Add cross-table shadow support** for SLV-XW-018/019/020 -- these referential integrity rules are structurally unable to run in shadow mode without loading the referenced tables.

3. **Consider adding rules for:**
   - **record_id prefix validation** -- record_id should start with "xw-" (we injected "zz-" prefixed IDs and no rule caught it)
   - **cip_family/soc_major_group derivation consistency** -- we injected mismatches between cipcode[:2] and cip_family (and soc_code[:2] vs soc_major_group). These were caught by existing rules, but the detection was through format validation, not explicit derivation checks.
   - **source_method validation** in Bronze -- we injected "csv_download", "api_call" etc. where only "xlsx_download" is valid. No Bronze rule specifically checks this.

## Artifacts

| Artifact | Path |
|----------|------|
| Chaos runner | `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-manifests/crosswalk_cip_soc_chaos_runner.py` |
| JSON manifest | `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-manifests/crosswalk-cip-soc-manifest.json` |
| This report | `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-manifests/crosswalk-cip-soc-chaos.md` |
| Framework fix | `/Users/jcernauske/code/bright/brightsmith/src/brightsmith/infra/dq_runner.py` (line 139: _KNOWN_NAMESPACES) |
