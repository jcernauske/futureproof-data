## PII Scan Report: base.bea_rpp
**Date:** 2026-04-10
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance — BEA Regional Price Parities sub-domain (U.S. macroeconomic / state-level cost-of-living reference data)
**Spec:** docs/specs/silver-base-bea-rpp.md
**Parent Spec:** docs/specs/raw-ingest-bea-rpp.md
**Upstream Scan:** governance/pii-scans/raw-ingest-bea-rpp.md (2026-04-10, decision: NO PII)
**Zone:** Silver
**Source table:** bronze.bea_rpp (51 rows, 8 columns, already certified zero-PII)
**Silver table:** base.bea_rpp (51 rows, 11 columns)
**Records Scanned:** 51 (50 U.S. states + District of Columbia — full population, identical to Bronze)
**Columns Scanned:** 11 (record_id, state_fips, state_name, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, verification_status, data_year, source_load_date, ingested_at)
**PII Instances Found:** 0
**Quasi-identifiers Found:** 0
**Decision:** NO PII — zero-PII claim holds across all 11 Silver columns

---

### Scan Scope and Method

Because Bronze (`bronze.bea_rpp`) has already been certified zero-PII with full per-field analysis, this Silver scan is a **delta scan**. Its job is to verify that the Silver transformation does not introduce any new PII, quasi-identifiers, or re-identification risk via:

1. Passthrough fields that might be reshaped in a privacy-meaningful way (e.g., truncation, combination)
2. Newly derived fields from in-code lookups (`state_abbr`, `census_region`)
3. Newly computed numeric fields (`purchasing_power_multiplier`)
4. Newly derived categorical fields (`verification_status`)
5. New operational columns (`record_id`, Silver `ingested_at`, `source_load_date`)
6. Grain changes or cell-size changes that would alter k-anonymity

The grain of `base.bea_rpp` is **identical to Bronze** — one row per `state_fips`, 51 rows, no fan-out, no filter, no collapse. Every k-anonymity property of the Bronze scan carries forward unchanged.

---

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| — | — | — | — | — | — | No PII detected in any field |

---

### Field-by-Field Delta Analysis

| # | Field | Origin | Type | Example | PII Risk | Quasi-ID Risk | Assessment |
|---|-------|--------|------|---------|----------|---------------|------------|
| 1 | record_id | **New (Silver)** | string | `"rpp:06"`, `"rpp:19"` (hash/concat form per `compute_grain_id`) | None | None | Deterministic grain identifier built from `['state_fips']` with prefix `rpp`. Derived entirely from a non-PII input (state FIPS), so the output is a transformation of non-PII and inherits non-PII status. Cannot encode anything about an individual. 51 distinct values, one per state. Not a pseudonym for a person — it is a pseudonym for a jurisdiction. |
| 2 | state_fips | Bronze passthrough (renamed `geo_fips` → `state_fips`) | string | `"06"`, `"19"`, `"11"` | None | None | Already certified non-PII in Bronze. Field rename only, no value change. 2-digit ANSI/FIPS state code. State-level jurisdiction identifier — categorically non-PII under HIPAA Safe Harbor §164.514(b)(2)(i)(B). |
| 3 | state_name | Bronze passthrough (renamed `geo_name` → `state_name`) | string | `"California"`, `"Iowa"`, `"District of Columbia"` | None | None | Already certified non-PII in Bronze. Field rename only. Full U.S. state / jurisdiction name. Not a personal name. |
| 4 | state_abbr | **New (Silver, derived from in-code FIPS→USPS lookup)** | string | `"CA"`, `"IA"`, `"DC"` | None | None | 2-letter USPS postal abbreviation for a U.S. state. Derived deterministically from `state_fips` via a structural 51-entry lookup constant. A state abbreviation is a public jurisdiction label, not a personal identifier. No additional information is encoded — `state_abbr` is **isomorphic** to `state_fips` (1:1 bijection per DQ rule). A transformation that is 1:1 with a non-PII field cannot introduce PII. Does not match any sensitive ID format (SSN, EIN, ICD, passport, etc.) — it is exactly 2 uppercase letters. |
| 5 | census_region | **New (Silver, derived from in-code FIPS→region lookup)** | string | `"Northeast"`, `"Midwest"`, `"South"`, `"West"` | None | None | One of four U.S. Census Bureau regional groupings. Deterministic lookup from `state_fips`. This is actually a **generalization** (51→4), which *reduces* specificity and *strengthens* k-anonymity. The smallest region by population is the Northeast at ~57M residents; the largest is the South at ~128M. Cannot re-identify an individual. DC quirk (assigned to South) is a documented taxonomy detail, not a privacy concern. |
| 6 | rpp_all_items | Bronze passthrough, unchanged | double | `110.7`, `87.8`, `100.3` | None | None | Already certified non-PII in Bronze. Macroeconomic price index. Unchanged value, unchanged semantics. |
| 7 | purchasing_power_multiplier | **New (Silver, computed)** | double | `0.9034`, `1.1390`, `0.9970` | None | None | `100.0 / rpp_all_items`. A pure reciprocal transformation of a non-PII aggregate is still a non-PII aggregate. The output is mathematically a function of a single state-level index number — it encodes no additional information about any individual. Every row is still a statistical aggregate over hundreds of thousands to tens of millions of people. Range per DQ rule: `0.7 ≤ x ≤ 1.3`. |
| 8 | verification_status | **New (Silver, derived from 8-state allow-list)** | string | `"bea_official"`, `"estimate"` | None | None | Per-row categorical provenance label. Two-valued enum. Derived from a hard-coded allow-list of 8 `state_fips` codes. Encodes data-quality provenance of the row, not anything about individuals. A provenance tag on a state-level aggregate inherits the non-PII status of the aggregate. The allow-list itself contains only state FIPS codes (public jurisdiction identifiers), not PII. |
| 9 | data_year | Bronze passthrough | int | `2024` | None | None | Already certified non-PII in Bronze. Constant across all 51 rows. Publication reference year, not a date of birth or event date. |
| 10 | source_load_date | Bronze passthrough (renamed `load_date` → `source_load_date`) | date | `2026-04-10` | None | None | Already certified non-PII in Bronze. Operational ETL timestamp. Same value across all rows. |
| 11 | ingested_at | **New (Silver promotion timestamp)** | timestamp | `2026-04-10T...Z` | None | None | Timestamp of the Silver promotion run. Same value across all 51 rows (batch stamp). Identifies when the ETL job ran, not when any individual did anything. No behavioral or personal timing information. Standard operational provenance field, categorically non-PII. |

