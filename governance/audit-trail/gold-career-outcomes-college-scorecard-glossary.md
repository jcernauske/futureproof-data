# Audit Trail: Business Glossary — Gold Career Outcomes
**Date:** 2026-04-06
**Agent:** @data-steward
**Spec:** gold-career-outcomes-college-scorecard
**Mode:** Greenfield
**Domain:** Higher Education Outcomes

## Business Term Proposals: gold-career-outcomes-college-scorecard

### New Terms Proposed
| Term ID | Term | Source | Category | Status |
|---------|------|--------|----------|--------|
| BT-018 | Cross-Institution Earnings Percentile Band | project-specific | derived | PROPOSED |
| BT-019 | Debt-to-Earnings Ratio (Annual) | domain-standard | measurement | AUTO-APPROVED |
| BT-020 | Debt-to-Earnings Tier | project-specific | classification | PROPOSED |
| BT-021 | Cross-Cohort Earnings Differential (was: Earnings Growth Rate) | project-specific | derived | APPROVED (renamed) |
| BT-022 | CIP Family Earnings Rank | project-specific | derived | PROPOSED |
| BT-023 | Program Value Index | project-specific | derived | PROPOSED |
| BT-024 | Confidence Tier | project-specific | classification | PROPOSED |
| BT-025 | Outcome Completeness | project-specific | derived | PROPOSED |
| BT-026 | Promotion Timestamp | project-specific | temporal | PROPOSED |

### Existing Terms Referenced (used_in_models updated)
| Term ID | Term | Added To |
|---------|------|----------|
| BT-001 | UNITID | gold-career-outcomes-college-scorecard |
| BT-002 | Institution Name | gold-career-outcomes-college-scorecard |
| BT-003 | CIP Code | gold-career-outcomes-college-scorecard |
| BT-004 | Program Name | gold-career-outcomes-college-scorecard |
| BT-005 | CIP Family | gold-career-outcomes-college-scorecard |
| BT-006 | CIP Family Name | gold-career-outcomes-college-scorecard |
| BT-007 | Credential Level | gold-career-outcomes-college-scorecard |
| BT-009 | Median Earnings 1-Year Post-Completion | gold-career-outcomes-college-scorecard |
| BT-010 | Median Earnings 2-Year Post-Completion | gold-career-outcomes-college-scorecard |
| BT-011 | Median Debt at Completion | gold-career-outcomes-college-scorecard |
| BT-012 | IPEDS Completions Count | gold-career-outcomes-college-scorecard |
| BT-014 | Small Cohort Flag | gold-career-outcomes-college-scorecard |
| BT-016 | Source Load Date | gold-career-outcomes-college-scorecard |

### Ambiguities Found

1. **~~Earnings Growth Rate naming~~ RESOLVED:** Renamed to "Cross-Cohort Earnings Differential" per human reviewer feedback. The term "growth rate" implied longitudinal tracking; the new name reflects the cross-cohort reality. Old name preserved in synonyms.

2. **~~Program Value Index vs. Debt-to-Earnings Ratio~~ RESOLVED:** BT-023 definition updated to explicitly note it is the mathematical inverse of BT-019. Both terms retained because they serve different analytical purposes (DTE = affordability, lower is better; PVI = value, higher is better).

### Source Attribution

| Term ID | Definition Source |
|---------|------------------|
| BT-018 | Spec (Derived: Percentile Bands section) + Source Data Constraint section explaining cross-institution aggregation |
| BT-019 | Gainful Employment Final Rule (34 CFR 668, 2023) + spec financial ratios section |
| BT-020 | Spec (Debt-to-Earnings Tier Thresholds table) |
| BT-021 | Spec (Derived: Financial Ratios) + domain-context.md (Temporal Patterns: Measurement windows) |
| BT-022 | Spec (Derived: Relative Position) |
| BT-023 | Spec (Derived: Relative Position) |
| BT-024 | Spec (Confidence Tier Derivation table) |
| BT-025 | Spec (Derived: Data Quality Context) |
| BT-026 | Spec (Metadata: promoted_at field) |

