# DQ Rule Audit Trail: raw-ingest-college-scorecard

**Date:** 2026-04-05
**Agent:** @dq-rule-writer
**Zone:** Bronze
**Evidence Source:** governance/eda/raw-college-scorecard-eda.md
**Domain Context:** governance/domain-context.md
**Spec:** docs/specs/raw-ingest-college-scorecard.md

---

## Rules Written: 18

| Rule ID | Dimension | Priority | Summary |
|---------|-----------|----------|---------|
| RAW-CS-001 | Uniqueness | P0 | Grain uniqueness: unitid x cipcode x credlev |
| RAW-CS-002 | Completeness | P0 | unitid not null |
| RAW-CS-003 | Completeness | P0 | cipcode not null |
| RAW-CS-004 | Completeness | P0 | credlev not null |
| RAW-CS-005 | Completeness | P0 | instnm not null |
| RAW-CS-006 | Completeness | P1 | earn_mdn_hi_1yr null rate <= 70% |
| RAW-CS-007 | Completeness | P1 | earn_mdn_hi_2yr null rate <= 65% |
| RAW-CS-008 | Completeness | P1 | debt_all_stgp_eval_mdn null rate <= 68% |
| RAW-CS-009 | Completeness | P1 | ipedscount1 null rate <= 12% |
| RAW-CS-010 | Validity | P0 | credlev = 3 for all rows |
| RAW-CS-011 | Validity | P0 | cipcode 4-digit numeric format |
| RAW-CS-012 | Validity | P1 | earn_mdn_hi_1yr in $0-$300k range |
| RAW-CS-013 | Validity | P1 | earn_mdn_hi_2yr in $0-$300k range |
| RAW-CS-014 | Validity | P1 | debt_all_stgp_eval_mdn in $0-$200k range |
| RAW-CS-015 | Validity | P1 | unitid 6-digit range (100k-999k) |
| RAW-CS-016 | Volume | P0 | Row count between 50,000 and 100,000 |
| RAW-CS-017 | Freshness | P1 | load_date within 30 days |
| RAW-CS-018 | Consistency | P1 | 2yr vs 1yr earnings pattern monitoring |

## Dimension Coverage

| Dimension | Rule Count | Priority Mix |
|-----------|------------|-------------|
| Uniqueness | 1 | 1 P0 |
| Completeness | 8 | 4 P0, 4 P1 |
| Validity | 6 | 2 P0, 4 P1 |
| Volume | 1 | 1 P0 |
| Freshness | 1 | 1 P1 |
| Consistency | 1 | 1 P1 |
| **Total** | **18** | **8 P0, 10 P1** |

## Rules Considered But Not Written

### md_earn_wne completeness/range
**Decision:** Not written.
**Reason:** EDA confirms this field is 100% null across all 69,947 rows. Domain context investigation indicates md_earn_wne is an institution-level metric that does not populate in the Field of Study file. Writing a completeness or range rule would either always fail (if expecting data) or be vacuously true (if allowing 100% null). Per EDA recommendation: "Do NOT create completeness or range rules for md_earn_wne until the 100% null issue is investigated and resolved."

### ipedscount2 completeness
**Decision:** Not written separately.
**Reason:** EDA shows 8.3% null rate, very similar to ipedscount1 (8.7%). The ipedscount1 rule (RAW-CS-009) serves as a proxy. Could be added if the two fields diverge in future refreshes.

### cipdesc / creddesc / source_url / source_method / ingested_at completeness
**Decision:** Not written.
**Reason:** These are metadata or descriptor fields with 0% null rates that are populated by the framework (metadata fields) or have a 1:1 relationship with already-covered grain fields (cipdesc with cipcode, creddesc with credlev). Adding rules would be redundant with framework guarantees and would not catch meaningful data quality issues.

### Referential integrity (unitid against external IPEDS list)
**Decision:** Not written -- Bronze zone scope.
**Reason:** Referential integrity against external reference data is a Silver zone concern per the DQ dimension matrix. The Bronze zone validates that the data landed correctly; cross-referencing against IPEDS institutional lists requires a reference table not yet ingested.

### CIP code valid in CIP 2020 taxonomy
**Decision:** Not written -- Bronze zone scope.
**Reason:** Same as above. CIP taxonomy validation requires a reference table. The format check (RAW-CS-011) validates structural correctness at the Bronze level.

## Threshold Rationale Summary

### P0 Rules (threshold = 0)
All P0 rules have a threshold of 0 violations because the EDA confirmed zero violations exist in the current data, and any violation would indicate a structural failure (broken grain, failed filter, data corruption). These are not aspirational -- they reflect observed reality.

### P1 Completeness Rules (percentage-based)
Thresholds for earnings/debt null rates are set as absolute row counts derived from the EDA-recommended percentages:
- earn_mdn_hi_1yr: 70% of 69,947 = 48,963 max nulls (observed: 44,751 = 64.0%)
- earn_mdn_hi_2yr: 65% of 69,947 = 45,466 max nulls (observed: 42,266 = 60.4%)
- debt_all_stgp_eval_mdn: 68% of 69,947 = 47,564 max nulls (observed: 44,138 = 63.1%)
- ipedscount1: 12% of 69,947 = 8,394 max nulls (observed: 6,098 = 8.7%)

Headroom of 4-7 percentage points above observed rates allows for normal variation in privacy suppression across annual data refreshes without causing false alarms.

### RAW-CS-018 (Consistency, threshold = 12,000)
The 2yr < 1yr pattern is expected in 44.2% of dual-present rows per EDA. This is NOT an anomaly -- it reflects different cohort measurement windows. The threshold of 12,000 rows (vs. observed ~11,137) monitors for dramatic shifts in this pattern that could indicate a methodology change at the source.
