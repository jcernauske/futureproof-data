## PII Scan Report: consumable.regional_price_parities
**Date:** 2026-04-11
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance — BEA Regional Price Parities sub-domain (U.S. macroeconomic / state-level cost-of-living reference data)
**Spec:** docs/specs/gold-regional-price-parities.md
**Parent Specs:** docs/specs/silver-base-bea-rpp.md, docs/specs/raw-ingest-bea-rpp.md
**Upstream Scans:**
- governance/pii-scans/raw-ingest-bea-rpp.md (2026-04-10, decision: NO PII)
- governance/pii-scans/silver-base-bea-rpp.md (2026-04-10, decision: NO PII, k-anonymity floor ~584,000)

**Zone:** Gold (Consumable)
**Silver source:** base.bea_rpp (51 rows, 11 columns, certified zero-PII)
**Gold table:** consumable.regional_price_parities (51 rows, 15 columns)
**Records Scanned:** 51 (50 U.S. states + District of Columbia — full population, identical grain to Silver and Bronze)
**Columns Scanned:** 15 (record_id, state_fips, state_name, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, cost_tier, adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k, verification_status, data_year, promoted_at)
**PII Instances Found:** 0
**Quasi-identifiers Found:** 0
**k-Anonymity Floor:** ~584,000 (Wyoming — unchanged from Silver/Bronze)
**Decision:** **NO PII** — zero-PII claim from Bronze and Silver holds across all 15 Gold columns

---

### Scan Scope and Method

Bronze (`bronze.bea_rpp`) and Silver (`base.bea_rpp`) have both been certified zero-PII with full per-field analysis and a verified ~584K k-anonymity floor. This Gold scan is a **delta scan** focused on the 4 newly derived columns and the 1 new operational column that Gold introduces beyond Silver. It verifies that none of the Gold derivations:

1. Introduce person-level fields (names, addresses, DOBs, SSNs, phones, emails, GPS, biometric, health, financial accounts)
2. Disaggregate Silver's state-level grain to a finer (and therefore smaller-population) grain
3. Combine with passthrough fields to form a quasi-identifier fingerprint
4. Inject external person-level data via joins
5. Introduce individual-level earnings, wages, or compensation data
6. Introduce temporal variation at a grain finer than the Silver batch timestamp

The grain of `consumable.regional_price_parities` is **identical to Silver and Bronze** — one row per `state_fips`, 51 rows. No fan-out, no filter, no collapse, no join. This is the "pure shaping" Gold pattern described in the spec: row-for-row promote with 4 derived columns and 1 carry-forward preserved.

Per the spec, the Gold agent workflow explicitly lists **"@pii-scanner — no PII, expected SKIP"** (step 11). This scan discharges that expectation with an explicit delta verification rather than a blind skip.

---

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| — | — | — | — | — | — | No PII detected in any of the 15 Gold columns |

---

### Field-by-Field Delta Analysis

All 11 Silver columns either pass through unchanged or are explicitly carried forward; the prior Silver scan's per-field analysis applies verbatim. Columns flagged **New (Gold)** below are the delta requiring fresh analysis.

