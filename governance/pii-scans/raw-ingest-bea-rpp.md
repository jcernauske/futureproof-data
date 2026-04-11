## PII Scan Report: bronze.bea_rpp
**Date:** 2026-04-10
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance — BEA Regional Price Parities sub-domain (U.S. macroeconomic / state-level cost-of-living reference data)
**Spec:** docs/specs/raw-ingest-bea-rpp.md
**Source file scanned:** data/raw/bea_cache/bea_rpp_2024.csv
**Records Scanned:** 51 (50 U.S. states + District of Columbia — full population)
**Columns Scanned:** 8 (geo_fips, geo_name, rpp_all_items, data_year, source_url, ingested_at, source_method, load_date)
**PII Instances Found:** 0
**Quasi-identifiers Found:** 0
**Decision:** NO PII — zero-PII claim verified

---

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| — | — | — | — | — | — | No PII detected in any field |

---

### Field-by-Field Analysis

| # | Field | Type | Example | PII Risk | Quasi-ID Risk | Assessment |
|---|-------|------|---------|----------|---------------|------------|
| 1 | geo_fips | string | `"06"`, `"19"`, `"11"` | None | None | 2-digit ANSI/FIPS state code. Identifies a U.S. state (jurisdiction), not a person, household, or address. State-level geographic identifiers are categorically non-PII under HIPAA Safe Harbor and every other U.S. privacy framework. No sub-state granularity (no county, tract, ZIP, or block). 51 distinct values, each representing ~700K–39M people; cannot re-identify an individual. |
| 2 | geo_name | string | `"California"`, `"Iowa"`, `"District of Columbia"` | None | None | Full U.S. state / jurisdiction name. Same analysis as geo_fips — a state name is a public jurisdiction label, not a personal name. Field-name heuristic ("geo_name") confirms geographic, not person, context. No individuals, officers, or custodians named. |
| 3 | rpp_all_items | double | `110.7`, `87.8`, `100.3` | None | None | BEA Regional Price Parity index (national = 100.0). A macroeconomic price index is a statistical aggregate, not a measurement of any individual's income, spending, wealth, or transactions. Observed range in current load: [86.9, 110.7]. Cannot be inverted to any personal attribute. |
| 4 | data_year | int | `2024` | None | None | Year of the RPP estimate. Constant `2024` across all 51 rows in the current load. A calendar year is not a date of birth, event date, or any personal temporal attribute — it is the reference period for the statistical publication. |
| 5 | source_url | string | `"https://apps.bea.gov/api/data/..."` or cache path | None | None | URL or local path identifying the provenance of the load (BEA public API endpoint or local CSV cache path). Contains no user credentials, no API key (API key is loaded from `.env` at runtime and not persisted into the URL column), no personal identifiers. Public BEA API URL is the same for all consumers. |
| 6 | ingested_at | timestamp | `2026-04-10T...Z` | None | None | Pipeline batch timestamp. Identifies when the ETL job ran, not when any individual did anything. All 51 rows share the same value (batch stamp, not event time). No behavioral or personal timing information. |
| 7 | source_method | string | `"bea_api"` or `"csv_cache"` | None | None | Enum identifying whether the row came from the live BEA API or the CSV fallback. Operational provenance metadata. No personal information. |
| 8 | load_date | date | `2026-04-10` | None | None | Date the load ran. Operational metadata, identical across all 51 rows. Not a date of birth, event date, or any personal date. |

---

### Summary by Sensitivity
| Level | Label | Count | Fields Affected |
|-------|-------|-------|-----------------|
| 1 | Public | 0 | — |
| 2 | Internal | 0 | — |
| 3 | Confidential | 0 | — |
| 4 | Restricted | 0 | — |

All 8 columns are non-PII operational, geographic, or aggregate-statistical fields. No sensitivity classification is required.

---

### Quasi-Identifier Re-identification Analysis

A quasi-identifier is a field (or combination of fields) that, when joined with external data, could re-identify an individual. The strongest re-identification test is the k-anonymity question: "what is the smallest population any single row represents?"

| Check | Result |
|-------|--------|
| Smallest population represented by any row | Wyoming, ~584,000 residents (2024 Census estimate). DC ~680,000. All other rows represent millions. |
| k-anonymity floor | k ≈ 584,000 (every row is an aggregate over hundreds of thousands to tens of millions of people) |
| Combination test (geo_fips + rpp_all_items + data_year) | Still identifies only a U.S. state in a given year — no individual can be isolated |
| External-join re-identification | Joining this table to any external dataset yields state-level joins, not person-level joins. No amplification risk. |
| Temporal linkability | Single-year snapshot, single batch timestamp shared across all rows. No temporal pattern that could link to an individual's behavior. |
| Small-cell risk | None — the smallest cell (Wyoming) represents ~584K people, orders of magnitude above any small-cell disclosure threshold. |

