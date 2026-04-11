# Audit Trail: @pii-scanner — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @pii-scanner
**Spec:** docs/specs/gold-regional-price-parities.md
**Zone:** Gold (Consumable)
**Dataset:** consumable.regional_price_parities
**Report:** governance/pii-scans/gold-regional-price-parities.md
**Decision:** NO PII — zero-PII claim propagates from Bronze and Silver to Gold

---

## Dataset Scanned

- **Table:** `consumable.regional_price_parities`
- **Grain:** one row per `state_fips` (51 rows = 50 U.S. states + District of Columbia)
- **Columns:** 15 total
  - 11 Silver passthroughs: `state_fips`, `state_name`, `state_abbr`, `census_region`, `rpp_all_items`, `purchasing_power_multiplier`, `verification_status`, `data_year` (and a regenerated `record_id` with a new `rpc` prefix replacing Silver's `rpp` prefix)
  - 4 new analytical derivations: `cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`
  - 1 new operational timestamp: `promoted_at` (replaces Silver's `ingested_at` / `source_load_date` pair)
- **Upstream:** `base.bea_rpp` (Silver, 51 rows, 11 columns — scan 2026-04-10 decision: NO PII)
- **Bronze source:** `bronze.bea_rpp` (51 rows, 8 columns — scan 2026-04-10 decision: NO PII, k-anonymity floor ~584K)

---

## Detection Methods Used

This was a **delta scan** because Bronze and Silver have already been certified zero-PII with full per-field analysis, and the Gold transformation is explicitly a "pure shaping" row-for-row promote (no joins, no cross-source work, no grain change). The scan focused on:

1. **Field-by-field delta analysis** of the 4 new derived columns and 1 new operational column against the standard PII categories (personal names, addresses, government IDs, financial accounts, contact info, health records, DOB, biometric, location data)
2. **Quasi-identifier / k-anonymity delta analysis** across 9 risk vectors: grain refinement, individual earnings introduction, cost_tier narrowing, adjusted_Nk narrowing, Silver+Gold field combinations, direct personal field injection, temporal linkability, external join amplification, and precision/rounding fingerprinting
3. **Domain context cross-reference** against `governance/domain-context.md` BEA RPP section (lines 1495–1505), which explicitly declares zero PII for this source and categorizes state-level aggregation as safe under HIPAA Safe Harbor §164.514(b)(2)(i)(B)
4. **Format-pattern matching** against sensitive ID regexes (SSN, EIN, passport, ICD, CPT, credit card with Luhn check, phone, email, address patterns) — no matches
5. **Spec review** of the transformation logic in `docs/specs/gold-regional-price-parities.md` sections "Gold Transformations" and "Gold Schema"

---

## Key Decisions and Rationale

### Decision 1: cost_tier is not a quasi-identifier

`cost_tier` is a 5-bucket CASE expression over `rpp_all_items` (≥108 → `very_high`; ≥103 → `high`; ≥97 → `average`; ≥91 → `low`; else → `very_low`). This is a **lossy generalization** of a single non-PII numeric column.

**Rationale:** An information-theoretic lossy function of a non-PII input cannot encode additional information about any individual. Because the generalization collapses states into coarser buckets, per-tier populations are *larger* than per-state populations, so k-anonymity is *strengthened* rather than weakened. The smallest possible tier still covers multiple states totaling tens of millions of residents — orders of magnitude above the per-state floor of ~584K. Classified as non-PII with high confidence.

### Decision 2: adjusted_30k / adjusted_50k / adjusted_75k / adjusted_100k are NOT individual earnings data

This was the central verification requested by the parent agent. These four columns look superficially like financial/compensation data and could trip a naive financial-PII matcher.

**Rationale:**
- The "30k / 50k / 75k / 100k" values in the column names refer to **fixed national salary anchors** chosen by the product team as common frontend display thresholds. They are hard-coded constants in the Gold transformation (`30000.0`, `50000.0`, `75000.0`, `100000.0`), **not** observed salaries of any individual.
- Each output value is `anchor × purchasing_power_multiplier`, where `purchasing_power_multiplier` is itself a reciprocal of the state-level BEA RPP index — a non-PII public macroeconomic aggregate.
- The resulting numbers are therefore scalar multiples of a non-PII state-level index. They are mathematically 1:1 isomorphic to `purchasing_power_multiplier` (and thus to `rpp_all_items`), meaning the 4 columns collectively contain **the same information** as `purchasing_power_multiplier` — they identify a state, not a person.
- No individual wage, compensation, account number, transaction, or financial record is referenced or reconstructible from any `adjusted_Nk` value.
- Every row still aggregates over an entire state population (~584K to ~39M residents).

Classified as non-PII with high confidence. Flagged as a high-value false-positive candidate in the report with an explicit recommendation to the data contract author and doc generator to document that these are reference values, not observed wages, so that downstream consumers cannot misread them.

### Decision 3: The 4 adjusted_Nk columns do not collectively form a fingerprint

Even though there are four of them, the tuple `(adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k)` is mathematically isomorphic to `purchasing_power_multiplier` (modulo 2-decimal rounding). A fingerprint made from four 1:1-redundant copies of the same underlying value does not narrow the grain further than the underlying value already does. The underlying value already identifies a state, which has ~584K+ residents. Classified as non-QID.

### Decision 4: Grain is unchanged

The spec explicitly declares `Dedup grain: [state_fips]` and `Row count guarantee: Exactly 51`, with no fan-out, no filter, no join, no cross-source work. The k-anonymity floor is therefore *identical* to Silver and Bronze at ~584,000 (Wyoming). `data_year` is a constant `2024`, not a temporal dimension, so there is no temporal expansion either.

### Decision 5: promoted_at is operational, not behavioral

The `promoted_at` timestamp is a Gold promotion batch stamp — identical across all 51 rows, tied to a single ETL run. It cannot encode individual timing or behavior. Standard operational provenance field, categorically non-PII.

### Decision 6: record_id prefix change is cosmetic

Gold regenerates `record_id` with a new `rpc` prefix (replacing Silver's `rpp` prefix) to mark the Gold consumable zone. The derivation pattern (`compute_grain_id(row, ['state_fips'], prefix='rpc')`) is identical to Silver's, and the input is still the non-PII `state_fips`. Inherits non-PII status from the input.

---

## False Positive Decisions

| Field | Could Trip Matcher | Decision | Rationale |
|-------|-------------------|----------|-----------|
| `adjusted_30k` / `adjusted_50k` / `adjusted_75k` / `adjusted_100k` | Naive financial-PII matcher seeing dollar amounts in a salary-named column | False positive — non-PII | Fixed national anchors × non-PII state index; not observed wages |
| `cost_tier` | Naive segmentation-PII matcher | False positive — non-PII | Categorical generalization of a state-level macro index; not a customer tier |
| `record_id` (rpc:*) | Naive pseudonym-PII matcher | False positive — non-PII | Pseudonym for a state (jurisdiction), not a person |
| `promoted_at` | Naive behavioral-timestamp matcher | False positive — non-PII | Batch ETL timestamp identical across all 51 rows |

---

## Sensitivity Classifications Summary

| Level | Label | Count | Fields |
|-------|-------|-------|--------|
| 1 | Public | 0 | — |
| 2 | Internal | 0 | — |
| 3 | Confidential | 0 | — |
| 4 | Restricted | 0 | — |
| — | Non-PII (public domain macroeconomic aggregate + deterministic derivations) | 15 | all columns |

Data classification: `public`. All values are U.S. Government Work in the public domain (BEA publication) plus deterministic transformations thereof.

---

## Regulatory Applicability

No regulation applies. HIPAA, FERPA, GDPR, CCPA/CPRA, PCI DSS, SOX, and GLBA were all checked and explicitly ruled out. State-level aggregation is categorically safe under HIPAA Safe Harbor §164.514(b)(2)(i)(B) and no other regime imposes narrower obligations.

---

## Downstream Implications

- **@policy-engineer:** No RLS, no column masking, no PII-motivated encryption required. Public access tier.
- **@data-contract-author:** Contract may declare `pii_classification: none` and `data_classification: public` for all 15 columns. Must explicitly document that `adjusted_Nk` columns are reference values at fixed national anchors, not individual earnings.
- **@doc-generator:** Data dictionary entries may note `pii: false, sensitivity: public` for all 15 columns. Include "NOT observed individual salary" note on the `adjusted_Nk` family.
- **MCP (`mcp-bea-rpp`):** May freely return all 15 columns in tool responses. The Bronze Condition 7 `data_source` carry-forward obligation is a semantic requirement, not a PII masking requirement.
- **Frontend / Fight Location Lock boss:** No PII-motivated display restrictions.
- **@pii-scanner agent workflow step (step 11 in spec):** Gold spec lists this as "expected SKIP — no PII." This scan explicitly discharges that expectation rather than blind-skipping.

---

## Artifacts Produced

- `governance/pii-scans/gold-regional-price-parities.md` — full PII scan report
- `governance/audit-trail/2026-04-11-pii-scanner-gold-regional-price-parities.md` — this file

---

## Final Decision

**NO PII** — zero-PII claim from `bronze.bea_rpp` and `base.bea_rpp` holds across all 15 Gold columns of `consumable.regional_price_parities`. The 4 new derived columns (`cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`) are either lossy generalizations or 1:1 scalar functions of existing non-PII state-level aggregates; the new operational column (`promoted_at`) is a batch ETL stamp; the grain is unchanged at 51 state rows; and the k-anonymity floor remains ~584,000 (Wyoming). The Gold zone is cleared for zero-PII handling.
