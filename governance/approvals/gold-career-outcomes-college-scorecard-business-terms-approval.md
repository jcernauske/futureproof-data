# Approval Required: Business Glossary Terms (Gold Zone)
**Spec:** gold-career-outcomes-college-scorecard
**Produced by:** @data-steward
**Date:** 2026-04-06
**Artifact:** governance/business-glossary.json

## What You Are Approving

The @data-steward agent reviewed the Gold zone spec for the career outcomes consumable table and identified 9 new business terms describing the derived fields in this data product. Of those 9 terms:

- **1 was auto-approved** (BT-019: Debt-to-Earnings Ratio) because the concept is rooted in the Department of Education's Gainful Employment rule, a recognized domain standard. While our specific computation (total debt / annual earnings rather than annual payment / earnings) differs from the GE formula, the concept and its interpretation thresholds are well-established in higher education policy.
- **8 require your approval** because they are project-specific derived concepts created by the FutureProof Data project to power the career outcomes data product. These terms define how we compute, classify, and contextualize program outcomes for end users.

Additionally, 13 existing Silver-zone terms (BT-001 through BT-012, BT-014, BT-016) had their `used_in_models` updated to include "gold-career-outcomes-college-scorecard" since they are carried forward into the Gold table. No definitions were changed on existing terms.

## Terms Requiring Approval

### 1. BT-018: Cross-Institution Earnings Percentile Band (Category: Derived)

**Proposed Definition:**
"A distributional summary (25th, 50th, and 75th percentiles) of program-level median earnings across all institutions within the same CIP family. Computed via window functions (PERCENTILE_CONT) over the set of non-null program medians. These bands answer the question 'what range of earnings outcomes can I expect for a given field of study across different schools?' They are NOT within-cohort percentiles of individual earners -- they are percentiles of institutional program medians. CIP families with fewer than 3 non-null values have their bands set to null (insufficient sample)."

**Why this is project-specific:** This is the core analytical concept powering the FutureProof effort slider. The College Scorecard provides only program-level medians; the decision to aggregate these into CIP-family percentile bands, the choice of 25th/50th/75th percentiles, and the minimum sample size of 3 are all project design decisions. No external standard defines this aggregation pattern.

**What to look for:**
- Is it clear that these are "percentiles of medians" (a distribution of institutional outcomes), NOT percentiles of individual earners?
- Is the minimum sample size of 3 non-null values per CIP family appropriate, or should a higher threshold be used?
- Does the term name "Cross-Institution Earnings Percentile Band" adequately communicate this distinction?

---

### 2. BT-020: Debt-to-Earnings Tier (Category: Classification)

**Proposed Definition:**
"A categorical classification of the debt-to-earnings ratio into four buckets: 'Low' (ratio < 0.75, debt very manageable), 'Moderate' (0.75 to 1.5, typical range), 'High' (1.5 to 2.5, may require extended repayment), 'Very High' (ratio >= 2.5, debt significantly exceeds first-year earnings). Null when the underlying ratio is null. Threshold values are informed by Department of Education Gainful Employment guidance and industry convention."

**Why this is project-specific:** While the Gainful Employment rule establishes the concept of debt-to-earnings evaluation, our specific bucket thresholds (0.75, 1.5, 2.5) and tier names (Low/Moderate/High/Very High) are project design choices. The GE rule uses different thresholds (8% of total earnings, 20% of discretionary income as annual payment ratios) and a pass/fail framework rather than tiers.

**What to look for:**
- Are the four tier names (Low, Moderate, High, Very High) intuitive for end users?
- Are the threshold values (0.75, 1.5, 2.5) reasonable breakpoints? The spec notes these are "based on Department of Education guidance and industry convention."
- Should there be a fifth tier for extreme cases (e.g., ratio > 5.0)?

---

### 3. BT-021: Earnings Growth Rate (Category: Derived)

**Proposed Definition:**
"The rate of change in median earnings between the 1-year and 2-year post-completion measurement windows, computed as (earnings_2yr_median - earnings_1yr_median) / earnings_1yr_median. IMPORTANT: because the 1-year and 2-year figures come from different cohort measurement windows (not longitudinal tracking of the same individuals), negative values are valid and expected -- approximately 44% of programs show 2-year earnings below 1-year earnings due to cohort differences. Null when either earnings value is missing."

**Why this is project-specific:** This derived metric is a project invention. The College Scorecard does not compute or publish an earnings growth rate. More critically, the "growth" label is potentially misleading because the 1yr and 2yr figures represent different cohorts, not the same people tracked over time. The decision to compute and present this metric (with appropriate caveats) is a project design choice.

**What to look for:**
- Is "Earnings Growth Rate" the right name given that it does NOT represent true growth of the same cohort? Would "Cohort Earnings Differential" or "Cross-Cohort Earnings Change" be more accurate?
- Is the caveat about different cohort measurement windows prominent enough in the definition?
- Is this metric useful for end users despite the cohort difference limitation, or could it mislead?

