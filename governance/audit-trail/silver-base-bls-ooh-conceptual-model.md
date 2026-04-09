# Audit Trail: silver-base-bls-ooh Conceptual Model

**Agent:** @semantic-modeler
**Date:** 2026-04-07
**Spec:** docs/specs/silver-base-bls-ooh.md
**Mode:** Greenfield
**Stage:** Conceptual (1 of 3)
**Status:** PROPOSED -- awaiting human approval

## Inputs Read

- `docs/specs/silver-base-bls-ooh.md` -- full spec for Silver BLS OOH table
- `governance/business-glossary.json` -- terms BT-027 through BT-046 (BLS OOH domain)
- `governance/models/silver-base-college-scorecard-conceptual.md` -- pattern reference for entity structure and formatting
- `governance/domain-context.md` -- domain vocabulary, taxonomy systems, cross-source integration context
- `/Users/jcernauske/code/bright/brightsmith/CLAUDE.md` -- Brightsmith framework rules

## Modeling Decisions

### 1. Five entities identified: Occupation, SOC Major Group, Employment Projection, Compensation, Entry Requirements

**Rationale:** The spec defines a single-grain table (one row per SOC code) with distinct conceptual groupings: identity/classification, employment outlook, wages, and workforce readiness requirements. Separating these into entities clarifies the business semantics and makes optionality explicit (compensation is null for 23 occupations).

**Alternatives considered:**
- **Single Occupation entity with all attributes:** Rejected because it obscures the optional nature of compensation and the distinct business concepts (employment outlook vs. wages vs. entry requirements).
- **Separate Classification Flags entity:** Rejected because broad_occupation_flag and catchall_flag describe the nature of the occupation record itself, not independent business concepts.

### 2. Compensation modeled as one-to-zero-or-one

**Rationale:** 23 of 832 occupations have null wages. Making this relationship optional at the conceptual level signals to downstream consumers (especially Gold zone ERN stat) that wage data is not universal and must be handled.

### 3. Classification flags kept as Occupation attributes

**Rationale:** The broad_occupation_flag (7 codes) and catchall_flag (~46 codes) are boolean properties of the occupation record. They don't have independent identity, relationships, or lifecycle. Modeling them as separate entities would add complexity without business value.

### 4. Cross-source integration documented but not modeled

**Rationale:** The CIP-to-SOC crosswalk is a separate Silver spec. This model documents the integration role (SOC-side anchor) but does not include crosswalk entities. This matches the College Scorecard conceptual model's approach of documenting but not modeling the crosswalk.

### 5. No temporal entity

**Rationale:** Single projection cycle snapshot (2024-2034). Mirrors the College Scorecard decision. Source Load Date and Ingestion Timestamp are pipeline metadata, not business time dimensions.

## Stage Progression

| Stage | Status | Date | Reviewer |
|-------|--------|------|----------|
| Conceptual | PROPOSED | 2026-04-07 | Pending human review |
| Logical | Not started | -- | -- |
| Physical | Not started | -- | -- |
