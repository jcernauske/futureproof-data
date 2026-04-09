# Audit Trail: Gold Career Outcomes Conceptual Model

**Spec:** gold-career-outcomes-college-scorecard
**Agent:** @semantic-modeler
**Stage:** Conceptual Model (Stage 1 of 3)
**Date:** 2026-04-06
**Mode:** Greenfield

---

## Mode Detection

| Check | Result |
|-------|--------|
| Target table `consumable.career_outcomes` exists in Iceberg catalog? | No |
| Source code exists at `src/gold/`? | No |
| **Mode** | **Greenfield** |

## Stage Progression

| Stage | Status | Timestamp |
|-------|--------|-----------|
| Conceptual | PROPOSED | 2026-04-06 |
| Logical | NOT STARTED | -- |
| Physical | NOT STARTED | -- |

## Inputs Consulted

| Artifact | Path | Purpose |
|----------|------|---------|
| Gold spec | docs/specs/gold-career-outcomes-college-scorecard.md | Requirements, schema, derivation rules |
| Business glossary | governance/business-glossary.json | Term IDs BT-001 through BT-026 |
| Silver conceptual model | governance/models/silver-base-college-scorecard-conceptual.md | Continuity with upstream model |
| Domain context | governance/domain-context.md | Domain vocabulary, temporal patterns, edge cases |
| Brightsmith CLAUDE.md | /Users/jcernauske/code/bright/brightsmith/CLAUDE.md | Framework rules for data models |
| Silver-Gold workflow | /Users/jcernauske/code/bright/brightsmith/docs/workflows/silver-gold-pipeline.md | Greenfield pipeline steps |

## Design Decisions

### 1. Entity Decomposition Strategy
**Decision:** Decompose the single wide Gold table into 6 conceptual entities based on business concern.
**Rationale:** The physical table is a single denormalized fact, but the conceptual model must communicate distinct business concepts to stakeholders. The decomposition follows the spec's own section organization: identity fields, core outcomes, percentile bands, financial ratios, relative position, and data quality context.
**Alternatives:** (a) Model as a single "Career Outcome" entity with many attributes -- rejected because it obscures the distinct analytical dimensions. (b) Star schema with separate dimension tables -- rejected because the query pattern always needs everything inline.

### 2. CIP Family as Shared Dimension
**Decision:** CIP Family appears as its own entity linked to both Program Identity and Earnings Percentile Band.
**Rationale:** CIP Family serves a dual role: classification context for the program (inherited from Silver) and partition key for percentile band computation. Making it a distinct entity communicates this dual role.

### 3. Financial Assessment as Grouped Entity
**Decision:** Group all five financial metrics (BT-019 through BT-023) into a single "Financial Assessment" entity.
**Rationale:** All five share the same null propagation pattern (null when earnings or debt inputs are missing) and the same business purpose (program evaluation). Splitting them into five entities would create entity proliferation without adding clarity.

### 4. Data Confidence as Mandatory
**Decision:** Data Confidence is the only entity with a mandatory (non-null) relationship to Career Outcome.
**Rationale:** The spec requires confidence_tier on every row with no nulls. This is a deliberate business decision: every program must carry a quality signal, even if that signal is "insufficient."

### 5. Silver-to-Gold Entity Consolidation
**Decision:** Silver's separate entities (Earnings 1yr, Earnings 2yr, Debt Outcome, Completions Measure) are absorbed into Career Outcome at the Gold level.
**Rationale:** In Silver, separating earnings windows was justified by independent suppression patterns. In Gold, the consumable layer prioritizes query convenience. The business concepts remain tracked via distinct business terms (BT-009, BT-010, BT-011, BT-012) even though they share a physical row.

## Human Feedback Incorporated
None yet -- this is the initial proposal.
