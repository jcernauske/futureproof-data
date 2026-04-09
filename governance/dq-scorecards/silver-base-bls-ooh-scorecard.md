## DQ Scorecard: silver-base-bls-ooh
**Spec:** silver-base-bls-ooh
**Date:** 2026-04-07
**Agent:** @dq-engineer
**Overall Score:** 36/36 rules passing (100%)
**Data Source:** Production Data Validation (executed 2026-04-07T17:56:02.447709+00:00)
**Run ID:** 8fb39ca1

### Execution Results

| Rule ID | Category | Priority | Description | Result | Details |
|---------|----------|----------|-------------|--------|---------|
| SLV-OOH-001 |  | P0 | The declared grain is one row per soc_code. Any duplicate SOC code indicates a transformer or promote failure. This is the structural foundation of the table. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-002 |  | P0 | Every soc_code must match the SOC standard format XX-XXXX (2-digit major group, hyphen, 4-digit detail). This is the primary join key for O*NET and the CIP-SOC crosswalk. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-003 |  | P0 | Silver transformation is 1:1 with Bronze. No rows should be added or dropped. Exact count of 832 must be preserved. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-OOH-004 |  | P0 | The soc_major_group field (first 2 characters of soc_code) must be one of the 22 valid SOC major group codes defined in the spec. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-005 |  | P0 | Every row must have a non-null, non-empty soc_major_group_name. This is derived via lookup from soc_major_group, so all 22 valid group codes must resolve to a name. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-006 |  | P0 | The soc_major_group field must equal the first 2 characters of soc_code. Validates the derivation logic. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-007 |  | P0 | record_id is the deterministic surrogate primary key computed via compute_grain_id(). It must be non-null and unique across all rows. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-008 |  | P0 | soc_code is the natural key and must be present in every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-009 |  | P0 | occupation_title is a required field used for catchall_flag derivation and human display. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-010 |  | P1 | Exactly 7 SOC codes should be flagged as broad/rolled-up occupations. These are hardcoded from the Bronze SOC audit: 13-1020, 13-2020, 29-2010, 31-1120, 39-7010, 47-4090, 51-2090. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-OOH-011 |  | P1 | Exactly 70 occupations should have catchall_flag=True. These are occupations with 'all other' in the title (case-insensitive substring match). | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-OOH-012 |  | P1 | None of the 7 broad occupation codes should also be catchall categories. The flags are independent classifications with no expected overlap. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-013 |  | P0 | broad_occupation_flag is a derived NOT NULL boolean. Must be True or False for every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-014 |  | P0 | catchall_flag is a derived NOT NULL boolean. Must be True or False for every row. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-015 |  | P1 | Employment current must be a positive count when present. Zero or negative employment is impossible for an active BLS occupation. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-016 |  | P1 | Employment projected must be a positive count when present. Zero or negative projected employment is impossible. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-017 |  | P1 | Employment change percentage must fall within -50.0 to +60.0. This is a tight sanity bound based on actual data range, with headroom for future variation. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-018 |  | P1 | Annual average openings must be >= 0. Four occupations have zero due to BLS rounding, which is valid. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-019 |  | P1 | growth_category must be one of the 6 valid enum values when not null. Null is only valid when employment_change_pct is null. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-020 |  | P1 | growth_category must be null exactly when employment_change_pct is null, and non-null exactly when employment_change_pct is non-null. They are logically coupled. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-021 |  | P1 | Validates that growth_category is derived correctly from employment_change_pct using the spec-defined half-open interval thresholds. Critical because boundary rows exist at every threshold. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-022 |  | P1 | When present, median_annual_wage must fall between $25,000 and $250,000. Lower bound set below observed min for robustness; upper bound above BLS cap threshold. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-023 |  | P1 | Exactly 23 occupations should have null median_annual_wage. These are physicians/surgeons, performers, dental specialists, and 1 fishing/hunting worker where BLS does not report wage data. | PASS | actual=0.0, threshold=result = 0.0 |
| SLV-OOH-024 |  | P1 | wage_available must exactly equal (median_annual_wage IS NOT NULL). True for 809 rows, False for 23 rows. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-025 |  | P1 | No wages should be capped in the interactive export. The median_wage_capped flag exists for future-proofing but should be all False in current data. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-026 |  | P0 | wage_available is a derived NOT NULL boolean convenience flag. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-027 |  | P0 | median_wage_capped is a NOT NULL boolean preserved from Bronze. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-028 |  | P1 | BLS education level codes must be in the range 1-8 when present (1=Doctoral through 8=No formal credential). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-029 |  | P1 | BLS work experience codes must be in the range 1-3 when present (1=5+ years, 2=Less than 5 years, 3=None). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-030 |  | P1 | BLS training codes must be in the range 1-6 when present (1=Internship/residency through 6=None). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-031 |  | P1 | When education_code is not null, education_level_name must be one of the 8 valid labels from the spec lookup table. Validates the derivation lookup. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-032 |  | P1 | employment_projected minus employment_current should equal employment_change within a tolerance of +/- 1,000 (BLS rounding from thousands). | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-033 |  | P0 | source_load_date is a NOT NULL pipeline metadata field renamed from Bronze load_date. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-034 |  | P0 | ingested_at is a NOT NULL pipeline metadata timestamp generated at Silver transformation time. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-035 |  | P0 | In current data, all 832 rows have non-null employment_change_pct, so growth_category should never be null. If future data has null pct values, this rule will need adjustment. | PASS | actual=0, threshold=result_count = 0.0 |
| SLV-OOH-036 |  | P1 | All 22 SOC major groups must be present in the data. Missing groups indicate data loss during transformation. | PASS | actual=0.0, threshold=result = 0.0 |

### Summary by Category
| Category | Rules | Passing | Rate |
|----------|-------|---------|------|
|  | 36 | 36 | 100% |

### Gate Status
- **P0 Gate: PASS** — All critical rules passed.

