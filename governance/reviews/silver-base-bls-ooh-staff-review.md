## Staff Engineer Review

### Date: 2026-04-07
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is production-quality work. The transformer is clean, correct, and matches the physical model exactly. 73 tests pass with meaningful assertions -- no test theater. The warehouse table exists with 832 rows, 25 columns, zero duplicates, and all derived fields verify against independently checkable BLS reference values. The adversarial audit found 12 risks, the 4 must-fix items were addressed (golden dataset created, catchall count corrected to 70 everywhere, data contract rule total corrected to 36, lineage catchall count corrected). Idempotent promote verified -- re-run produces 0 new rows, 832 skipped. I would put my name on this.

### Code Quality

**`src/silver/bls_ooh_transformer.py`** -- Clean. Functions do one thing. `derive_growth_category()` is a pure function with no side effects. `transform_row()` validates, derives, and assembles a record. `transform()` orchestrates read-transform-promote. No god functions, no unnecessary abstractions.

The lookup tables (SOC_MAJOR_GROUP_LOOKUP, EDUCATION_LEVEL_LOOKUP, BROAD_OCCUPATION_CODES) are defined at module scope as constants. The broad occupation codes use a frozenset, which is the right choice for a fixed membership test. The spec explicitly calls for hardcoding rather than pattern matching, and the code follows that directive with a comment pointing to the rationale.

SOC code validation is strict -- regex match on XX-XXXX, ValueError on failure. Major group lookup raises ValueError on unknown groups. This is correct fail-fast behavior.

One minor concern: null occupation_title is silently coerced to empty string (lines 163-165) rather than raising ValueError. The adversarial audit flagged this (RISK-008). Since DQ rule SLV-OOH-009 catches empty titles post-hoc and current Bronze data has zero null titles, this is not a blocking issue. But it is inconsistent with the SOC code validation approach. Noted, not blocking.

### Test Quality

73 tests, all passing. This exceeds the 15-test minimum for Silver zone by a wide margin.

The tests are real. Specific observations:

- **Growth category boundary tests**: 14 tests covering every threshold boundary (-10.0, -1.0, 0.0, 1.0, 10.0, 20.0) plus interior values. Assertions are exact string matches against specific category names. This is thorough.
- **Broad occupation flag**: Parametrized test for all 7 known broad codes, plus exact count assertion (`len(BROAD_OCCUPATION_CODES) == 7`), plus negative tests for codes ending in 0 that are NOT broad. Good.
- **Catchall flag**: Tests case-insensitivity, partial matches ("other" without "all other"), and the happy path. Correct.
- **SOC major group**: 22-count assertion, 3 specific (code, name) pair checks, and a ValueError test for invalid groups.
- **Schema tests**: Exact field count (25), required/nullable field set assertions using set equality, not subset. The nullable field test uses `==` not `issubset`, which means any extra nullable field would fail the test.
- **Validation tests**: 5 tests for missing, null, empty, invalid format, and alpha SOC codes. All assert specific ValueError messages.

The test fixtures use synthetic data that does not match real warehouse values (e.g., SW Dev fixture uses $130,160 wage vs $133,080 actual). The adversarial audit flagged this. The tests validate transformation logic, not end-to-end data correctness. That is acceptable because the golden dataset handles end-to-end validation separately.

### Spec Compliance

The implementation matches the spec. Verified:

- 832 rows, 25 columns -- matches spec schema exactly
- SOC codes validated XX-XXXX format -- spec requirement met
- 7 broad occupation codes flagged from hardcoded list -- matches spec list exactly
- 70 catchall categories flagged via case-insensitive "all other" match -- matches corrected spec count
- 22 SOC major groups with names derived from lookup -- matches spec lookup table
- 23 null-wage occupations preserved with wage_available=False -- not dropped
- growth_category derived with correct half-open interval thresholds
- education_level_name derived from 8-value lookup
- load_date renamed to source_load_date
- source_url and source_method dropped
- record_id computed via compute_grain_id with 'ooh' prefix
- Idempotent promote pattern used

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| Software Developers (15-1252) | median_annual_wage | 2024-2034 | $133,080 | $133,080 | BLS OOH interactive export / golden dataset | Yes |
| Software Developers (15-1252) | growth_category | 2024-2034 | growing_fast | growing_fast (15.8% growth) | BLS OOH / golden dataset | Yes |
| Software Developers (15-1252) | education_code | 2024-2034 | 3 (Bachelor's) | 3 (Bachelor's) | BLS OOH / golden dataset | Yes |
| Registered Nurses (29-1141) | median_annual_wage | 2024-2034 | $93,600 | $93,600 | BLS OOH interactive export / golden dataset | Yes |
| Registered Nurses (29-1141) | growth_category | 2024-2034 | growing | growing (4.9% growth) | BLS OOH / golden dataset | Yes |
| Word Processors (43-9022) | growth_category | 2024-2034 | declining_fast | declining_fast (-36.1%) | BLS OOH / golden dataset | Yes |

All 6 golden dataset values match. No discrepancies.

### Warehouse Verification

- `base.bls_ooh` exists in Silver Iceberg warehouse: YES
- Row count: 832 (exact match with Bronze)
- Column count: 25 (matches physical model)
- Unique SOC codes: 832 (zero duplicates)
- Broad occupation flag count: 7
- Catchall flag count: 70
- Null wage count: 23
- SOC major groups present: 22
- Idempotent re-run: 0 promoted, 832 skipped (dedup)

### DQ Coverage

36 rules, 36 passing (100%). Coverage spans: uniqueness, validity, volume, consistency, referential integrity, completeness. 16 P0 rules, 20 P1 rules. All executed against the persistent warehouse, not ephemeral data.

### Governance Completeness

All artifacts exist and are substantive:

- Business glossary: 20 terms including project-specific BT-040 through BT-045
- Models: Conceptual, logical, physical -- all APPROVED status
- EDA report: Silver-specific profiling with corrected catchall count
- DQ rules: 36 rules with real SQL, real thresholds, real rationale
- DQ scorecard: 36/36 from real execution (run ID 8fb39ca1)
- Chaos manifest: 5 cycles, 22/36 rules fired
- Lineage: Full OpenLineage with column-level derivation descriptions
- Data contract: 25 columns with constraints, quality thresholds, and consumers
- Golden dataset: 6 values across 3 occupations, all verifiable
- Pipeline state: All steps COMPLETED except staff-engineer (this review)

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | LOW | governance/data-contracts/base-bls-ooh.yaml | DQ priority sub-counts wrong: says p0=15, p1=10, p2=6 (sums to 31). Actual is P0=16, P1=20, P2=0 (sums to 36). Total was corrected to 36 but breakdown was not. | Not blocking. Fix when convenient. |
| 2 | LOW | src/silver/bls_ooh_transformer.py:163-165 | Null occupation_title silently coerced to empty string instead of raising ValueError. Inconsistent with soc_code validation. | Not blocking. Current Bronze data has zero null titles. DQ rule SLV-OOH-009 provides post-hoc safety net. |
| 3 | INFO | docs/specs/silver-base-bls-ooh.md:81 | Spec schema marks growth_category as required=yes but code and physical model correctly have it as nullable. | Spec documentation error. Does not affect runtime. |

### What's Acceptable

The transformer code is straightforward and correct. The growth_category boundary tests are thorough -- every threshold tested with exact values. The broad occupation flag uses a hardcoded frozenset with a comment explaining why, which is exactly what the spec asked for. The lineage artifact has full column-level derivation descriptions that are accurate. The golden dataset has 6 independently verifiable values and all match. 73 tests with meaningful assertions for a 277-line transformer is good coverage density.
