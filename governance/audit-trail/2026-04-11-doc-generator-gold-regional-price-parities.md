# Audit Trail: @doc-generator — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @doc-generator
**Spec:** docs/specs/gold-regional-price-parities.md
**Zone:** Gold (Consumable)
**Target table:** consumable.regional_price_parities

---

## Summary

Produced the Gold-layer governance documentation artifacts for
`consumable.regional_price_parities`: a draft data contract, 15 data
dictionary column entries, and one table-level dictionary entry. All
artifacts link back to the 55 DQ rules in
`governance/dq-rules/gold-regional-price-parities.json`, the CDE tagging
doc at `governance/cde-tagging/gold-regional-price-parities.md` (13 CDEs,
0 PII), the lineage capture at
`governance/lineage/gold-regional-price-parities-20260411.json`, and the
business glossary terms BT-098..BT-107.

---

## Files Created

### 1. Data contract (DRAFT)
**Path:** `governance/data-contracts/consumable-regional-price-parities.yaml`

**Naming note:** This file follows the project convention
`consumable-<table>.yaml` per the gold-regional-price-parities pre-review
advisory #2. It is intentionally NOT named `gold-regional-price-parities.yaml`
even though the spec title uses that form. Matching convention precedent:
- `consumable-career-branches.yaml`
- `consumable-program-career-paths.yaml`
- `consumable-occupation-profiles.yaml`

**Status:** `draft` — pending @staff-engineer sign-off via
`governance/approvals/gold-regional-price-parities-staff-review.md`.

**Version:** 1.0.0 (greenfield — no prior Gold contract for this table).

**Key fields set:**
- `quality_tier: partial_verification` (carry-forward from Silver/Bronze
  unchanged — 43/51 rows are estimates)
- `record_count: 51`, `row_count_guarantee: 51`, `row_count_tolerance: 0`
- `null_guarantee: 0% nulls across all 15 columns`
- `completeness_threshold: 1.00`, `validity_threshold: 1.00`
- `verified_row_count: 8`, `estimated_row_count: 43`
- `per_row_provenance_column: verification_status`
- Bronze staff-review Condition 7 documented under
  `staff_review_conditions.condition_7_implemented_at_gold` with status
  `IMPLEMENTED HERE`. The MCP-layer strict-mode obligation is documented
  under `condition_7_carry_forward_to_mcp` with status
  `FORWARD-ONLY OBLIGATION` (owned by the `mcp-bea-rpp` spec).

### 2. Data dictionary entries
**Path:** `governance/data-dictionary.json`

Added a new top-level entry `tables.consumable.regional_price_parities`
with 15 column records and 3 table-level DQ rule references. Full columns:

| # | Column | Type | is_cde | is_pii | business_term | dq_rules count |
|---|---|---|---|---|---|---|
| 1 | record_id | string | false | false | — | 3 |
| 2 | state_fips | string | **true** | false | BT-100 | 18 |
| 3 | state_name | string | **true** | false | BT-101 | 2 |
| 4 | state_abbr | string | **true** | false | BT-103 | 13 |
| 5 | census_region | string | **true** | false | BT-104 | 3 |
| 6 | rpp_all_items | double | **true** | false | BT-098 | 5 |
| 7 | purchasing_power_multiplier | double | **true** | false | BT-099 | 7 |
| 8 | cost_tier | string | **true** | false | BT-106 | 14 |
| 9 | adjusted_30k | double | **true** | false | BT-107 | 2 |
| 10 | adjusted_50k | double | **true** | false | BT-107 | 12 |
| 11 | adjusted_75k | double | **true** | false | BT-107 | 2 |
| 12 | adjusted_100k | double | **true** | false | BT-107 | 2 |
| 13 | verification_status | string | **true** | false | BT-105 | 11 |
| 14 | data_year | int | **true** | false | BT-102 | 2 |
| 15 | promoted_at | timestamp | false | false | — | 1 |

**Table-level DQ rules:** GLD-RPP-001 (row count 51), GLD-RPP-043
(passthrough integrity — cross-zone, production_only/chaos_exclude),
GLD-RPP-055 (source Silver freshness — cross-zone,
production_only/chaos_exclude).

### 3. Audit trail (this file)
**Path:** `governance/audit-trail/2026-04-11-doc-generator-gold-regional-price-parities.md`

---

## Per-Column DQ Rule Mapping Methodology

Per the task input, per-column `dq_rules` arrays were built by reading the
actual SQL of each GLD-RPP-* rule in
`governance/dq-rules/gold-regional-price-parities.json` and mapping each
rule to every column whose drift would cause the rule to fire. Silver's
HIGH-2 audit finding was caused by a contiguous-slice guess pattern; this
audit trail explicitly records the decision rules used to avoid that
failure mode:

