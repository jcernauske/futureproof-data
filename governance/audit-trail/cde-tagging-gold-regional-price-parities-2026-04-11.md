# Audit Trail: CDE/PII Tagging — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @cde-tagger
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Table:** `consumable.regional_price_parities` (Gold / Consumable zone)
**Rows:** 51 (50 states + DC)
**Columns:** 15
**Output artifact:** `governance/cde-tagging/gold-regional-price-parities.md`

---

## Inputs Consulted

| Artifact | Purpose |
|---|---|
| `docs/specs/gold-regional-price-parities.md` | Schema (15 cols), derivation formulas, DQ rules, consumer list, BT-106/BT-107 definitions |
| `governance/cde-tagging/silver-base-bea-rpp.md` | Silver CDE baseline (8 CDE, 0 PII) for carry-forward evaluation |
| `governance/cde-tagging/raw-ingest-bea-rpp.md` | Bronze CDE baseline (4 CDE, 0 PII) for full lineage context |
| `governance/pii-scans/gold-regional-price-parities.md` | Gold PII delta scan — decision NO PII, k-anonymity ~584K unchanged |
| `governance/domain-context.md` §BEA RPP | Regulatory posture (none), PII expectations (none), explicit @cde-tagger auto-approvals, Canonical Concept Map |
| `governance/audit-trail/2026-04-11-data-analyst-gold-regional-price-parities.md` | Gold EDA — cost_tier distribution, adjusted_Nk arithmetic verification |

---

## Decision Log

### Carry-forward re-evaluation (Silver → Gold, 8 columns)

Per Brightsmith no-backward/no-forward-propagation policy, each Silver CDE was re-evaluated against its Gold role. All 8 were re-affirmed.

| Column | Silver CDE | Gold CDE | Reason |
|---|---|---|---|
| `state_fips` | true | **true** | Still the primary key and dedup grain; Gold uses `rpc` prefix but the field is unchanged. ANSI/FIPS standard. |
| `state_name` | true | **true** | Still the primary display label for MCP tool responses and frontend. |
| `state_abbr` | true | **true** | Still the identifier the frontend and MCP tool parameters use. |
| `census_region` | true | **true** | Drives frontend regional comparisons and Fight Location Lock boss. Gold P0 DQ re-enforces value domain and completeness. |
| `rpp_all_items` | true | **true** | Still the entire analytical payload; every Gold derivation is a pure function of it. Highest criticality in the table. |
| `purchasing_power_multiplier` | true | **true** | Every adjusted_Nk is N * this column. Inverse invariant P0 at rest. |
| `verification_status` | true | **true** | Bronze staff review Condition 7 explicitly requires Gold to preserve it. Gold P0 pins bea_official count = 8. Gates Gemma narrative precision. |
| `data_year` | true | **true** | Provenance-critical temporal dimension. P0 pin to 2024. |

### New Gold-origin CDE flags (5 columns)

| Column | Decision | Reason |
|---|---|---|
| `cost_tier` | **CDE = true** | Explicit spec callout: drives frontend color coding, boss-fight difficulty, Gemma narrative prompts. P0 DQ on value domain AND classification correctness. BT-106. No substitute column encodes tier. |
| `adjusted_30k` | **CDE = true** | Pre-computed display-ready value consumed directly by Gemma and the frontend. Spec's stated purpose of the Gold layer. P0 DQ within 1 cent of formula. BT-107. |
| `adjusted_50k` | **CDE = true** | Same role as adjusted_30k. P0 includes CA and IA spot-check assertions. BT-107. |
| `adjusted_75k` | **CDE = true** | Same role. BT-107. |
| `adjusted_100k` | **CDE = true** | Same role. Closes out the 4-value set the product team selected. BT-107. |

All 4 `adjusted_Nk` columns were treated as a single decision class — they share derivation pattern, DQ treatment, and downstream consumption. Flagging any one and not the others would be inconsistent with the spec's stated Gold-layer purpose.

### Columns evaluated and NOT flagged (2 columns)

| Column | CDE | PII | Reason |
|---|---|---|---|
| `record_id` | false | false | Deterministic Gold grain surrogate (`compute_grain_id(['state_fips'], prefix='rpc')`). Pure function of `state_fips`; flagging would be redundant. Consumed only by pipeline dedup/upsert machinery, not by business consumers or MCP tools. Same rationale as Silver's own `record_id`. |
| `promoted_at` | false | false | Gold promotion batch timestamp. Identical across all 51 rows. Operational observability only — not a decision input. Freshness governed by annual refresh cadence, not per-row timestamp. Not a personal date. |

### PII decisions (all 15 columns)

Delegated to `governance/pii-scans/gold-regional-price-parities.md`, which analyzed all 15 Gold columns and issued **NO PII**:

- 8 Silver passthrough columns inherit Silver non-PII classification
- `cost_tier` is a lossy generalization of a non-PII input — *increases* k-anonymity
- 4 `adjusted_Nk` columns are 1:1 scalar functions of `purchasing_power_multiplier` at fixed national anchors — explicitly NOT individual earnings data
- `record_id` is a deterministic hash of a non-PII input
- `promoted_at` is a batch ETL timestamp, not a personal date
- k-anonymity floor unchanged at ~584,000 (Wyoming)

All 15 columns receive `is_pii: false`. No regulatory framework (HIPAA, FERPA, GLBA, SOX, GDPR, CCPA, PCI DSS) applies. Sensitivity classification is `public`.

---

## Summary

| Metric | Value |
|---|---|
| Columns evaluated | 15 |
| CDE flags set | **13** |
| PII flags set | **0** |
| Silver carry-forward CDE re-affirmed | 8 |
| Gold-origin CDE (new) | 5 |
| Not flagged | 2 (`record_id`, `promoted_at`) |
| Regulatory frameworks triggered | None |
| Sensitivity classification | `public` across all 15 columns |

---

## Handoff to @doc-generator

The YAML fragment embedded in `governance/cde-tagging/gold-regional-price-parities.md` under "Tag List for Data Contract" is ready for merge into `governance/data-contracts/gold-regional-price-parities.yaml`. All 15 columns have explicit `is_cde`, `cde_rationale`, `is_pii`, `pii_rationale`, and `description` fields. Business-term references (BT-098 through BT-107) align with the existing glossary plus the two new terms (BT-106, BT-107) added by @data-steward during this Gold spec.

## Handoff to @governance-reviewer

All flags are justified by either (a) explicit spec language (consumer list, DQ P0 rules, Bronze Condition 7 carry-forward mandate), (b) domain-context.md §BEA RPP auto-approvals, or (c) the Gold PII scan's delta analysis. No speculative or unsupported flags. No backward propagation attempted. The no-propagation policy was explicitly honored by re-evaluating every Silver CDE against its Gold role before re-affirming.
