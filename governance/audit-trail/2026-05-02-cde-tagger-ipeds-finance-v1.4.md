# Audit Trail: CDE/PII Re-Tagging — `ipeds-finance-v1.4`

**Date:** 2026-05-02
**Agent:** @cde-tagger
**Spec:** `docs/specs/ipeds-finance-v1.4.md`
**Reference baselines:** `docs/specs/completed/full-pipeline-ipeds-finance.md` (v1.3); `governance/cde-tagging/consumable-ipeds-finance-profile.md` (v1.3 baseline pre-edit); `governance/cde-tagging/raw-ipeds-finance.md` (v1.3 baseline pre-edit)

---

## Scope

v1.4 introduces two consumable schema additions and one base + one bronze schema addition that require CDE classification:

| Zone | Column | Origin | Classification |
|------|--------|--------|----------------|
| Bronze (raw) | `endowment_value_flag` | NEW v1.4 — captured from `XF1H02` (F1A) / `XF2H02` (F2) | **CDE** |
| Base (silver) | `endowment_value_flag` | Bronze passthrough (no rename per spec §2 Decision A — preserves IPEDS-vocabulary `flag` name; rename happens at consumable) | **CDE** |
| Consumable (gold) | `endowment_value_provenance` | Base passthrough renamed at consumable per spec §2 Decision A (consumer-clarity rename) | **CDE** |
| Consumable (gold) | `source_load_date` | Restored passthrough from base (was already at base in v1.3; v1.4 restores at consumable per spec §6 Data Contract delta) | **NOT CDE** |

In addition, the v1.2 corrected semantics for the 5-code domain (`A` = "Not applicable", `N` = "Imputed using Nearest Neighbor procedure") are propagated through the CDE tagging artifacts to replace the v1.3 EDA §7 narrative inversion.

---

## Files Modified

