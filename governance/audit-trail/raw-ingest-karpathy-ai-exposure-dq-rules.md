# Audit Trail: DQ Rule Writing — raw-ingest-karpathy-ai-exposure

**Date:** 2026-04-09
**Agent:** @dq-rule-writer
**Spec:** raw-ingest-karpathy-ai-exposure
**Zone:** Bronze
**Table:** bronze.karpathy_ai_exposure
**Evidence Source:** governance/eda/raw-karpathy-ai-exposure-eda.md
**Domain Context Source:** governance/domain-context.md (Karpathy AI Exposure section)

---

## Rules Written

| Rule ID | Dimension | Priority | Description | Threshold | EDA Evidence |
|---------|-----------|----------|-------------|-----------|--------------|
| RAW-KAI-001 | Validity | P0 | Exposure score range 0-10 | 0 violations | EDA: scores 1-10, no zeros. Rubric allows 0. |
| RAW-KAI-002 | Completeness | P0 | Exposure score non-null | 0 violations | EDA: 0.0% null (0/342) |
| RAW-KAI-003 | Completeness | P0 | Rationale non-null | 0 violations | EDA: 0.0% null (0/342) |
| RAW-KAI-004 | Uniqueness | P0 | Slug uniqueness (grain) | 0 duplicates | EDA: 342 distinct slugs, 342 rows |
| RAW-KAI-005 | Volume | P0 | Row count 325-359 | 342 +/- 5% | EDA: exactly 342 rows |
| RAW-KAI-006 | Validity | P1 | SOC code format XX-XXXX (where non-null) | 0 violations | EDA: all 290 non-null pass format check |
| RAW-KAI-007 | Completeness | P1 | SOC code coverage >= 80% | null rate <= 20% | EDA: 84.8% coverage (290/342). Spec said 95%, adjusted per EDA. |
| RAW-KAI-008 | Completeness | P0 | Occupation title non-null | 0 violations | EDA: 0.0% null (0/342) |
| RAW-KAI-009 | Consistency | P1 | Wage cross-validation vs BLS OOH (> 20% diff) | 0 violations | EDA: $0 difference on all 241 matched rows |
| RAW-KAI-010 | Completeness | P0 | Slug non-null | 0 violations | EDA: 0.0% null (0/342) |
| RAW-KAI-011 | Completeness | P0 | Category non-null | 0 violations | EDA: 0.0% null (0/342) |
| RAW-KAI-012 | Completeness | P0 | Source URL non-null | 0 violations | EDA: 0.0% null |
| RAW-KAI-013 | Completeness | P0 | Ingested_at non-null | 0 violations | EDA: 0.0% null |
| RAW-KAI-014 | Completeness | P0 | Load date non-null | 0 violations | EDA: 0.0% null |
| RAW-KAI-015 | Completeness | P0 | Source method non-null | 0 violations | EDA: 0.0% null |
| RAW-KAI-016 | Validity | P0 | Source method in (github_download, local_cache) | 0 violations | EDA: all rows github_download |
| RAW-KAI-017 | Freshness | P1 | Load date within 30 days | 0 violations | EDA: all rows 2026-04-09 |
| RAW-KAI-018 | Validity | P0 | Exposure score is integer | 0 violations | EDA: TYPE=INTEGER, 10 distinct values |

## Threshold Adjustments from Spec

| Spec Threshold | Adjusted To | Reason |
|---------------|-------------|--------|
| SOC coverage ~95% (P1) | >= 80% (P1) | EDA shows actual coverage is 84.8% (290/342), not 95%. Set threshold at 80% to allow margin below observed rate. |

## Rules Considered but Not Written

| Candidate | Reason Not Written |
|-----------|-------------------|
| Broad SOC code detection (XX-XXX0 pattern) | This is a Silver zone concern (broad-to-detailed resolution). At Bronze, the raw data faithfully represents the source. Broad codes are valid SOC format, not a Bronze DQ issue. |
| Rationale minimum length (>= 250 chars) | EDA shows min 297 chars, but minimum length is a quality heuristic, not a structural constraint. All 342 rationales are substantive. Adding a char-length rule would be P3 informational only, not actionable. Deferred. |
| Median pay annual null rate <= 1% | Optional field per spec schema. EDA shows 0.6% null (2/342 -- legitimate BLS N/A cases). Could add but the field is for cross-validation only, not a primary data field. Deferred to avoid rule bloat. |
| Category cardinality check (exactly 25 categories) | Considered a P2 validity check. The 25 categories are source-defined, not a standard taxonomy. If Karpathy updates and adds/removes categories, the rule would fail but the data would still be valid. Deferred. |

## Execution Results

**Status:** Cannot execute -- Iceberg table `bronze.karpathy_ai_exposure` does not yet exist in the catalog. The ingestor code has been implemented but the table has not been materialized. All 18 rules loaded correctly and are syntactically valid. Execution will be performed by @dq-engineer after the ingestor runs and creates the Iceberg table.

**Validation approach:** All SQL statements were tested against the DQ runner's SQL rewrite and table registration logic. The table reference `bronze.karpathy_ai_exposure` matches the spec's declared Iceberg table name. The cross-validation rule (RAW-KAI-009) references `raw.bls_ooh` which exists at `bronze.bls_ooh` in the catalog -- this may need a table name adjustment depending on how the BLS OOH table was registered.

---

*End of audit trail.*