---

### 4. BT-022: CIP Family Earnings Rank (Category: Derived)

**Proposed Definition:**
"A program's relative position within its CIP family based on 1-year median earnings, computed via PERCENT_RANK() window function partitioned by CIP family and ordered by earnings_1yr_median. Values range from 0.0 (lowest earner in the family) to 1.0 (highest earner). Null when earnings data is missing."

**Why this is project-specific:** This is a pipeline-derived positional metric. No external standard defines how to rank programs within a CIP family by earnings. The choice to use PERCENT_RANK (vs. RANK or NTILE), partition by CIP family (vs. credential level or other dimensions), and base it on 1-year earnings (vs. 2-year) are all project decisions.

**What to look for:**
- Is 1-year earnings the right basis for ranking, or should 2-year earnings also be considered?
- Is the 0.0-1.0 scale intuitive? Note that 0.0 means lowest and 1.0 means highest within the same discipline.
- Should the ranking exclude small cohort programs (small_cohort_flag = True)?

---

### 5. BT-023: Program Value Index (Category: Derived)

**Proposed Definition:**
"A return-on-investment proxy computed as earnings_1yr_median / debt_median. Higher values indicate better value -- more earnings relative to debt incurred. Null when either earnings or debt data is missing. This is a simplified ROI measure that does not account for time value of money, opportunity cost, or non-financial benefits of education."

**Why this is project-specific:** This is a novel project-invented metric. While ROI concepts exist broadly in education policy, our specific formula (simple ratio of earnings to debt) and the name "Program Value Index" are project design choices. It is intentionally simple, trading precision for interpretability.

**What to look for:**
- Is "Program Value Index" the right name? Alternatives: "Earnings-to-Debt Ratio", "Simple ROI Proxy", "Program Affordability Score."
- Is the formula clear enough? It is the inverse of debt-to-earnings ratio (BT-019), which could be confusing. Should the definition explicitly note this inverse relationship?
- Are the limitations (no time value of money, no opportunity cost) adequately flagged?

---

### 6. BT-024: Confidence Tier (Category: Classification)

**Proposed Definition:**
"A four-level data quality classification assigned to every row in the career outcomes table, based on cohort size and data availability. Tiers: 'high' (large cohort with both earnings and debt data), 'medium' (large cohort with either earnings or debt), 'low' (small cohort with some outcome data), 'insufficient' (no earnings or debt data available). Determines how much trust downstream consumers should place in a program's outcome metrics. Every row receives a tier -- there are no nulls."

**Why this is project-specific:** This classification is entirely invented by the FutureProof project. The Department of Education does not assign confidence levels to its data. The specific tier names, the criteria for each tier (combination of cohort size and data availability), and the decision to classify rather than filter are all project design choices.

**What to look for:**
- Are the four tier names (high, medium, low, insufficient) clear and actionable for end users?
- Is the criteria mapping intuitive? Specifically: a large cohort with only earnings OR debt data gets "medium", while a small cohort with the same data availability gets "low" -- is cohort size the right differentiator?
- Should the product UI hide "insufficient" tier programs by default, or show them with appropriate warnings?

---

### 7. BT-025: Outcome Completeness (Category: Derived)

**Proposed Definition:**
"A numeric score representing the proportion of core outcome fields (earnings_1yr_median, earnings_2yr_median, debt_median) that are non-null for a given program row. Computed as count of non-null fields divided by 3. Possible values are exactly 0.0, 0.33, 0.67, or 1.0."

**Why this is project-specific:** This is a pipeline convenience metric. The choice of which three fields constitute "core outcomes," the equal weighting of all three, and the decision to express completeness as a proportion are project choices.

**What to look for:**
- Should all three outcome fields be weighted equally? One could argue that 1-year earnings is more important than 2-year earnings for career guidance.
- Is the discrete value set (0.0, 0.33, 0.67, 1.0) useful, or would a finer-grained score be better?
- Is "Outcome Completeness" the right name, or would "Data Availability Score" be clearer?

---

### 8. BT-026: Promotion Timestamp (Category: Temporal)

**Proposed Definition:**
"The timestamp recording when a row was promoted from the Silver zone to the Gold zone consumable table. Used for pipeline auditing, data freshness tracking, and debugging. Generated at Gold zone promotion time. Analogous to the Silver zone's ingested_at field but marks the transition to the consumable layer."

**Why this is project-specific:** This is a pipeline-generated audit field, analogous to BT-017 (Ingestion Timestamp) in the Silver zone. It records when data was promoted to Gold, not when it was produced or measured.

