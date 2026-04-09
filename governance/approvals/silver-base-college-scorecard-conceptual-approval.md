# Approval Required: Conceptual Model
**Spec:** silver-base-college-scorecard
**Produced by:** @semantic-modeler
**Date:** 2026-04-06
**Artifact:** governance/models/silver-base-college-scorecard-conceptual.md

## What You Are Approving

This is the conceptual data model for the Silver zone `base.college_scorecard` table. It describes how we think about the College Scorecard data in business terms -- what the main "things" (entities) are, and how they relate to each other.

This model does not define column names or data types. It defines the business concepts that the physical table will represent. Getting this right matters because every downstream product (Gold zone reports, AI-ready data, debt-to-earnings ratios) will inherit these concepts.

The dataset covers U.S. bachelor's degree programs at postsecondary institutions, with information about graduate earnings, student debt, and program completion counts. The data comes from the U.S. Department of Education's College Scorecard initiative.

## The 8 Entities: What They Represent

| # | Entity | What It Represents | Example |
|---|--------|--------------------|---------|
| 1 | **Institution** | A college or university campus, identified by its federal IPEDS ID. | Stanford University (UNITID 110635) |
| 2 | **Academic Program** | A field of study classified by a CIP code, independent of where it is offered or at what level. | Business Administration (CIP 52.0201) |
| 3 | **CIP Family** | A broad discipline grouping derived from the first two digits of the CIP code. Used for high-level aggregation. | "52" = Business, Management, Marketing |
| 4 | **Credential Type** | The level of degree or certificate awarded. In the current dataset, only Bachelor's Degree (level 3) is present. | Bachelor's Degree |
| 5 | **Program Offering** | The central entity: a specific program at a specific institution at a specific credential level. This is the fundamental unit of analysis -- every row in the table is one program offering. | Business Administration at Stanford, Bachelor's level |
| 6 | **Earnings Outcome** | Post-graduation median earnings for completers of a program offering, measured at 1-year and 2-year windows. May be missing due to privacy suppression. | Median earnings of $58,200 at 1 year post-completion |
| 7 | **Debt Outcome** | Median cumulative federal loan debt for graduates of a program offering. May be missing due to privacy suppression. | Median debt of $27,000 at graduation |
| 8 | **Completions Measure** | The count of students who completed a program offering, reported in two measurement windows. Drives the Small Cohort Flag that indicates whether outcome data is likely suppressed. | 45 completers (first major count) |

## How They Relate to Each Other

The model is structured like a star, with **Program Offering** at the center:

- An **Institution** offers many **Program Offerings** (one-to-many)
- An **Academic Program** is offered as many **Program Offerings** across different institutions (one-to-many)
- A **Credential Type** applies to many **Program Offerings** (one-to-many)
- A **CIP Family** classifies many **Academic Programs** (one-to-many) -- this captures the 2-digit to 6-digit hierarchy in the CIP taxonomy
- Each **Program Offering** may have one **Earnings Outcome** or none (one-to-zero-or-one) -- "none" means the data was suppressed for privacy
- Each **Program Offering** may have one **Debt Outcome** or none (one-to-zero-or-one) -- same suppression logic
- Each **Program Offering** has exactly one **Completions Measure** (one-to-one)

The key insight is that earnings and debt are optional (zero-or-one) because the Department of Education suppresses outcome data when fewer than approximately 30 students completed the program, to protect student privacy under FERPA.

## Key Decisions Made

These are the modeling choices where the agent exercised judgment. These are the items most worth scrutinizing.

1. **Program Offering as the central entity.** The raw data has one row per institution-program-credential combination. The modeler chose to name this concept "Program Offering" and make it the hub of all relationships. This is a natural fit for the data grain, but reviewers should confirm this term matches how your team thinks about the data. Alternative names could have been "Program Instance" or "Institution-Program."

2. **Earnings and Debt modeled as separate entities rather than attributes.** Earnings and debt values could have been treated as simple columns on Program Offering. Instead, they are separate entities with optional (zero-or-one) cardinality. The rationale is that this makes the privacy suppression pattern explicit in the model -- these outcomes may or may not exist. It also supports downstream Gold zone calculations like debt-to-earnings ratios, which need both present. Reviewers should consider whether this separation adds useful clarity or unnecessary complexity for your use cases.

