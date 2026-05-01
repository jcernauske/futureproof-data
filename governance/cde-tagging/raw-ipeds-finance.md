# Bronze CDE Tags: `bronze.ipeds_finance`

**Spec:** `docs/specs/full-pipeline-ipeds-finance.md`
**Date:** 2026-04-30
**Agent:** @cde-tagger
**PII:** None — see `governance/pii-scans/raw-ipeds-finance-pii-scan.md` (institution-level public IPEDS data).

## Tagged CDEs

| Column | Tier | Rationale | Gold dependent — `consumable.ipeds_finance_profile` | Gold dependent — `consumable.institution_aura` (EADA spec) |
|--------|------|-----------|------------------------------------------------------|-------------------------------------------------------------|
| `unitid` | Public | Structural join key for cross-source institution integration. | All rows (PK) | `unitid` (PK) |
| `instruction_expenses` | L1 | Numerator for `instruction_per_fte`; denominator for `marketing_ratio`. | `instruction_per_fte`, `marketing_ratio` | (indirect via `marketing_ratio` aura input) |
| `institutional_support_expenses` | L1 | Numerator for `institutional_support_per_fte` and `marketing_ratio`. | `institutional_support_per_fte`, `marketing_ratio` | `marketing_ratio` aura input |
| `endowment_value` | L1 | Sole source for `endowment_per_fte`; declared aura_score input. | `endowment_per_fte` | `endowment_per_fte` aura input |
| `total_fte_enrollment` | L1 | FTE backbone for all four per-FTE derivations; preferred branch of EADA Option-C COALESCE (spec §2 Decision 3). | All `*_per_fte` fields | FTE denominator across aura per-FTE inputs |

## Not Flagged

All other bronze columns (reporting year metadata, raw line-item subtotals not consumed downstream) — retained for lineage but not on the gold critical path.

---

**Path:** `/Users/jcernauske/code/bright/futureproof-data/governance/cde-tagging/raw-ipeds-finance.md`