**What to look for:**
- Is the distinction between this timestamp (Gold promotion time), Source Load Date (raw fetch time), and Ingestion Timestamp (Silver processing time) clear?
- Is "Promotion Timestamp" the right name, or would "Gold Zone Timestamp" be less jargon-heavy for non-pipeline users?

---

## Summary Table

| Term ID | Term Name | Category | Source | Key Question for Reviewer |
|---------|-----------|----------|--------|--------------------------|
| BT-018 | Cross-Institution Earnings Percentile Band | Derived | project-specific | Is the "percentiles of medians" concept clearly communicated? |
| BT-019 | Debt-to-Earnings Ratio (Annual) | Measurement | domain-standard | AUTO-APPROVED (Gainful Employment concept) |
| BT-020 | Debt-to-Earnings Tier | Classification | project-specific | Are the 4 tier thresholds (0.75/1.5/2.5) appropriate? |
| BT-021 | ~~Earnings Growth Rate~~ Cross-Cohort Earnings Differential | Derived | project-specific | RENAMED per reviewer feedback (see below) |
| BT-022 | CIP Family Earnings Rank | Derived | project-specific | Is 1yr earnings the right ranking basis? |
| BT-023 | Program Value Index | Derived | project-specific | CLARIFIED per reviewer feedback (see below) |
| BT-024 | Confidence Tier | Classification | project-specific | Are the tier criteria intuitive and actionable? |
| BT-025 | Outcome Completeness | Derived | project-specific | Should all 3 outcome fields be equally weighted? |
| BT-026 | Promotion Timestamp | Temporal | project-specific | Is the name clear relative to other pipeline timestamps? |

## Auto-Approved Term (No Action Needed)

BT-019 (Debt-to-Earnings Ratio, Annual) was auto-approved because the debt-to-earnings concept is established in federal higher education policy through the Gainful Employment rule. The Department of Education uses debt-to-earnings evaluation as a formal program accountability mechanism. While our specific formula differs from the GE calculation, the concept and its interpretive framework are authoritative domain standards.

## Existing Terms Updated (No Action Needed)

The following 13 Silver-zone terms had "gold-career-outcomes-college-scorecard" added to their `used_in_models` array. No definitions were changed:

BT-001 UNITID, BT-002 Institution Name, BT-003 CIP Code, BT-004 Program Name, BT-005 CIP Family, BT-006 CIP Family Name, BT-007 Credential Level, BT-009 Median Earnings 1-Year, BT-010 Median Earnings 2-Year, BT-011 Median Debt at Completion, BT-012 IPEDS Completions Count, BT-014 Small Cohort Flag, BT-016 Source Load Date.

## Impact If Rejected

If any of these terms are rejected:

- The rejected term remains in "proposed" status and cannot be referenced by downstream governance artifacts (data contracts, grounding documents, CDE mappings).
- The @data-steward agent will revise the definition based on your feedback and resubmit.
- This does **not** block implementation of the Gold transformer code, but it **does** block the @doc-generator from producing the final data dictionary and data contract for the `consumable.career_outcomes` table.
- The governance completeness checklist cannot be marked complete until all terms are approved.

## How to Respond

- **Approve all:** "Approved" -- all 8 terms move to `approved` status.
- **Approve some, reject others:** Specify which terms to approve and provide feedback on the ones to revise.
- **Reject all:** Provide feedback on what needs to change.

For any rejected term, please indicate whether the issue is with the name, the definition, the thresholds, or the categorization, so the @data-steward can make targeted revisions.

---

## Human Review Decisions (2026-04-06)

**Reviewer feedback received and applied.** Of the 8 project-specific terms submitted for review:

- **6 approved as-is:** BT-018 (Cross-Institution Earnings Percentile Band), BT-020 (Debt-to-Earnings Tier), BT-022 (CIP Family Earnings Rank), BT-024 (Confidence Tier), BT-025 (Outcome Completeness), BT-026 (Promotion Timestamp).
- **1 renamed:** BT-021 renamed from "Earnings Growth Rate" to **"Cross-Cohort Earnings Differential"**. Reviewer rationale: "Growth rate" is misleading because the 1yr and 2yr earnings come from different cohorts, not the same individuals tracked over time. 44% of programs show negative values, which contradicts the "growth" framing. The old name "Earnings Growth Rate" has been added to the synonyms list. The definition was updated to lead with the cross-cohort nature of the comparison.
- **1 clarified:** BT-023 (Program Value Index) definition updated to explicitly note: "This is the mathematical inverse of the Debt-to-Earnings Ratio (BT-019); higher PVI = lower DTE." Reviewer rationale: downstream consumers seeing both `debt_to_earnings_annual` and `program_value_index` in the same table need this callout to avoid confusion.

All 8 project-specific terms now have `approval_status: approved` in the glossary. Combined with the 1 auto-approved domain-standard term (BT-019), all 9 Gold zone terms are fully approved.
