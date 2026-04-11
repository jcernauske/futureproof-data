# Audit Trail: CDE Tagging — silver-base-bea-rpp

**Date:** 2026-04-10
**Agent:** @cde-tagger
**Spec:** `docs/specs/silver-base-bea-rpp.md`
**Parent Spec:** `docs/specs/raw-ingest-bea-rpp.md`
**Zone:** Silver
**Table:** `base.bea_rpp` (11 columns, 51 rows)
**Artifact produced:** `governance/cde-tagging/silver-base-bea-rpp.md`
**Upstream tagging:** `governance/cde-tagging/raw-ingest-bea-rpp.md` (Bronze, 4 CDEs, 0 PII)
**Upstream PII scan:** `governance/pii-scans/silver-base-bea-rpp.md` (NO PII, 11 columns)

---

## Inputs Consulted

| Source | Purpose |
|--------|---------|
| `docs/specs/raw-ingest-bea-rpp.md` | Full pipeline spec including Silver schema, DQ rules, glossary terms, and downstream consumers |
| `governance/domain-context.md` §BEA RPP (lines 1352–1620) | Canonical domain context — regulatory posture (none), CDE auto-approval guidance, concept map, downstream join topology |
| `governance/domain-context.md` §BEA RPP Source-Codes→Business-Concepts table (lines 1522–1529) | Explicit @cde-tagger instructions per column |
| `governance/cde-tagging/raw-ingest-bea-rpp.md` | Bronze CDE set to carry forward: `geo_fips`, `geo_name`, `rpp_all_items`, `data_year` |
| `governance/pii-scans/silver-base-bea-rpp.md` | Delta scan decision: NO PII across all 11 Silver columns |

---

## Decisions

### CDE Decisions (8 flagged, 3 not flagged)

| Column | is_cde | Carry-Forward? | Decision Driver |
|--------|--------|----------------|-----------------|
| `record_id` | false | — | Pure function of `state_fips`; pipeline plumbing only |
| `state_fips` | **true** | Bronze carry-forward | Primary key, dedup grain, sole machine join key; auto-approved per domain context |
| `state_name` | **true** | Bronze carry-forward | Display label in MCP tool response and frontend; auto-approved per domain context |
| `state_abbr` | **true** | **New** | Identifier the frontend/MCP tool parameter uses; product surface area is built on it |
| `census_region` | **true** | **New** | Frontend regional comparison views + stretch boss; P0 DQ coverage in spec; no substitute column |
| `rpp_all_items` | **true** | Bronze carry-forward | Entire analytical payload of the table; auto-approved per domain context, cross-ref BT-098 |
| `purchasing_power_multiplier` | **true** | **New** | Pre-computed adjustment factor consumed directly by Gemma/Gold/frontend; cross-ref BT-099 |
| `verification_status` | **true** | **New** | Per-row provenance hedge driving MCP response precision and contract quality tier split |
| `data_year` | **true** | Bronze carry-forward | Provenance-critical temporal dimension governing annual refresh semantics |
| `source_load_date` | false | — | Batch freshness metadata, not a decision input |
| `ingested_at` | false | — | Silver batch stamp, not a decision input |

**Total: 8 CDEs of 11 columns.**

### PII Decisions (0 flagged)

**No column receives `is_pii: true`.** Per the delta PII scan, all 11 columns are non-PII:

- Passthrough fields `state_fips`, `state_name`, `rpp_all_items`, `data_year` inherit Bronze's zero-PII certification
- Newly derived `state_abbr`, `census_region` are deterministic 1:1 or generalizing transformations of `state_fips` — a transformation of a non-PII input is non-PII
- Newly computed `purchasing_power_multiplier` is a pure reciprocal of a macroeconomic aggregate
- Newly derived `verification_status` is a provenance enum over state-level aggregates
- `record_id` is a deterministic hash of a non-PII jurisdiction key
- `source_load_date`, `ingested_at` are batch operational timestamps

k-anonymity floor is unchanged from Bronze at ~584,000 (Wyoming). No regulatory framework (HIPAA, FERPA, GLBA, GDPR, CCPA, PCI DSS, SOX) is triggered. Data classification: `public`.

---

## Rationale for New Silver CDE Flags

