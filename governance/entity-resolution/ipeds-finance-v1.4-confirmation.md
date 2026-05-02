# Entity Resolution Confirmation: IPEDS Finance v1.4

**Spec:** `docs/specs/ipeds-finance-v1.4.md`
**Date:** 2026-05-01
**Agent:** @entity-resolver
**Verdict:** **NO-OP for entity resolution.**

v1.4 is an additive delta over v1.3. The institution UNITID surface is unchanged: same source forms (F1A/F2/F3 + EFIA + HD), same `unitid` grain, same federally-canonical IPEDS identifier, no new sources, no new join keys, no new identity reconciliation. The new `endowment_value_flag` column (spec §1) is a passthrough categorical scalar on the existing UNITID grain — not an entity attribute requiring resolution.

The system-office filter introduced at the consumable zone (spec §6, Decision D) is a **hard row-exclusion** of organizational reporting artifacts based on name patterns plus numeric proxies (zero FTE / zero core expenses). It removes rows that should never have been candidate institutions in the first place; it does not reconcile identities across sources, does not alias, does not fuzzy-match. Per Decision D it is explicitly classified as exclusion, not entity resolution.

The v1.3 entity-resolution artifact `governance/entity-resolution/raw-ipeds-finance-er-assessment.md` (verdict: NOT APPLICABLE; UNITID exact-match, confidence 1.0 for all 2,675 rows; cross-form UNION structurally disjoint) covers the v1.4 UNITID surface unchanged. No registry update, no new ER assessment, no rerun warranted.
