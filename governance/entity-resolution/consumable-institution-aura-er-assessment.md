# Entity Resolution Assessment: `consumable.institution_aura`

**Date:** 2026-04-30
**Agent:** @entity-resolver
**Snapshot:** `5887248523326294782`
**Row Count:** 3,223
**Verdict:** NOT APPLICABLE

---

## Summary

`consumable.institution_aura` is a Gold-zone integration product built via FULL OUTER JOIN on `UNITID` between `base.ipeds_finance` and `base.eada` (per spec §6). Both upstream Silver tables expose `UNITID` as the canonical IPEDS institution identifier, and both have already passed entity-resolution assessment in their respective Silver-zone reports (`base-eada-er-assessment.md`, `raw-ipeds-finance-er-assessment.md`). No new entity resolution is required at the Gold layer.

## Resolution Strategy

**Strategy:** ID-based resolution (inherited from Silver).
**Join Key:** `UNITID` (single column, IPEDS canonical institution identifier).
**Identity Columns:** `unitid`, `institution_name` — both produced via `COALESCE(ipeds.col, eada.col)` per spec §6.
**Aliasing:** None. Both source UNITIDs are already canonical IPEDS values; there is no second identifier system to reconcile.

## Rationale for NOT APPLICABLE

1. **Single canonical key.** `UNITID` is the IPEDS-issued institution ID and is the only identifier in either source. There are no name-based, address-based, or fuzzy matches to perform.
2. **Pre-resolved upstream.** Both `base.ipeds_finance` and `base.eada` are derived from IPEDS-rooted ingestors where `UNITID` is the primary key. Entity resolution was performed (or assessed NOT APPLICABLE) at the Silver layer.
3. **No aliasing surface.** The COALESCE pattern in §6 is a null-handling fallback for non-key columns when a UNITID exists in only one source — it is not an identity-merging operation. Identity is fixed by the join key.
4. **No lifecycle events introduced.** Mergers, name changes, or splits between IPEDS reporting years are handled at the source-ingestor level (one row per UNITID per snapshot year). The Gold join does not introduce new lifecycle reconciliation.
5. **Unmatched rows are expected, not ambiguous.** UNITIDs present in only one source produce a row with nulls in the other source's measure columns. This is the documented behavior of FULL OUTER JOIN integration, not an unresolved-entity case.

## Confidence

All 3,223 rows resolve at confidence 1.0 via exact `UNITID` equality. No fuzzy matches, no flagged-for-review records.

## Registry Impact

No update to `governance/entity-registry.json` required. The IPEDS institution registry is maintained at the Silver layer; the Gold integration consumes it unchanged.

## Audit Trail

- Spec: `docs/specs/full-pipeline-ipeds-finance.md` §6 (integration / COALESCE)
- Upstream ER assessments: `governance/entity-resolution/base-eada-er-assessment.md`, `governance/entity-resolution/raw-ipeds-finance-er-assessment.md`
- Snapshot: `5887248523326294782`
- Resolved by: @entity-resolver
- Resolved date: 2026-04-30
