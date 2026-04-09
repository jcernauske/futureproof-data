# Audit Trail: DQ Rules for crosswalk-cip-soc

**Date:** 2026-04-08
**Agent:** @dq-rule-writer
**Spec:** docs/specs/crosswalk-cip-soc.md
**Evidence:** governance/eda/crosswalk-cip-soc-eda.md
**Model:** governance/models/crosswalk-cip-soc-logical.md
**Output:** governance/dq-rules/crosswalk-cip-soc.json

---

## Summary

Wrote 20 DQ rules (8 Bronze, 12 Silver) for the CIP-SOC crosswalk spec. All rules are in PROPOSED status pending human approval and execution.

## Key Threshold Decisions

### 1. Row count updated from spec estimate
- **Spec estimated:** 3,000-5,000
- **EDA actual:** 6,097 (Bronze), 5,903 (Silver after filtering)
- **Decision:** Bronze range 5,500-6,500; Silver range 5,500-6,200. Centered on actuals with margin for minor NCES updates.

### 2. has_scorecard_match expectation corrected
- **Spec expected:** 60-90% TRUE
- **EDA actual:** 0% TRUE (strict 6-digit CIP matching)
- **Decision:** Threshold set to <= 5% TRUE. The CIP granularity mismatch (6-digit crosswalk vs 4-digit Scorecard) means zero direct matches. Spec Open Decision #1 acknowledges this and defers to Gold zone. This is NOT a data quality bug.

### 3. has_bls_match and has_onet_match ranges
- **has_bls_match:** EDA shows 94.6%. Range set to 90-97%.
- **has_onet_match:** EDA shows 92.0%. Range set to 88-95%.
- **Rationale:** Mismatches are systematic (SOC version granularity, O*NET "All Other" exclusions), not random. Ranges account for this.

### 4. match_quality distribution
- **EDA Scenario A (strict matching):** 100% no_scorecard
- **Decision:** Rule SLV-XW-013 expects >= 95% no_scorecard, allowing margin for potential matching strategy changes.

## Rules Written

### Bronze (BRZ-XW-001 through BRZ-XW-008)

| Rule ID | Dimension | Priority | Description |
|---------|-----------|----------|-------------|
| BRZ-XW-001 | Validity | P0 | CIP format XX.XXXX -- 100% compliance in EDA |
| BRZ-XW-002 | Validity | P0 | SOC format XX-XXXX -- 100% compliance in EDA |
| BRZ-XW-003 | Uniqueness | P0 | Grain uniqueness cipcode x soc_code -- zero duplicates in EDA |
| BRZ-XW-004 | Volume | P0 | Row count 5,500-6,500 -- actual 6,097 |
| BRZ-XW-005 | Completeness | P0 | No nulls on source fields -- zero nulls in EDA |
| BRZ-XW-006 | Completeness | P0 | No nulls on metadata fields -- pipeline-generated |
| BRZ-XW-007 | Validity | P0 | source_method = 'xlsx_download' -- physical model constraint |
| BRZ-XW-008 | Validity | P2 | No-match sentinel count ~194 -- informational tracking |

### Silver (SLV-XW-001 through SLV-XW-020)

| Rule ID | Dimension | Priority | Description |
|---------|-----------|----------|-------------|
| SLV-XW-001 | Uniqueness | P0 | record_id uniqueness (surrogate key) |
| SLV-XW-002 | Uniqueness | P0 | cipcode x soc_code uniqueness (natural key) |
| SLV-XW-003 | Validity | P0 | Zero rows with soc_code 99-9999 (filter check) |
| SLV-XW-004 | Validity | P0 | CIP format XX.XXXX |
| SLV-XW-005 | Validity | P0 | SOC format XX-XXXX |
| SLV-XW-006 | Validity | P0 | SOC major group valid 22 codes |
| SLV-XW-007 | Validity | P0 | match_quality valid enum |
| SLV-XW-008 | Volume | P0 | Row count 5,500-6,200 |
| SLV-XW-009 | Completeness | P0 | No nulls on any field (all 13 columns) |
| SLV-XW-010 | Consistency | P1 | has_scorecard_match <= 5% TRUE |
| SLV-XW-011 | Consistency | P1 | has_bls_match 90-97% TRUE |
| SLV-XW-012 | Consistency | P1 | has_onet_match 88-95% TRUE |
| SLV-XW-013 | Consistency | P1 | match_quality >= 95% no_scorecard |
| SLV-XW-014 | Consistency | P0 | cip_family = LEFT(cipcode, 2) |
| SLV-XW-015 | Consistency | P0 | soc_major_group = LEFT(soc_code, 2) |
| SLV-XW-016 | Consistency | P0 | match_quality derivation matches CASE expression |
| SLV-XW-017 | Validity | P0 | record_id format xw-<hex16> |
| SLV-XW-018 | Referential Integrity | P3 | BLS SOC RI -- ~47 mismatches expected |
| SLV-XW-019 | Referential Integrity | P3 | O*NET SOC RI -- ~69 mismatches expected |
| SLV-XW-020 | Referential Integrity | P3 | Scorecard CIP RI -- ~1,949 mismatches expected (granularity) |

## Rules Considered but NOT Written

### 1. cip_family validity against College Scorecard families
- **Spec suggested:** "cip_family must be one of the valid 2-digit CIP families (check against base.college_scorecard distinct cip_family values)"
- **Decision:** NOT written. The crosswalk contains CIP families not present in Scorecard (60, 61, 99 per EDA). Cross-referencing against Scorecard would incorrectly flag valid crosswalk families. The cip_family derivation consistency rule (SLV-XW-014) is sufficient.

### 2. Freshness rule
- **Considered:** Data recency check on ingested_at or source_load_date
- **Decision:** NOT written. This is a static reference table (CIP 2020 x SOC 2018 vintage, updated ~10-year cycles). Freshness is meaningless for a taxonomy crosswalk. The load_date metadata field provides provenance.

### 3. CIP cardinality distribution monitoring
- **Considered:** Assert that the max SOCs per CIP is within expected range
- **Decision:** NOT written as a rule. The EDA documents the distribution (max 23 SOCs per CIP for Business Administration). Cardinality is a source characteristic, not a data quality issue. If needed, this could be added as a P3 monitoring rule later.

### 4. SOC-CIP sheet discrepancy validation
- **Considered:** Cross-check CIP-SOC vs SOC-CIP sheet row counts
- **Decision:** NOT written. The ingestor only reads the CIP-SOC sheet. The 4-row discrepancy with the SOC-CIP sheet is documented in the EDA but has no impact on the pipeline.

## Execution Status

Rules are in PROPOSED status. Execution will be performed by @dq-engineer after the pipeline implementation is complete (pipeline step 6 must finish first -- the tables do not yet exist).
