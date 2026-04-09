# Human Approval: Gold Career Outcomes Conceptual Model

**Spec:** gold-career-outcomes-college-scorecard
**Artifact:** governance/models/gold-career-outcomes-college-scorecard-conceptual.md
**Stage:** Conceptual Model (Stage 1 of 3)
**Author:** @semantic-modeler
**Date:** 2026-04-06
**Status:** PENDING APPROVAL

---

## What Is Being Proposed

A conceptual data model for the `consumable.career_outcomes` Gold zone table. This is the first of three modeling stages (conceptual, logical, physical) that must be approved before implementation begins.

The model defines six business entities and their relationships:

1. **Career Outcome** -- the central fact entity (one per institution-program-credential)
2. **Program Identity** -- who and what (institution, program, CIP code, credential level)
3. **CIP Family** -- broad discipline grouping used for peer comparisons
4. **Earnings Percentile Band** -- cross-institution earnings/debt distribution within a CIP family
5. **Financial Assessment** -- affordability and value metrics (debt-to-earnings, growth rate, ROI proxy)
6. **Data Confidence** -- quality tier and completeness score for every row

## Key Design Decisions for Review

### 1. Single consumable fact table (denormalized)
The six conceptual entities will likely collapse into a single wide physical table. This optimizes for the primary query pattern (school + major = outcomes) at the cost of some redundancy in percentile band values across rows in the same CIP family.

**Alternative considered:** Star schema with a separate CIP Family Percentile dimension table. Rejected because the query pattern always needs the bands inline, and the dataset size (70K rows) does not benefit from normalization.

### 2. All programs carried forward, flagged not excluded
Programs with insufficient data receive a confidence tier of "insufficient" but remain in the table. Filtering happens at query time.

**Why this matters:** Users searching for a specific school/program should always find a row, even if the row says "we don't have reliable outcome data for this program."

### 3. Percentile bands require minimum 3 data points
CIP families with fewer than 3 non-null values for a given field (earnings or debt) will have null percentile bands for that field. This prevents misleading percentiles from tiny samples.

### 4. Earnings growth rate is cross-cohort, not longitudinal
The "earnings growth rate" (BT-021) compares 1yr and 2yr cohort earnings from different graduating classes. Negative values are expected (~44% of programs). The conceptual model emphasizes this to prevent misinterpretation.

## Business Terms Referenced

All terms below are defined in `governance/business-glossary.json`. The model stores IDs only.

| Term ID | Term Name | Used In Entity |
|---------|-----------|---------------|
| BT-001 | UNITID | Program Identity |
| BT-003 | CIP Code | Program Identity |
| BT-005 | CIP Family | CIP Family |
| BT-007 | Credential Level | Program Identity |
| BT-009 | Median Earnings 1-Year | Career Outcome |
| BT-010 | Median Earnings 2-Year | Career Outcome |
| BT-011 | Median Debt at Completion | Career Outcome |
| BT-012 | IPEDS Completions Count | Career Outcome |
| BT-013 | Privacy Suppression | (contextual -- drives nulls) |
| BT-014 | Small Cohort Flag | Career Outcome, Data Confidence |
| BT-015 | Record ID | Career Outcome |
| BT-018 | Cross-Institution Earnings Percentile Band | Earnings Percentile Band |
| BT-019 | Debt-to-Earnings Ratio (Annual) | Financial Assessment |
| BT-020 | Debt-to-Earnings Tier | Financial Assessment |
| BT-021 | Cross-Cohort Earnings Differential | Financial Assessment |
| BT-022 | CIP Family Earnings Rank | Financial Assessment |
| BT-023 | Program Value Index | Financial Assessment |
| BT-024 | Confidence Tier | Data Confidence |
| BT-025 | Outcome Completeness | Data Confidence |
| BT-026 | Promotion Timestamp | (metadata) |

## What Happens Next

- **If APPROVED:** @semantic-modeler proceeds to the logical model (Stage 2), adding attributes, keys, and data domains to each entity.
- **If CHANGES REQUESTED:** @semantic-modeler revises this conceptual model based on feedback and resubmits.
- **If REJECTED:** The modeling approach is reconsidered from scratch.

## Approval

To approve, set the status in the conceptual model file to `APPROVED` and note any conditions:

```
**Status:** APPROVED
**Approved By:** [name]
**Approved Date:** [date]
**Conditions:** [any conditions or none]
```
