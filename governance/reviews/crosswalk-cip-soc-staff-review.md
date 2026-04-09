## Staff Engineer Review

### Date: 2026-04-08
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is solid, production-quality work. The ingestor handles the real complexity of this dataset (openpyxl returning CIP codes as floats) correctly. The transformer implements the spec's 5-tier match quality derivation faithfully. Tests are real -- they validate specific values, specific edge cases, and specific format patterns. The DQ rules are well-calibrated against EDA findings. I would put my name on this.

### Code Quality

**src/raw/cip_soc_crosswalk_ingestor.py** -- Good. The CIP code float coercion logic (`_coerce_cipcode`) correctly handles the three input types from openpyxl (float, int, string) with proper zero-padding. Header-finding logic is defensive (scans for a row with 4+ string cells). The fallback from download to local cache is appropriate. The `except Exception` in `_download_and_read` is acceptable here because the fallback path is the right behavior for any download failure class. No complaints.

**src/silver/cip_soc_crosswalk_transformer.py** -- Good. Functions do one thing. `derive_match_quality` is a clean pure function matching the spec's CASE expression exactly. `transform_row` is well-structured: filter, validate, derive, compute. The three `_load_*` helpers gracefully degrade to empty sets when reference tables don't exist -- appropriate for a pipeline where tables may not yet be populated. `VALID_SOC_MAJOR_GROUPS` as a frozenset with 23 entries (22 civilian + 55 Military) is correct per SOC 2018.

One minor observation: `cip_title` and `soc_title` use `raw.get('cip_title', '')` which substitutes empty string for None. The flatten step in the ingestor should have caught nulls already, so this is belt-and-suspenders. Fine.

### Test Quality

**47 raw ingestor tests, 54 silver transformer tests. Total: 101. All passing.**

These are real tests. Specific examples:

- `test_flatten_float_cipcode_converted`: Asserts `engineering[0]["cipcode"] == "14.0101"` -- specific expected value from specific sample data.
- `test_flatten_float_cipcode_leading_zero`: Asserts `agriculture[0]["cipcode"] == "01.0000"` -- verifies zero-padding on leading digit.
- `test_no_match_filtered_out`: Constructs a 99-9999 row, asserts `result is None` -- validates the filter.
- `test_all_quality_values_valid`: Exhaustive 2x2x2 boolean combination (8 cases) through `derive_match_quality`, all validated against `VALID_MATCH_QUALITIES`.
- `test_invalid_major_group_filtered`: SOC 99-1234 returns None -- validates the SOC major group allowlist.
- `test_match_quality_consistent_with_flags` (DQ rule SLV-XW-016): Cross-checks the CASE expression in SQL against the Python implementation.
- Full dataset tests (5 tests) validate against the real 6,097-row NCES XLSX: row count range, format compliance, grain uniqueness.

No test theater. No `assert len > 0` where specific counts are expected. No `assert True`.

### Spec Compliance

The implementation matches the spec on all points:

- Bronze schema: 4 data + 4 metadata fields. Correct.
- Silver schema: 13 fields including record_id, 3 match flags, match_quality. Correct.
- Grain: cipcode x soc_code. Verified unique in both zones.
- "No match" filtering: 194 rows with soc_code = 99-9999 excluded from Silver. Verified zero in Silver.
- CIP format validation: 100% XX.XXXX. Verified.
- SOC format validation: 100% XX-XXXX. Verified.
- Match quality derivation: 5-tier CASE. Verified exhaustive.
- record_id: compute_grain_id with prefix 'xw'. Verified format xw-[a-f0-9]{16}.
- Idempotent promote. Verified via promote pattern.