### Auto-Approval Rationale

- **BT-019 (Debt-to-Earnings Ratio):** Auto-approved as domain-standard. The Gainful Employment rule (34 CFR 668) establishes debt-to-earnings evaluation as an official Department of Education accountability mechanism for postsecondary programs. While the GE formula uses annual loan payments rather than total debt, the underlying concept of comparing debt burden to earnings outcomes is an established domain standard with formal regulatory backing. The domain-context.md Regulatory section explicitly references Gainful Employment rules and debt-to-earnings ratios.

### Decisions

- Did NOT add terms for `has_earnings` and `has_debt` convenience flags -- these are simple boolean derivations (IS NOT NULL checks) that do not represent independent business concepts. They are implementation details of the confidence tier and filtering logic.
- Did NOT add a separate term for `institution_control` (Public/Private) -- this is carried from Silver but is a standard IPEDS attribute already covered by the Institution entity (BT-001/BT-002). It does not need its own glossary entry.
- BT-008 (Credential Description) and BT-013 (Privacy Suppression) were NOT added to Gold used_in_models because they are not carried forward to the Gold table (credential_description is dropped per spec; privacy suppression is an underlying mechanism, not a Gold field).
- BT-015 (Record ID) was NOT updated for Gold because the Gold table uses a different prefix ('co' vs 'cs'), making it a distinct instance of the same concept. The definition already covers the general pattern.
- BT-017 (Ingestion Timestamp) was NOT added to Gold because it is dropped in the Gold table (replaced by BT-026 Promotion Timestamp).

### Validation

Glossary validated successfully via `python3 -m brightsmith.infra.glossary_validator validate` -- PASS.

---

## Human Review Decisions (2026-04-06)

**Reviewer:** Human reviewer (via @data-steward revision)
**Date:** 2026-04-06

### Decisions

| Term ID | Original Name | Decision | Details |
|---------|---------------|----------|---------|
| BT-018 | Cross-Institution Earnings Percentile Band | APPROVED as-is | No changes needed |
| BT-020 | Debt-to-Earnings Tier | APPROVED as-is | No changes needed |
| BT-021 | Earnings Growth Rate | RENAMED | Renamed to "Cross-Cohort Earnings Differential". Reviewer rationale: "Growth rate" is misleading -- the 1yr and 2yr earnings come from different cohorts, not the same individuals tracked over time. 44% of programs show negative values, contradicting the "growth" framing. Definition updated to lead with cross-cohort nature. Old name added to synonyms. |
| BT-022 | CIP Family Earnings Rank | APPROVED as-is | No changes needed |
| BT-023 | Program Value Index | CLARIFIED | Definition updated to explicitly note: "This is the mathematical inverse of the Debt-to-Earnings Ratio (BT-019); higher PVI = lower DTE." Reviewer rationale: downstream consumers seeing both debt_to_earnings_annual and program_value_index in the same table need this callout. |
| BT-024 | Confidence Tier | APPROVED as-is | No changes needed |
| BT-025 | Outcome Completeness | APPROVED as-is | No changes needed |
| BT-026 | Promotion Timestamp | APPROVED as-is | No changes needed |

### Summary

- 6 of 8 project-specific terms approved as-is
- 1 term renamed (BT-021: "Earnings Growth Rate" -> "Cross-Cohort Earnings Differential")
- 1 term definition clarified (BT-023: added inverse relationship callout to BT-019)
- All 8 terms moved from `proposed` to `approved` status
- Combined with auto-approved BT-019, all 9 Gold zone terms are now fully approved

### Post-Review Validation

Glossary re-validated successfully via `uv run python3 -m brightsmith.infra.glossary_validator validate` -- PASS.
