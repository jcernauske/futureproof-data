# Audit Trail: DQ Rules for raw-ingest-onet

**Date:** 2026-04-07
**Agent:** @dq-rule-writer
**Spec:** raw-ingest-onet
**Zone:** Bronze
**Evidence Source:** governance/eda/raw-onet-eda.md
**Domain Context Source:** governance/domain-context.md (O*NET section)
**Rules File:** governance/dq-rules/raw-ingest-onet.json

---

## Summary

Wrote 40 DQ rules across 5 active tables for the raw-ingest-onet spec. All rules are in PROPOSED status with evidence-based thresholds sourced from the EDA report.

### Tables Covered (5 of 7 spec tables)

| Table | Rules | Notes |
|-------|-------|-------|
| raw.onet_occupations | 7 | Full coverage: format, completeness, uniqueness, volume, freshness |
| raw.onet_task_statements | 6 | Format, completeness, validity, referential integrity, volume |
| raw.onet_work_activities | 8 | Format, uniqueness, scale validation, enum checks, RI, volume |
| raw.onet_work_context | 9 | Format, uniqueness, 4-scale validation, category completeness, RI, volume |
| raw.onet_related_occupations | 10 | Format (both SOCs), uniqueness, range, consistency, self-ref, RI (both), structure, volume |

### Tables NOT Covered (2 of 7 spec tables)

| Table | Reason |
|-------|--------|
| raw.onet_career_changers | Career Changers Matrix.txt does not exist in O*NET 30.2 ZIP. EDA confirmed file missing, all download URLs returned HTTP 404. Domain context recommends removing or making conditional. |
| raw.onet_career_starters | Career Starters Matrix.txt does not exist in O*NET 30.2 ZIP. Same situation as Career Changers. |

---

## Rule Breakdown by Dimension

| Dimension | Count | P0 | P1 |
|-----------|-------|----|----|
| Validity | 17 | 15 | 2 |
| Completeness | 6 | 5 | 1 |
| Uniqueness | 4 | 4 | 0 |
| Referential Integrity | 5 | 5 | 0 |
| Volume | 5 | 0 | 5 |
| Consistency | 2 | 2 | 0 |
| Freshness | 1 | 0 | 1 |
| **Total** | **40** | **30** | **10** |

---

## Threshold Decisions with EDA Evidence

### raw.onet_occupations

| Rule | Threshold | EDA Evidence |
|------|-----------|-------------|
| RAW-ONET-001: SOC format | 0 violations | 100% valid in 1,016 rows |
| RAW-ONET-002: onet_soc_code not null | 0 violations | 0% null in 1,016 rows |
| RAW-ONET-003: title not null | 0 violations | 0% null in 1,016 rows |
| RAW-ONET-004: description not null | 0 violations | 0% null in 1,016 rows |
| RAW-ONET-005: grain unique | 0 duplicates | 1,016 distinct = 1,016 rows |
| RAW-ONET-006: row count | 900-1,100 | Actual: 1,016. EDA recommends +/- 5%. Used wider range for quarterly release variance. |
| RAW-ONET-007: freshness | load_date within 30 days | Consistent with RAW-CS-017 and RAW-OOH-017. |

### raw.onet_task_statements

| Rule | Threshold | EDA Evidence |
|------|-----------|-------------|
| RAW-ONET-008: SOC format | 0 violations | 100% valid in 18,796 rows |
| RAW-ONET-009: task_id not null | 0 violations | 0% null, 18,796 globally unique |
| RAW-ONET-010: task not empty | 0 violations | 0% null, min length=13 chars |
| RAW-ONET-011: task_type values | {"Core", "Supplemental", "n/a"} | Only 3 observed. "n/a" = 4.5%, correlates 1:1 with Analyst domain_source. |
| RAW-ONET-012: RI to occupations | 0 orphans | All 923 SOCs exist in Occupation Data |
| RAW-ONET-013: row count | 18,000-22,000 | Actual: 18,796. EDA recommends +/- 10%. |

### raw.onet_work_activities

| Rule | Threshold | EDA Evidence |
|------|-----------|-------------|
| RAW-ONET-014: SOC format | 0 violations | 100% valid in 73,308 rows |
| RAW-ONET-015: grain unique | 0 duplicates | Verified unique across 73,308 rows |
| RAW-ONET-016: IM range [1.0, 5.0] | 0 violations | Observed 1.00-4.99 in 36,654 rows |
| RAW-ONET-017: LV range [0.0, 7.0] | 0 violations | Observed 0.00-6.81 in 36,654 rows |
| RAW-ONET-018: scale_id in {IM, LV} | 0 violations | Only 2 values, perfectly balanced 50/50 |
| RAW-ONET-019: recommend_suppress values | {Y, N, n/a} | Only 3 values: N=74.9%, n/a=23.6%, Y=1.5% |
| RAW-ONET-020: RI to occupations | 0 orphans | All 894 SOCs exist in Occupation Data |
| RAW-ONET-021: row count | 70,000-80,000 | Actual: 73,308. Very stable (894 x 41 x 2). |

