# Audit Trail: Gold Career Outcomes Logical Model

**Spec:** gold-career-outcomes-college-scorecard
**Agent:** @semantic-modeler
**Stage:** Logical Model (Stage 2 of 3)
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
| Logical | PROPOSED | 2026-04-06 |
| Physical | NOT STARTED | -- |

## Inputs Consulted

| Artifact | Path | Purpose |
|----------|------|---------|
| Gold spec | docs/specs/gold-career-outcomes-college-scorecard.md | Requirements, schema, derivation rules, all 30+ field definitions |
| Approved conceptual model | governance/models/gold-career-outcomes-college-scorecard-conceptual.md | Entity decomposition, relationships, scope boundaries |
| Business glossary | governance/business-glossary.json | Term IDs BT-001 through BT-026 |
| Silver logical model | governance/models/silver-base-college-scorecard-logical.md | Attribute continuity, type domain conventions, Silver-to-Gold mapping |
| Silver data contract | governance/data-contracts/base-college-scorecard.yaml | CDE designations, constraint patterns, quality thresholds |
| Conceptual approval doc | governance/approvals/gold-career-outcomes-college-scorecard-conceptual-approval.md | Design decisions approved at conceptual stage |
| Brightsmith CLAUDE.md | /Users/jcernauske/code/bright/brightsmith/CLAUDE.md | Framework rules for data models |
| Silver-Gold workflow | /Users/jcernauske/code/bright/brightsmith/docs/workflows/silver-gold-pipeline.md | Greenfield pipeline steps |

## Design Decisions

### 1. Single Denormalized Table (Confirmed from Conceptual)
**Decision:** All 6 conceptual entities flatten into a single `consumable.career_outcomes` table with 30 attributes.
**Rationale:** Confirmed at conceptual stage. The consumable layer optimizes for the primary query pattern. The logical model groups attributes by conceptual entity for semantic clarity but acknowledges the physical denormalization.

### 2. Attribute Type Domain Assignments
**Decision:** Used the same 6 type domains as the Silver logical model (identifier, text, numeric, boolean, date, timestamp).
**Rationale:** Consistency across zones. No new domain types needed -- Gold's derived metrics (ratios, ranks, tiers) fit within existing numeric and text domains.

### 3. CDE Designations for Percentile Bands and Debt-to-Earnings
**Decision:** All 6 percentile band attributes and the debt_to_earnings_annual ratio are marked as CDE.
**Rationale:** Percentile bands power the effort slider, the primary product feature. The debt-to-earnings ratio is the core affordability metric related to Gainful Employment guidance. These are critical data elements whose corruption would directly impact user-facing outcomes.
**Alternatives:** Could have limited CDE to only the p25/p75 pairs (not all 6). Included all because each independently contributes to the effort slider across different outcome dimensions (1yr earnings, 2yr earnings, debt).

### 4. Rename completions_count_1 to completions_count
**Decision:** Simplified the field name for the consumable layer since completions_count_2 is dropped.
**Rationale:** In the consumable layer, there is only one completions measure. The "_1" suffix is confusing without its counterpart. The business term (BT-012) still references IPEDSCOUNT1 for traceability.

### 5. Null-Safe Derivation Rules Throughout
**Decision:** Every derived field explicitly documents its null propagation behavior.
**Rationale:** ~56% of rows have both earnings fields null. Derived fields must handle this pervasive nullability gracefully. Documenting the null behavior at the logical level ensures the physical implementation and DQ rules are consistent.

### 6. Confidence Tier as the Only Mandatory Derived Field
**Decision:** confidence_tier is NOT NULL while all other derived fields are NULLABLE.
**Rationale:** Per conceptual model decision #4 -- every row must carry a quality signal. The tier serves as the universal "should I trust this row?" indicator for downstream consumers.

### 7. Earnings Growth Rate Named as Cross-Cohort Differential
**Decision:** The logical model uses earnings_growth_rate as the attribute name (per spec) but maps to business term BT-021 "Cross-Cohort Earnings Differential" and prominently notes the cross-cohort nature in the description.
**Rationale:** The spec uses earnings_growth_rate as the field name, which is well-understood by engineers. The business term captures the semantic nuance that this is NOT longitudinal growth. Both names are needed for different audiences.

## Alternatives Considered

| Decision Point | Alternative | Why Rejected |
|---------------|-------------|--------------|
| Separate percentile band dimension table | Star schema with CIP family dimension | Query pattern always needs bands inline; 70K rows doesn't warrant normalization; adds join complexity for no benefit |
| Include p50 (median of medians) as explicit field | Add earnings_1yr_p50, earnings_2yr_p50, debt_p50 | Spec does not include p50 -- the effort slider uses p25/p50/p75 where p50 is the row's own program median (earnings_1yr_median), not the CIP family median. Adding CIP-family p50 would create confusion. |
| Make cip_family_earnings_rank NOT NULL | Exclude null-earnings rows from rank | Spec says rank is null when earnings is null. This is correct -- you cannot rank what you cannot measure. |
| Separate DTE tier as a lookup dimension | Map tier thresholds via a reference table | Only 4 tier values with fixed thresholds. Lookup table is over-engineering for static business rules. |

## Human Feedback Incorporated
None yet -- this is the initial proposal. The conceptual model is still in PROPOSED status (pending human approval).

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Logical model | governance/models/gold-career-outcomes-college-scorecard-logical.md |
| Approval document | governance/approvals/gold-career-outcomes-college-scorecard-logical-approval.md |
| Audit trail (this file) | governance/audit-trail/gold-career-outcomes-college-scorecard-logical-model.md |
