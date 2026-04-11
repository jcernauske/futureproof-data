## Staff Engineer Review

### Date: 2026-04-09
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is production-quality Silver zone work. The transformer is clean, testable, and does what the spec says. The 419-row output is explainable and correct. I spot-checked 5 exposure scores against the source scores.json and all match. SOC code resolution is working correctly across all four paths (direct, broad expansion, title match, unresolved). The 49 tests are real tests with real assertions. DQ rules are comprehensive (23 rules, all passing). I would put my name on this.

Two caveats that are acceptable for hackathon MVP but must be addressed before production: (1) the title match substring logic is bidirectional and over-inclusive -- "gambling services workers" matches "first-line supervisors of gambling services workers" which is semantically wrong (workers != supervisors), and (2) financial-analysts (SOC 13-2051, arguably the most recognizable occupation in the dataset) sits in the unresolved bucket because Karpathy's source has null SOC for it and BLS renamed the occupation to "Financial and investment analysts" which breaks the substring match.

### Code Quality

**src/silver/karpathy_ai_exposure_transformer.py** -- Good. Clean separation of concerns: lookup builders, title matcher, row transformer, dedup, and orchestrator are all separate functions. No god function. The `_num_jobs_2024` temp field pattern for carrying dedup metadata through the pipeline is slightly ugly but pragmatic. Module docstring is informative without being bloated. Constants at module level. Logging is appropriate -- method distributions and match rates logged at INFO. No `except: pass` anywhere. The `int()` cast on exposure_score (line 195) is defensive and correct.

One nit: `build_bls_soc_lookup` returns a title->soc dict but the function name says "lookup" which is vague. `build_bls_title_to_soc_map` would be clearer. Not blocking.

### Test Quality

49 tests across 7 test classes. These are real tests:

- **TestNormalizeSocCode** (5): Correct edge cases -- None, empty, whitespace-only, clean passthrough, strip.
- **TestSocPatterns** (3+5=8): Valid/invalid format detection plus broad code detection. The `test_major_group_code_is_broad` test (XX-X000) is a good edge case.
- **TestBuildBlsLookups** (4): Verifies lookup structures with specific expected values (count=16, specific codes in/out of prefix map).
- **TestTitleMatch** (4): Exact match, substring match (nurse anesthetists -> 3 SOC codes), no match, case insensitivity. Assertions check specific SOC codes, not just `len > 0`.
- **TestTransformRows** (17): The core logic tests. Good coverage: direct match, broad expansion (verifies all 4 detailed codes), broad-to-broad exact, unmatched broad, null SOC title match, null SOC unresolved, record_id prefix/determinism, passthrough fields, dropped fields, temp field cleanup. Assertions are specific: `rows[0]["soc_code"] == "13-2051"`, not `is not None`.
- **TestDedup** (5): Covers: no-op, highest num_jobs wins, alpha tiebreak, null SOC excluded, null num_jobs treated as zero.
- **TestSilverSchema** (4): Field count, required set, nullable set. Fine.
- **TestSocWhitespace** (2): End-to-end whitespace stripping through transform_rows.

Missing test: no negative test for title match false positives (adversarial audit RISK-02 flagged this). With 16 BLS rows in the fixture vs 832 in production, the false positive surface area is underrepresented. Acceptable for now but should be added before Gold.

The test fixture for `bronze_row` uses `soc_code="13-2051"` and `exposure_score=8`, but the actual Bronze data has `soc_code=None` and `exposure_score=9` for the financial-analysts slug. The fixture is synthetic and internally consistent, so the tests are valid, but the fixture doesn't represent real data for this specific occupation. Not a test quality issue per se -- the fixture tests the code path correctly -- but worth noting.

### Spec Compliance

The implementation matches the spec for Zone 2 (Silver) requirements:

1. SOC code normalization -- done (whitespace strip, XX-XXXX validation)
2. Null SOC resolution via title matching -- done (exact then substring, case-insensitive)
3. SOC cross-validation against base.bls_ooh -- done (bls_match flag)
4. Broad SOC expansion -- done (XX-XXX0 to detailed codes, with broad-to-broad exact match handling)
5. Duplicate SOC handling -- done (highest num_jobs_2024, alpha tiebreak)
6. Exposure score passthrough -- done (no rescaling)
7. Rationale passthrough -- done
8. Schema matches spec -- all 11 fields present with correct types and nullability
9. Grain: soc_code (unique where non-null) -- verified via DQ and spot-check
10. Promote pattern with kai prefix -- done

