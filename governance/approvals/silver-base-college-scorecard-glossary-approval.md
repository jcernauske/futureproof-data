# Approval Required: Business Glossary Terms
**Spec:** silver-base-college-scorecard
**Produced by:** @data-steward
**Date:** 2026-04-06
**Artifact:** governance/business-glossary.json

## What You Are Approving

The @data-steward agent reviewed the Silver zone spec for the College Scorecard base table and identified 17 business terms that describe the fields in this dataset. Of those 17 terms:

- **12 were auto-approved** because they come from established external standards (IPEDS, NCES, U.S. Department of Education). These terms have official definitions that our project adopts as-is.
- **5 require your approval** because they are project-specific -- they were created by the FutureProof Data project team to describe fields or concepts that do not have an external standard definition. You are being asked to confirm that these 5 terms are well-defined, necessary, and accurate.

## Terms Requiring Approval

### 1. BT-013: Privacy Suppression (Category: Regulatory)

**Proposed Definition:**
"The U.S. Department of Education's practice of replacing outcome data (earnings, debt) with null values when program cohort sizes are too small to protect student privacy under FERPA. The effective threshold is approximately 30 completers: programs with 30+ completers have 88.7% earnings data availability, while programs below 10 completers have under 11%. Suppressed values appear as null in the dataset."

**Why this is project-specific:** While FERPA suppression is a real government practice, the Department of Education does not publish a formal glossary term for it. The specific threshold observations (88.7% availability above 30 completers, under 11% below 10) come from our own exploratory data analysis of the College Scorecard dataset. This definition packages external regulatory practice together with our project's empirical findings, which is why it cannot be auto-approved as a pure external standard.

**What to look for:**
- Is the 30-completer threshold the right number to cite? The government does not publish the exact cutoff, so our definition describes what we observed in the data.
- Is "privacy suppression" the right name for this concept, or does your team use different terminology?
- Are the data availability percentages (88.7% and 11%) helpful context, or do they make the definition too specific to one dataset snapshot?

---

### 2. BT-014: Low Confidence Outcomes (Category: Derived)

**Proposed Definition:**
"A derived boolean flag indicating that a program has fewer than 30 completers (completions_count_1 < 30), meaning its outcome data is likely subject to privacy suppression and should be interpreted with caution. Programs are flagged but not excluded from the dataset."

**Why this is project-specific:** This field does not exist in the source data. The FutureProof team created it as a convenience flag to help downstream consumers quickly identify programs whose earnings and debt figures may be missing or unreliable due to small cohort sizes. The 30-completer threshold and the decision to flag (rather than exclude) these programs are both project design choices.

**What to look for:**
- Is "Low Confidence Outcomes" the right name? It describes programs where outcome data (earnings, debt) may be suppressed or unreliable -- but the flag itself is about program size, not data quality directly. Would "Small Program Flag" or "Low Completions Flag" be clearer?
- Is the 30-completer threshold appropriate for your use cases?
- Is it correct that flagged programs should remain in the dataset rather than being excluded?

---

### 3. BT-015: Record ID (Category: Derived)

**Proposed Definition:**
"A deterministic hash-based identifier computed from the grain fields (unitid, cipcode, credlev) using the Brightsmith compute_grain_id() function. Provides a stable, unique surrogate key for each row in the base table. Prefixed with 'cs' for the College Scorecard domain."

**Why this is project-specific:** This is a technical surrogate key that the pipeline generates. It does not come from any source system. The hashing approach, the choice of grain fields, and the "cs" prefix are all internal project decisions.

**What to look for:**
- Does it make sense that the unique identity of a record is the combination of institution (unitid), program (cipcode), and credential level (credlev)?
- The "cs" prefix is a project convention to distinguish College Scorecard records from records in other domains. Is this clear enough?
- This is the most technical of the five terms. If you are a business reviewer, the key question is: "Does each row represent one program at one school at one credential level?" If yes, this ID is correct.

---

### 4. BT-016: Source Load Date (Category: Temporal)

**Proposed Definition:**
"The date on which the source data was loaded into the pipeline's raw zone. Represents when the data was fetched from the U.S. Department of Education, not when the underlying outcomes were measured."

**Why this is project-specific:** This field tracks pipeline operations, not source data content. The distinction between "when we fetched the data" and "when the outcomes were measured" is a project-specific concept that helps users avoid misinterpreting temporal data.

**What to look for:**
- Is the distinction between "load date" and "measurement date" clear enough? This is important because earnings data may be from cohorts measured years before the load date.
- Is "Source Load Date" the right name, or would "Data Fetch Date" or "Pipeline Load Date" be less ambiguous?

---

### 5. BT-017: Ingestion Timestamp (Category: Temporal)

**Proposed Definition:**
"The timestamp recording when a row was written to the Silver zone base table. Used for pipeline auditing and data freshness tracking. Generated at Silver zone transformation time."

**Why this is project-specific:** This is a pipeline-generated audit field. It records when the data transformation happened, not when the data was originally produced. It exists for operational tracking and debugging.

**What to look for:**
- Is the distinction between this timestamp (Silver zone write time) and the Source Load Date (raw zone fetch time) clear? They serve different purposes -- Source Load Date tells you when data entered the pipeline; Ingestion Timestamp tells you when it was processed into its clean form.
- Is "Ingestion Timestamp" clear enough, or could it be confused with the raw zone load time?

---

## Summary Table

| Term ID | Term Name | Category | Key Question for Reviewer |
|---------|-----------|----------|--------------------------|
| BT-013 | Privacy Suppression | Regulatory | Is the ~30 completer threshold and the empirical stats appropriate to include? |
| BT-014 | Low Confidence Outcomes | Derived | Is this the right name and threshold for flagging small programs? |
| BT-015 | Record ID | Derived | Does institution + program + credential level correctly define a unique record? |
| BT-016 | Source Load Date | Temporal | Is "when we fetched the data" clearly distinguished from "when outcomes were measured"? |
| BT-017 | Ingestion Timestamp | Temporal | Is it clear this means "Silver processing time" not "raw ingestion time"? |

## Auto-Approved Terms (No Action Needed)

For reference, these 12 terms were auto-approved because they adopt definitions from IPEDS, NCES, or the U.S. Department of Education without modification:

BT-001 UNITID, BT-002 Institution Name, BT-003 CIP Code, BT-004 Program Name, BT-005 CIP Family, BT-006 CIP Family Name, BT-007 Credential Level, BT-008 Credential Description, BT-009 Median Earnings 1-Year Post-Completion, BT-010 Median Earnings 2-Year Post-Completion, BT-011 Median Debt at Completion, BT-012 IPEDS Completions Count.

## Impact If Rejected

If any of these terms are rejected, the following happens:

- The rejected term remains in "proposed" status and cannot be referenced by downstream governance artifacts (data contracts, grounding documents, CDE mappings).
- The @data-steward agent will need to revise the definition based on your feedback and resubmit.
- This does **not** block implementation of the transformer code, but it **does** block the @doc-generator from producing the final data dictionary and data contract for the `base.college_scorecard` table.
- The governance completeness checklist cannot be marked complete until all terms are approved.

## How to Respond

- **Approve all:** "Approved" -- all 5 terms move to `approved` status.
- **Approve some, reject others:** Specify which terms to approve and provide feedback on the ones to revise.
- **Reject all:** Provide feedback on what needs to change.

For any rejected term, please indicate whether the issue is with the name, the definition, or both, so the @data-steward can make targeted revisions.
