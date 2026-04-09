# CDE/PII Tagging Audit Log: crosswalk-cip-soc

**Date:** 2026-04-08
**Agent:** @cde-tagger
**Spec:** docs/specs/crosswalk-cip-soc.md
**Contract:** governance/data-contracts/base-cip-soc-crosswalk.yaml
**Table:** base.cip_soc_crosswalk
**Zone:** Silver (Base)

## Domain Context Referenced

- **governance/domain-context.md** -- Regulatory section confirms no applicable regulations requiring specific CDE flags (this is a public taxonomy crosswalk, not financial or health data). PII Expectations section across all three data sources confirms zero PII in institutional/aggregate/taxonomic data.
- **governance/models/crosswalk-cip-soc-conceptual.md** -- Conceptual model identifies cipcode, soc_code, and match_quality as CDEs at the entity level. These are the Crosswalk Mapping entity's core identity and derived classification attributes.
- **governance/models/crosswalk-cip-soc-physical.md** -- Physical model confirms 3 CDE columns and 0 PII columns.
- **PII scanner result** -- governance/audit-trail/pii-scan-crosswalk-cip-soc-2026-04-08.md confirms 0 PII fields.

## Tagging Decisions

### Columns Flagged as CDE

| Column | Rationale |
|--------|-----------|
| cipcode | Composite natural key (1 of 2) and join key to base.college_scorecard. CIP-side anchor of the crosswalk bridge; without it the entire program-to-occupation integration chain breaks. |
| soc_code | Composite natural key (2 of 2) and join key to base.bls_ooh and base.onet_occupations. SOC-side anchor of the crosswalk bridge; without it no occupation data can be reached from student queries. |
| match_quality | Business-critical classification determining which FutureProof stats can be computed per program-occupation pair. Drives Gold product confidence scoring and data completeness transparency. |

### Columns Flagged as PII

None. This dataset is a public taxonomy crosswalk published by NCES/BLS. It contains no personal, financial, or health information about individuals.

### Columns Evaluated -- Not Flagged

| Column | Reason Not Critical/Sensitive |
|--------|-------------------------------|
| record_id | Deterministic surrogate key (xw-<hex>). Technical artifact for dedup and pipeline mechanics. Not consumed by business logic or downstream joins. |
| cip_title | Descriptive label for cipcode. Display only; not used in joins, computations, or business rules. Downstream Gold products should prefer College Scorecard's program name. |
| cip_family | Derived 2-digit classification from cipcode. Aggregation convenience field; not a join key or business decision driver at this table's grain. |
| soc_title | Descriptive label for soc_code. Display only; not used in joins, computations, or business rules. Downstream Gold products should prefer BLS OOH's occupation title. |
| soc_major_group | Derived 2-digit classification from soc_code. Aggregation convenience field; not a join key or business decision driver at this table's grain. |
| has_scorecard_match | Derived boolean flag, input to match_quality. Intermediate computation result; match_quality is the business-facing classification that consumers use. |
| has_bls_match | Derived boolean flag, input to match_quality. Same reasoning as has_scorecard_match. |
| has_onet_match | Derived boolean flag, input to match_quality. Same reasoning as has_scorecard_match. |
| source_load_date | Pipeline metadata. No business consumption. |
| ingested_at | Pipeline metadata. No business consumption. |
