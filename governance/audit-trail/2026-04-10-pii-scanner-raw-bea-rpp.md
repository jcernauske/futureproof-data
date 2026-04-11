# Audit Trail: @pii-scanner — raw-ingest-bea-rpp

**Date:** 2026-04-10
**Agent:** @pii-scanner
**Spec:** docs/specs/raw-ingest-bea-rpp.md
**Dataset:** bronze.bea_rpp (source file: data/raw/bea_cache/bea_rpp_2024.csv)
**Zone:** Bronze (Raw)
**Report produced:** governance/pii-scans/raw-ingest-bea-rpp.md

---

## Context

Scan requested by orchestrator to verify the zero-PII claim in `governance/domain-context.md` BEA RPP section. Domain context states: "51-row state-level macroeconomic reference table from BEA; all values are public-domain aggregate statistics; no individual-level data of any kind; no sensitivity review required at any zone."

Task: independently verify by scanning all 8 columns for PII and quasi-identifiers.

---

## Inputs Read

| Path | Purpose |
|------|---------|
| docs/specs/raw-ingest-bea-rpp.md | Understand schema, source, and ingest method |
| governance/domain-context.md (BEA RPP section, lines 1352–1506) | Read declared PII expectations |
| data/raw/bea_cache/bea_rpp_2024.csv | Inspect actual source data (all 51 rows) |
| governance/pii-scans/raw-ingest-bls-ooh-pii-scan.md | Reference format for project conventions |

---

## Scope

- **Records scanned:** 51 (full population — 50 states + DC)
- **Columns scanned:** 8
  1. geo_fips
  2. geo_name
  3. rpp_all_items
  4. data_year
  5. source_url
  6. ingested_at
  7. source_method
  8. load_date

The current source file contains only 4 raw columns (`GeoFips, GeoName, TimePeriod, DataValue`); the remaining 4 columns (`source_url, ingested_at, source_method, load_date`) are ingestor-populated operational metadata per the spec. All 8 were evaluated.

---

## Detection Methods Used

| Method | Applied To | Result |
|--------|-----------|--------|
| Field-name heuristic | All 8 columns | No column name matches PII lexicon (name, email, phone, ssn, tin, ein, dob, addr, zip, account, card, patient, member, employee). `geo_name` matched "name" substring but context (field semantics + observed values) confirms geographic name, not person name. |
| Full-value enumeration | geo_fips, geo_name | 51 values each — exhaustively reviewed. All are U.S. state / DC identifiers. |
| Format-specific regex (SSN, EIN, TIN, credit card, phone, email) | All string columns | Zero matches. |
| Luhn check (credit card) | Numeric and string columns | Zero matches. |
| NER (simulated via lexical review) | geo_name | All values are GPE (geo-political entity) at state level. LOCATION at state-level is not PII per HIPAA Safe Harbor and standard privacy frameworks. |
| k-anonymity analysis | Full record | Smallest population represented by any row ≈ 584,000 (Wyoming). k-anonymity floor is orders of magnitude above any small-cell disclosure threshold. |
| Temporal linkability check | ingested_at, data_year, load_date | Single-year reference period; batch timestamp shared across all rows. No per-individual temporal pattern. |
| External-join re-identification simulation | geo_fips + rpp_all_items + data_year | Any join to external data is a state-level join, not a person-level join. No amplification risk. |

---

## Decisions and Rationale

### Decision 1: geo_name is not PII despite containing "name"

**Context:** Field-name heuristic flagged substring "name". Values reviewed: all 51 are U.S. state or jurisdiction names ("Alabama" through "Wyoming" plus "District of Columbia").

**Rationale:** A state name is a public jurisdiction label, not a personal name. No individual can be re-identified from knowing that a row represents "California". The k-anonymity floor is ~584,000 (Wyoming), vastly above any disclosure threshold.

**Decision:** Not PII. No sensitivity classification.

### Decision 2: geo_fips is not a Government ID in the sensitive sense

**Context:** PII lexicon includes "Government IDs". FIPS codes are government-issued identifiers.

**Rationale:** FIPS state codes identify jurisdictions (states), not persons or legal entities in a privacy-relevant sense. They are public, static, and used in every open U.S. government dataset. Format (2-digit numeric, values 01–56 with intentional gaps at 03/07/14/43/52) does not overlap with SSN, EIN, passport, driver's license, or any personal ID format.

