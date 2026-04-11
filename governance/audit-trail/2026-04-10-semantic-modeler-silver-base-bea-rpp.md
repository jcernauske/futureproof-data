# Audit Trail: @semantic-modeler — silver-base-bea-rpp

**Date:** 2026-04-10
**Agent:** @semantic-modeler
**Spec:** docs/specs/silver-base-bea-rpp.md
**Mode:** Greenfield (Conceptual → Logical → Physical)
**Parent Bronze spec:** docs/specs/raw-ingest-bea-rpp.md

---

## Summary

Produced the three-stage data model for the smallest Silver transformation in the project: `base.bea_rpp` (51 rows, 11 columns). The table is a closed-set geographic reference table for cost-of-living adjustment. All three models saved to `governance/models/` with status `PROPOSED`, pending human review per `REQUIRE_HUMAN_APPROVAL = true`.

---

## Artifacts Produced

| Stage | Path |
|-------|------|
| Conceptual | `governance/models/silver-base-bea-rpp-conceptual.md` |
| Logical | `governance/models/silver-base-bea-rpp-logical.md` |
| Physical | `governance/models/silver-base-bea-rpp-physical.md` |
| Audit trail | `governance/audit-trail/2026-04-10-semantic-modeler-silver-base-bea-rpp.md` (this file) |

All three model files include the required Mermaid `erDiagram` block immediately after the header per pre-review advisory.

---

## Inputs Reviewed

- **Spec:** `docs/specs/silver-base-bea-rpp.md` — complete schema table, DQ rule list, 8-state verification allow-list, Bronze staff-review Conditions 6 and 7.
- **Bronze staff review:** referenced via `governance/approvals/raw-ingest-bea-rpp-staff-review.md` (Ruling 2 / Condition 6) — drove the `verification_status` column addition.
- **Business glossary:** confirmed BT-098 through BT-105 exist in `governance/business-glossary.json`. No new term proposals needed from the modeler.
- **Prior Silver model patterns:** `silver-base-karpathy-ai-exposure-{conceptual,logical,physical}.md`, `silver-base-bls-ooh-*`, `silver-base-onet-*` — all used as reference for format and narrative conventions.

---

## Key Design Decisions

### 1. `State` as the anchor entity (not `Region`)

The user prompt asked whether to call the top-level entity `State` or `Region`. I chose **State**. Rationale:

- The row grain is one per U.S. state (or DC). `State` describes the grain directly.
- `Region` is already overloaded in this model — it refers to the Census aggregation (Northeast, Midwest, South, West), not the row grain. Calling the row entity `Region` would collide with `Census Region` and confuse the ER diagram.
- Business stakeholders (frontend devs, MCP consumers, BEA data readers) think in terms of states, not regions, when selecting a cost-of-living adjustment.

### 2. `state_abbr` as an attribute of `State`, not a separate entity

Per the user prompt's explicit question. I chose **attribute**. Rationale:

- `state_abbr` is a 1:1 synonym for `state_fips` — a second canonical identifier used by the frontend and MCP tool signatures.
- It carries no independent relationships: no attributes of its own, no reference data hanging off it, no cardinality variations.
- Promoting it to an entity would add structural noise without any resolvable business concept.
- Keeping it as an attribute of `State` (tagged with `BT-103`) preserves the clean one-table shape and matches the treatment of `state_name` (which nobody would propose as a separate entity).
- The conceptual model is therefore more parsimonious at 5 entities rather than 6.

### 3. `Verification Status` as a first-class conceptual entity

Bronze staff-review Condition 6 elevated verification provenance from a nice-to-have to a governance requirement. I modeled it as a distinct conceptual entity (rather than burying it as a soft attribute) to make the governance intent visible at the conceptual level and to ensure Gold and MCP specs inherit the carry-forward obligation (Condition 7).

At the logical and physical level the entity flattens into a single column (`verification_status`) drawn from a closed two-value enum. The conceptual separation preserves the auditability story; the logical flattening preserves the query-ready shape.

### 4. `census_region` as a derived attribute, not a reference table

