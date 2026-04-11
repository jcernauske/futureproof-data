# CDE/PII Tagging Audit: raw-ingest-bea-rpp
**Date:** 2026-04-10
**Agent:** @cde-tagger
**Spec:** raw-ingest-bea-rpp
**Table:** `bronze.bea_rpp` (Iceberg: `raw.bea_rpp`)
**Contract:** `governance/data-contracts/raw-bea-rpp.yaml` *(pending @doc-generator — tags to be embedded from `governance/cde-tagging/raw-ingest-bea-rpp.md`)*
**Primary tagging document:** `governance/cde-tagging/raw-ingest-bea-rpp.md`
**PII scan reference:** `governance/pii-scans/raw-ingest-bea-rpp.md` (decision: NO PII)

## Domain Context Referenced
- `governance/domain-context.md` — BEA Regional Price Parities section (added 2026-04-10)
- `governance/eda/raw-bea-rpp-eda.md` — 51 rows (50 states + DC), 8 columns, single-year snapshot (`data_year=2024`), 100% `source_method = 'csv_cache'` on current load, 8 spec-verified values + 43 estimated placeholders pending live BEA API load
- **Concept Mapping Guidance for @cde-tagger (domain-context.md §BEA RPP):** `rpp_all_items`, `geo_fips`, `geo_name` explicitly auto-approved as CDEs; cross-reference BT-098 (Regional Price Parity)
- **Downstream consumers:** MCP tools `get_regional_price_parity(state)` and `compare_purchasing_power(salary, state_a, state_b)`; frontend salary adjustment display on Screens 4, 6, 8; stretch-goal Fight Location Lock boss
- **PII expectations:** NO PII — all 8 columns are non-personal; k-anonymity floor ~584,000; state-level aggregate safe under HIPAA Safe Harbor §164.514(b)(2)(i)(B)
- **Applicable regulations:** None — U.S. Government Work, public domain, zero personal data

## Columns Flagged as CDE

| Column | Rationale |
|--------|-----------|
| geo_fips | Primary key and **sole join key** for every downstream use of the table. The student's state selection (frontend or MCP) resolves to `state_fips` which joins back to this column through Silver and Gold. No substitute exists — `geo_name` is display-only and `rpp_all_items` is not unique (Iowa and Oklahoma tie at 87.8). Also the dedup grain for the Bronze→Silver promote. ANSI/FIPS external standard. Domain-context.md §BEA RPP auto-approves. |
| geo_name | Human-readable state name served as the display label by the MCP tool response and the frontend salary-adjustment UI (e.g., "In California, that's equivalent to about $58,700 in purchasing power"). Also the fallback identifier when a user or LLM passes a state by name rather than FIPS code or abbreviation. Without it, Gemma cannot produce the user-facing narrative. Domain-context.md §BEA RPP auto-approves. |
| rpp_all_items | **The entire analytical payload of the table.** Every derived field in Silver (`purchasing_power_multiplier`) and Gold (`cost_tier`, `adjusted_30k/50k/75k/100k`) is a pure function of this column. Every salary adjustment displayed to students on Screens 4, 6, 8, and in Fight Location Lock is `national_salary × (100 / rpp_all_items)`. Wrong values here silently mislead every student who selects that state. BT-098 (Regional Price Parity). Domain-context.md §BEA RPP auto-approves. **Highest-criticality column in the table.** |
| data_year | Provenance-critical temporal dimension. RPP is re-published annually and values shift year-over-year as BEA updates the underlying price index methodology. A mis-labeled vintage silently stales every downstream purchasing-power figure. Governs annual-refresh replacement semantics. Distinguishes the 8 spec-verified rows from the 43 estimated placeholder rows in the current load — the field that tells a future refresh "these rows are the 2024 vintage and may be replaced on next live BEA API load." Affects correctness of all derived values. P0 DQ rule: `data_year = 2024`. |

## Columns Flagged as PII

**None.** Per `governance/pii-scans/raw-ingest-bea-rpp.md`: all 8 columns are non-PII. State FIPS and state names are public jurisdiction identifiers, categorically non-PII under HIPAA Safe Harbor §164.514(b)(2)(i)(B). `rpp_all_items` is a macroeconomic aggregate (price index), not an individual measurement. Pipeline-metadata columns (`source_url`, `ingested_at`, `source_method`, `load_date`) carry no personal information. k-anonymity floor of the table is ~584,000 (smallest state population, Wyoming); every row represents hundreds of thousands to tens of millions of people in aggregate. No sensitivity classification above `public` applies. No RLS, no column masking, no encryption-beyond-baseline required.

## Columns Evaluated — Not Flagged

| Column | Reason Not Critical |
|--------|---------------------|
| source_url | Pipeline provenance metadata — BEA API endpoint or local CSV cache path. Not consumed by downstream business logic or user-facing display. Lineage captures provenance at better granularity. *Secrets-hygiene guardrail (not a CDE concern): ingestor must not persist the substituted `UserID=<API_KEY>` query parameter; store URL template or redact `UserID=REDACTED`.* |
| ingested_at | ETL batch timestamp. Identical across all 51 rows in a single load (batch stamp, not event time). Freshness is governed by the annual refresh cadence, not a per-row timestamp. Not a decision input. |
| source_method | Operational provenance enum (`bea_api` / `csv_cache`). Current load is 100% `csv_cache`. DQ rule must be `IN ('bea_api','csv_cache')`, NOT `= 'bea_api'`. Not consumed by downstream business logic. Could be re-considered as a quality-tier input in a future spec, but not a CDE in this Bronze zone. |
| load_date | Pipeline freshness metadata. Identical across all 51 rows. Not a decision input, not a personal date. |

## Decision Summary

| Metric | Value |
|--------|-------|
| Columns evaluated | 8 |
| Columns flagged CDE | **4** (`geo_fips`, `geo_name`, `rpp_all_items`, `data_year`) |
| Columns flagged PII | **0** |
| Columns not flagged | 4 (`source_url`, `ingested_at`, `source_method`, `load_date`) |
| Regulatory frameworks triggered | None |
| Sensitivity classification | `public` on all 8 columns |

## Handoff Notes

- **@doc-generator:** When generating `governance/data-contracts/raw-bea-rpp.yaml`, embed the column-level tag list from `governance/cde-tagging/raw-ingest-bea-rpp.md` §"Tag List for Data Contract". Set `is_cde: true` on the 4 flagged columns with the rationale strings provided; set `is_cde: false, is_pii: false` on the remaining 4. All 8 columns use `pii_classification: none`, `data_classification: public`.
- **@data-contract-author:** Mark contract quality tier as "High (for 8 spec-verified rows) / Medium (for 43 estimated rows) until the live BEA API load replaces estimates" per the EDA note in domain-context.md.
- **@governance-reviewer:** CDE count (4 of 8 = 50%) is higher than the pattern for peer raw tables (Karpathy raw: 5/13, BLS OOH raw: 5/15) — this reflects the tiny-reference-table nature of BEA RPP, where every non-metadata column is a load-bearing business column. Expected and defensible.
- **@cde-tagger (future runs):** CDE flags do NOT propagate. When tagging `silver-base-bea-rpp` and `gold-regional-price-parities`, re-evaluate each derived column (`state_abbr`, `census_region`, `purchasing_power_multiplier`, `cost_tier`, `adjusted_30k/50k/75k/100k`) on its own merits in those zones.
