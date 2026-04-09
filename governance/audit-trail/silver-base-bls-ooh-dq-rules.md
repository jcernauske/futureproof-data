# Audit Trail: DQ Rules for silver-base-bls-ooh

**Spec:** silver-base-bls-ooh
**Agent:** @dq-rule-writer
**Date:** 2026-04-07T14:00:00Z
**Zone:** Silver
**Table:** base.bls_ooh
**Evidence Source:** governance/eda/silver-bls-ooh-eda.md
**Model Source:** governance/models/silver-base-bls-ooh-logical.md

---

## Rules Written (36 total)

### Grain & Identity (P0) -- 9 rules
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-001 | Uniqueness | Grain uniqueness: soc_code | 0 duplicates |
| SLV-OOH-002 | Validity | SOC code format XX-XXXX | 0 violations |
| SLV-OOH-003 | Volume | Row count exactly 832 | Exact match |
| SLV-OOH-004 | Validity | SOC major group: 22 valid codes | 0 violations |
| SLV-OOH-005 | Referential Integrity | SOC major group name not null | 0 violations |
| SLV-OOH-006 | Consistency | SOC major group = soc_code[:2] | 0 violations |
| SLV-OOH-007 | Uniqueness | record_id not null and unique | 0 violations |
| SLV-OOH-008 | Completeness | soc_code not null | 0 violations |
| SLV-OOH-009 | Completeness | occupation_title not null or empty | 0 violations |

### Classification Flags (P1/P0) -- 5 rules
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-010 | Validity | broad_occupation_flag: exactly 7 True | Exact count |
| SLV-OOH-011 | Validity | catchall_flag: exactly 70 True | Exact count (EDA correction from 46) |
| SLV-OOH-012 | Consistency | No broad+catchall overlap | 0 overlap |
| SLV-OOH-013 | Completeness | broad_occupation_flag not null | 0 nulls |
| SLV-OOH-014 | Completeness | catchall_flag not null | 0 nulls |

### Employment & Projections (P1/P0) -- 8 rules
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-015 | Validity | employment_current positive | 0 violations |
| SLV-OOH-016 | Validity | employment_projected positive | 0 violations |
| SLV-OOH-017 | Validity | employment_change_pct range -50 to +60 | 0 violations |
| SLV-OOH-018 | Validity | openings_annual_avg >= 0 | 0 violations |
| SLV-OOH-019 | Validity | growth_category valid enum | 0 violations |
| SLV-OOH-020 | Consistency | growth_category null iff pct null | 0 violations |
| SLV-OOH-021 | Consistency | growth_category matches pct bucket | 0 violations |
| SLV-OOH-035 | Completeness | growth_category not null | 0 nulls |

### Compensation (P1/P0) -- 6 rules
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-022 | Validity | median_annual_wage $25K-$250K | 0 violations |
| SLV-OOH-023 | Completeness | median_annual_wage null count = 23 | Exact count |
| SLV-OOH-024 | Consistency | wage_available matches wage nullity | 0 violations |
| SLV-OOH-025 | Validity | median_wage_capped: 0 True | 0 True |
| SLV-OOH-026 | Completeness | wage_available not null | 0 nulls |
| SLV-OOH-027 | Completeness | median_wage_capped not null | 0 nulls |

### Education & Requirements (P1) -- 4 rules
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-028 | Validity | education_code 1-8 | 0 violations |
| SLV-OOH-029 | Validity | work_experience_code 1-3 | 0 violations |
| SLV-OOH-030 | Validity | training_code 1-6 | 0 violations |
| SLV-OOH-031 | Referential Integrity | education_level_name valid lookup | 0 violations |

### Cross-Field Consistency (P1) -- 1 rule
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-032 | Consistency | projected - current = change (+/- 1000) | 0 violations |

### Pipeline Metadata (P0) -- 2 rules
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-033 | Completeness | source_load_date not null | 0 nulls |
| SLV-OOH-034 | Completeness | ingested_at not null | 0 nulls |

### Coverage (P1) -- 1 rule
| Rule ID | Dimension | Description | Threshold |
|---------|-----------|-------------|-----------|
| SLV-OOH-036 | Coverage | All 22 SOC major groups present | Exact count |

---

## Key Threshold Decisions

### Catchall count: 70, not 46
- **Spec states:** 46 true "all other" catch-all categories
- **EDA found:** 70 titles containing "all other" (case-insensitive)
- **Decision:** Set threshold to 70 per EDA evidence. The spec's count of 46 is incorrect and must be corrected.

### Employment change/pct sign consistency: NOT enforced
- **EDA found:** 12 rows have employment_change=0 but employment_change_pct < 0 (BLS rounding artifact from thousands conversion)
- **Decision:** Intentionally omitted a sign-consistency rule. This is documented in the EDA as expected BLS methodology, not a data quality issue.

### Wage range: $25,000-$250,000
- **EDA actual:** $30,160-$238,380
- **Spec suggested:** $15,000 lower bound
- **Decision:** Set lower bound to $25,000 (below observed min but above spec's $15K which is unrealistically low for a BLS median annual wage). Upper bound $250,000 provides headroom above the BLS cap of $239,200.

### Employment change pct range: -50.0 to +60.0
- **EDA actual:** -36.1 to 49.9
- **Spec suggested:** -100 to +200
- **Decision:** Tightened significantly from spec. The -100/+200 range is far too loose to catch real anomalies. Set to -50/+60 which provides ~40% headroom beyond observed extremes.

---

## Rules Considered but NOT Written

1. **Employment change sign consistency** -- Intentionally omitted. 12 known BLS rounding mismatches where employment_change=0 but employment_change_pct < 0 (plus 2 where change is nonzero but pct=0.0). EDA confirms this is inherent to BLS methodology. Writing this rule would produce 14 false-positive violations.

2. **Employment fields completeness (0% null)** -- Current data has 0 nulls for all employment fields, but the logical model marks them NULLABLE as defensive design. Did not write explicit P0 null checks for employment_current/projected/change/change_pct because they are NULLABLE by design. The P1 range/validity rules implicitly catch nulls that should not exist.

3. **Occupation title uniqueness** -- EDA confirms 832 distinct titles (1:1 with soc_code), but this is an artifact of the current dataset, not a structural constraint. BLS could theoretically assign the same title to different SOC codes. Not enforced.

4. **Code-text determinism** (education_code -> education_typical, work_experience_code -> work_experience, training_code -> training_typical) -- EDA confirms 1:1 deterministic mapping, but this is validated by the normalized name lookup (SLV-OOH-031). Adding separate rules for the raw text labels would be redundant.

5. **Employment change range check** -- employment_change can be negative (232 declining occupations) and ranges from -313,600 to 739,800. The consistency rule (SLV-OOH-032: projected - current = change) provides a more meaningful validation than a simple range bound.

---

## DQ Rule Template Evaluation

The `governance/dq-rule-templates/` directory is empty -- no mandatory Silver zone patterns to evaluate. All rules were written from first principles based on the EDA report, logical model, and spec.

---

## Execution Status

Rules are in PROPOSED status. They will be executed by @dq-engineer after the transformer is implemented and the `base.bls_ooh` table exists.
