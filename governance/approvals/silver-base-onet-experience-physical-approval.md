# Human Approval: Silver Base O*NET Experience Physical Model

**Spec:** docs/specs/onet-experience-requirements.md
**Artifacts:**
- governance/models/silver-base-onet-experience-physical.md (the Silver physical model)
- governance/models/gold-futureproof-engine-physical.md (Addendum: Experience Columns on consumable.career_branches)
**Stage:** Physical Model (Stage 3 of 3)
**Author:** @semantic-modeler
**Date:** 2026-04-16
**Status:** APPROVED
**Approved By:** Jeff Cernauske
**Approved Date:** 2026-04-16
**Conditions:** none

---

## Context

`docs/specs/onet-experience-requirements.md` adds a new experience-gating layer. Per the governance re-review (APPROVED 2026-04-16), the Phase 1 Semantic Modeling gate requires three Silver models plus a Gold physical-model addendum to be authored and approved before any Bronze or Silver implementation begins.

This approval request covers the **physical** stage (Stage 3 of 3). The conceptual (Stage 1) and logical (Stage 2) models are under separate approvals. This stage locks the PyIceberg schema, DuckDB column types, partition/sort strategy, CHECK constraints, and the Gold-side schema diff (four additive columns on `consumable.career_branches`).

All derivation choices trace back to the open-decisions approval file (`governance/approvals/onet-experience-requirements-open-decisions.md`) -- the physical model does not introduce new value judgments, it only binds the logical model to implementation specifics.

## What Is Being Proposed

Two physical artifacts:

### A. New Silver table: `base.onet_experience_profiles`
- 11 columns, all NOT NULL
- Namespace: `base`, table name: `onet_experience_profiles`
- Grain: `[bls_soc_code]`, surrogate key prefix: `exp`
- Expected row count: ~867
- Unpartitioned (justified), sorted by `bls_soc_code ASC`
- Full PyIceberg `Schema` definition matching the style of `silver-base-onet-physical.md`
- Writes invoked by `src/silver/onet_experience_transformer.py` (to be implemented by `bs:primary-agent` in Phase 3 of the agent workflow)
- Promote pattern: `compute_grain_id(row, ['bls_soc_code'], prefix='exp')` -- matches the `raw-ingest-onet.md` precedent for O*NET Silver prefixes

### B. Gold addendum: 4 additive columns on `consumable.career_branches`
Appended to the existing `gold-futureproof-engine-physical.md` as a new "Addendum" section dated 2026-04-16. No existing column is modified, renamed, or dropped.

- `related_experience_years DOUBLE` (nullable; CDE; BT-117)
- `related_experience_tier STRING` (nullable; CDE; BT-118; enum `entry`/`early`/`mid`/`senior`)
- `source_experience_years DOUBLE` (nullable; CDE; BT-117)
- `experience_delta_years DOUBLE` (nullable; CDE; BT-117; **NULL-propagating** when either side is NULL)

Contract version bump: `governance/data-contracts/consumable-career-branches.yaml` v1.1.0 -> v1.2.0 (additive only).

## Key Design Decisions for Review

### 1. PyIceberg schema matches `silver-base-onet-physical.md` style
Same `NestedField` numbering pattern, same imports, same `required=True` / `required=False` conventions. This keeps the O*NET Silver family uniform.

### 2. Unpartitioned table (~867 rows)
Explicitly chosen to match every peer O*NET Silver table (`onet_occupations` at 798, `onet_activity_profiles` at 31K, `onet_context_profiles` at 44K, `onet_career_transitions` at 16K -- all unpartitioned). Partitioning a sub-1K table would produce tiny file fragments with net-negative value.

### 3. Sort order: `bls_soc_code ASC`
Clusters related rows for point-lookup and full-table-scan Gold joins. Matches `onet_occupations`.

### 4. Dedup grain: `[bls_soc_code]`
Zero-duplicate enforcement at promote-time. Two rows with the same `bls_soc_code` would indicate a bug in BLS aggregation and should fail loudly.

### 5. Prefix choice: `exp`
Three-letter prefix, unambiguous, matches the short-mnemonic convention established in `raw-ingest-onet.md` for O*NET Silver (`on`, `wa`, `wc`, `ct`).

### 6. `experience_distribution` stored as VARCHAR (JSON string)
Matches the `onet_detail_codes` precedent in `base.onet_occupations`. DuckDB+Iceberg interop is strongest on scalar types; `json_extract()` is available for targeted lookups.

### 7. CHECK constraint bound on `experience_years_typical` is loose (0.0 - 15.0)
Defensive headroom above the theoretical max of 12.0 (category-11 midpoint). Tight business-level validation is done in DQ rules (`governance/dq-rules/silver-onet-experience.json`) via spot checks and tighter range rules. This matches the split-responsibility convention in the existing Silver models (CHECK = crash-prevention guard; DQ rules = business validation).

### 8. Tie-breaking at 50% cumulative frequency: lower-numbered (more-conservative) category
Locked in the physical model per the human-approved test matrix case ("Tie at 50%") and the explicit directive in the open-decisions approval file. This is an implementation-binding choice visible in the derivation rules.

### 9. Gold addendum is additive-only
The spec explicitly commits to "Additive only -- no breaking changes" for the `career_branches` contract change. Existing consumers (MCP `get_career_branches`, backend `branch_tree.py`, frontend) continue to work unchanged until they explicitly opt in to the new fields.

### 10. NULL-propagating `experience_delta_years` semantics
Locked in the Gold addendum with the full CASE expression from §Zone 3 of the spec. The earlier `COALESCE(..., 0)` variant was deliberately rejected because it overstated the gap when source experience data was missing. "Unknown" is now explicit and filterable.

### 11. CDE tags on all 4 Gold additions
All four new Gold columns (`related_experience_years`, `related_experience_tier`, `source_experience_years`, `experience_delta_years`) are flagged `is_cde = true` per §CDE & PII Assessment in the spec. `bs:cde-tagger` applies these to the bumped contract.

## Business Terms Referenced

| Term ID | Name | Used In |
|---------|------|---------|
| BT-015 | Record ID | Silver record_id |
| BT-016 | Source Load Date | Silver provenance |
| BT-017 | Ingestion Timestamp | Silver provenance |
| BT-027 | BLS SOC Code | Silver natural key + Gold join keys |
| BT-062 | Recommend Suppress | Silver provenance |
| BT-063 | Multi-Detail Aggregation | Silver provenance |
| BT-117 | Related Work Experience | Silver primary scalar + Gold 3 columns -- **pending data-steward approval** |
| BT-118 | Experience Tier | Silver classifier + Gold 1 column -- **pending data-steward approval** |

## What Happens Next

- **If APPROVED:** All four semantic-modeling artifacts (conceptual, logical, Silver physical, Gold physical addendum) are considered approved together. `bs:primary-agent` can begin Phase 2 (Bronze ingestor implementation), which in turn unblocks Phase 3 (Silver transformer) and Phase 4 (Gold transformer modification).
- **If CHANGES REQUESTED:** @semantic-modeler revises the physical model(s) based on feedback. No Bronze or Silver code begins until all revisions are approved.
- **If REJECTED:** The physical design is reconsidered, potentially requiring changes to the approved logical or conceptual models.

## Approval

To approve, set the status in both physical model files (or on the addendum header) to `APPROVED` and note any conditions:

```
**Status:** APPROVED
**Approved By:** [name]
**Approved Date:** [date]
**Conditions:** [any conditions or none]
```
