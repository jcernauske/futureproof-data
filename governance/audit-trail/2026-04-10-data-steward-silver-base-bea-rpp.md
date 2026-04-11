# Data Steward Assessment: silver-base-bea-rpp

**Agent:** @data-steward
**Date:** 2026-04-10
**Spec:** docs/specs/silver-base-bea-rpp.md
**Scope:** Business-glossary additions required for the Silver base transformation of BEA Regional Price Parity data
**Mode:** Greenfield (additive to the BEA RPP cluster: BT-098 through BT-102)

---

## Summary

Three new business terms are required to fully cover the silver-base-bea-rpp output columns that are not already defined by the Raw-zone glossary cluster (BT-098 through BT-102). The Raw cluster defines the core metric (RPP), its derived inverse (Purchasing Power Multiplier), the canonical state identifier (FIPS), the display name (State Name), and the vintage (Data Year). The Silver zone introduces three additional columns — a compact state display code, a Census-region grouping, and a per-row provenance label — that need their own terms.

| Term ID | Name | Source | Category | Approval Status |
|---------|------|--------|----------|-----------------|
| BT-103 | USPS State Abbreviation | external-standard (USPS Publication 28) | identifier | auto-approved |
| BT-104 | Census Region | external-standard (U.S. Census Bureau) | taxonomy | auto-approved |
| BT-105 | Data Verification Status | project-specific | provenance | **proposed** (requires human approval) |

## New Terms Proposed

### BT-103 USPS State Abbreviation

- **Source:** external-standard — USPS Publication 28, Appendix B.
- **Approval:** auto-approved. The USPS is an authoritative external standard for postal abbreviations and the closed 51-value set is definitional, not editorial.
- **Why needed:** The silver-base-bea-rpp output surfaces a two-letter state code as the frontend display identifier and as the state-selection key in the forthcoming MCP tool signature. BT-100 (FIPS) and BT-101 (State Name) do not cover this form. BT-100 remains the internal join key.
- **Cross-references:** related to BT-100 (State FIPS Code) and BT-101 (State Name). These three terms are 1:1 with each other across the 51-row state grain.
- **Used in models:** silver-base-bea-rpp, gold-regional-price-parities.

### BT-104 Census Region

- **Source:** external-standard — U.S. Census Bureau (Statistical Abstract / Geographic Terms and Concepts).
- **Approval:** auto-approved. The four-region scheme is defined by a federal statistical agency and is not subject to project editorial judgment.
- **Why needed:** The Silver transformer adds a Census-region label per state so the frontend and Gold zone can aggregate states into the four canonical regions (Northeast, Midwest, South, West). No existing glossary term covers this taxonomy.
- **DC quirk — explicitly documented in the definition.** The definition calls out that the District of Columbia is assigned to the 'South' region by Census convention, and warns consumers that this grouping does not align with DC's Regional Price Parity profile (which is closer to Northeast metros). This is the key semantic hazard flagged by the pre-review advisory for consumers composing Census Region with RPP.
- **Cross-references:** related to BT-101 (State Name). Note: BT-100 is a natural join key but Census Region is semantically a state-level classification, so BT-101 was selected as the primary related term for the display/taxonomy pairing; BT-103 also shares this relationship transitively.
- **Used in models:** silver-base-bea-rpp, gold-regional-price-parities.

### BT-105 Data Verification Status

- **Source:** project-specific. This is a FutureProof-invented provenance mechanism; it is not an external standard.
- **Approval:** **proposed** — requires human approval per the project-specific rule. `REQUIRE_HUMAN_APPROVAL` is `true` in this project (`CLAUDE.md`), and even if it were false, project-specific terms always require human review.
- **Why needed:** The silver-base-bea-rpp transformer hard-codes an 8-state allow-list of BEA-official values and labels the remaining 43 states as primary-agent estimates pending a live BEA API refresh. Consumers of the RPP column must be able to tell these apart; the label is a first-class provenance field that propagates through Gold and MCP and must be disclosed in the Gemma narrative agent's generated copy.
- **Self-contained per pre-review advisory:** BT-105 does not refer the reader to an external document to learn the enum values or the allow-list membership. Its definition:
  - Enumerates both values explicitly: `bea_official` and `estimate`.
  - Lists all 8 authoritative states by name: California, Hawaii, District of Columbia, New Jersey, Arkansas, Mississippi, Iowa, Oklahoma.
  - Cites BEA Regional Economic Accounts SARPP table, LineCode=1, 2024 vintage as the authoritative source of the `bea_official` rows.
  - States the row total (51 = 50 states + DC) and the split (8 official / 43 estimate) at the current hackathon snapshot.
  - Describes the post-hackathon refresh transition where all 51 rows become `bea_official`.
- **Cross-references:** related to BT-098 (Regional Price Parity) as the provenance qualifier for RPP values.
- **Used in models:** silver-base-bea-rpp, gold-regional-price-parities, and `mcp-purchasing-power` (flagged forward-looking — the MCP spec has not yet been drafted; this reference should be refreshed when the MCP spec is authored).

