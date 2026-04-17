# Human Approval: Silver Base O*NET Experience Conceptual Model

**Spec:** docs/specs/onet-experience-requirements.md
**Artifact:** governance/models/silver-base-onet-experience-conceptual.md
**Stage:** Conceptual Model (Stage 1 of 3)
**Author:** @semantic-modeler
**Date:** 2026-04-16
**Status:** APPROVED
**Approved By:** Jeff Cernauske
**Approved Date:** 2026-04-16
**Conditions:** none

---

## Context

`docs/specs/onet-experience-requirements.md` adds a new experience-gating layer to the career evolution tree. Its governance re-review (2026-04-16 APPROVED) made semantic modeling a Phase 1 gate: three Silver data models (conceptual, logical, physical) plus an addendum to the Gold engine physical model must exist and be human-approved BEFORE any Bronze or Silver code is written. This is the first of those four artifacts.

Three open decisions (tier thresholds, "Over 10 years" midpoint, multi-detail aggregation) were resolved ahead of time in `governance/approvals/onet-experience-requirements-open-decisions.md` (approved 2026-04-16 by Jeff Cernauske). Those values flow directly into this conceptual model's business attributes -- Experience Tier thresholds and the Experience Years Typical derivation both cite the approval file.

Two new business glossary terms (BT-117 Related Work Experience, BT-118 Experience Tier) must also be approved by `bs:data-steward` -- the conceptual model references them but does not author them.

## What Is Being Proposed

A conceptual data model for the `base.onet_experience_profiles` Silver zone table -- the first of three modeling stages (conceptual, logical, physical) plus a Gold physical-model addendum that must all be approved before implementation begins.

The model defines one new primary entity plus two classifier/context entities and their relationships to existing O*NET Silver entities:

1. **Experience Profile** -- the new primary entity, one per BLS SOC occupation, carrying the typical prior work experience required to enter that occupation
2. **Experience Tier** -- a four-value classifier (`entry` / `early` / `mid` / `senior`) derived from Experience Years Typical
3. **Occupation** -- reference from `silver-base-onet` (context only, not re-specified)
4. **Career Transition** -- reference from `silver-base-onet` (context only, not re-specified)

Plus six business attributes on Experience Profile: Occupation Identifier, Experience Years Typical, Experience Tier, Experience Distribution, Provenance (suppression), and Provenance (detail count).

## Key Design Decisions for Review

### 1. Single-entity model, not a star
Unlike `silver-base-onet` which has four tables (a dimensional `Occupation` and three fact-like children), this spec adds exactly one new entity. Experience data is conceptually a single attribute bundle on each occupation, not a separate grain. A standalone Silver table (rather than additional columns on `base.onet_occupations`) keeps the existing `onet_occupations` table unchanged and isolates the new concern.

**Alternative considered:** Extend `base.onet_occupations` with experience columns. Rejected because it mixes dimensional occupation identity with measured experience attributes, forces a schema change on an already-approved Silver table, and couples this spec's release cadence to any other future changes on `onet_occupations`.

### 2. Experience Tier as a classifier, not a dimension table
The four tiers are a fixed enumeration derived deterministically from `experience_years_typical` using human-approved thresholds. Modeling as a classifier attribute (not a separate lookup entity) keeps the model flat and avoids a dimension table whose only value is storing four rows.

### 3. Preserve the full category distribution
`Experience Distribution` retains all 11 RW percent-frequencies as JSON -- optional to consume but essential for auditability. Downstream analysts can verify the weighted-median derivation or recompute alternative summaries without re-running Bronze.

### 4. Tier thresholds and "Over 10 years" midpoint are human-approved
The model explicitly cites `governance/approvals/onet-experience-requirements-open-decisions.md` as the source of approval for: tier boundaries (`entry 0-1`, `early 1-4`, `mid 4-8`, `senior 8+`), the "Over 10 years" midpoint (12.0 years), and multi-detail aggregation (unweighted mean). None of these are being re-litigated at modeling time.

### 5. Boundaries are inclusive-at-lower, exclusive-at-upper (except `senior`)
Ranges are half-open: `entry = [0, 1]`, `early = (1, 4]`, `mid = (4, 8]`, `senior = (8, infinity)`. A value of exactly 4 is `early`, not `mid`. This avoids boundary ambiguity and matches the SQL expressions in the open-decisions approval file.

### 6. Cross-source relationship to `consumable.career_branches` shown but not embedded
The Experience Profile -> Career Transition "gates" relationship is shown in the conceptual diagram because it is the primary downstream consumer, but the Gold schema diff is documented separately in the Gold physical-model addendum (`governance/models/gold-futureproof-engine-physical.md`), not inline here.

## Business Terms Referenced

Stored as IDs only (per governance policy -- definitions live in `governance/business-glossary.json`).

| Term ID | Name | Used In |
|---------|------|---------|
| BT-015 | Record ID | Experience Profile (primary key) |
| BT-016 | Source Load Date | Experience Profile (provenance) |
| BT-017 | Ingestion Timestamp | Experience Profile (provenance) |
| BT-027 | BLS SOC Code | Experience Profile (natural key) |
| BT-060 | Career Transition (Similarity) | Career Transition (context entity) |
| BT-062 | Recommend Suppress | Experience Profile (provenance) |
| BT-063 | Multi-Detail Aggregation | Experience Profile (provenance) |
| BT-117 | Related Work Experience | Experience Profile (primary concept) -- **new term, pending data-steward approval** |
| BT-118 | Experience Tier | Experience Profile (classifier) -- **new term, pending data-steward approval** |

## What Happens Next

- **If APPROVED:** @semantic-modeler proceeds to the logical model (Stage 2), adding attributes, keys, data types (domains), nullability, and derivation rules.
- **If CHANGES REQUESTED:** @semantic-modeler revises this conceptual model based on feedback and resubmits.
- **If REJECTED:** The modeling approach is reconsidered from scratch, potentially re-opening the open decisions captured in the open-decisions approval file.

## Approval

To approve, set the status in the conceptual model file to `APPROVED` and note any conditions:

```
**Status:** APPROVED
**Approved By:** [name]
**Approved Date:** [date]
**Conditions:** [any conditions or none]
```
