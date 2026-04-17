# Audit Trail: @doc-generator — raw-ingest-college-scorecard-institution

**Agent:** @doc-generator
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Zone:** Bronze (Raw)
**Table:** `raw.college_scorecard_institution`
**Date:** 2026-04-14
**Task ID:** #11 (Documentation generation)

---

## Artifacts Produced

| Artifact | Path | Purpose |
|----------|------|---------|
| Data Dictionary | [governance/data-dictionaries/raw-college-scorecard-institution.md](../data-dictionaries/raw-college-scorecard-institution.md) | Plain-English field-by-field reference for all 28 columns (24 source + 4 metadata) |
| Data Contract | [governance/data-contracts/raw-college-scorecard-institution.yaml](../data-contracts/raw-college-scorecard-institution.yaml) | Machine-readable contract v1.0.0 with schema, grain, CDE/PII flags, DQ rule refs, lineage ref |
| Grounding Document | [governance/grounding/raw-college-scorecard-institution.md](../grounding/raw-college-scorecard-institution.md) | MCP-zone consumption fact sheet with confidence notes for AI consumers |

New directories created:
- `governance/data-dictionaries/` (first entry in project — will be populated by subsequent specs)
- `governance/grounding/` (first entry in project — will be populated by subsequent specs)

---

## Inputs Consumed

| Input | Role |
|-------|------|
| `docs/specs/raw-ingest-college-scorecard-institution.md` | Source of truth for schema, grain, filter predicate, glossary terms, and downstream usage |
| `governance/cde-registry/raw-ingest-college-scorecard-institution-cdes.md` | CDE/PII flags and rationales for all 28 columns (17 CDE, 0 PII) |
| `governance/dq-rules/raw-ingest-college-scorecard-institution.json` | 13 approved DQ rules (7 P0, 6 P1) used to populate `dq_rules` per-column links |
| `governance/lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json` | OpenLineage transformation record (all fields DIRECT or DERIVED) |
| `domain/raw-ingest-college-scorecard-institution-context.md` | EDA-backed domain knowledge for plain-English definitions and confidence notes |
| `governance/data-contracts/raw-college-scorecard.yaml` | Sibling Bronze contract — structural pattern reference |
| `governance/data-contracts/raw-bea-rpp.yaml` | Recent Bronze contract — pattern reference for `quality_tier`, `downstream_consumers`, `cde_summary` structure |

---

## Decisions & Judgment Calls

### 1. Record count updated from spec (~6,500) to EDA-verified (3,039)

The spec assumed ~6,500 institutions based on the unfiltered file row count (6,429). EDA confirmed that after `PREDDEG=3 OR ICLEVEL=1` filtering, only 3,039 remain. All three artifacts cite **3,039** as authoritative, matching the DQ rule RAW-CSI-001 (range 2,500–3,500) and the domain context. No substitution of the spec's stated figure — the EDA is the post-implementation truth.

### 2. COA coverage reported as 73.5%, not spec's 90%

The spec originally assumed ≥90% of rows would have at least one COA field. EDA showed actual coverage of 73.5%, and DQ rule RAW-CSI-010 was approved at ≥70%. All three artifacts cite 73.5% and explicitly note the two populations driving the gap (PREDDEG=0 and PREDDEG=4 institutions admitted by `ICLEVEL=1`).

### 3. Negative net prices documented as legitimate in all three artifacts

The spec is silent on negatives but the EDA and the approved DQ rules (RAW-CSI-006 range -$5,000 to $60,000 for `npt4_pub`; RAW-CSI-007 range -$5,000 to $80,000 for `npt4_priv`) make negative values a first-class case. Documented in:
- Dictionary: field-level note on `npt4_pub`/`npt4_priv` + caveat #2 in "Caveats for Consumers"
- Contract: description text on both columns + `cde_rationale` citing "negatives legitimate"
- Grounding: confidence note #2 (explicit "do not clip to $0" guidance for AI consumers)

Specific example values (San Diego Mesa -$904, Skyline College -$1,180, St Petersburg College -$52, MIT Q1 -$4,129) are cited verbatim from EDA.

### 4. Adjacent-quintile non-monotonicity explicitly documented

