# Human Approval: Silver Base O*NET Experience Logical Model

**Spec:** docs/specs/onet-experience-requirements.md
**Artifact:** governance/models/silver-base-onet-experience-logical.md
**Stage:** Logical Model (Stage 2 of 3)
**Author:** @semantic-modeler
**Date:** 2026-04-16
**Status:** APPROVED
**Approved By:** Jeff Cernauske
**Approved Date:** 2026-04-16
**Conditions:** none

---

## Context

`docs/specs/onet-experience-requirements.md` adds a new experience-gating layer to the career evolution tree. Per the governance re-review (APPROVED 2026-04-16), all three Silver models plus the Gold physical-model addendum must exist and be approved before any Bronze or Silver code is written. The conceptual model (Stage 1) has been proposed and is pending approval.

This logical model translates the 1 primary conceptual entity (Experience Profile) into 11 concrete attributes with type domains, nullability, CDE/PII tags, derivation lineage, and foreign-key relationships.

All three prior open decisions (tier thresholds, "Over 10 years" midpoint, multi-detail aggregation) are resolved in `governance/approvals/onet-experience-requirements-open-decisions.md` and baked into the derivation rules -- no additional value judgments are introduced at this stage.

## What Is Being Proposed

A logical data model for `base.onet_experience_profiles` -- Stage 2 of 3. The model defines:

- 1 table, 11 attributes
- 1 natural key (`bls_soc_code`), 1 surrogate key (`record_id`, prefix `exp`)
- 3 CDE columns, 0 PII
- 8 attributes derived at the Silver layer, 1 carried from Bronze, 1 generated at write, 1 surrogate key
- A complete derivation lineage showing how each attribute traces back to `raw.onet_experience` Bronze rows (filtered to `scale_id = 'RW' AND element_id = '3.A.1'`)
- The human-approved midpoint mapping (11 categories -> years) and tier thresholds (4 bands) as explicit SQL
- 1 foreign-key relationship: `bls_soc_code` -> `base.onet_occupations.bls_soc_code`

## Summary of the Logical Model

### Attribute Count by Category

| Category | Count |
|----------|-------|
| Identifier / key | 2 (record_id, bls_soc_code) |
| Primary measurement | 1 (experience_years_typical) |
| Classifier | 1 (experience_tier) |
| Internal derivation intermediates | 2 (experience_category_median, experience_category_mode) |
| Distribution | 1 (experience_distribution -- JSON text) |
| Provenance | 2 (onet_details_averaged, suppress_flag) |
| Metadata | 2 (source_load_date, ingested_at) |
| **Total** | **11** |

### Key Design Decisions for Review

#### 1. Single-table realization of the conceptual entity
Experience Profile becomes one physical table with no composite grain. The BLS SOC single-field natural key matches `base.onet_occupations` exactly.

#### 2. Internal derivation intermediates retained for auditability
`experience_category_median` and `experience_category_mode` are internal derivation steps. Keeping them on the Silver row (rather than hiding them inside the transformer) lets DQ rules spot-check the weighted-median computation directly and lets analysts investigate edge cases without re-running Bronze.

**Alternative considered:** Drop the intermediates and keep only `experience_years_typical`. Rejected because the weighted-median is the spec's most adversarial logic (7 explicit edge cases in the §Test Matrix) and auditability outweighs the 2-column cost.

#### 3. Full distribution preserved as a JSON VARCHAR
`experience_distribution` stores `{"1": 5.2, "7": 45.3, ...}` -- an 11-key JSON object. VARCHAR rather than a native nested type matches the `onet_detail_codes` precedent in `base.onet_occupations` and is the most reliable Iceberg/DuckDB interop path.

#### 4. All 11 attributes NOT NULL
O*NET RW data is complete for all retained occupations -- occupations without any RW coverage are excluded entirely rather than producing rows with null values. Documented in §Nullability Semantics.

#### 5. CDE tags applied to exactly 3 columns
`bls_soc_code` (grain + cross-source join key), `experience_years_typical` (primary scalar, feeds Gold + frontend filter), and `experience_tier` (classifier driving UX gating). Internal derivation intermediates, provenance, and metadata are not CDEs. Matches §CDE & PII Assessment in the spec exactly.

#### 6. No separate dimension table for the Experience Tier classifier
Tier is an enum stored directly on the fact row. Thresholds are the human-approved ranges captured in the open-decisions file. Adding a dimension table for a 4-value static enum would be overmodeling.

#### 7. Midpoint mapping and tier thresholds shown as SQL in the model
Both tables (category -> years midpoint, years -> tier boundary) appear directly in the logical model, not just in the spec. This makes the logical model self-contained for DQ-rule-writer and primary-agent implementers.

### Derivation Lineage Documented

Complete Bronze-to-Silver lineage shown:

```
raw.onet_experience (~35,881 rows, 4 scales)
  -> FILTER scale_id = 'RW' AND element_id = '3.A.1'
  -> GROUP BY onet_soc_code (O*NET detail level)
  -> weighted median category + mode per detail
  -> convert median category to midpoint years
  -> TRUNCATE onet_soc_code to bls_soc_code
  -> GROUP BY bls_soc_code (BLS level)
  -> unweighted average years across details
  -> merge distribution dicts + logical OR suppress flag
base.onet_experience_profiles (~867 rows)
```

Every derived attribute has an explicit rule including SQL/pseudocode, source fields, and null/edge-case behavior.

## Business Terms Referenced

All 9 business terms from the conceptual model are carried forward in the attribute table. New terms BT-117 (Related Work Experience) and BT-118 (Experience Tier) remain **pending data-steward approval**.

## What Happens Next

- **If APPROVED:** @semantic-modeler proceeds to the physical model (Stage 3), mapping logical type domains to DuckDB column types, producing the exact PyIceberg schema, and locking partition/sort decisions. Also produces the Gold physical-model addendum for the 4 additive `career_branches` columns.
- **If CHANGES REQUESTED:** @semantic-modeler revises the logical model based on feedback and resubmits.
- **If REJECTED:** The logical model approach is reconsidered, potentially requiring changes to the approved conceptual model.

## Approval

To approve, set the status in the logical model file to `APPROVED` and note any conditions:

```
**Status:** APPROVED
**Approved By:** [name]
**Approved Date:** [date]
**Conditions:** [any conditions or none]
```