1. **Single-column rules** (non-null, range, format, uniqueness) → mapped
   to that one column only.
2. **Bijection rules (GLD-RPP-007, 012)** → mapped to BOTH paired columns
   (state_fips + state_name; state_fips + state_abbr). Dropping either
   column from a bijection rule would cause a governance drift where a
   column rename in isolation could pass CI.
3. **Inverse-invariant rule (GLD-RPP-020)** → mapped to BOTH
   rpp_all_items AND purchasing_power_multiplier.
4. **Derivation-purity rules (GLD-RPP-026/028/030/032)** → mapped to both
   the derived column (adjusted_Nk) AND the source column
   (purchasing_power_multiplier). A drift in either would fire these rules.
5. **cost_tier classification correctness (GLD-RPP-023)** → mapped to
   BOTH cost_tier AND rpp_all_items.
6. **TN left-closed boundary witness (GLD-RPP-024)** → mapped to ALL
   THREE of state_fips, rpp_all_items, and cost_tier. The rule fires on
   any of: wrong TN FIPS, wrong TN RPP value, wrong TN cost_tier.
7. **CA/IA sanity rules (GLD-RPP-033/034)** → mapped to BOTH state_fips
   AND adjusted_50k.
8. **verification_status allow-list rule (GLD-RPP-037)** → mapped to
   BOTH verification_status AND state_fips.
9. **BEA-verified spot-check rules (GLD-RPP-044..051)** → each mapped to
   FIVE columns: state_fips (scoped), state_abbr, cost_tier,
   adjusted_50k, verification_status. These rules assert a conjunction of
   4 column values per bound state.
10. **Column-scoped COUNT DISTINCT rules (GLD-RPP-015, 042, 052)** →
    mapped to the single column they count (census_region, data_year,
    cost_tier). They are NOT treated as table-level because they
    constrain one column's distinct value set, matching Silver's
    convention where SIL-BEA-028 (COUNT DISTINCT data_year) stayed
    under the data_year column.
11. **Table-level rules** (3 total): GLD-RPP-001 (row count),
    GLD-RPP-043 (cross-zone passthrough integrity), GLD-RPP-055
    (cross-zone source freshness). These are the only three rules that
    live under the top-level `table_level_dq_rules` field. The two
    cross-zone rules carry their original `evaluation_mode:
    production_only` and `chaos_exclude: true` carve-outs from the DQ
    rules file.

**Orphan rule verification:** The union of all per-column `dq_rules`
arrays plus `table_level_dq_rules` covers exactly the set
{GLD-RPP-001, GLD-RPP-002, ..., GLD-RPP-055}. Zero orphans, zero
duplicates with respect to set coverage. Programmatic verification was
run against both the contract YAML and the dictionary JSON.

---

## Key Decisions and Judgment Calls

1. **Contract filename convention honored.** Per pre-review advisory #2,
   the contract is `consumable-regional-price-parities.yaml` (matching
   the existing `consumable-*.yaml` pattern), not
   `gold-regional-price-parities.yaml` (which would have matched the
   spec title but diverged from project convention). A prominent comment
   block at the top of the YAML file explains the decision so future
   doc-generator runs do not regress it.

2. **Contract `status: draft`.** Per agent protocol, data contracts
   start as `draft` until @staff-engineer signs off, at which point the
   status transitions to `active`. The Silver contract for `base.bea_rpp`
   is `active` (staff-engineer sign-off 2026-04-10); this Gold contract
   inherits the same upgrade path.

3. **`promoted_at` disambiguation.** Per task input, the dictionary
   entry for `promoted_at` explicitly calls out that this is the Gold
   promote timestamp and is distinct from `base.bea_rpp.ingested_at` (the
   Silver batch stamp) AND `bronze.bea_rpp.ingested_at` (the Bronze batch
   stamp). Every downstream consumer that needs to distinguish these
   must reference the fully-qualified table name. This matches Silver's
   ingested_at disambiguation added in advisory #7.

4. **DC-in-South Census quirk surfaced.** Per task input, the
   `census_region` dictionary entry explicitly documents that the
   District of Columbia is assigned to 'South' under Census Bureau
   classification despite its Northeast-like cost-of-living profile.
   This is the same language used in the Silver data dictionary entry
   for continuity. Downstream consumers that compare DC to 'Northeast'
   states must handle this quirk explicitly.

5. **adjusted_Nk columns described as reference values, NOT earnings.**
   Per the PII scan decision and CDE tagging doc, the four
   `adjusted_Nk` columns are state-level reference values at fixed
   national salary anchors ($30K, $50K, $75K, $100K). They are
   categorically NOT observations of individual earnings. The
   dictionary `description` and `cde_rationale` fields both repeat this
   language so any future PII re-scan cannot accidentally flag these
   columns as earnings data.

