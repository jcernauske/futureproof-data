# Entity Resolution Report: ingest-bls-oews-wage-percentiles

**Date:** 2026-05-07
**Agent:** @entity-resolver
**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Bronze Table:** `bronze.bls_oews` (831 rows, May 2024 reference period)
**Entity Type:** Detailed occupation (SOC 2018)
**Resolution Strategy:** ID-based (`soc_code` direct equality join)
**Verdict:** **TRIVIAL**

---

## Summary

Entity resolution for `bronze.bls_oews` is genuinely trivial. Each row is one detailed SOC 2018 occupation, the `soc_code` column is the canonical identifier, and the format and uniqueness invariants required for joining to sibling SOC-keyed tables (`bronze.bls_ooh`, `silver.onet_work_profiles`) are already proven by the existing Bronze DQ rules with 0 violations. No fuzzy matching, no name normalization, no probabilistic linkage, and no canonical-entity registry is required for OEWS — the resolver step reduces to a direct equality join. The single residual edge case (`45-3031 Fishing and Hunting Workers` is in OOH but not in the May 2024 OEWS publication) is already specified as a `LEFT JOIN` outcome with null wage columns, which is a coverage matter, not an entity-resolution matter.

---

## Verification Checklist

### 1. `soc_code` Uniqueness

**CONFIRMED.** RAW-OEWS-003 (Grain uniqueness: soc_code) PASSED on the May 2024 load:
- `total=831, distinct=831, duplicates=0`
- Source: `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md` line 17
- Rule: `governance/dq-rules/raw-ingest-bls-oews.json` rule_id `RAW-OEWS-003`
- Chaos-tested: chaos report S6 (injected duplicate `29-1141`) was CAUGHT by RAW-OEWS-003

### 2. `soc_code` Format Consistency with `bronze.bls_ooh`

**CONFIRMED.** Both Bronze tables enforce identical format invariants:

| Table | Rule | Pattern | Violations |
|-------|------|---------|------------|
| `bronze.bls_oews` | RAW-OEWS-002 (SOC code format: XX-XXXX) | `^\d{2}-\d{4}$` | 0 / 831 |
| `bronze.bls_ooh` | "SOC code format: XX-XXXX" | `^\d{2}-\d{4}$` | 0 / 832 |

Both ingestors preserve the hyphen and never coerce SOC to float (per `CLAUDE.md` rule "CIPCODE must always be treated as string type … never float" — the analogous discipline applies to SOC). String-equality join is safe with no normalization step.

EDA cross-check (`governance/eda/raw-bls-oews-eda.md` line 40): "`soc_code` is a near-perfect foreign key to `base.bls_ooh.soc_code` (831 of 832 OOH SOCs covered) and to `consumable.onet_work_profiles.bls_soc_code` (772 of 798)."

### 3. `occupation_title` Variation is Harmless

**CONFIRMED.** `occupation_title` is descriptive metadata, not a join key:
- Spec §Zone 3 defines the join exclusively as `op.soc_code = oews.soc_code` (line 206 of the spec).
- The Gold enrichment carries OOH's `occupation_title` forward unchanged; OEWS's `occupation_title` is not surfaced in `consumable.occupation_profiles` or `consumable.program_career_paths`.
- Domain context (`governance/domain-context.md` §"Why OEWS is Different from BLS OOH") explicitly notes that OEWS and OOH share the SOC 2018 taxonomy "and many of the same occupation titles" but that small text differences are expected and not reconciled. There is no downstream surface that fuzzy-compares titles across sources.
- 100% uniqueness of titles within OEWS (831 distinct of 831) means even if a future surface needed title-based disambiguation within OEWS, it would still be 1:1 with `soc_code`.

**No name normalization required.**

### 4. Edge Cases Where Entity Resolution Might Still Be Needed

Surveyed and assessed:

| Candidate Edge Case | Assessment | Disposition |
|---------------------|------------|-------------|
| **OOH↔OEWS coverage gap** (`45-3031 Fishing and Hunting Workers` is in OOH but suppressed by May 2024 OEWS) | Not an entity-resolution problem — both sources agree the occupation exists and uses `soc_code = '45-3031'`. OEWS simply has no wage row to surface. | Spec already prescribes `LEFT JOIN` and Gold DQ rule allows ≥98% non-null `wage_p25` (currently 826/832 = 99.28%). No resolver action. |
| **SOC 2018 → SOC 2028 vintage migration** | Both OEWS and OOH publish against OMB's current SOC vintage and would migrate simultaneously per the next BLS rebase. Domain context notes: "Plan reactively, same as OOH." | Out of scope — no entity-resolution work required at current vintage. When 2028 lands, the resolver would need a vintage-bridge mapping, but only across vintages, not within May 2024. |
| **OEWS top-coding (`#`) and suppression (`*`) sentinels** | Value-level encoding, not identity-level — handled by the Bronze ingestor (`*` → null, `#` → 239200 + `wage_capped = True`). The entity itself (the SOC) is unaffected. | Out of scope for entity resolution. Owned by the ingestor / DQ rules. |
| **Reference-period wage drift (May 2024 vs. earlier May)** | Year-over-year wage advances (e.g., RN median $86K → $93,600) are a temporal-modeling concern, not an entity concern — the SOC identity is stable. | Out of scope for entity resolution. Documented in domain-context §"Reference-period advance". |
| **Cross-survey median discrepancies (OOH median vs. OEWS median)** | Domain context explicitly forbids reconciling these via DQ rules. They are separate measurements of the same entity, not an identity ambiguity. | Out of scope. Display rule (OEWS-anchored where shown) is settled in the spec. |
| **Mean-above-p90 anomaly on top-coded SOCs** | A value-monotonicity quirk on 23 SOCs (Cardiologists, Anesthesiologists, etc.) where BLS publishes mean uncapped while p90 floors at $239,200. Identity is unaffected; spec deliberately omits a `mean ≤ p90` rule. | Out of scope for entity resolution. |

**No edge case requires resolver-level rules, fuzzy matching, or human review.**

---

## Resolved Entities

| Source ID (`soc_code`) | Raw Name (`occupation_title`) | Canonical Entity | Confidence | Method |
|------------------------|-------------------------------|------------------|------------|--------|
| 831 detailed SOC 2018 codes (e.g. 15-1252, 29-1141, 29-1171, 11-1011) | OEWS-published occupation titles, 100% unique 1:1 with `soc_code` | Same `soc_code` in `bronze.bls_ooh` (831 of 832) and `consumable.onet_work_profiles.bls_soc_code` (772 of 798) | 1.0 | `exact_id_match` (string equality on `soc_code`) |

No resolver registry entries are written — the SOC 2018 vocabulary itself is the canonical registry, maintained by OMB/BLS and consumed identically by all three FutureProof SOC-keyed sources.

## Lifecycle Events Discovered

None. SOC 2018 is the active vintage for all sources; no name changes, mergers, splits, or reclassifications occur within this load.

## Unresolved / Flagged for Review

None.

## Resolution Statistics

- Total entities processed: **831**
- Exact ID matches (against `bronze.bls_ooh`): **831 / 832 OOH SOCs** (99.88%); only `45-3031` not present in OEWS — coverage gap, not an unresolved entity
- High-confidence matches: **831 / 831** (100%)
- Flagged for human review: **0**

---

## Verdict

**TRIVIAL.** No entity-resolution rules are needed beyond the Bronze DQ rules already in place (RAW-OEWS-002 format, RAW-OEWS-003 uniqueness). Downstream Gold enrichment (`LEFT JOIN base.bls_oews ON soc_code`) is safe to execute as written. The spec's claim that this is a direct equality join is verified.