| Path | Change |
|------|--------|
| `governance/cde-tagging/consumable-ipeds-finance-profile.md` | Patched: header (spec ref → v1.4, dates, upstream-tagging line); table-context "v1.4 ADDS 2 new consumable columns" block; Columns Flagged as CDE table (+row #11 `endowment_value_provenance`); CDE total 10/15 → 11/17; PII section enumerates 17 columns and adds `endowment_value_provenance` + `source_load_date` rationale; Columns Evaluated — Not Flagged table (+row #16 `source_load_date`); YAML data-contract fragment (+`endowment_value_provenance` + `source_load_date` entries); Summary table now v1.3 vs v1.4 columns; Quality SLO Suggestions (+row #11); CDE density commentary updated to 65% (11/17); Non-obvious CDE choices (+#6 `endowment_value_provenance` CDE rationale, +#7 `source_load_date` NOT-CDE rationale); Diverges-from-spec-§6 reconciliation rewritten to note v1.4 spec §6 alignment. |
| `governance/cde-tagging/raw-ipeds-finance.md` | Patched: header (spec ref + dates updated); Tagged CDEs table (+`endowment_value_flag` v1.4 row); PII line updated to note v1.4 enum literal not a person identifier. |
| `governance/cde-tagging/base-ipeds-finance.md` | **CREATED** — net-new v1.4 file (v1.3 noted "no `governance/cde-tagging/base-ipeds-finance.md` exists — base zone tagging not yet authored"). 6 CDE flagged (`unitid`, `total_fte_enrollment`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `endowment_value_flag` v1.4); 0 PII. |

No changes to `governance/cde-registry/` — no per-spec or per-zone IPEDS Finance index file exists in the registry directory; the `governance/cde-tagging/` files are the canonical artifacts per the v1.4 spec §8 governance artifacts list ("CDE re-tagging (DELTA): patch `governance/cde-tagging/consumable-ipeds-finance-profile.md`").

---

## Decisions

### Decision 1 — `endowment_value_provenance` is CDE at consumable

**Classification:** CDE
**Rationale:** Interpretation-changing for `endowment_value` and `endowment_per_fte`. The 5-code enum distinguishes institution-reported (`R`) values from NCES-imputed values (`N` Nearest Neighbor / `P` prior year / `Z` zero) AND from the no-endowment-fund population (`A` = Not applicable, with exact `A`↔NULL coupling on `endowment_value`). Without this column, every consumer of `endowment_value` and `endowment_per_fte` reads a silent mix and treats the values as homogeneous. The longitudinal-filter mechanism (filter to `R`) is the load-bearing downstream interpretation guidance; this column is the only way to apply it.

**Cross-spec leverage:** `consumable.institution_aura` consumes `endowment_per_fte` as a direct aura composite plank per `docs/specs/full-pipeline-eada.md` §6 Decision 11 — making the provenance distinction load-bearing for the aura-score composite.

**Precedent:** Same as `fte_source` CDE in `governance/cde-tagging/base-eada.md` (provenance enum tagged CDE because it changes how downstream consumers interpret the per-FTE values).

### Decision 2 — `source_load_date` is NOT CDE at consumable

**Classification:** NOT CDE
**Rationale:** Vintage-observability metadata, not a substantive measure. It does not change the interpretation of any business metric (the values of `endowment_value`, `marketing_ratio`, etc., are interpreted the same regardless of when the load happened); it does not feed any downstream composite (no `aura_score` plank consumes it); it does not gate any consumer decision (CON-IFP-016 freshness rule cross-checks it against `promoted_at` for staleness detection but freshness is operational, not analytical).

**Distinction vs. `endowment_value_provenance`:** provenance-of-the-measurement (CDE) vs. observability-of-the-load (NOT CDE).

**Precedent:** Same as `source_load_date` non-CDE in `silver-base-college-scorecard-institution-cdes.md` ("Pipeline metadata — provenance tracking only") and `base-eada.md` ("Bronze passthrough. Pipeline freshness metadata. Not a decision input").

### Decision 3 — `endowment_value_flag` at base + bronze is CDE consistent with consumable rename

**Classification:** CDE at both bronze and base
**Rationale:** Per Brightsmith no-propagation policy, each zone is independently evaluated; however the load-bearing rationale (interpretation-changing for `endowment_value`) applies at every zone where `endowment_value` and the flag co-occur. Bronze + base preserve the IPEDS-vocabulary `flag` name (faithful-to-source convention); consumable renames to `endowment_value_provenance` (consumer clarity) per spec §2 Decision A. The CDE flag follows the load-bearing rationale, not the column name.

### Decision 4 — Propagate v1.2 corrected `A`/`N` semantics through all CDE tagging artifacts

**Action:** Every reference to flag-code semantics in the CDE tagging artifacts now uses the dictionary-correct interpretation: `R` = Reported by institution; `A` = **Not applicable** (institution has no endowment fund — exact `A`↔NULL coupling on `endowment_value`); `N` = **Imputed using Nearest Neighbor procedure**; `P` = Imputed using prior year's data; `Z` = Imputed using a zero value.

**v1.3 EDA §7 narrative inversion:** `A` was described as "model-imputed" and `N` as "not applicable". v1.4 v1.2 corrected against FY2023 dictionary + empirical evidence (every `A`-flagged row has NULL endowment).

**Operational impact:** The longitudinal-filter mechanism (filter to `R`) is unchanged in operational outcome — because of the `A`↔NULL coupling, filtering to `R` is operationally close to filtering to `endowment_value IS NOT NULL`. But the rationale phrasing is corrected throughout. The explicit `R` filter is the correct guidance because it drops the small `N`/`P`/`Z` imputed-value rows that *do* carry a populated `endowment_value`.

---

## Updated CDE Counts

| Zone | v1.3 baseline | v1.4 (this re-tag) | Delta |
|------|---------------|--------------------|-------|
| Bronze (`bronze.ipeds_finance`) | 5 CDE | **6 CDE** | +1 (`endowment_value_flag`) |
| Base (`base.ipeds_finance`) | 5 CDE (implicit; un-authored prior to v1.4) | **6 CDE** | +1 (`endowment_value_flag`) |
| Consumable (`consumable.ipeds_finance_profile`) | 10 CDE / 15 columns | **11 CDE / 17 columns** | +1 CDE (`endowment_value_provenance`); +1 NOT-CDE (`source_load_date`) |
| PII (all zones) | 0 | **0** | unchanged |

---

## Convention Compliance

- **Format:** matches v1.3 `consumable-ipeds-finance-profile.md` style (Domain Context Referenced → Table Context → Columns Flagged as CDE → Columns Flagged as PII → Columns Evaluated — Not Flagged → Tag List for Data Contract → Summary). The new `base-ipeds-finance.md` follows the more concise `base-eada.md` style.
- **No registry update:** `governance/cde-registry/` does not have per-spec or per-zone IPEDS Finance index files; no convention-mandated update there.
- **YAML fragment update:** the consumable Tag List for Data Contract has been extended with the two new columns for @doc-generator to merge into `governance/data-contracts/consumable-ipeds-finance-profile.yaml` per the §8 governance artifact list line item ("Data contract amendment (DELTA)" — separate from this re-tag).
- **No deviation from v1.3 convention.**

---

## Sign-off Hand-off

Surfaces to:
- **@bs:doc-generator** — for embedding the new YAML fragment entries (`endowment_value_provenance`, `source_load_date`) into `governance/data-contracts/consumable-ipeds-finance-profile.yaml`, and authoring the new `governance/data-contracts/base-ipeds-finance.yaml` if it does not yet exist (no v1.3 base contract YAML found in `governance/data-contracts/`).
- **@bs:governance-reviewer** — for sign-off per the v1.4 spec workflow (§7).
- **@bs:data-steward** — `BT-IPF-ENDOWMENT-PROVENANCE` business glossary term assignment (proposed in v1.4 spec §6).

---

**Path:** `/Users/jcernauske/code/bright/futureproof-data/governance/audit-trail/2026-05-02-cde-tagger-ipeds-finance-v1.4.md`