3. **Completions Measure as a separate entity.** Completion counts could also have been attributes of Program Offering. The modeler separated them because completions drive the Small Cohort Flag and the privacy suppression behavior -- they are the "gatekeeper" for whether outcome data exists. Reviewers should assess whether this distinction matters for how you will use the data.

4. **CIP Family as its own entity.** The 2-digit CIP family code is derived from the full CIP code (just the first two characters). The modeler gave it entity status because it is used for aggregation and filtering in downstream products. This adds a small hierarchy (CIP Family classifies Academic Program). If your downstream use cases do not need this grouping level, it could be simplified.

5. **Credential Type kept as an entity despite having only one value.** The current dataset contains only Bachelor's Degree (credential level 3). The modeler kept Credential Type as a separate entity for future extensibility -- if the project later ingests Associate's or Master's degree data, the model will not need restructuring. The trade-off is that it adds an entity that currently has a single row.

6. **No time dimension entity.** The current dataset is a point-in-time snapshot with no historical tracking. Dates (source load date, ingestion timestamp) are treated as attributes on Program Offering, not as a separate time dimension. The modeler noted this may need to change if historical tracking is added later.

## What To Look For

### For Business Users and Data Stewards
- Do the 8 entity names match how your team talks about this data? Would you call it a "Program Offering" or something else?
- Are the plain-English descriptions accurate? Do they match your understanding of what the College Scorecard data contains?
- Is the privacy suppression concept (outcomes missing for small programs) correctly represented?
- Are there any business concepts missing that you would expect to see? For example, is there a concept of "institution type" (public vs. private) that should be an entity?

### For the Conceptual Model Specifically
- Do the entity types match how you think about this data?
- Are the relationships correct? In particular:
  - Is it true that every program offering belongs to exactly one institution, one academic program, and one credential type?
  - Is the optional nature of earnings and debt outcomes correctly captured?
  - Does the one-to-one relationship between program offering and completions measure make sense, or could a program offering have zero completions records?
- Is anything missing? The model explicitly excludes the CIP-to-SOC crosswalk (a separate spec) and Gold zone products (downstream consumers). Are there other concepts that should be in scope?

### For Technical Reviewers
- The grain is defined as `unitid x cipcode x credlev`. The model captures this through the three parent entities (Institution, Academic Program, Credential Type) converging on Program Offering. Confirm this correctly represents the data's natural key.
- The 1-year and 2-year earnings are attributes of a single Earnings Outcome entity, not separate entities. This means they are always present or absent together. Verify this matches the actual data behavior (do they suppress independently or together?).
- The `md_earn_wne` field (institution-level median earnings) is confirmed dropped per spec -- it is structurally empty at the field-of-study grain. The model does not include it.

## Proposed Artifact

The full conceptual model is at `governance/models/silver-base-college-scorecard-conceptual.md`. Below is a summary of its structure:

**8 entities** organized around a central Program Offering, with three "dimension" entities (Institution, Academic Program, Credential Type) and one classification entity (CIP Family) feeding in, and three "outcome/measure" entities (Earnings Outcome, Debt Outcome, Completions Measure) hanging off.

**7 relationships**, all flowing through Program Offering:
- 3 mandatory inbound (institution, program, credential type)
- 1 classification (CIP family to academic program)
- 2 optional outbound (earnings and debt outcomes -- optional due to privacy suppression)
- 1 mandatory outbound (completions measure)

**6 documented modeling decisions** with rationale for each.

**4 key business concepts** explained: grain definition, privacy suppression, small cohort flag, CIP code hierarchy.

**Scope boundaries** clearly stated: Silver zone only, no Bronze modeling, no Gold zone products, no CIP-to-SOC crosswalk.

## Impact If Rejected

If this conceptual model is rejected, the following downstream steps are blocked:

- **Logical model** -- cannot proceed without an approved conceptual model
- **Physical model and table creation** -- depends on the logical model
- **DQ rule writing** -- rules reference entities and relationships from the model
- **Data contract generation** -- contracts describe the schema that the model defines
- **Gold zone specs** -- downstream products depend on a stable Silver base table

The @semantic-modeler would need to revise the conceptual model based on review feedback and resubmit for approval. Specific feedback on which entities or relationships need changes will enable the fastest turnaround.ls