| # | Field | Origin | Type | Example | PII Risk | Quasi-ID Risk | Assessment |
|---|-------|--------|------|---------|----------|---------------|------------|
| 1 | record_id | **Regenerated (Gold, new prefix)** | string | `"rpc:06"`, `"rpc:19"` | None | None | Deterministic grain identifier built from `compute_grain_id(row, ['state_fips'], prefix='rpc')`. Same derivation pattern as Silver's `rpp:*` record_id but with the `rpc` prefix to mark the Gold consumable zone. A pseudonym for a state, not a person. Derived from non-PII input, inherits non-PII status. 51 distinct values, one per state. |
| 2 | state_fips | Silver passthrough | string | `"06"`, `"19"`, `"11"` | None | None | Certified non-PII in Bronze and Silver. Unchanged. |
| 3 | state_name | Silver passthrough | string | `"California"`, `"Iowa"`, `"District of Columbia"` | None | None | Certified non-PII in Bronze and Silver. Unchanged. Jurisdiction label, not a personal name. |
| 4 | state_abbr | Silver passthrough | string | `"CA"`, `"IA"`, `"DC"` | None | None | Certified non-PII in Silver. 2-letter USPS code. Bounded 51-value public enum. |
| 5 | census_region | Silver passthrough | string | `"Northeast"`, `"Midwest"`, `"South"`, `"West"` | None | None | Certified non-PII in Silver. 4-valued generalization (~57M–128M residents per region) — *strengthens* rather than weakens k-anonymity. |
| 6 | rpp_all_items | Silver passthrough | double | `110.7`, `87.8`, `100.3` | None | None | Certified non-PII in Bronze and Silver. Published macroeconomic price index. |
| 7 | purchasing_power_multiplier | Silver passthrough | double | `0.9034`, `1.1390`, `0.9970` | None | None | Certified non-PII in Silver. Reciprocal of `rpp_all_items / 100`. |
| 8 | cost_tier | **New (Gold, derived)** | string | `"very_high"`, `"high"`, `"average"`, `"low"`, `"very_low"` | None | None | 5-bucket enum derived from `rpp_all_items` via a fixed CASE expression (≥108 / ≥103 / ≥97 / ≥91 / else). This is a **lossy generalization** of a single non-PII numeric column — information-theoretically, `cost_tier` contains strictly less information than `rpp_all_items`. A lossy function of a non-PII input cannot encode additional information about any individual. The 5 tiers each cover multiple states totaling tens to hundreds of millions of residents, so the per-tier k-anonymity is even larger than the per-state floor of ~584K. Not a financial, health, contact, or biometric attribute. Does not match any sensitive ID format (no digits, no fixed-length code patterns, no address structure). |
| 9 | adjusted_30k | **New (Gold, derived)** | double | `27102.98` (CA), `34168.56` (IA) | None | None | Computed as `30000.0 × purchasing_power_multiplier`, rounded to 2 decimals. **This is NOT individual earnings data.** The `30000` is a fixed national constant, not an observed salary of any person. The output is a 1:1 scalar transformation of `purchasing_power_multiplier` (which is itself non-PII), and therefore inherits non-PII status. Mathematically equivalent to publishing the same state-level RPP index expressed in dollars at a $30K reference point. No individual wage, compensation, account, or financial record is referenced or reconstructible. Every row aggregates over an entire state population (~584K to ~39M). |
| 10 | adjusted_50k | **New (Gold, derived)** | double | `45167.12` (CA), `56947.61` (IA) | None | None | Computed as `50000.0 × purchasing_power_multiplier`, rounded to 2 decimals. Identical privacy analysis to `adjusted_30k`. A fixed national anchor ($50K) multiplied by a non-PII state-level index. Not an individual salary. 1:1 scalar function of `purchasing_power_multiplier`. |
| 11 | adjusted_75k | **New (Gold, derived)** | double | `67750.68` (CA), `85421.41` (IA) | None | None | Computed as `75000.0 × purchasing_power_multiplier`, rounded to 2 decimals. Identical privacy analysis to `adjusted_30k`. Fixed $75K anchor × state-level index. Not an individual salary. 1:1 scalar function of `purchasing_power_multiplier`. |
| 12 | adjusted_100k | **New (Gold, derived)** | double | `90334.24` (CA), `113895.22` (IA) | None | None | Computed as `100000.0 × purchasing_power_multiplier`, rounded to 2 decimals. Identical privacy analysis to `adjusted_30k`. Fixed $100K anchor × state-level index. Not an individual salary. 1:1 scalar function of `purchasing_power_multiplier`. |
| 13 | verification_status | Silver passthrough (carry-forward per Bronze Condition 7) | string | `"bea_official"`, `"estimate"` | None | None | Certified non-PII in Silver. 2-valued provenance enum. Explicit carry-forward required by Bronze staff-review Condition 7. |
| 14 | data_year | Silver passthrough | int | `2024` | None | None | Certified non-PII in Bronze and Silver. Constant across all 51 rows. Publication reference year, not a DOB or event date. |
| 15 | promoted_at | **New (Gold promotion timestamp)** | timestamp | `2026-04-11T...Z` | None | None | Timestamp of the Gold promotion run. Same value across all 51 rows (batch stamp). Identifies when the ETL job ran, not when any individual did anything. Replaces Silver's `ingested_at`/`source_load_date` pair with a single Gold-zone batch timestamp. Standard operational provenance field, categorically non-PII. No within-row temporal variation usable for behavioral linkage. |