---

### Summary by Sensitivity
| Level | Label | Count | Fields Affected |
|-------|-------|-------|-----------------|
| 1 | Public | 0 | — |
| 2 | Internal | 0 | — |
| 3 | Confidential | 0 | — |
| 4 | Restricted | 0 | — |

All 11 Silver columns are non-PII. The 8 Bronze-passthrough columns inherit their prior classification. The 3 new derived columns (`state_abbr`, `census_region`, `purchasing_power_multiplier`), the new grain identifier (`record_id`), the new provenance label (`verification_status`), and the new Silver batch timestamp (`ingested_at`) all derive deterministically from non-PII inputs and introduce no new PII.

---

### Quasi-Identifier and k-Anonymity Delta Analysis

A Silver transformation can break a Bronze zero-PII claim in exactly three ways. Each is explicitly checked here.

| Risk Vector | Check | Result |
|-------------|-------|--------|
| **Grain refinement** — did Silver split rows to a finer grain (e.g., state → county) that represents a smaller population? | Grain is unchanged at `[state_fips]`. Row count remains exactly 51. | PASS — k-anonymity floor is identical to Bronze (~584,000, Wyoming). |
| **Combination of low-cardinality fields that together create a fingerprint** — could `state_abbr + census_region + purchasing_power_multiplier + verification_status + data_year` narrow a cell to a small population? | Every combination is a function of `state_fips`. The combined tuple is isomorphic to `state_fips` and identifies exactly one state — a jurisdiction, not a person. Population-per-cell is identical to Bronze (~584K to ~39M). | PASS — no narrowing effect. |
| **Introduction of a direct personal field** (name, address, DOB, SSN, phone, email, GPS, biometric) via derivation or join | No joins occur in this Silver transformation. No derivations introduce person-level fields. `state_abbr` is a 2-letter postal code (not initials of a person). `census_region` is a 4-valued taxonomy. `purchasing_power_multiplier` is a numeric index. `verification_status` is a 2-valued enum. `record_id` is a deterministic hash of `state_fips`. None of these fields have any person-level semantic. | PASS — no direct personal fields introduced. |
| **Generalization reduction** — did Silver introduce a field that *decreases* k-anonymity relative to Bronze? | `census_region` is a *generalization* (4 values, 50M+ per region) and `state_abbr` is *1:1 isomorphic* to `state_fips`. Neither refines or disaggregates. | PASS — k-anonymity is either preserved or strengthened. |
| **Temporal linkability** — does Silver add a new temporal column at a finer grain that could enable behavioral fingerprinting? | Two new temporal columns exist (`source_load_date`, `ingested_at`), but both are batch-level — identical across all 51 rows and tied to ETL runs, not to any individual event. `data_year` remains a constant `2024`. | PASS — no within-row temporal variation usable for linkage. |
| **External join amplification** — does Silver make the table more joinable to person-level external data? | `state_abbr` and `census_region` are common external-join keys, but any external join using these fields still resolves at the state or region level, not at the person level. External data that can be joined on a state does not yield a person-level link. | PASS — join targets remain state/region aggregates. |

