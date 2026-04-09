# Audit Trail: DQ Rules for silver-base-college-scorecard

**Date:** 2026-04-06
**Agent:** @dq-rule-writer
**Spec:** docs/specs/silver-base-college-scorecard.md
**Zone:** Silver (Base)
**Evidence Source:** governance/eda/silver-college-scorecard-eda.md
**Model Source:** governance/models/silver-base-college-scorecard-physical.md
**Domain Context:** governance/domain-context.md
**Output:** governance/dq-rules/silver-base-college-scorecard.json

---

## Summary

35 DQ rules written for `base.college_scorecard` covering 7 dimensions:
- **Uniqueness:** 2 rules (SLV-CS-001, SLV-CS-031)
- **Validity:** 7 rules (SLV-CS-002, SLV-CS-003, SLV-CS-022-025, SLV-CS-027, SLV-CS-030, SLV-CS-034)
- **Completeness:** 13 rules (SLV-CS-005 through SLV-CS-020)
- **Consistency:** 4 rules (SLV-CS-004, SLV-CS-026, SLV-CS-028, SLV-CS-035)
- **Volume:** 1 rule (SLV-CS-021)
- **Coverage:** 3 rules (SLV-CS-029, SLV-CS-032, SLV-CS-033)

Priority breakdown:
- **P0:** 15 rules (structural constraints, zero-tolerance)
- **P1:** 11 rules (business rules with known edge cases)
- **P2:** 9 rules (soft expectations, monitoring)

---

## Rules Written

| Rule ID | Name | Dimension | Priority | Threshold | Evidence Citation |
|---------|------|-----------|----------|-----------|-------------------|
| SLV-CS-001 | Grain uniqueness | Uniqueness | P0 | 0 duplicates | EDA: 0 duplicates in 69,947 rows |
| SLV-CS-002 | CIP code format | Validity | P0 | 0 violations | EDA: All codes normalize to XX.XX; corrected from physical model |
| SLV-CS-003 | CIP family 2-digit format | Validity | P1 | 0 violations | EDA: 45 valid families, all 2-digit |
| SLV-CS-004 | CIP family matches cipcode prefix | Consistency | P0 | 0 violations | EDA derivation rule: cip_family = cipcode[:2] |
| SLV-CS-005 | unitid not null | Completeness | P0 | 0 violations | EDA: 0% null |
| SLV-CS-006 | institution_name not null/empty | Completeness | P0 | 0 violations | EDA: 0% null, 0 empty |
| SLV-CS-007 | cipcode not null | Completeness | P0 | 0 violations | EDA: 0% null |
| SLV-CS-008 | program_name not null/empty | Completeness | P0 | 0 violations | EDA: 0% null, 0 empty |
| SLV-CS-009 | credential_level not null | Completeness | P0 | 0 violations | EDA: 0% null |
| SLV-CS-010 | credential_description not null/empty | Completeness | P0 | 0 violations | EDA: 0% null, 0 empty |
| SLV-CS-011 | cip_family not null | Completeness | P0 | 0 violations | EDA: derived from cipcode (0% null) |
| SLV-CS-012 | cip_family_name not null/empty | Completeness | P0 | 0 violations | EDA: all 45 families must resolve |
| SLV-CS-013 | small_cohort_flag not null | Completeness | P0 | 0 violations | EDA: always generated |
| SLV-CS-014 | source_load_date not null | Completeness | P0 | 0 violations | EDA: 0% null |
| SLV-CS-015 | ingested_at not null | Completeness | P0 | 0 violations | EDA: always generated |
| SLV-CS-016 | earnings_1yr_median null rate | Completeness | P2 | <= 70% | EDA: 64.0% null |
| SLV-CS-017 | earnings_2yr_median null rate | Completeness | P2 | <= 65% | EDA: 60.4% null |
| SLV-CS-018 | debt_median null rate | Completeness | P2 | <= 68% | EDA: 63.1% null |
| SLV-CS-019 | completions_count_1 null rate | Completeness | P2 | <= 12% | EDA: 8.72% null |
| SLV-CS-020 | completions_count_2 null rate | Completeness | P2 | <= 12% | EDA: 8.3% null |
| SLV-CS-021 | Row count range | Volume | P1 | 60,000-80,000 | EDA: 69,947 rows |
| SLV-CS-022 | Earnings 1yr range | Validity | P1 | $1k-$250k | EDA: $4,880-$161,723, 0 violations |
| SLV-CS-023 | Earnings 2yr range | Validity | P1 | $1k-$250k | EDA: $5,938-$160,116, 0 violations |
| SLV-CS-024 | Debt range | Validity | P1 | $1k-$100k | EDA: $2,750-$57,500, 0 violations |
| SLV-CS-025 | credential_level = 3 | Validity | P0 | 0 violations | EDA: all = 3, domain hard constraint |
| SLV-CS-026 | small_cohort_flag consistency | Consistency | P1 | 0 violations | EDA: True=75.52%, derivation must match |
| SLV-CS-027 | institution_control values | Validity | P1 | 0 violations | DEFERRED: CONTROL not in parquet |
| SLV-CS-028 | Silver/raw count consistency | Consistency | P1 | <= 5% diff | EDA: 1:1 transformation |
| SLV-CS-029 | Distinct institution count | Coverage | P1 | 2,200-3,000 | EDA: 2,559 institutions |
| SLV-CS-030 | Completions non-negative | Validity | P0 | 0 violations | EDA: 0 negatives |
| SLV-CS-031 | record_id unique and not null | Uniqueness | P0 | 0 violations | Physical model: PRIMARY KEY |
| SLV-CS-032 | Distinct CIP families | Coverage | P2 | 40-50 | EDA: 45 families |
| SLV-CS-033 | Distinct CIP codes | Coverage | P2 | 350-450 | EDA: 390 codes |
| SLV-CS-034 | unitid range | Validity | P1 | 100k-999k | EDA: 100,654-497,268 |
| SLV-CS-035 | small_cohort_flag True rate | Consistency | P2 | 70-80% | EDA: 75.52% |