One deviation from spec: the spec says "case-insensitive exact match first, then fuzzy match" for title resolution. The implementation does exact match then bidirectional substring match. Substring matching is not fuzzy matching -- it's stricter in some ways (requires literal substring) and looser in others (no edit distance threshold). For hackathon MVP this is acceptable. The spec's "fuzzy match" was underspecified anyway.

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| Accountants and auditors | exposure_score | 2025 | 8 | 8 | scores.json | Yes |
| Actuaries | exposure_score | 2025 | 8 | 8 | scores.json | Yes |
| Actors | exposure_score | 2025 | 7 | 7 | scores.json | Yes |
| Carpenters | exposure_score | 2025 | 2 | 2 | scores.json | Yes |
| Lawyers | exposure_score | 2025 | 8 | 8 | scores.json | Yes |

SOC cross-validation (3 checks):
| Slug | Silver SOC | BLS OOH Title | Correct? |
|------|-----------|---------------|----------|
| registered-nurses | 29-1141 | Registered nurses | Yes |
| lawyers | 23-1011 | Lawyers | Yes |
| carpenters | 47-2031 | Carpenters | Yes |

Row count reconciliation: 342 Bronze -> 419 Silver. Breakdown: 243 direct + 110 broad_expansion + 36 title_match + 30 unresolved = 419. The 7-row delta vs EDA prediction of 412 is explained by title match 1:N expansion (28 source slugs produced 36 rows because 8 slugs matched multiple BLS titles). Acceptable.

One slug lost: "receptionists" (SOC 43-4171) deduped in favor of "information-clerks" which also resolved to 43-4171 via title match. Both had exposure_score=7. Dedup kept information-clerks per the alphabetical tiebreak rule. The SOC code is preserved in the output. Correct behavior.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | LOW | src/silver/karpathy_ai_exposure_transformer.py | Title match substring logic matches "gambling services workers" to "First-line supervisors of gambling services workers" (SOC 39-1013). Workers != supervisors. This is a semantic false positive. ~1-2 rows affected. | Not blocking. Document in known issues for Gold zone to filter or manually correct. |
| 2 | LOW | src/silver/karpathy_ai_exposure_transformer.py | Financial analysts (the poster-child occupation for AI exposure) has null SOC in source, and title match fails because BLS renamed it to "Financial and investment analysts". Lands as unresolved. | Not blocking for Silver. Gold zone should handle this via manual SOC override or the unresolved row will simply not appear in consumable. |
| 3 | INFO | governance/models/silver-base-karpathy-ai-exposure-physical.md | Physical model says "Expected row count: ~500+" but actual is 419. | Governance issue flagged by post-review. Not a code issue. |

### What's Acceptable

The transformer code is well-structured. Functions are small and testable. The four-path SOC resolution logic (direct, broad expansion, title match, unresolved) handles the combinatorial complexity cleanly without over-abstracting. The dedup logic is correct. The test suite is thorough -- 49 tests with specific assertions, not theater. DQ rules are comprehensive at 23 rules covering all dimensions. Lineage documentation is detailed at column level. The adversarial audit's P1 items (SLV-KAI-022 shadow mode, title match false positives, row count delta) are all explainable and non-blocking for hackathon MVP.

### Adversarial Audit P1 Disposition

1. **SLV-KAI-022 shadow mode** -- The cross-table referential integrity rule can't run in chaos monkey shadow namespace because base.bls_ooh isn't present. This is a test infrastructure limitation, not a data quality issue. The rule passes against production data (verified in scorecard). Acceptable.
2. **Title match false positive risk (~36 rows)** -- I audited all 36 title-match rows. Most are correct (exact or near-exact title matches). One confirmed false positive: gambling services workers -> supervisors of gambling services workers. Acceptable for hackathon.
3. **419 vs 412 row count delta** -- Fully explained by title match 1:N expansion (28 slugs -> 36 rows = 8 extra). Acceptable.