**Verdict:** No quasi-identifiers. Every row represents a U.S. state aggregating hundreds of thousands to tens of millions of people. State-level geographic aggregation is categorically safe under HIPAA Safe Harbor (§164.514(b)(2)(i)(B) — geographic units of first three ZIP digits or larger; a state is far larger), FERPA, GDPR, and CCPA.

---

### False Positive Candidates
| Field | Could Look Like | Why It's Not PII | Recommendation |
|-------|-----------------|------------------|----------------|
| geo_name | "Personal name" to a naive NER model | Values are exclusively U.S. state / jurisdiction names, not individual names. Any NER model flagging "California" or "New York" as LOCATION is correct — and LOCATION at state-level is not PII. | Whitelist the 51 state + DC values; do not surface as a PII finding. |
| geo_fips | "Government ID" to a naive regex matcher | FIPS state codes are 2-digit public jurisdiction identifiers (01–56 with intentional gaps), not SSN, EIN, or personal IDs. Format does not overlap with any sensitive ID format. | Whitelist field name and value range. |
| source_url | "URL that could contain PII in query params" | BEA public API URL contains only `UserID`, `method`, `datasetname`, `TableName`, `LineCode`, `Year`, `GeoFips`, `ResultFormat` query params. `UserID` is an API key for service auth; per spec the key is read from `.env` and NOT persisted in the stored `source_url` column (ingestor should store the template or redact `UserID`). | Verify at ingest that `UserID` is stripped or not substituted into the stored URL. Flagged as a 0% finding here, but noted as a process guardrail below. |

---

### Process Guardrail (Not a Finding)

The `source_url` field, if the ingestor were to persist the fully-substituted BEA API URL, could contain the `UserID=<API_KEY>` query parameter. This is **not PII** (it is a service credential, not a personal identifier), but it is a secret that should not be committed to the Iceberg table or audit logs. @primary-agent should ensure the ingestor:

1. Reads `BEA_API_KEY` from `.env` at runtime, and
2. Either stores the URL template (e.g., `https://apps.bea.gov/api/data/?method=GetData&datasetname=Regional&TableName=SARPP&LineCode=1&Year=2024&GeoFips=STATE&ResultFormat=JSON`) without the `UserID` parameter, or redacts `UserID` to a placeholder like `UserID=REDACTED`.

This is a **secrets-hygiene concern, not a PII concern.** Forwarding to @governance-reviewer / @primary-agent for operational verification — not to @policy-engineer (no data-access policy needed).

---

### Regulatory Implications

**None.** This dataset contains zero personal data.

| Regulation | Applies? | Rationale |
|------------|----------|-----------|
| HIPAA | No | No health information. No individuals at all. State-level geographic aggregation is explicitly safe under Safe Harbor §164.514(b)(2)(i)(B). |
| FERPA | No | No education records. No students. |
| GDPR | No | No personal data of EU data subjects. The dataset is U.S.-only and contains no person-level records. Even if it reached EU consumers, state-level aggregate statistics are not "personal data" under Article 4(1). |
| CCPA / CPRA | No | No personal information of California residents. California appears only as a row representing ~39M residents in aggregate. |
| PCI DSS | No | No payment card data. |
| SOX | No | No financial records of any reporting entity. |
| GLBA | No | No nonpublic personal financial information. |

**All values are U.S. Government Work in the public domain**, published by the Bureau of Economic Analysis as open statistical data under the U.S. Federal Open Data Policy. No license or access restriction applies.

---

### Recommendations

**For @policy-engineer:**
- **No RLS, no column masking, no encryption-at-rest-beyond-baseline required for PII reasons.** This table may be written as plaintext to Iceberg with no row-level security predicates on any personal dimension.
- A `public` access tier is appropriate. Any access controls should be operational (e.g., governance roles) rather than privacy-motivated.

**For @primary-agent (ingestor):**
- Verify that `source_url` does not persist the BEA `UserID` API key. Either store the URL template without the key, or substitute `UserID=REDACTED`. This is a secrets-hygiene guardrail, not a PII finding.

**For @data-contract-author:**
- Contract may declare `pii_classification: none` and `data_classification: public` for all 8 columns.

**For @cde-tagger:**
- No CDE tags required for PII / sensitivity. Standard business-critical tagging (e.g., `rpp_all_items` as a key measure) applies independently.

**For @doc-generator:**
- Data dictionary entries may note `pii: false, sensitivity: public` for all 8 columns.

**Pipeline-level recommendation:** **Skip PII remediation steps for all downstream zones (Silver, Gold, MCP)** of this pipeline. Future scans of `base.bea_rpp` and `consumable.regional_price_parities` should reference this report and confirm no PII has been introduced via Silver/Gold derivations (derived fields `state_abbr`, `census_region`, `purchasing_power_multiplier`, `cost_tier`, `adjusted_30k/50k/75k/100k` are all transformations of the same non-PII inputs and introduce no new PII).

---

### Justification (One-Line Summary)

"governance/domain-context.md BEA RPP PII Expectations section confirms no personal data — 51 state-level aggregate rows, k-anonymity floor ~584,000, no individuals of any kind, no quasi-identifiers."
