# Human Approval: Gold Career Outcomes Logical Model

**Spec:** gold-career-outcomes-college-scorecard
**Artifact:** governance/models/gold-career-outcomes-college-scorecard-logical.md
**Stage:** Logical Model (Stage 2 of 3)
**Author:** @semantic-modeler
**Date:** 2026-04-06
**Status:** PENDING APPROVAL

---

## What Is Being Proposed

A logical data model for the `consumable.career_outcomes` Gold zone table. This is the second of three modeling stages (conceptual, logical, physical). The conceptual model (Stage 1) was proposed and is pending approval.

The logical model translates the 6 conceptual entities into 30 concrete attributes with type domains, nullability, derivation rules, and business term references.

## Summary of the Logical Model

### Attribute Count by Entity Group

| Conceptual Entity | Attributes | Derivation |
|-------------------|-----------|------------|
| Career Outcome (identity + core) | 14 | 13 carried from Silver, 1 recomputed (record_id) |
| Earnings Percentile Band | 6 | All derived via PERCENTILE_CONT window functions |
| Financial Assessment | 5 | All derived via arithmetic and window functions |
| Data Confidence | 4 | All derived via conditional logic |
| Pipeline Metadata | 2 | 1 carried, 1 generated at promotion |
| **Total** | **30** | |

### Key Design Decisions for Review

#### 1. 30 attributes in a single denormalized table
The 6 conceptual entities flatten into one wide fact table. This follows the Silver pattern and optimizes for the primary query pattern (school + major = outcomes).

#### 2. 17 new derived attributes
Gold adds 17 derived attributes on top of 13 Silver carry-forwards:
- 6 percentile bands (CIP-family window aggregates)
- 5 financial metrics (ratios, tiers, ranks)
- 4 data confidence fields (tier, flags, completeness score)
- 1 pipeline metadata field (promoted_at)
- 1 recomputed surrogate key (record_id with 'co' prefix)

#### 3. Minimum sample size of 3 for percentile bands
CIP families with fewer than 3 non-null values for a given field get null bands. This prevents misleading distributions from tiny samples.

#### 4. All derivation rules are null-safe
Privacy suppression from Silver propagates through all derived fields. If a required input is null, the derived output is null. The confidence tier captures this impact per row.

#### 5. Dropped fields documented with justification
Three Silver attributes are dropped: completions_count_2 (not relevant), credential_description (redundant), ingested_at (replaced by promoted_at). One is renamed: completions_count_1 becomes completions_count.

#### 6. CDE designations
11 total CDE attributes: 4 carried from Silver (unitid, earnings_1yr_median, earnings_2yr_median, debt_median) plus 6 percentile band attributes and debt_to_earnings_annual. Percentile bands are CDE because they power the effort slider, which is the primary product feature.

### Business Terms Referenced

All 20 business terms from the conceptual model are carried forward. Each attribute maps to its BT-XXX identifier. One open issue: institution_control still lacks a business term (inherited from Silver).

### Derivation Rules Documented

Every derived attribute has a complete derivation rule including:
- SQL/pseudocode formula
- Source attributes
- Null propagation behavior
- Partition key (for window functions)
- Minimum sample threshold (for percentile bands)

### Constraints Documented

9 hard constraints (P0) and 5 soft constraints (P1) are specified. These will feed the DQ rule writer.

## What Happens Next

- **If APPROVED:** @semantic-modeler proceeds to the physical model (Stage 3), mapping logical type domains to DuckDB column types and adding implementation-specific details.
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