6. **Quality tier unchanged from Silver/Bronze.** `partial_verification`
   is carried forward from the parent Silver contract unchanged. Gold
   MUST NOT claim more verification than Silver. The count-of-8 P0 rule
   (GLD-RPP-036) and the 8-state FIPS allow-list P0 rule (GLD-RPP-037)
   are the enforcement mechanism; per the contract
   `staff_review_conditions.condition_7_implemented_at_gold` block,
   these rules flip to count-of-51 when the live BEA API refresh lands
   — a minor version bump, not a breaking change.

7. **Condition 7 carry-forward obligation captured twice.** The
   contract documents Condition 7 in two places:
   (a) `condition_7_implemented_at_gold` — status `IMPLEMENTED HERE`
       for the Gold table carrying verification_status verbatim from
       Silver.
   (b) `condition_7_carry_forward_to_mcp` — status
       `FORWARD-ONLY OBLIGATION` for the `mcp-bea-rpp` spec, which must
       return a `data_source` field per row and support a strict mode
       that refuses to return `estimate` rows. This obligation lives in
       the Gold contract (not the Silver contract) so the MCP pre-review
       cannot miss it when the MCP spec is drafted.

8. **BT-107 (Adjusted Salary) used for all 4 adjusted_Nk columns.** The
   four columns share a single business term because they represent the
   same concept at different anchors. Per the business glossary
   (BT-107), the term explicitly defines the derivation formula and
   lists all 4 anchor values.

9. **Version set to 1.0.0.** First active/draft Gold contract for this
   table; there is no prior version to bump. Subsequent changes (e.g.,
   the 8→51 verification count flip) will be minor bumps per the
   `breaking_changes.policy` section.

---

## Parse Validation

Both artifacts were programmatically re-parsed after write:

- **YAML contract** → parsed via `yaml.safe_load`. 15 columns present.
  Every column has the required keys: `name`, `type`, `required`,
  `is_cde`, `is_pii`, `description`. Every column has
  `required: true` and `is_pii: false`.
- **JSON dictionary** → parsed via `json.load`. 28 top-level tables
  (27 existing + 1 new). 15 columns on the new table entry. Every
  column has the required fields: `type`, `nullable`, `is_cde`,
  `is_pii`, `description`, `dq_rules`. Every column has
  `nullable: false` and `is_pii: false`.

Cross-validation between the YAML contract and the JSON dictionary
confirms zero drift on `dq_rules` arrays for every one of the 15
columns and zero drift on the 3-entry `table_level_dq_rules` list.

---

## Business Glossary Verification

All 10 BT-* references used in the contract and dictionary were
verified to exist as `term_id` entries in
`governance/business-glossary.json`:

- BT-098 (Regional Price Parity)
- BT-099 (Purchasing Power Multiplier)
- BT-100 (State FIPS Code)
- BT-101 (State Name)
- BT-102 (RPP Data Year)
- BT-103 (USPS State Abbreviation)
- BT-104 (Census Region)
- BT-105 (Data Verification Status)
- BT-106 (Cost Tier) — new in this Gold spec
- BT-107 (Adjusted Salary) — new in this Gold spec

Phantom reference count: **0**.

---

## Orphan Rule Verification

Union of per-column `dq_rules` + `table_level_dq_rules` covers
GLD-RPP-001 through GLD-RPP-055 exactly. Orphan rule count: **0**.

All 55 rules are defined in
`governance/dq-rules/gold-regional-price-parities.json`.

---

## Conflicts / Open Items

None. Every hard constraint from the task input is satisfied:

- [x] No phantom business term IDs
- [x] Every column has description, data_type, nullable: false,
      is_cde, is_pii: false, business_term where applicable,
      dq_rules array
- [x] YAML + JSON parse cleanly
- [x] Zero orphaned rules
- [x] Contract uses `consumable-regional-price-parities.yaml` naming
- [x] Quality tier `partial_verification` carried forward
- [x] Row count (51) and null guarantee (0% across 15 columns) embedded
- [x] Bronze Condition 7 marked `IMPLEMENTED HERE` with MCP carry-forward
      obligation noted
- [x] Per-column dq_rules derived from actual SQL (no contiguous-slice
      guessing)
- [x] `promoted_at` disambiguated from Silver and Bronze ingested_at
- [x] DC-in-South Census quirk note preserved on `census_region`

Next step: @governance-reviewer post-implementation review, then
@staff-engineer final sign-off to transition the contract from `draft`
to `active`.