The DQ rule RAW-CSI-013 only enforces full-span (Q1 ≤ Q5) monotonicity, not adjacent pairs, because EDA found 37.9% of private schools have Q1 > Q2 due to merit aid patterns. All three artifacts call this out (Dictionary caveat #3, Contract column descriptions, Grounding confidence note #3) to prevent downstream consumers from writing rules or narratives assuming strict ascent.

### 5. Business terms cross-referenced at the column level

BT-110 (Cost of Attendance), BT-111 (Net Price), and BT-112 (Net Price by Income Quintile) are referenced in:
- Dictionary: `Business Term` column in each field table
- Contract: `business_term` field on applicable columns + `glossary_terms` list at document level
- Grounding: dedicated "Glossary Terms Referenced" section

Per the CDE registry, BT-CSI-CONTROL was proposed as a local term for `control` but the registry is ambiguous on whether it should be a full glossary entry. Chose to **omit** BT-CSI-CONTROL from the column-level `business_term` field in the contract and treat `control` as self-describing in the Dictionary (no BT-link in the table). Rationale: the business glossary is external to this spec and a new BT entry should be promoted deliberately through the glossary process, not side-effected by this doc-generation pass. Flagged for @staff-engineer review — if BT-CSI-CONTROL should be elevated, this can be a minor patch.

### 6. Contract version set to 1.0.0

First emission of this contract — no prior version exists. Backward compatibility is N/A. Future changes will follow the documented semver policy in the `breaking_changes` block.

### 7. Status remains DRAFT pending @staff-engineer approval

Per the CLAUDE.md governance model and the @doc-generator role definition, data contracts become `active` only after @staff-engineer approves. Status is set to `DRAFT` in the YAML; approval workflow is the next step (task #13).

### 8. `quality_tier` set to `high`

The sibling `raw-college-scorecard.yaml` did not set a quality tier, and `raw-bea-rpp.yaml` set `partial_verification` because its data was estimated. This ingest is different: all 3,039 rows are structurally valid, the source is authoritative (U.S. Government Work), 13/13 DQ rules pass, zero cross-contamination between `npt4_pub` and `npt4_priv`. Known coverage gaps are documented as upstream IPEDS limitations, not pipeline defects. Tier: `high`.

---

## Governance Completeness Checklist

| Item | Status |
|------|--------|
| Every field has a plain-English definition | ✅ All 28 fields in Dictionary; matches Contract descriptions |
| CDE flags cross-referenced from CDE registry | ✅ 17/28 CDE, 0/28 PII in all three artifacts |
| DQ rules cross-referenced from DQ rules file | ✅ Per-column `dq_rules` lists in Contract; summary table in Dictionary |
| Lineage referenced | ✅ `lineage_reference` field in Contract; dedicated Lineage section in Grounding |
| Business terms linked | ✅ BT-110, BT-111, BT-112 in all three artifacts |
| Spec cross-reference | ✅ `spec_reference` in Contract; header link in Dictionary and Grounding |
| Domain context cross-reference | ✅ `domain_context_reference` in Contract; header link in Dictionary |
| Confidence notes for AI consumers | ✅ 8 notes in Grounding covering CONTROL routing, negatives, quintile monotonicity, COA gaps, for-profit thinness, tuition vs ROI, snapshot semantics, missing room-board |
| Change log present | ✅ Dictionary and Grounding |

---

## Handoff Notes for Downstream Agents

- **@governance-reviewer (task #12):** all three artifacts reference the approved DQ rules by ID (RAW-CSI-001 through RAW-CSI-013). No P0/P1 rule is missing from the Contract's per-column `dq_rules` lists.
- **@staff-engineer (task #13):** contract status is `DRAFT`. Promote to `active` after review. One judgment call to verify: whether `BT-CSI-CONTROL` should be elevated to a full glossary entry (see Decision #5 above).
- **Silver-zone @doc-generator (future):** the CDE registry's "Forward Note" lists the expected Silver CDE set. This is a recommendation, not binding — Silver will be re-evaluated on its own merits. Do not propagate CDE flags automatically.
- **Gold-zone @doc-generator (future):** the enrichment columns added to `consumable.career_outcomes` (`net_price_annual`, `cost_of_attendance_annual`, `net_price_4yr`, `institution_control`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`) will be documented there. This artifact does not describe Gold.

---

## Timestamp

Generated: 2026-04-14
Ingest lineage reference: 2026-04-14T21:30:00Z