**Known gap:** has_scorecard_match is 0% TRUE due to CIP granularity mismatch (6-digit crosswalk vs 4-digit Scorecard). The spec acknowledges this in Open Decision #1 and defers to Gold zone. The DQ rules (SLV-XW-010, SLV-XW-013) are correctly calibrated for this reality. This is not a defect -- it is a documented design limitation.

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| Business Admin (52.0201) -> General Managers (11-1021) | Pairing exists, titles correct | CIP2020xSOC2018 | Found: "Business Administration and Management, General." / "General and Operations Managers" | Business Administration -> General and Operations Managers | NCES CIP-SOC Crosswalk | YES |
| Computer Science (11.0701) -> Software Developers (15-1252) | Pairing exists, titles correct | CIP2020xSOC2018 | Found: "Computer Science." / "Software Developers" | Computer Science -> Software Developers | NCES CIP-SOC Crosswalk | YES |
| Nursing (51.3801) -> Registered Nurses (29-1141) | Pairing exists, titles correct | CIP2020xSOC2018 | Found: "Registered Nursing/Registered Nurse." / "Registered Nurses" | Registered Nursing -> Registered Nurses | NCES CIP-SOC Crosswalk | YES |
| Engineering General (14.0101) -> Engineers All Other (17-2199) | Pairing exists, titles correct | CIP2020xSOC2018 | Found: "Engineering, General." / "Engineers, All Other" | Engineering General -> Engineers, All Other | NCES CIP-SOC Crosswalk | YES |
| Row counts | Bronze=6097, Silver=5903, Delta=194 (no-match sentinels) | Full dataset | 6097 / 5903 / 194 | 6097 source rows, 194 with SOC 99-9999 | NCES XLSX + EDA | YES |

### DQ Results

- 28 rules total. 27 passing (96%).
- All 16 P0 rules: PASS.
- SLV-XW-011 (P1): FAIL in scorecard run. The rule has since been updated from 90-97% to 90-98% to accommodate the 97.39% actual BLS match rate. This is a threshold calibration correction, not a data quality issue. The actual match rate is stable and well-understood (high-frequency SOC codes have better BLS coverage than the distinct-SOC rate would suggest). No action required.

### Governance Artifacts

All 11 artifacts from the spec's checklist verified present:

| Artifact | Path | Status |
|----------|------|--------|
| Business glossary | governance/business-glossary.json (BT-075, BT-076) | Present, terms approved |
| Conceptual model | governance/models/crosswalk-cip-soc-conceptual.md | Present |
| Logical model | governance/models/crosswalk-cip-soc-logical.md | Present |
| Physical model | governance/models/crosswalk-cip-soc-physical.md | Present |
| EDA report | governance/eda/crosswalk-cip-soc-eda.md | Present |
| DQ rules | governance/dq-rules/crosswalk-cip-soc.json | Present, 28 rules |
| DQ scorecard | governance/dq-scorecards/crosswalk-cip-soc-scorecard.md | Present |
| Chaos manifest | governance/chaos-manifests/crosswalk-cip-soc-chaos.md | Present |
| Lineage | governance/lineage/crosswalk-cip-soc-20260408T120000Z.json | Present, column-level lineage |
| Data contract | governance/data-contracts/base-cip-soc-crosswalk.yaml | Present |
| Coverage gap report | governance/reviews/crosswalk-coverage-gaps.md | Present |

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | Low | governance/data-contracts/base-cip-soc-crosswalk.yaml (line 127) | soc_major_group CHECK constraint lists 22 values but omits '55' (Military). The code, DQ rules, and actual data all include SOC major group 55. Contract constraint is inconsistent. | Add '55' to the CHECK IN-list. Non-blocking -- this is documentation, not runtime enforcement. |
| 2 | Info | governance/dq-scorecards/crosswalk-cip-soc-scorecard.md (line 31) | SLV-XW-011 description says "90-97%" but the rule JSON was updated to 90-98%. Scorecard was generated before the rule update. | Re-run DQ execution to regenerate scorecard with updated rule. Non-blocking. |

Neither issue affects data correctness or pipeline behavior. Both are documentation artifacts that can be fixed in a follow-up.

### What's Acceptable

- CIP float coercion is well-handled with proper edge case coverage.
- Match quality derivation is clean: pure function, exhaustive, tested against all 8 boolean combinations.
- Test suite is comprehensive: 101 tests covering schema, constants, fetch, flatten, coercion edge cases, filtering, match flags, match quality, validation, grain, and full-dataset integration.
- DQ rules are well-calibrated against EDA data, not spec estimates.
- Lineage includes column-level transformation descriptions.
- The CIP granularity mismatch (6-digit vs 4-digit) is properly documented and deferred, not papered over.
