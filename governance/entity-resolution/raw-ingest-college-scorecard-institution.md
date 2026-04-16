# Entity Resolution Assessment: raw-ingest-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @entity-resolver
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Domain Context:** domain/raw-ingest-college-scorecard-institution-context.md
**DQ Scorecard:** governance/dq-scorecards/raw-ingest-college-scorecard-institution-scorecard.md
**Resolution Complexity:** TRIVIAL
**Recommendation:** NO ENTITY RESOLUTION LOGIC REQUIRED

---

## Summary

This source requires no active entity resolution work. The data has a single, federally-assigned integer primary key (UNITID) with zero duplicates, and all downstream joins use the same key on the same identifier system. The @entity-resolver agent is formally skipped for this source.

---

## Entity Type

| Field | Value |
|-------|-------|
| Entity Type | Institution (postsecondary, Title IV) |
| Scope | U.S. 4-year bachelor's-granting institutions (filtered PREDDEG=3 OR ICLEVEL=1) |
| Row Count | 3,039 institutions (post-filter) |
| Grain | One row per institution |

---

## Identity Strategy

| Property | Value |
|----------|-------|
| Primary Identifier | `UNITID` |
| Identifier Type | 6-digit positive integer |
| Authority | NCES / IPEDS (federal, U.S. Department of Education) |
| Assignment | Federally assigned — centrally administered, no self-reporting ambiguity |
| Stability | Stable across annual refreshes (institution closure removes UNITID; no re-use) |
| Resolution Method | `exact_id_match` (direct lookup) |
| Confidence | 1.0 (exact match on authoritative federal ID) |

UNITID is the sole grain key. There is no need for fuzzy name matching, composite keys, attribute corroboration, or hierarchical resolution. The field is issued and maintained by IPEDS under the Higher Education Act, making it the canonical institution identity in U.S. higher education data.

---

## Resolution Complexity: TRIVIAL

| Dimension | Finding |
|-----------|---------|
| Key type | Single integer primary key |
| Name matching required? | No |
| Composite grain? | No |
| Cross-system reconciliation? | No — same issuing authority as the join target |
| Lifecycle event handling in-scope? | No — single-snapshot ingest, no history to reconcile |
| Fuzzy matching in-scope? | No |

Confirmed by EDA (`docs/sessions/eda-college-scorecard-institution.md`) and domain context: 3,039 rows / 3,039 distinct UNITIDs / 0 duplicates.

---

## Duplicate Rate

| Metric | Value |
|--------|-------|
| Duplicate rate on grain key | **0.0%** |
| Confirming DQ rule | `RAW-CSI-002` (unitid uniqueness, P0) |
| Rule status | PASS |
| Evidence | 3,039 rows, 3,039 distinct UNITIDs |

No deduplication pass, merge logic, or conflict resolution is needed at any zone boundary. The Silver `compute_grain_id(row, ['unitid'], prefix='csi')` pattern is safe and produces one record per institution.

---

## Cross-Source Linkage

| Property | Value |
|----------|-------|
| Target table | `raw.college_scorecard` / `base.college_scorecard` / `consumable.career_outcomes` |
| Join key | `unitid` (both sides) |
| Join type | LEFT JOIN (institution cost enriches program-level earnings) |
| Identifier system | Identical — same IPEDS UNITID on both sides |
| Coverage | **91.9%** (2,352 of 2,559 field-of-study UNITIDs match institution-level UNITIDs) |
| Unmatched rows | 207 field-of-study schools (8.1%) |
| Unmatched cause | Schools report program-level data but not institution-level cost data, or were excluded by the PREDDEG=3 / ICLEVEL=1 filter |
| Resolution required for unmatched rows? | No — LEFT JOIN yields NULL cost columns; documented as expected coverage gap |

Because both sources come from the same provider (College Scorecard / U.S. Department of Education) and use the same federally-assigned UNITID, cross-source entity resolution reduces to a direct equi-join. No mapping table, crosswalk, or probabilistic matching is required.

---

## Lifecycle Event Handling

| Event | In-scope for this ingest? | Notes |
|-------|---------------------------|-------|
| Institution closure | No | Single-snapshot ingest. Cross-refresh change detection is a future concern. Handle as SCD Type 1 (overwrite) if annual refresh pipeline is built. |
| Merger / acquisition | No | IPEDS retires/reassigns UNITIDs upstream; by the time data reaches us, UNITIDs are already post-resolution. |
| Name change | No | Name changes do not affect UNITID stability. `instnm` is descriptive only; `unitid` is the identity. |
| Reclassification | No | Changes in CONTROL / PREDDEG / ICLEVEL do not create new UNITIDs. Entity identity is preserved. |

No lifecycle logic is required for this spec.

---

## Recommendation

**No entity resolution logic required.** Proceed with the ingestor as specified:

1. Bronze: land UNITID as `long`, enforce uniqueness via `RAW-CSI-002`.
2. Silver: use `compute_grain_id(row, ['unitid'], prefix='csi')` for deterministic record IDs.
3. Gold: LEFT JOIN `base.college_scorecard_institution.unitid = consumable.career_outcomes.unitid`. Accept 8.1% null-on-right as documented coverage gap.

The @entity-resolver agent can be formally skipped for this source, per the conditional-agent decision recorded in the domain context.

---

## Resolution Statistics

| Metric | Value |
|--------|-------|
| Total entities processed | 3,039 |
| Exact ID matches (confidence 1.0) | 3,039 |
| High confidence matches (0.9+) | 0 (not needed) |
| Fuzzy / flagged for review | 0 |
| Lifecycle events handled | 0 |
| Active resolution work performed | None |

---

## Audit Trail

- Decision: SKIP active entity resolution for raw-ingest-college-scorecard-institution
- Rationale: Trivial ID-based identity (UNITID, federal assignment), zero duplicates confirmed by RAW-CSI-002, same-key cross-source linkage at 91.9% coverage
- Decided by: @entity-resolver
- Decision date: 2026-04-14
- Spec reference: docs/specs/raw-ingest-college-scorecard-institution.md
- Domain context reference: domain/raw-ingest-college-scorecard-institution-context.md (Entity Resolution Complexity: TRIVIAL)