### raw.onet_work_context

| Rule | Threshold | EDA Evidence |
|------|-----------|-------------|
| RAW-ONET-022: SOC format | 0 violations | 100% valid in 297,676 rows |
| RAW-ONET-023: grain unique | 0 duplicates | Including category in grain. Verified unique. |
| RAW-ONET-024: scale_id in {CX, CT, CXP, CTP} | 0 violations | Only 4 values: CXP=81.1%, CX=16.5%, CTP=1.8%, CT=0.6% |
| RAW-ONET-025: CX range [1.0, 5.0] | 0 violations | Observed 1.00-5.00 |
| RAW-ONET-026: CT range [1.0, 7.0] | 0 violations | Observed 1.00-3.00. Used wider domain range [1, 7] for forward compatibility. |
| RAW-ONET-027: CXP/CTP range [0.0, 100.0] | 0 violations | CXP: 0.00-100.00, CTP: 0.00-100.00 |
| RAW-ONET-028: category for CXP/CTP | 0 null on percentage rows | All CXP/CTP rows have category values; only CX/CT rows have null category |
| RAW-ONET-029: RI to occupations | 0 orphans | All 894 SOCs exist in Occupation Data |
| RAW-ONET-030: row count | 280,000-320,000 | Actual: 297,676 (6x spec estimate due to CXP/CTP rows). |

### raw.onet_related_occupations

| Rule | Threshold | EDA Evidence |
|------|-----------|-------------|
| RAW-ONET-031: source SOC format | 0 violations | 100% valid (923 distinct) |
| RAW-ONET-032: related SOC format | 0 violations | 100% valid (920 distinct) |
| RAW-ONET-033: grain unique | 0 duplicates | Verified unique across 18,460 rows |
| RAW-ONET-034: related_index [1, 20] | 0 violations | All values in range, perfectly uniform |
| RAW-ONET-035: is_primary consistent | 0 violations | index 1-10 = primary, 11-20 = supplemental. Derived from Relatedness Tier. |
| RAW-ONET-036: no self-references | 0 violations | 0 cases where source = related |
| RAW-ONET-037: RI source SOC | 0 orphans | All 923 source SOCs exist |
| RAW-ONET-038: RI related SOC | 0 orphans | All 920 related SOCs exist |
| RAW-ONET-039: 20 rows per occupation | 0 violations | 923 x 20 = 18,460, no exceptions |
| RAW-ONET-040: row count | 17,000-20,000 | Actual: 18,460. |

---

## Rules Considered But Not Written

| Considered Rule | Reason Not Written |
|-----------------|-------------------|
| not_relevant values in Work Activities | Considered P2 but deferred -- "n/a" (50%, all IM), "N" (48.5%, LV relevant), "Y" (1.5%, LV not relevant). All values are documented and expected. Not critical for Bronze zone. |
| domain_source enum validation | Deferred -- only 4 values observed ("Incumbent", "Occupational Expert", "Analyst", "Analyst - Transition") but domain_source is metadata, not a structural constraint. |
| Work Activities: exactly 82 rows per occupation | Considered but deferred -- would be a strong structural check but currently redundant with grain uniqueness + volume rules. Could add in Silver zone. |
| Work Context: rows per occupation (338 or 57) | Deferred -- 16 occupations have 57 rows (partial CXP/CTP data). This is documented and expected. A rule would flag a known edge case without actionable outcome in Bronze. |
| Task statement length validation | Deferred -- EDA shows min=13 chars which is sufficient. No truncation detected. |
| CXP category sum to 100% per element-occupation | Considered -- would validate that percentage categories sum correctly. Deferred to Silver zone where aggregation logic is applied. |
| task_type "n/a" implies domain_source "Analyst" | Considered as a cross-field consistency rule. Deferred -- the correlation is documented in EDA but the Bronze zone preserves raw data as-is. |
| Career Changers Matrix rules | Files do not exist in O*NET 30.2. No tables to validate. |
| Career Starters Matrix rules | Files do not exist in O*NET 30.2. No tables to validate. |

---

## Execution Results

**Initial validation run:** All 40 rules returned "Table not found" errors because the O*NET Iceberg tables have not yet been ingested into the DQ runner's DuckDB execution environment. This is expected -- the DQ rules are written at step 4 of the pipeline (after EDA, before ingestor execution against production tables). The rules will be re-executed after the O*NET ingestor populates the tables.

**Scorecard generated:** governance/dq-scorecards/raw-ingest-onet-scorecard.md

---

## Notes

- The spec estimated ~49,000 Work Context rows but actual is 297,676 (6x). This is NOT a bug -- CXP/CTP category-percentage rows were not accounted for. All volume rules use actual counts.
- 93 "All Other"/Military occupations exist in Occupation Data but have NO child data. RI rules are written as "child SOC codes must exist in parent" (not "all parent SOC codes must have children") per domain-context guidance.
- Related Occupations schema changed from spec: "Related Index" column renamed to "Index", new "Relatedness Tier" column added. Ingestor was updated to handle both.
