# Audit Trail: @doc-generator — raw-ingest-bea-rpp

**Date:** 2026-04-10
**Agent:** @doc-generator
**Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Zone:** Bronze
**Table:** `bronze.bea_rpp` (Iceberg: `raw.bea_rpp`)

---

## Scope

Generate Bronze-zone documentation artifacts for the BEA Regional Price Parities ingest:

1. Data dictionary entries for all 8 columns of `raw.bea_rpp`
2. Bronze data contract at `governance/data-contracts/raw-bea-rpp.yaml`
3. Business glossary additions BT-098 (Regional Price Parity) and BT-099 (Purchasing Power Multiplier)

Gold contract (`consumable.regional_price_parities`) and Silver/Gold dictionary entries are explicitly **out of scope** for this run — Bronze only.

---

## Inputs Consumed

| Artifact | Path | Purpose |
|---|---|---|
| Spec | `docs/specs/raw-ingest-bea-rpp.md` | Schema, grain, DQ rules, business glossary definitions |
| CDE tagging | `governance/cde-tagging/raw-ingest-bea-rpp.md` | CDE flags + rationales (ready-to-merge YAML fragment) |
| EDA | `governance/eda/raw-bea-rpp-eda.md` | Field profiles, observed ranges, cardinality, notes |
| DQ rules | `governance/dq-rules/raw-ingest-bea-rpp.json` | 19 rule IDs (RAW-BEA-001…019) for cross-reference |
| Business glossary | `governance/business-glossary.json` | Confirmed BT-098 and BT-099 free slots |

---

## Artifacts Produced / Updated

### 1. `governance/data-dictionary.json` (UPDATED)

Added one table entry: `raw.bea_rpp`.

- **Columns documented:** 8 (`geo_fips`, `geo_name`, `rpp_all_items`, `data_year`, `source_url`, `ingested_at`, `source_method`, `load_date`)
- **CDE flags:** 4 of 8 (`geo_fips`, `geo_name`, `rpp_all_items`, `data_year`) — all carried directly from `governance/cde-tagging/raw-ingest-bea-rpp.md` with full rationales
- **PII flags:** 0 of 8 — consistent with the PII scan (`governance/pii-scans/raw-ingest-bea-rpp.md`) and CDE tagging
- **DQ rule cross-references:** Every column links to its relevant RAW-BEA-### rule(s). Total 19 rules referenced.
- **Notes fields:** Every column carries an EDA-sourced note capturing observed cardinality, null rate, range, or operational quirk (e.g., Iowa/Oklahoma legitimate RPP tie, DC spelled out in full).

No conflicts with existing entries — `raw.bea_rpp` is a new table not previously documented.

### 2. `governance/data-contracts/raw-bea-rpp.yaml` (CREATED)

Bronze data contract following the existing project convention (matches `raw-karpathy-ai-exposure.yaml` structure).

- **Status:** `DRAFT` (per @doc-generator default; promotes to `ACTIVE` after @staff-engineer approval)
- **Grain:** `geo_fips`
- **Record count:** 51
- **Quality tier:** `high` with a note about the 8-verified / 43-estimated split
- **SLA:** Annual refresh; 400-day freshness guardrail
- **Columns:** 8 column blocks with full `is_cde`, `cde_rationale`, `is_pii`, `pii_rationale`, `description`, `dq_rules`
- **DQ summary:** 19 rules (10 P0, 5 P1, 4 P2)
- **CDE summary:** 4 CDE, 0 PII, `public` sensitivity, no regulatory frameworks
- **Breaking-change policy:** Standard semver
- **Downstream consumers:** Enumerated (base.bea_rpp, consumable.regional_price_parities, 2 MCP tools, frontend, stretch boss)

Naming convention: followed the `raw-*.yaml` pattern used by `raw-karpathy-ai-exposure.yaml`, `raw-bls-ooh.yaml`, etc. Confirmed existing convention by `ls governance/data-contracts/`.

### 3. `governance/business-glossary.json` (UPDATED)

Added two new terms:

| Term ID | Name | Category | Source Type | Approval |
|---|---|---|---|---|
| BT-098 | Regional Price Parity (RPP) | metric | external-standard (BEA) | approved |
| BT-099 | Purchasing Power Multiplier | derived | project-specific | approved |

- BT-098 definition sourced verbatim from the spec's business glossary table, with an expansion clarifying that RPP covers state-level aggregates (housing rents included), and a cross-reference to BT-099.
- BT-099 definition sourced verbatim from the spec, with added context that FutureProof computes this at Silver and carries it through Gold/MCP.
- Both terms cross-linked via `related_terms`.
- BT-099's `used_in_models` notes Silver/Gold only — it is not present in the Bronze raw table. The task brief explicitly approved adding it now even though it's a Silver derivation, since this is the only Bronze run for this data source and the downstream agents will reference it.