## Existing Terms Referenced

| Term ID | Name | Already Covers | Status |
|---------|------|----------------|--------|
| BT-098 | Regional Price Parity (RPP) | The core RPP metric carried from Raw through Silver | approved |
| BT-099 | Purchasing Power Multiplier | Derived 100/RPP carried into Silver | approved |
| BT-100 | State FIPS Code | Canonical state join key | approved |
| BT-101 | State Name | Display label in English (e.g., "District of Columbia") | approved |
| BT-102 | RPP Data Year | Vintage / provenance year (= 2024) | approved |

No modifications are needed to any of BT-098 through BT-102. The existing BT-098 definition is the semantic anchor for BT-105; BT-105 explicitly names BT-098 as its related parent and carries the provenance qualifier on top of the existing RPP concept.

## Conflicts with Existing Terms

None. I scanned the glossary for potential collisions:

- **State abbreviation / state_code / state_abbr:** not previously defined. BT-103 is the first term covering this concept.
- **Region / census_region / regional grouping:** not previously defined. BT-104 is the first taxonomy term at the four-region level.
- **Verification status / provenance label / bea_official / estimate:** not previously defined. BT-105 is the first provenance-qualifier term on an RPP value.

I also checked for synonym collisions. None of the synonyms attached to BT-103 (`state_abbr`, `USPS code`, `state_code`, etc.), BT-104 (`census_region`, `Census Bureau region`), or BT-105 (`verification_status`, `rpp_verification_status`, `bea_official_flag`) appear as synonyms or primary names on any existing term BT-001 through BT-102.

## Coverage Confirmation vs. Pre-Review Advisory

The pre-review advisory raised two specific coverage concerns. Both are addressed:

1. **"BT-105 should be self-contained — enumerate the two values and cite the 8-state allow-list authoritatively."**
   BT-105 enumerates `bea_official` and `estimate`, lists all 8 states by name, cites the BEA SARPP table with LineCode and vintage, and documents the 51-row split and the post-hackathon refresh semantics. A reader can learn the full meaning of the field without leaving the glossary entry. The source_reference field additionally points at the Silver spec and the EDA notebook as implementation anchors.

2. **DC quirk under Census Region.**
   BT-104 explicitly calls out that DC is grouped into 'South' by Census convention despite its Northeast-adjacent geography and despite its RPP profile resembling Northeast metros. Consumers are warned not to compose Census Region with cost-of-living conclusions without checking for this edge case.

## Ambiguities Found

None in the new-term scope. One forward-looking open item:

- **`used_in_models` for BT-105 references `mcp-purchasing-power`, which does not yet exist as a spec.** This is flagged inline in the term entry ("forward-looking — spec not yet drafted"). When the MCP spec is authored, the data-steward should confirm the canonical spec name and remove the forward-looking marker. This does not block Silver zone progression.

## Source Attribution Summary

| Term | Attribution | Type |
|------|-------------|------|
| BT-103 | USPS Publication 28, Appendix B | Authoritative federal standard — auto-approved |
| BT-104 | U.S. Census Bureau geographic terms & concepts | Authoritative federal statistical agency — auto-approved |
| BT-105 | docs/specs/silver-base-bea-rpp.md + governance/eda/raw-bea-rpp-eda.md | Project-invented provenance mechanism — requires human approval |

## Validator Note

Running `uv run python -m brightsmith.infra.glossary_validator validate` after the edits returns 9 category-mismatch warnings covering BT-094, BT-095, BT-098, BT-100, BT-101, BT-102, and the three new BT-103/104/105 entries. The validator's allowed category set is `{regulatory, temporal, measurement, entity, classification, derived}`, but the authored BEA cluster (BT-098 through BT-102) already uses `metric`, `identifier`, and `provenance`, and BT-094/095 already use `metric` and `descriptive`. These are pre-existing mismatches authored before this session. I have kept BT-103/104/105 consistent with the sibling BEA cluster (`identifier`, `taxonomy`, `provenance`) rather than rewriting the established project convention in a glossary-addition session. Reconciling the validator allow-list vs. the authored category vocabulary is a separate governance task and should be raised with the framework maintainer.

## Recommendation

1. **Auto-approve BT-103 and BT-104** — both are external-standard definitions from federal authorities (USPS, U.S. Census Bureau).
2. **Route BT-105 through the governance-reviewer and staff-engineer approval gates** before silver-base-bea-rpp implementation lands, per `REQUIRE_HUMAN_APPROVAL = true`. The term is ready for review: it is self-contained, enumerates both values, lists the 8-state allow-list by name, and cites its authoritative sources.
3. **Proceed with semantic modeling** for silver-base-bea-rpp once BT-105 receives approval. BT-098 through BT-104 are all cleared for referencing.

---

## Artifacts

- **Updated:** `governance/business-glossary.json` — 3 new terms appended (BT-103, BT-104, BT-105); term count now 105.
- **Created:** `governance/audit-trail/2026-04-10-data-steward-silver-base-bea-rpp.md` — this file.