**Decision:** Not PII. Whitelist field and value range.

### Decision 3: rpp_all_items is not Financial PII

**Context:** PII lexicon includes "Financial Accounts" and financial data.

**Rationale:** RPP is a macroeconomic price index published as an aggregate statistic. It is not a measurement of any individual's income, spending, wealth, or transactions. A price level index for a state cannot be inverted to any personal attribute.

**Decision:** Not PII. Not financial PII.

### Decision 4: ingested_at, load_date, data_year are not DOB / personal dates

**Context:** PII lexicon includes "Dates of Birth" and other personal dates.

**Rationale:** These are operational batch metadata and statistical reference period — not personal dates. `ingested_at` and `load_date` identify when the ETL job ran; `data_year` identifies the year of the statistical publication (2024). No row represents an individual, so no row has a personal date.

**Decision:** Not PII.

### Decision 5: source_url secrets-hygiene observation (not a PII finding)

**Context:** The BEA API URL may, if the ingestor persists the fully-substituted URL, contain `UserID=<API_KEY>`. `UserID` here is a service API key, not a personal identifier.

**Rationale:** An API key is a credential/secret, not PII. It does not identify a natural person. However, committing secrets to a governed Iceberg table is a separate hygiene concern that should be raised with @primary-agent / @governance-reviewer. This was called out in the PII scan report as a "process guardrail" rather than a PII finding.

**Decision:** Not a PII finding. Flag as a secrets-hygiene guardrail for @primary-agent to verify. Do not forward to @policy-engineer.

### Decision 6: No quasi-identifiers

**Rationale:** The combination `(geo_fips, rpp_all_items, data_year)` identifies a U.S. state in a given year — a population of hundreds of thousands to tens of millions of people. The smallest row represents ~584,000 residents. State-level geographic aggregation is categorically safe under HIPAA Safe Harbor §164.514(b)(2)(i)(B) (which only becomes concerning at ZIP-3 granularity or smaller — states are far larger). No joinable external dataset can escalate this to person-level re-identification.

**Decision:** No quasi-identifiers present.

---

## False Positive Log

| Field | Detection Trigger | Decision | Rationale |
|-------|-------------------|----------|-----------|
| geo_name | "name" substring in field name | False positive | Values are U.S. state/jurisdiction names, not person names. |
| geo_fips | "Government ID" category | False positive | FIPS state codes identify jurisdictions, not persons. |
| source_url | URLs may contain personal info in query params | False positive (with process guardrail) | BEA API URL contains no personal info. UserID query param is a service API key (secret, not PII) — guardrail forwarded to @primary-agent. |

---

## Final Classification

| Level | Label | Count | Fields |
|-------|-------|-------|--------|
| 1 | Public | 0 | — |
| 2 | Internal | 0 | — |
| 3 | Confidential | 0 | — |
| 4 | Restricted | 0 | — |

**PII instances found:** 0
**Quasi-identifiers found:** 0
**Decision:** NO PII — zero-PII claim verified

---

## Regulatory Implications Checked

HIPAA, FERPA, GDPR, CCPA/CPRA, PCI DSS, SOX, GLBA — **none apply.** All values are U.S. Government Work in the public domain, published by BEA as open statistical data.

---

## Handoff

| Consumer | Signal |
|----------|--------|
| @policy-engineer | No policy work required. No RLS, column masking, or encryption-for-privacy needed. Table is `public` tier for PII purposes. |
| @primary-agent | Verify `source_url` does not persist BEA `UserID` API key. Operational secrets-hygiene check, not PII remediation. |
| @data-contract-author | Contract may declare `pii_classification: none`, `data_classification: public` for all 8 columns. |
| @cde-tagger | No PII / sensitivity CDE tags required. |
| @doc-generator | Data dictionary may note `pii: false, sensitivity: public` for all 8 columns. |
| Downstream zones (Silver base.bea_rpp, Gold consumable.regional_price_parities, MCP) | Skip PII remediation. Derived fields (state_abbr, census_region, purchasing_power_multiplier, cost_tier, adjusted_*k) are transformations of the same non-PII inputs and introduce no new PII. Future scans of those zones should reference this report. |

---

## Artifacts Produced

- `governance/pii-scans/raw-ingest-bea-rpp.md` — full PII scan report
- `governance/audit-trail/2026-04-10-pii-scanner-raw-bea-rpp.md` — this audit trail

---

*— End of Audit Trail —*