### `state_abbr` (new CDE)
The frontend state selector, MCP tool `state` parameter (`get_regional_price_parity(state)`), URL query strings, and every chart/display label use the 2-letter USPS abbreviation. While `state_abbr` is 1:1-isomorphic to `state_fips`, the product surface area is functionally built on the abbreviation — `state_fips` is a machine code the user never sees. Without this column materialized at Silver, Gold and MCP would have to re-derive it, breaking the "materialize once, consume many" Silver principle. Flagging CDE makes the criticality of the lookup table correctness explicit.

### `census_region` (new CDE)
Four-valued Census Bureau enum used by (a) frontend regional comparison views and (b) the stretch-goal Fight Location Lock boss regional cost tiering. Marginal vs. clear CDE, flagged **true** because:

1. The spec authors put P0 DQ coverage on both its value domain (`IN ('Northeast','Midwest','South','West')`) and completeness (all four represented) — strong signal the field is business-critical
2. It is a newly derived business-semantic field with no substitute in the table
3. Downstream consumers already plan to use it (frontend regional views, boss scoring)
4. Ambiguity risk: DC's Census-assigned "South" classification is a documented quirk that needs to surface correctly in the frontend

### `purchasing_power_multiplier` (new CDE)
Pre-computed salary adjustment factor (`100.0 / rpp_all_items`). Every downstream Gold field (`adjusted_30k/50k/75k/100k`), every MCP tool response field, and every Gemma-narrated salary adjustment is a single multiply against this factor. Materializing at Silver (rather than computing on the fly) enables the inverse-invariant DQ rule (`multiplier × rpp_all_items ≈ 100.0`) to guard computation correctness at rest. Cross-references BT-099 (Purchasing Power Multiplier) per domain context. This is the second-most-critical column in the table after `rpp_all_items` itself.

### `verification_status` (new CDE)
Two-valued provenance enum (`bea_official` / `estimate`) distinguishing the 8 BEA-verified rows from the 43 primary-agent plausible placeholders. This column:

1. Is consumed directly by the MCP tool response and governs whether Gemma hedges numeric precision
2. Is a direct input to the data contract's quality tier split (High for 8 verified rows, Medium for 43 estimated rows per domain-context.md)
3. Without it, downstream consumers cannot distinguish authoritative BEA values from placeholder values — a material correctness concern

Unique to this source in the FutureProof pipeline; a governance-motivated correctness indicator.

---

## No-Backward-Propagation Statement

Per Brightsmith governance policy, **CDE flags do not propagate across zones**. This tagging covers only Silver. The Bronze tagging (`governance/cde-tagging/raw-ingest-bea-rpp.md`) remains the authoritative record for Bronze CDE state. When @cde-tagger runs on `gold-regional-price-parities`, each Gold column (`cost_tier`, `adjusted_30k/50k/75k/100k`, etc.) will be re-evaluated independently on its own merits in the Gold zone.

---

## Final Counts

| Metric | Value |
|--------|-------|
| Columns evaluated | 11 |
| CDEs flagged | **8** |
| — carried forward from Bronze | 4 (`state_fips`, `state_name`, `rpp_all_items`, `data_year`) |
| — new in Silver | 4 (`state_abbr`, `census_region`, `purchasing_power_multiplier`, `verification_status`) |
| PII flagged | **0** |
| Not flagged | 3 (`record_id`, `source_load_date`, `ingested_at`) |
| Sensitivity classification | `public` across all 11 columns |
| Regulatory frameworks triggered | None |

---

## Next Steps

1. `@doc-generator` embeds the YAML fragment from `governance/cde-tagging/silver-base-bea-rpp.md` into `governance/data-contracts/silver-base-bea-rpp.yaml`
2. `@data-steward` validates that `state_abbr`, `census_region`, `purchasing_power_multiplier`, and `verification_status` have matching business-glossary entries (BT-RPP-STATE-ABBR, BT-RPP-CENSUS-REGION, BT-099, BT-RPP-VERIFICATION-STATUS) — three are project-specific proposals, BT-099 is already defined
3. `@governance-reviewer` checks that every CDE rationale references a downstream consumer, regulation, or DQ guardrail (all 8 do)
4. `@cde-tagger` runs again on Gold `consumable.regional_price_parities` when that contract is ready — each Gold column will be re-evaluated independently, no backward propagation