**Verdict:** No quasi-identifiers, no k-anonymity degradation. The k-anonymity floor is unchanged at ~584,000 (Wyoming). State-level aggregation remains categorically safe under HIPAA Safe Harbor, FERPA, GDPR, and CCPA.

---

### False Positive Candidates
| Field | Could Look Like | Why It's Not PII | Recommendation |
|-------|-----------------|------------------|----------------|
| state_abbr | "Initials" to a naive NER/heuristic matcher | Values are strictly drawn from the canonical 51-member USPS postal-code set (`AL`, `AK`, ..., `DC`). Format is exactly 2 uppercase letters, but the value space is bounded and public. No overlap with personal initials as a PII concept. | Whitelist the 51 USPS values; do not surface as a PII finding. |
| census_region | "Geographic location" to a naive location-PII matcher | 4-valued enum, each value covering ~57M to ~128M residents. A region is a jurisdiction grouping, not an address or coordinate. | Whitelist the 4 values. |
| record_id | "Pseudonymized identifier" to a naive ID-PII matcher | Pseudonym for a state (jurisdiction), not for a person. Derived from a non-PII input. Cannot be de-anonymized to an individual because the input population is an entire state. | No action; document as a jurisdiction key. |
| verification_status | "Status code that might be a user status" | 2-valued enum `{bea_official, estimate}` describing data-quality provenance of a row. Not a user status, not a PII field. | No action. |

---

### Regulatory Implications

**None.** The Silver transformation introduces no personal data. Inherited from Bronze:

| Regulation | Applies? | Rationale |
|------------|----------|-----------|
| HIPAA | No | No health information. State-level aggregation is explicitly safe under Safe Harbor §164.514(b)(2)(i)(B). |
| FERPA | No | No education records, no students. |
| GDPR | No | No personal data of EU data subjects. Aggregates over ~584K to ~39M people per row are not personal data under Article 4(1). |
| CCPA / CPRA | No | No personal information of California residents. |
| PCI DSS | No | No payment card data. |
| SOX | No | No financial records of any reporting entity. |
| GLBA | No | No nonpublic personal financial information. |

**Data classification:** `public`. All values are U.S. Government Work in the public domain (BEA publication) plus deterministic transformations thereof.

---

### Recommendations

**For @policy-engineer:**
- **No RLS, no column masking, no encryption-at-rest-beyond-baseline required for PII reasons.** `base.bea_rpp` may be written as plaintext to Iceberg with no row-level security predicates.
- `public` access tier is appropriate. Any access controls should be operational (governance roles) rather than privacy-motivated.

**For @data-contract-author:**
- Contract may declare `pii_classification: none` and `data_classification: public` for all 11 columns.

**For @cde-tagger:**
- No CDE tags required for PII/sensitivity reasons. Standard business-critical tagging (`state_abbr`, `census_region`, `purchasing_power_multiplier` as join keys and core measures) applies independently.

**For @doc-generator:**
- Data dictionary entries for all 11 columns may note `pii: false, sensitivity: public`.

**For downstream zones (Gold `consumable.regional_price_parities`, MCP tools, frontend):**
- The zero-PII posture propagates forward. Any Gold derivations (e.g., `cost_tier`, `adjusted_30k/50k/75k/100k` salary columns) are further transformations of these same non-PII inputs and likewise introduce no PII. Downstream PII scans of Gold and MCP artifacts for this source may reference this Silver report as evidence and confirm no new person-level fields are introduced.

**For @primary-agent (Silver implementer):**
- No special handling required. Standard Silver promotion pattern applies.

---

### Justification (One-Line Summary)

"Zero-PII claim from `bronze.bea_rpp` holds across all 11 Silver columns — the 3 new derived columns (`state_abbr`, `census_region`, `purchasing_power_multiplier`) are deterministic 1:1 or generalizing transformations of a non-PII state FIPS code, `verification_status` and `record_id` encode provenance of state-level aggregates not individuals, and the grain is unchanged at 51 state rows so the k-anonymity floor remains ~584,000."
