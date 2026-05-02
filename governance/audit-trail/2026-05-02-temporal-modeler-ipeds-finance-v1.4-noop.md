# Temporal Modeler — ipeds-finance-v1.4 (No-Op)

**Date:** 2026-05-02
**Agent:** @temporal-modeler
**Spec:** `docs/specs/ipeds-finance-v1.4.md`

## Decision: No temporal modeling work required

v1.4 is a single-vintage (FY2023) additive delta on top of v1.3. Per spec §1 hard scope boundary, bitemporal / SCD2 versioning is explicitly out of scope.

### Confirmations
1. **Zero new temporal dimensions.** The four deltas (endowment provenance flag, system-office filter, CON-IFP-012, source_load_date passthrough) introduce no valid-time or transaction-time columns beyond v1.3.
2. **`source_load_date` is point-in-time observability metadata**, not a versioning dimension. CON-IFP-015 (P0 NOT NULL) and CON-IFP-016 (P1 freshness within 400 days of `promoted_at`) treat it as a single scalar tag of when the bronze source was loaded — no `valid_from`/`valid_to` interval, no supersession semantics.
3. **`fiscal_year` remains single-valued.** CON-IFP-012 (P0) asserts present + single-valued across the consumable, preserving the single-vintage contract.

Iceberg snapshot strategy is unchanged: one snapshot per re-promotion; transaction time recovered via Iceberg time travel. No bitemporal schema design needed.