---

## Rules Considered But Not Written

| Rule Concept | Reason Not Written |
|-------------|-------------------|
| institution_control completeness (not null) | DEFERRED. CONTROL field is not yet in Bronze parquet (EDA Critical Finding #2). Cannot validate until re-ingestion. SLV-CS-027 covers validity when present. |
| institution_control distribution check | DEFERRED. No distribution data available. EDA notes: "CONTROL distribution cannot be profiled from the 50-row sample." |
| Earnings 2yr > 1yr (anomaly flag) | NOT WRITTEN. Domain context explicitly states: "2yr < 1yr earnings is NOT an anomaly (different cohorts)." 44.2% of rows show 2yr < 1yr. |
| Joint nullity check (earnings 1yr + 2yr) | NOT WRITTEN. EDA confirms independent suppression: "12.27% of rows (8,585) have different suppression status between the two earnings fields." Rules validate each field independently. |
| md_earn_wne completeness | NOT WRITTEN. Field dropped in Silver. Domain context: "100% null -- institution-level metric that does not populate in field-of-study file." |
| CIP code referential integrity against CIP 2020 taxonomy | NOT WRITTEN as formal SQL rule. No CIP 2020 reference table exists in the warehouse. The cip_family_name derivation via lookup serves as a partial check (SLV-CS-012). |
| record_id format check (cs-hex16) | CONSIDERED. Deferred to transformer unit tests. The compute_grain_id() function is tested independently. |
| credential_description = "Bachelor's Degree" | CONSIDERED. This is a constant value in MVP (redundant with credential_level=3). Could be added as P3 but omitted to avoid rule bloat. |

---

## Blocking Issues Noted for Upstream Agents

1. **CIP code CHECK constraint mismatch (for @semantic-modeler):** Physical model defines `^\d{2}\.\d{4}$` but EDA shows all codes normalize to XX.XX format. DQ rule SLV-CS-002 uses corrected pattern `^\d{2}\.\d{2,4}$`.

2. **CONTROL field missing from parquet (for @primary-agent):** institution_control cannot be populated until raw ingestor is updated to include CONTROL. SLV-CS-027 is written proactively but will only validate after re-ingestion.

3. **CONTROL derivation assumes integers (for @primary-agent):** Source CSV has text values ("Public"), not integers. Physical model derivation rule must be corrected.

---

## Execution

Rules have not yet been executed against real data. The Silver table `base.college_scorecard` does not yet exist (transformer not implemented). Rules are in "proposed" status pending:
1. Transformer implementation
2. DQ runner execution
3. Scorecard generation

---

## Timestamp
2026-04-06T12:00:00Z
