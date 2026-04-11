## Staff Engineer Review

### Date: 2026-04-09
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is solid Bronze ingest work. The ingestor is clean, handles both source formats defensively, and the warehouse data matches the actual source files exactly. 34 tests pass, 18 DQ rules pass against real Iceberg data, governance artifacts are present and substantive. I verified 5 occupation records in the warehouse against the raw source files -- all match. The code is simple, readable, and does what the spec asks. I would put my name on this for Bronze zone.

Two issues are real but non-blocking for Bronze: the test name/assertion mismatch (cosmetic but sloppy), and the spec's wrong source format description (the code already handles it correctly). Neither requires a code change to approve.

### Code Quality

**src/raw/karpathy_ai_exposure_ingestor.py** -- Good. 300 lines, well-structured. Each method does one thing. The `_normalize_scores()` method handles the dict-vs-array format discrepancy between what the spec describes and what the actual source provides. Type coercion methods handle commas, dollar signs, whitespace, and empty strings correctly. The `except Exception` in `_download_or_fallback` (line 116) is broad but acceptable here -- it's a fallback mechanism, and the warning log captures the failure. The `_coerce_soc` and `_coerce_string` methods are identical in logic -- minor redundancy, not worth blocking over. No god functions, no abstraction astronautics.

### Test Quality

**tests/raw/test_karpathy_ai_exposure_ingestor.py** -- 34 tests, all pass in 0.34s. These are real tests with meaningful assertions:

- Schema tests verify specific field names, counts (== 13), and nullability (soc_code required=False).
- Fetch tests verify exact counts (10 scores, 9 occupations) and specific source_method value.
- Flatten tests verify join logic (9 matched rows from 10 scores + 9 occupations - 1 unmatched), null SOC preservation for specific slugs, boundary values (exposure 0 and 10), specific parsed values (median_pay == 99890.0, num_jobs == 338200).
- Coercion tests verify None/empty/whitespace handling and comma/dollar parsing.
- Full dataset tests verify row count range (325-360), score range, slug uniqueness, and SOC coverage against the real cached data.

Not test theater. The assertions check specific expected values, not just `> 0` or `is not None`.

One issue: `test_full_soc_coverage_above_90_percent` asserts `coverage > 0.80` despite the name saying 90%. The test name lies. The 80% threshold is correct given the actual 84.8% coverage, but the name should say 80%.

### Spec Compliance

The implementation matches the spec for Bronze zone:

- Iceberg table `bronze.karpathy_ai_exposure` exists with 342 rows (spec says 342 expected).
- All 13 fields present with correct types and nullability.
- Grain is slug, 342 unique (spec says one row per slug).
- SOC codes resolved from occupations.csv with null preservation (spec requirement).
- Cross-validation fields carried forward (median_pay_annual, num_jobs_2024, entry_education).
- Fallback to local cache is implemented.
- User-Agent header is set correctly.
- `source_method` is populated as "github_download" or "local_cache".

Spec deviation: The spec says scores.json structure is `{"slug_name": {"exposure": 7, "rationale": "..."}, ...}` (dict keyed by slug). Actual format is a JSON array of objects. The ingestor handles both formats via `_normalize_scores()`. The spec is wrong about the format, but the code is correct. This should be noted in the spec but does not block Bronze approval.

### Data Correctness Spot-Check

Verified against actual Karpathy source files (`data/raw/karpathy_cache/scores.json` and `occupations.csv`):

| Occupation | Field | Pipeline Value | Source Value | Match? |
|-----------|-------|---------------|-------------|--------|
| medical-transcriptionists | exposure_score | 10 | 10 | YES |
| medical-transcriptionists | soc_code | 31-9094 | 31-9094 | YES |
| financial-analysts | exposure_score | 9 | 9 | YES |
| financial-analysts | median_pay_annual | 101910.0 | 101910 | YES |
| registered-nurses | soc_code | 29-1141 | 29-1141 | YES |
| registered-nurses | exposure_score | 4 | 4 | YES |
| carpenters | exposure_score | 2 | 2 | YES |
| carpenters | median_pay_annual | 59310.0 | 59310 | YES |
| athletes-and-sports-competitors | exposure_score | 1 | 1 | YES |

Additional warehouse-level verification:
- Row count: 342 (matches source)
- Unique slugs: 342 (grain integrity confirmed)
- SOC coverage: 290/342 = 84.8% (matches EDA report)
- Score range: 1-10 (no zeros in real data, consistent with EDA)
- Null exposure_score: 0
- Null rationale: 0

All values match. No data corruption detected.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | LOW | tests/raw/test_karpathy_ai_exposure_ingestor.py:373 | Test name `test_full_soc_coverage_above_90_percent` asserts `> 0.80`, not 90%. Name misleads. | Rename to `test_full_soc_coverage_above_80_percent`. Non-blocking. |
| 2 | INFO | docs/specs/raw-ingest-karpathy-ai-exposure.md:65 | Spec says scores.json is `{"slug_name": {...}}` dict. Actual format is JSON array of objects. Code handles both correctly. | Update spec to document actual format. Non-blocking. |
| 3 | INFO | governance/data-contracts/raw-karpathy-ai-exposure.yaml:6 | YAML comment says `# Status: DRAFT` but field value says `status: ACTIVE`. Pick one. | Align comment with field. Non-blocking. |
| 4 | INFO | governance/audit-trail/ | Adversarial auditor report not persisted to filesystem (referenced as `raw-ingest-karpathy-ai-exposure-adversarial-audit.md` but missing). Chaos monkey report exists. | Persist the adversarial auditor findings. Non-blocking for Bronze. |

### What's Acceptable

- The ingestor is clean and simple. No over-engineering.
- Test sample data is well-designed: includes boundary values (score 0, score 10), null SOC cases, unmatched slugs, comma-formatted numbers, and the real occupations.csv header format.
- DQ rules cover all spec requirements with correct thresholds (SOC coverage adjusted from spec's 95% to 80% based on EDA findings -- good judgment call).
- The EDA report is thorough and actionable. It identified the SOC coverage gap before the DQ rules were written.
- Governance artifacts reference real tables, real field counts, and real execution runs.
- 342 rows in the warehouse, verified against source. No data loss, no corruption.

### Decision

APPROVED. The four issues above are all LOW/INFO severity. None require code changes before marking Bronze zone complete. Issues 1 and 3 should be cleaned up in a follow-up commit. Issues 2 and 4 should be addressed when the Silver/Gold zones are implemented.

REQUIRE_HUMAN_APPROVAL is TRUE. This review is the staff engineer's recommendation. Human owner should review before marking the spec's Bronze zone COMPLETE.
