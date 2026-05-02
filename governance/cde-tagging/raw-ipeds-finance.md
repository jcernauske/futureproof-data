# Bronze CDE Tags: `bronze.ipeds_finance`

**Spec:** `docs/specs/completed/full-pipeline-ipeds-finance.md` (v1.3 baseline) + `docs/specs/ipeds-finance-v1.4.md` (v1.4 delta)
**Date:** 2026-04-30 (v1.3 baseline) · 2026-05-02 (v1.4 add: `endowment_value_flag`)
**Agent:** @cde-tagger
**PII:** None — see `governance/pii-scans/raw-ipeds-finance-pii-scan.md` (institution-level public IPEDS data; v1.4 `endowment_value_flag` is a 5-code enum literal, not a person identifier).

## Tagged CDEs

| Column | Tier | Rationale | Gold dependent — `consumable.ipeds_finance_profile` | Gold dependent — `consumable.institution_aura` (EADA spec) |
|--------|------|-----------|------------------------------------------------------|-------------------------------------------------------------|
| `unitid` | Public | Structural join key for cross-source institution integration. | All rows (PK) | `unitid` (PK) |
| `instruction_expenses` | L1 | Numerator for `instruction_per_fte`; denominator for `marketing_ratio`. | `instruction_per_fte`, `marketing_ratio` | (indirect via `marketing_ratio` aura input) |
| `institutional_support_expenses` | L1 | Numerator for `institutional_support_per_fte` and `marketing_ratio`. | `institutional_support_per_fte`, `marketing_ratio` | `marketing_ratio` aura input |
| `endowment_value` | L1 | Sole source for `endowment_per_fte`; declared aura_score input. | `endowment_per_fte` | `endowment_per_fte` aura input |
| `total_fte_enrollment` | L1 | FTE backbone for all four per-FTE derivations; preferred branch of EADA Option-C COALESCE (spec §2 Decision 3). | All `*_per_fte` fields | FTE denominator across aura per-FTE inputs |
| `endowment_value_flag` (v1.4) | L1 (Public) | Interpretation-changing CDE for `endowment_value` — distinguishes institution-reported (`R`) from NCES-imputed (`N` Nearest Neighbor / `P` prior year / `Z` zero) values, plus the no-endowment-fund population (`A` = Not applicable, exact `A`↔NULL coupling on `endowment_value`). 5-code observed FY2023 domain `{R, A, P, Z, N}`, a strict subset of the IPEDS dictionary's 13-code shared `Xvarname` lookup; FY2023+ appearance of any of the 8 unobserved codes is a Significant escalation per spec §3 (no silent allowed-set extension). Sources: `XF1H02` (F1A) / `XF2H02` (F2); structurally NULL on F3 (no F3H family). RAW-IPF-015 P0 enforces domain. | `endowment_value_provenance` (renamed at consumable per §2 Decision A) | (indirect — consumers of `endowment_per_fte` and `marketing_ratio` aura inputs benefit from this provenance) |

## Not Flagged

All other bronze columns (reporting year metadata, raw line-item subtotals not consumed downstream) — retained for lineage but not on the gold critical path.

---

**Path:** `/Users/jcernauske/code/bright/futureproof-data/governance/cde-tagging/raw-ipeds-finance.md`