**Slot confirmation:** Highest pre-existing term is BT-097 (BLS Match Flag). BT-098 and BT-099 were free slots as the pre-reviewer indicated.

### 4. `governance/audit-trail/2026-04-10-doc-generator-raw-bea-rpp.md` (CREATED)

This file.

---

## Key Decisions & Judgment Calls

1. **Pipeline metadata business terms not created.** Columns `source_url`, `ingested_at`, `source_method`, `load_date` received no `business_term` — these are operational/pipeline metadata, not business vocabulary, and the existing project convention (see `raw-karpathy-ai-exposure.yaml`, `raw-bls-ooh.yaml`) does not assign business terms to pipeline metadata columns. Consistent with prior patterns.

2. **Placeholder business term IDs retained for geo_fips / geo_name / data_year.** The CDE tagging YAML fragment used placeholder IDs `BT-RPP-STATE-FIPS`, `BT-RPP-STATE-NAME`, `BT-RPP-DATA-YEAR`. These are not in the glossary. I preserved them as-is in both the contract and the dictionary because:
   - The task brief only requested BT-098 and BT-099 be created in this run.
   - Creating new formal BT-### entries for "state FIPS" and "state name" as business terms should route through @data-steward review in a future run (likely when the project adopts geographic taxonomy terms more broadly).
   - The placeholder IDs are self-documenting and future-proof for a proper renaming migration.
   - **Action item for future run:** promote these placeholders to real BT-### entries if/when the glossary adds geographic identifier terms.

3. **BT-099 added in the Bronze run despite Silver derivation.** The brief explicitly approved this. BT-099 is not referenced by any Bronze column (correct — it doesn't exist until Silver). It is added now because this is the only Bronze run for this data source and future Silver/Gold agents will need to reference it. `used_in_models` correctly lists only Silver and Gold.

4. **RPP description emphasizes the Iowa/Oklahoma tie.** The EDA and DQ rule notes repeatedly flag that `rpp_all_items` has 50 distinct values because Iowa and Oklahoma both equal 87.8. I embedded that fact in the column's `notes` field so any future reader understands that a distinct-count check on this column should NOT assume 51.

5. **CDE rationales carried verbatim from the tagging document.** I did not paraphrase the 4 CDE rationales — they are load-bearing governance prose written by @cde-tagger and approved. I copied them into both the contract and the dictionary with only minor wrapping-for-YAML adjustments.

6. **Secrets-hygiene note preserved in source_url description.** The CDE tagging document flagged a secrets-hygiene guardrail: the ingestor must not persist the real BEA UserID API key into `source_url`. I included this warning in both the contract and the dictionary.

7. **Current-load caveats embedded in table description.** The table-level description in the data dictionary explicitly documents that the current load contains 8 verified + 43 estimated values. This is not a quality defect to hide — it is a known state that a future refresh will correct. Documenting it up-front prevents a future reader from being surprised.

8. **Data contract status set to DRAFT.** Per the doc-generator playbook, new contracts begin as `DRAFT` and become `ACTIVE` only after @staff-engineer approval. The existing `raw-karpathy-ai-exposure.yaml` (which I used as a template) says `status: ACTIVE` because it is post-approval. I set the BEA contract to `DRAFT` as it is pre-approval.

---

## Conflicts Checked

- **Existing data dictionary entries:** `raw.bea_rpp` does not exist in the dictionary. No conflict.
- **Existing business glossary IDs:** Highest existing ID is BT-097. BT-098 and BT-099 are free as the pre-reviewer confirmed. No conflict.
- **Existing data contracts:** No `raw-bea-rpp.yaml` or `bea-rpp*.yaml` files exist. New file created. No conflict.
- **Duplicate business term names:** No existing term named "Regional Price Parity", "RPP", "Purchasing Power Multiplier", or any of their synonyms. Confirmed via grep of `business-glossary.json`.

---

## Validation Performed

- `data-dictionary.json` parses as valid JSON (Python `json.load`).
- `business-glossary.json` parses as valid JSON (Python `json.load`).
- `raw-bea-rpp.yaml` parses as valid YAML and deserializes to a contract with 8 column blocks (PyYAML via `uv run`).

---

## Downstream Handoff

- **@governance-reviewer (post-review):** All Bronze governance artifacts for this spec are now present — data dictionary, data contract, business glossary, CDE tagging, DQ rules, EDA, lineage, domain context. Ready for post-review.
- **@staff-engineer:** Data contract is `DRAFT`; promote to `ACTIVE` on approval.
- **Future @doc-generator runs on Silver (`base.bea_rpp`) and Gold (`consumable.regional_price_parities`):** reference BT-098 and BT-099 (now in glossary) and re-evaluate CDE flags for the derived columns (`state_abbr`, `census_region`, `purchasing_power_multiplier`, `cost_tier`, `adjusted_30k/50k/75k/100k`). Also consider promoting the `BT-RPP-*` placeholder term IDs to real BT-### entries at that time.

---

*End of audit trail.*