The four-region set is a static Census convention. Materializing it as a reference table would add a join for zero analytical value. The FIPS-to-region mapping lives in code and the column is resolved at Silver build time. This matches the project's `base.bls_ooh` treatment of major group names.

### 5. Single denormalized Silver table

All five conceptual entities (State, RPP Measurement, Census Region, Verification Status, Reference Vintage) flatten into one table. All conceptual relationships are 1:1 per row. There is no normalization benefit to splitting, and the Silver Base zone pattern calls for wide, query-ready tables. Matches `base.bls_ooh`, `base.college_scorecard`, `base.karpathy_ai_exposure`.

### 6. `purchasing_power_multiplier` pre-computed in Silver, not Gold

Pre-computing in Silver guarantees every downstream consumer (Gold, MCP tools, frontend) reads an identical value and never risks formula drift. The multiplier is a business-meaningful derived measure, not a transformation Gold should have to repeat. This matches the spec explicitly (Silver transformation 6).

### 7. FIPS stored as VARCHAR, not INTEGER

Zero-padding on codes `01`–`09` must be preserved. Same rule already enforced for CIPCODE in the project. INTEGER storage would break joins.

### 8. `data_year` as INTEGER, not DATE

The column is a calendar-year value used for filtering and for the single-vintage invariant. It is not a date for arithmetic. INTEGER is the spec type (`int`) and matches the DQ rule `COUNT(DISTINCT data_year) = 1`.

### 9. `rpp_all_items` and `purchasing_power_multiplier` as DOUBLE, not DECIMAL

BEA publishes RPP with one decimal place of precision. DOUBLE is sufficient for the inverse invariant tolerance of 0.01 and matches the spec type table (`double`).

### 10. Unpartitioned

51 rows is smaller than any reasonable partition boundary. Partitioning would be pure overhead. Sort order `state_fips ASC` provides natural lookup ordering.

### 11. All columns NOT NULL

This is a closed-set reference table with zero optional fields. The only per-row softness is the `verification_status = 'estimate'` provenance qualifier on 43 of 51 rows, which is a first-class value in its enum — not missing data. Nullability summary: 0 nullable columns, 11 NOT NULL.

### 12. Column order: `verification_status` at position 8 of 11

Per the spec, `verification_status` sits between `purchasing_power_multiplier` (position 7) and `data_year` (position 9). This groups derivations together and keeps the provenance flag next to the measurement it qualifies. Gold and MCP must preserve this order per Condition 7.

---

## Alternatives Considered

| Alternative | Decision | Reason |
|-------------|----------|--------|
| Entity named `Region` or `GeographicUnit` | Rejected in favor of `State` | Less business-friendly; collides with `Census Region`. |
| `state_abbr` as a separate entity | Rejected | No independent relationships; 1:1 synonym for FIPS. Would add structural noise. |
| `census_region` as a reference table | Rejected | Static Census convention; join for zero analytical value. |
| `verification_status` as an attribute (not a conceptual entity) | Rejected | Bronze Condition 6 elevated this to a governance requirement. Modeling it as a distinct entity preserves the auditability story even though it flattens to one column. |
| Separate `RPP Measurement` table with `State` as dimension | Rejected | 1:1 cardinality; no row count benefit; fights the wide-query-ready Silver Base pattern. |
| `data_year` as DATE | Rejected | Calendar-year value, not a date for arithmetic. INTEGER per spec. |
| DECIMAL for RPP values | Rejected | Approximate measures, not currency. DOUBLE sufficient per spec. |
| Partitioning by `census_region` or `data_year` | Rejected | 51-row closed-set table. Partitioning would be metadata overhead with zero benefit. |
| `state_fips` as INTEGER | Rejected | Breaks zero-padding for codes 01-09. Same rule as CIPCODE. |
| Materialize the USPS / Census-region lookups as a Bronze or Silver reference table | Rejected | Static structural data. Per the spec, in-code constants are acceptable here as an explicit exception. |

---

## Glossary Cross-References

All 11 columns have glossary cross-references in both logical and physical models:

| Column | Business Term |
|--------|---------------|
| record_id | BT-015 |
| state_fips | BT-100 |
| state_name | BT-101 |
| state_abbr | BT-103 |
| census_region | BT-104 |
| rpp_all_items | BT-098 |
| purchasing_power_multiplier | BT-099 |
| verification_status | BT-105 |
| data_year | BT-102 |
| source_load_date | BT-016 |
| ingested_at | BT-017 |

CDE assignments: `state_fips`, `state_abbr`, `rpp_all_items`, `purchasing_power_multiplier` (4 columns). Zero PII columns.

Final CDE and PII flags will be set by @cde-tagger on the data contract at `governance/data-contracts/silver-base-bea-rpp.yaml`. The values recorded in the models mirror the spec's intent and match the expected contract values.

---

## Stage Progression

| Stage | Started | Completed | Status |
|-------|---------|-----------|--------|
| Conceptual | 2026-04-10 | 2026-04-10 | PROPOSED — pending human review |
| Logical | 2026-04-10 | 2026-04-10 | PROPOSED — pending human review |
| Physical | 2026-04-10 | 2026-04-10 | PROPOSED — pending human review |

All three stages produced in a single session since the spec is well-specified and the data shape is trivial (single denormalized 51-row reference table). Per the greenfield flow, the stages are top-down: conceptual defines entities and relationships without types, logical enriches with attributes and type domains, physical nails down DuckDB / Iceberg types and the PyIceberg schema.

---

## Flags for Downstream Agents

| Agent | Flag |
|-------|------|
| @data-analyst | EDA should verify: (a) all 51 expected FIPS codes present, (b) all 4 Census regions represented, (c) multiplier inverse invariant within tolerance for every row, (d) 8-state allow-list yields exactly 8 `bea_official` rows. |
| @dq-rule-writer | 15+ P0 rules needed. See "DQ Rule Alignment" table in the physical model for the proposed rule IDs. |
| @primary-agent | The three in-code lookup constants (`FIPS_TO_USPS`, `FIPS_TO_CENSUS_REGION`, `BEA_VERIFIED_FIPS`) are provided in full in the physical model's "In-Code Lookup Constants" section. Copy-paste ready. May need a `governance/exceptions/` filing per the spec. |
| @cde-tagger | 4 CDEs expected: `state_fips`, `state_abbr`, `rpp_all_items`, `purchasing_power_multiplier`. 0 PII. |
| @doc-generator | Must produce data contract, 11 dictionary entries, and confirm glossary terms BT-103/BT-104/BT-105 are present (they already are). |
| Gold spec and MCP spec authors | **Condition 7 carry-forward:** `verification_status` must be propagated to `consumable.regional_price_parities` and to the `get_regional_price_parity` / `compare_purchasing_power` MCP tool responses. This is a governance requirement, not an optional nicety. |

---

## Design Questions Worth Flagging

1. **`state_abbr` attribute vs entity (asked in prompt):** Resolved as **attribute**. See Decision 2 above.
2. **In-code lookup exception filing:** Whether `governance/exceptions/` requires a formal notice for the three static lookups. Spec already anticipates this; @primary-agent should file at implementation time if the project convention requires it. Non-blocking for the modeling stage.
3. **`data_year` INTEGER vs DATE:** Resolved as **INTEGER**. See Decision 8 above.

---

## Sign-off

- [x] Conceptual model produced with Mermaid erDiagram
- [x] Logical model produced with Mermaid erDiagram
- [x] Physical model produced with Mermaid erDiagram
- [x] All 11 columns match the spec schema table exactly
- [x] Column order matches spec (`verification_status` at position 8)
- [x] PyIceberg schema ready for `promote()` call
- [x] Glossary cross-references (BT-IDs) on all 11 columns in logical and physical
- [x] CDE / PII flags recorded (matching expected contract values)
- [x] Derivation rules specified with exact implementation expressions
- [x] In-code lookup constants provided in full (USPS, Census region, BEA allow-list)
- [x] Idempotent promote pattern notes included
- [x] DQ rule alignment table provided
- [x] Audit trail saved

Awaiting human approval per `REQUIRE_HUMAN_APPROVAL = true` before downstream agents (@data-analyst, @dq-rule-writer, @primary-agent) proceed.
