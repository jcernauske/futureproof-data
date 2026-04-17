# Entity Resolution Decision: onet-experience-requirements

**Spec:** `docs/specs/onet-experience-requirements.md`
**Source Table:** `raw.onet_experience` (~35,998 rows)
**Agent:** @entity-resolver
**Date:** 2026-04-16
**Decision:** SKIP CONFIRMED — no entity resolution work required
**Entity Types:** O*NET-SOC occupation, O*NET Content Model element, O*NET scale
**Resolution Strategy:** ID-based resolution against canonical external-standard identifiers

---

## Summary

The O*NET "Education, Training, and Experience" dataset is keyed by three canonical external-standard identifiers — `onet_soc_code` (O*NET-SOC, XX-XXXX.XX), `element_id` (O*NET Content Model element, e.g., `3.A.1`), and `scale_id` (O*NET scale code: `RL`, `RW`, `PT`, `OJ`) — plus a controlled-vocabulary `category` ordinal supplied by the source. All four grain columns are emitted by the source in fully resolved canonical form. No fuzzy matching, alias reconciliation, deduplication, or entity-lifecycle reconciliation is required at Bronze, and no source-level entity registry update is warranted. This disposition confirms the skip recommendation already documented in the spec's §CDE & PII Assessment: "O*NET-SOC is an external standard identifier, no resolution needed."

---

## Identifier Disposition

| Column | Nature | Format | Resolution Needed? |
|--------|--------|--------|--------------------|
| `onet_soc_code` | Canonical external identifier — O*NET-SOC 2019, derived from BLS SOC 2018 by the National Center for O*NET Development | `XX-XXXX.XX` (8 chars + hyphen + dot) | **NO** — authoritative federal/BLS-derived identifier; exact-match joins only |
| `element_id` | Canonical external identifier — O*NET Content Model element ID, stable across O*NET releases | Dotted hierarchical key, e.g., `3.A.1` | **NO** — authoritative O*NET taxonomy identifier; exact-match joins only |
| `scale_id` | Canonical external identifier — O*NET scale code | 2-letter code from enumerated set: `RL`, `RW`, `PT`, `OJ` | **NO** — closed enumeration from O*NET; exact-match joins only |
| `category` | Controlled-vocabulary ordinal supplied by O*NET per scale | Integer ordinal | **NO** — source-supplied ordinal, not an entity reference |

No column on this grain requires fuzzy matching, normalization, or alias reconciliation. All four identifiers are already resolved canonical values at the point of ingest.

---

## Silver Projection — Identifier Projection, Not Entity Resolution

The spec's Silver zone truncates `onet_soc_code` from `XX-XXXX.XX` (O*NET-SOC detail) to `XX-XXXX` (BLS SOC 2018) before joining to `consumable.career_branches`. This is an **identifier projection** — a deterministic, lossy-to-detail transformation from one canonical identifier space (O*NET-SOC) to its parent canonical identifier space (BLS SOC). It is **not entity resolution**:

- It is deterministic (no fuzzy matching, no thresholds, no confidence scoring).
- It is documented in the published O*NET-to-SOC crosswalk — the parent-child relationship is definitional, not inferred.
- Multiple O*NET-SOC detail codes legitimately map to a single BLS SOC parent; this is expected taxonomy granularity, not entity collision.
- No canonical-entity mapping, no `lifecycle_events`, and no `resolution_confidence` score are required.

Silver's responsibility here is a column derivation (`bls_soc_code = LEFT(onet_soc_code, 7)` or equivalent), which is the province of the semantic modeler / CDE tagger, not @entity-resolver.

---

## Gold Cross-Source Joins — Exact-Match on Canonical Codes

At Gold, the Silver-projected `bls_soc_code` joins `consumable.career_branches` on its existing BLS SOC 2018 key. The join is:

- **Method:** Exact-match on canonical BLS SOC 2018 codes
- **Confidence:** 1.0 for all matched rows
- **Fuzziness:** None
- **Unmatched handling:** Expected null-coalesce behavior (some O*NET-SOC detail codes may roll up to BLS SOC parents that are not present in `career_branches`, or vice versa); this is a coverage/fallback concern, not an entity-resolution concern

No entity resolution is required to execute this join. The broader cross-source linking strategy for BLS/O*NET/College Scorecard is already documented in `governance/reviews/raw-ingest-bls-ooh-entity-resolution.md` (Link 1: BLS OOH ↔ O*NET via exact SOC match), and this spec falls cleanly under that established policy.

---

## Lifecycle Events

- **O*NET-SOC:** Tracks BLS SOC revisions with a short lag. No O*NET-SOC lifecycle events affect this Bronze ingest on current timescales; future SOC 2028 migration risk is already flagged in `governance/reviews/raw-ingest-bls-ooh-entity-resolution.md`.
- **O*NET element_id:** Content Model element IDs are stable across O*NET releases; no lifecycle events to model.
- **O*NET scale_id:** Closed enumeration (`RL`, `RW`, `PT`, `OJ`); no lifecycle events to model.

No `lifecycle_events` entries required.

---

## NO ENTITY RESOLUTION REQUIRED

See `docs/specs/onet-experience-requirements.md` §CDE & PII Assessment (and §Agent Workflow step 10) for the corresponding skip justification documented in the spec itself.
