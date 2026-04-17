# Entity Resolution Assessment: silver-base-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @entity-resolver
**Spec:** docs/specs/silver-base-college-scorecard-institution.md
**Transformer:** src/silver/college_scorecard_institution_transformer.py
**Bronze Assessment:** governance/entity-resolution/raw-ingest-college-scorecard-institution.md
**Resolution Complexity:** TRIVIAL
**Recommendation:** NO ENTITY RESOLUTION LOGIC REQUIRED

---

## Summary

Silver inherits entity identity directly from Bronze with no semantic change. The grain, the primary identifier, the issuing authority, and the cross-source linkage behavior are all identical. The Silver layer adds a deterministic hash (`record_id`) as an implementation mechanic for idempotent promotion — not as a new identity. The @entity-resolver agent is formally skipped for this spec.

---

## Identity Inheritance from Bronze

| Property | Bronze | Silver | Change? |
|----------|--------|--------|---------|
| Entity type | Institution (postsecondary, Title IV) | Institution (postsecondary, Title IV) | No |
| Grain | One row per UNITID | One row per UNITID | No |
| Row count | 3,039 | 3,039 | No |
| Primary identifier | `UNITID` (6-digit int, federal) | `UNITID` (LongType, federal) | No |
| Resolution method | `exact_id_match` | `exact_id_match` | No |
| Issuing authority | NCES / IPEDS | NCES / IPEDS | No |
| Duplicate rate on UNITID | 0.0% | 0.0% | No |
| Cross-source linkage | UNITID equi-join, 91.9% coverage | UNITID equi-join, 91.9% coverage | No |

Silver is a cleanse-and-unify layer, not an identity layer. It normalizes cost-of-attendance and net-price measures, maps `control` to a human-readable label, derives 4-year totals, and preserves raw columns for provenance. None of these operations change what an institution *is* or how it is identified.

---

## `record_id`: Deterministic Hash, Not a New Identity

The transformer computes:

```python
record["record_id"] = compute_grain_id(record, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
# GRAIN_FIELDS = ["unitid"]
# GRAIN_PREFIX = "csi"
```

| Property | Value |
|----------|-------|
| Purpose | Stable primary key for idempotent `promote()` (dedup key in Iceberg merge) |
| Input fields | `["unitid"]` — single-field grain, identical to Bronze grain |
| Collision risk | Zero — same input deterministically produces same output; UNITID is already unique |
| Introduces new entities? | No — one `record_id` per UNITID, one UNITID per institution |
| Introduces merge/split logic? | No — no cross-record reasoning |
| Requires resolution agent? | No — pure function of the existing grain key |

`record_id` is a technical surrogate, not a semantic one. It exists so the Silver promote pattern can detect "have I already written this institution?" without scanning the content of every column. Because the input is `[unitid]` alone, a given UNITID will always produce the same `record_id`, and re-runs are naturally idempotent. This adds **zero** new resolution complexity: it is a hash of the already-resolved identity, not a new identity.

---

## Resolution Complexity: TRIVIAL

| Dimension | Finding |
|-----------|---------|
| Key type | Single integer primary key (inherited from Bronze) |
| New identifiers introduced? | No — `record_id` is a hash of `unitid`, not a new identifier system |
| Name matching required? | No |
| Composite grain? | No |
| Cross-system reconciliation? | No — same issuing authority, same join key |
| Lifecycle event handling in-scope? | No — single-snapshot, SCD Type 1 semantics |
| Fuzzy matching in-scope? | No |
| Rows skipped by transformer | Only rows missing required identity/classification fields (unitid, instnm, stabbr, mappable control) — these are DQ filter events, not unresolved entities |

---

## Transformer Skip Semantics

`transform_row()` may return `None` (and increment the `rows_skipped_transform` counter) when:

1. `unitid` is null
2. `instnm` is null/empty
3. `stabbr` is null/empty
4. `control` is null or not in `{1, 2, 3}` (unmappable to a required `institution_control` label)

These are **validation rejections**, not entity-resolution ambiguity. A row with no UNITID has no identity to resolve; a row with an unmappable control fails the physical model's NOT NULL contract. Operators are informed via `logger.warning` and the returned skip count. No fuzzy matching, corroboration, or human review queue is triggered because no ambiguous match ever exists.

---

## Recommendation

**No entity resolution logic required.** Proceed with the Silver transformer as implemented:

1. Inherit UNITID as the sole identity (LongType, NOT NULL).
2. Compute `record_id = compute_grain_id(row, ['unitid'], prefix='csi')` for idempotent promotion.
3. Let downstream Gold joins continue to use `unitid` directly against `consumable.career_outcomes`.

The @entity-resolver agent is formally skipped for this spec, consistent with the Bronze decision recorded in `governance/entity-resolution/raw-ingest-college-scorecard-institution.md`.

---

## Resolution Statistics

| Metric | Value |
|--------|-------|
| Total entities processed | 3,039 (inherited) |
| Exact ID matches (confidence 1.0) | 3,039 |
| New identities created at Silver | 0 |
| `record_id`s generated (1:1 with UNITID) | 3,039 |
| High confidence matches (0.9+) | 0 (not needed) |
| Fuzzy / flagged for review | 0 |
| Lifecycle events handled | 0 |
| Active resolution work performed | None |

---

## Audit Trail

- Decision: SKIP active entity resolution for silver-base-college-scorecard-institution
- Rationale: Silver inherits Bronze identity verbatim (UNITID, exact_id_match, 0% duplicates); `record_id` is a deterministic hash of the single-field grain, not a new identity system
- Decided by: @entity-resolver
- Decision date: 2026-04-14
- Spec reference: docs/specs/silver-base-college-scorecard-institution.md
- Bronze assessment reference: governance/entity-resolution/raw-ingest-college-scorecard-institution.md (Resolution Complexity: TRIVIAL)
- Transformer reference: src/silver/college_scorecard_institution_transformer.py (`GRAIN_FIELDS = ["unitid"]`, `GRAIN_PREFIX = "csi"`)