---

### Summary by Sensitivity
| Level | Label | Count | Fields Affected |
|-------|-------|-------|-----------------|
| 1 | Public | 0 | — |
| 2 | Internal | 0 | — |
| 3 | Confidential | 0 | — |
| 4 | Restricted | 0 | — |

All 15 Gold columns are non-PII. The 11 Silver-passthrough columns inherit their Silver classification. The 4 new derived columns (`cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`) and the new Gold batch timestamp (`promoted_at`) are either deterministic lossy generalizations or 1:1 scalar functions of existing non-PII state-level aggregates, and introduce no new person-level information.

(Note: the spec lists the schema as 15 columns, which is `cost_tier` + 4 `adjusted_Nk` = 5 new analytical columns plus 1 operational column `promoted_at` replacing Silver's two operational timestamps. All 6 Gold-originated values were analyzed in the table above; the net column count is +4 over Silver as expected.)

---

### Quasi-Identifier and k-Anonymity Delta Analysis

A Gold transformation over a Silver zero-PII table can in principle break the zero-PII claim in a few specific ways. Each is explicitly checked here against the Gold spec.

| Risk Vector | Check | Result |
|-------------|-------|--------|
| **Grain refinement** — did Gold split rows to a finer grain (e.g., state → county, or state × year) that represents a smaller population? | Grain is unchanged at `[state_fips]`. Row count remains exactly 51. Spec explicitly declares `Dedup grain: [state_fips]` and `Row count guarantee: Exactly 51`. `data_year` is a constant (2024), not a temporal dimension. | PASS — k-anonymity floor unchanged at ~584,000 (Wyoming). |
| **Individual earnings introduction** — do `adjusted_Nk` columns introduce individual-level wage, salary, or financial data? | Explicitly NO. The user prompt and the spec both affirm: the `N` in `adjusted_Nk` is a **fixed national salary anchor** (30000, 50000, 75000, 100000) chosen by the product team as common display thresholds. They are not observed salaries of any individual. Each value is `anchor × purchasing_power_multiplier`, a scalar multiple of a state-level index. Zero individuals are referenced, identified, or reconstructible. | PASS — no individual earnings data. |
| **cost_tier as a quasi-identifier** — could `cost_tier` narrow a row's population relative to `rpp_all_items`? | No. `cost_tier` is a 5-value lossy bucketing of `rpp_all_items`. A lossy generalization has strictly fewer distinct values than its input, so it can only *increase* k-anonymity (many states map to the same tier). Per-tier populations range from tens to hundreds of millions of residents — orders of magnitude above the per-state floor. | PASS — generalization increases k-anonymity. |
| **adjusted_Nk as a quasi-identifier** — could combining the 4 `adjusted_Nk` columns create a fingerprint? | No. All four `adjusted_Nk` columns are 1:1 scalar functions of the same `purchasing_power_multiplier`, so they contain the same information as `purchasing_power_multiplier` (modulo two-decimal rounding). The tuple `(adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k)` is mathematically isomorphic to `purchasing_power_multiplier`, which is itself isomorphic to `rpp_all_items`, which is a state-level public index. A fingerprint that resolves to a state is not a PII fingerprint; the state already has ~584K+ residents. | PASS — no narrowing effect; the 4 columns are mutually redundant and resolve to the same state-level grain. |
| **Combination of Gold + Silver fields** — does `(state_fips, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, cost_tier, adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k, verification_status, data_year)` create a narrower fingerprint than Silver? | No. Every field in the combined tuple is a deterministic function of `state_fips`. The combined tuple identifies exactly one state — a jurisdiction, not a person. Population-per-cell is identical to Silver (~584K to ~39M). | PASS — no narrowing. |
| **Introduction of a direct personal field** (name, address, DOB, SSN, phone, email, GPS, biometric, health) via derivation or join | No joins occur in the Gold transformation — the spec explicitly states `No joins. No cross-source work.` No derivation introduces a person-level field. `cost_tier` is a categorical tier, `adjusted_Nk` are state-indexed reference dollar values, `record_id` is a deterministic hash of `state_fips`, `promoted_at` is a batch operational timestamp. None of these fields have any person-level semantic. | PASS — no direct personal fields. |
| **Temporal linkability** — does Gold add a new temporal column at a finer grain that could enable behavioral fingerprinting? | One new temporal column (`promoted_at`), but it is batch-level — identical across all 51 rows and tied to a single ETL run, not to any individual event. `data_year` remains a constant `2024`. | PASS — no within-row temporal variation usable for linkage. |
| **External join amplification** — does Gold make the table more joinable to person-level external data than Silver was? | No. The Gold derivations (`cost_tier`, `adjusted_Nk`) are closed transformations of existing Silver columns. No new join keys are introduced. External data joined on any field still resolves at the state level, never at the person level. | PASS — join targets remain state/region aggregates. |
| **Rounding / precision as a fingerprint** — could sub-cent precision on `adjusted_Nk` create a unique-per-state numeric fingerprint enabling linkage? | The spec mandates rounding to 2 decimals (cents precision) at write time and explicitly rejects sub-cent precision as "false precision for a state-level index." Even at full precision, the values are 1:1 functions of `rpp_all_items` and thus already identify at most one state — no new fingerprinting capability. | PASS — rounding is explicit and adds no re-identification risk. |

**Verdict:** No quasi-identifiers, no k-anonymity degradation, no individual earnings introduction. The k-anonymity floor is unchanged at ~584,000 (Wyoming). State-level aggregation remains categorically safe under HIPAA Safe Harbor §164.514(b)(2)(i)(B), FERPA, GDPR, CCPA/CPRA, PCI DSS, SOX, and GLBA.

---

### False Positive Candidates

| Field | Could Look Like | Why It's Not PII | Recommendation |
|-------|-----------------|------------------|----------------|
| adjusted_30k / adjusted_50k / adjusted_75k / adjusted_100k | "Individual salary" or "compensation record" to a naive financial-PII matcher that sees dollar amounts in a column named `adjusted_*k` | Each value is a fixed national anchor (30/50/75/100 thousand dollars) multiplied by the state's purchasing power multiplier. The anchors are not derived from any individual's earnings — they are product-design display thresholds defined in the spec. The resulting numbers are state-level reference values, mathematically 1:1 with `purchasing_power_multiplier`. | Whitelist the 4 columns as "state-indexed reference values at fixed national anchors." Document in the data dictionary that these are NOT observed wages. |
| cost_tier | "Customer tier" or "pricing tier" to a naive segmentation-PII matcher | 5-valued categorical generalization of a state-level macroeconomic index. Not a customer segment, not a user tier. | Whitelist the 5 enum values. |
| record_id | "Pseudonymized identifier" to a naive ID-PII matcher | Pseudonym for a state (jurisdiction), not a person. Derived from a non-PII input (`state_fips`). Cannot be de-anonymized to an individual because each row is a whole-state aggregate. | No action; document as a jurisdiction key. |
| promoted_at | "Event timestamp" that could enable temporal fingerprinting | Batch ETL timestamp, identical across all 51 rows. No individual behavior encoded. | No action; standard operational provenance. |

---

### Regulatory Implications

**None.** The Gold transformation introduces no personal data. Inherited from Silver and Bronze:

| Regulation | Applies? | Rationale |
|------------|----------|-----------|
| HIPAA | No | No health information. State-level aggregation is explicitly safe under Safe Harbor §164.514(b)(2)(i)(B). |
| FERPA | No | No education records, no students. |
| GDPR | No | No personal data of EU data subjects. Aggregates over ~584K to ~39M people per row are not personal data under Article 4(1). |
| CCPA / CPRA | No | No personal information of California residents. |
| PCI DSS | No | No payment card data. The `adjusted_Nk` dollar amounts are state-indexed reference values at fixed national anchors, not payment instruments or transactions. |
| SOX | No | No financial records of any reporting entity. |
| GLBA | No | No nonpublic personal financial information. The `adjusted_Nk` columns do not describe any individual's financial situation. |

**Data classification:** `public`. All values are U.S. Government Work in the public domain (BEA publication) plus deterministic transformations thereof.

---

### Recommendations

**For @policy-engineer:**
- **No RLS, no column masking, no encryption-at-rest-beyond-baseline required for PII reasons.** `consumable.regional_price_parities` may be written as plaintext to Iceberg with no row-level security predicates.
- `public` access tier is appropriate. Any access controls should be operational (governance roles) rather than privacy-motivated.

**For @data-contract-author:**
- Contract may declare `pii_classification: none` and `data_classification: public` for all 15 columns.
- Explicitly document in the contract that `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k` are state-indexed reference values at fixed national salary anchors, **not** individual earnings data. This protects downstream consumers from misreading the columns as PII.

**For @cde-tagger:**
- No CDE tags required for PII/sensitivity reasons. Standard business-critical tagging (`state_fips`, `rpp_all_items`, `purchasing_power_multiplier`, `cost_tier`, the `adjusted_Nk` family as display measures, `verification_status` as a provenance-critical element) applies independently of PII concerns.

**For @doc-generator:**
- Data dictionary entries for all 15 columns may note `pii: false, sensitivity: public`.
- For the 4 `adjusted_Nk` columns, include a dictionary note: "Reference value. State-level RPP index applied to a fixed national salary anchor. NOT an observed individual salary."
- Glossary term BT-107 (Adjusted Salary) already describes the derivation pattern accurately; no privacy-motivated changes required.

**For @adversarial-auditor:**
- During skeptical audit, specifically sanity-check that the `adjusted_Nk` columns are consistently interpreted as reference values across the data contract, data dictionary, MCP tool responses, and frontend display. A downstream misinterpretation that treats these as "average wages in state X" would not change the PII posture (the data is still state-level) but would be a semantic correctness issue worth flagging.

**For downstream zones (MCP `mcp-bea-rpp` tools, frontend, Fight Location Lock boss):**
- The zero-PII posture propagates forward. MCP tool responses `get_regional_price_parity` and `compare_purchasing_power` may freely return all 15 columns (subject to the `data_source` carry-forward obligation from Bronze Condition 7) without PII masking.
- The frontend may display any of the 15 columns to any user without PII-motivated access controls.

**For @primary-agent (Gold implementer):**
- No special handling required. Standard Gold "pure shaping" promotion pattern applies. Agent workflow step 11 (@pii-scanner SKIP) is now explicitly discharged by this scan.

---

### Justification (One-Line Summary)

"Zero-PII claim from `bronze.bea_rpp` and `base.bea_rpp` holds across all 15 Gold columns — `cost_tier` is a lossy 5-bucket generalization of a non-PII state-level index (increases k-anonymity), the 4 `adjusted_Nk` columns are 1:1 scalar functions of `purchasing_power_multiplier` at fixed national salary anchors (NOT individual earnings data), `record_id` and `promoted_at` are operational fields, the grain is unchanged at 51 state rows, and the k-anonymity floor remains ~584,000 (Wyoming)."
