# Data Steward Audit Trail — silver-base-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @data-steward
**Mode:** Greenfield (Silver zone term definition, resolving dangling references inherited from Bronze)
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md (Business Glossary Terms table, lines 222-226)
**Glossary:** governance/business-glossary.json
**Domain:** Education / Career Guidance (College Scorecard institution-level cost sub-domain)

## Summary

Added three new business glossary terms — BT-110 (Cost of Attendance), BT-111 (Net Price), BT-112 (Net Price by Income Quintile) — required by the `silver-base-college-scorecard-institution` Silver zone spec and already referenced as `business_term:` values on 17+ columns of the approved Bronze data contract, the CDE registry, and the data dictionary. These terms were declared in the spec and in Bronze artifacts during the Bronze cycle but never written to the glossary JSON, resulting in dangling references that the Silver pre-implementation governance review flagged as a P0 blocker. This audit entry closes that defect.

All three terms come directly from the U.S. Department of Education's College Scorecard data dictionary (an authoritative external standard published by IPEDS/NCES), so they qualify for `auto-approved` status per the data-steward approval rules. No human review is required for the definitions themselves — the authority is the external standard, not the FutureProof pipeline.

## New Terms Proposed

| Term ID | Term | Source | Category | Approval Status |
|---------|------|--------|----------|------------------|
| BT-110 | Cost of Attendance (COA) | external-standard | measurement | auto-approved |
| BT-111 | Net Price | external-standard | measurement | auto-approved |
| BT-112 | Net Price by Income Quintile | external-standard | measurement | auto-approved |

### BT-110 Cost of Attendance (COA)

- **Source:** external-standard — published by U.S. Department of Education / College Scorecard, derived from IPEDS IC (Institutional Characteristics) and SFA (Student Financial Aid) components.
- **Category:** `measurement` — continuous dollar-valued quantity with a known unit (annual USD).
- **Source fields:** COSTT4_A (academic-year institutions, ~72.1% coverage), COSTT4_P (program-year institutions, ~1.3% coverage). Mutually exclusive at the institution level.
- **Synonyms:** include both raw field names plus the informal label "Sticker Price" used in downstream UI copy.
- **Related terms:** BT-001 (UNITID — grain), BT-111 (Net Price — paired concept, net = COA − aid), BT-112 (Net Price by Income Quintile — same aid-subtraction applied at finer grain).
- **Downstream consumers:** Silver `cost_of_attendance_annual` unified field (COALESCE(costt4_a, costt4_p)), `cost_of_attendance_4yr` derivation, Gold `consumable.career_outcomes.cost_of_attendance_annual` receipt-line column.
- **used_in_models:** `raw-ingest-college-scorecard-institution`, `silver-base-college-scorecard-institution`, `gold-career-outcomes-college-scorecard`.

### BT-111 Net Price

- **Source:** external-standard — published by U.S. Department of Education / College Scorecard, derived from IPEDS SFA component.
- **Category:** `measurement` — continuous dollar-valued quantity (annual USD, can legitimately be negative).
- **Source fields:** NPT4_PUB (public institutions, control=1), NPT4_PRIV (private institutions, control IN (2,3)). Keyed on institutional control — exactly one of the two applies per row.
- **Definition captures negative-value semantics:** explicitly documented that net price can be negative when average grant aid exceeds total COA (e.g., Skyline College at -$1,180). This prevents downstream consumers from adding a bogus `WHERE net_price > 0` filter.
- **ROI role:** the definition names BT-111 as the ROI denominator input in the FutureProof formula `earnings / (net_price * 4 * loan_pct)`. Every Fight Student Loans boss outcome depends on this term, so the definition carries full gameplay weight.
- **Related terms:** BT-001 (UNITID — grain), BT-110 (COA — parent concept), BT-112 (Net Price by Income Quintile — quintile-grained version).
- **used_in_models:** `raw-ingest-college-scorecard-institution`, `silver-base-college-scorecard-institution`, `gold-career-outcomes-college-scorecard`.

### BT-112 Net Price by Income Quintile

- **Source:** external-standard — published by U.S. Department of Education / College Scorecard, derived from IPEDS SFA component.
- **Category:** `measurement` — same as BT-111 but disaggregated across five family-income brackets.
- **Enumeration completeness:** all five income brackets and both control strata are documented in the definition (10 source fields total: NPT41_PUB..NPT45_PUB, NPT41_PRIV..NPT45_PRIV).
- **Monotonicity invariant:** the definition names the P1 DQ rule `net_price_q1 <= net_price_q5` explicitly so any DQ rule writer consuming this glossary term knows the expected aid gradient.
- **Negative-value semantics:** carried forward from BT-111 — Q1 net price can legitimately go negative at high-endowment private institutions (MIT Q1 at -$4,129 cited as a worked example).
- **Synonyms list:** includes all 10 raw field names plus the Silver-output column names (`net_price_q1`..`net_price_q5`) so upstream and downstream references both resolve to this term.
- **Related terms:** BT-001 (UNITID — grain), BT-110 (COA — total cost), BT-111 (Net Price — aggregate version).
- **used_in_models:** `raw-ingest-college-scorecard-institution`, `silver-base-college-scorecard-institution`, `gold-career-outcomes-college-scorecard`.

## Approval Status Rationale

All three terms are marked `auto-approved` rather than `proposed`. Per the data-steward approval rules:

> Auto-approval for external/domain standards means: if REQUIRE_HUMAN_APPROVAL = True, these terms are still auto-approved because the authority is the external standard, not our pipeline. Project-specific terms always require human review regardless of the toggle.

The College Scorecard data dictionary is the authoritative external standard. The definitions do not invent any FutureProof-specific semantics — they faithfully restate what the U.S. Department of Education publishes, with worked examples drawn from the observed 2023 data. Silver implementation can proceed without a human-in-the-loop gate on these definitions.

If a future editorial pass introduces project-specific derivations (e.g., a 4-year cost projection or an aid-gap score), those derivations will need new `project-specific` term IDs with `proposed` status and an explicit human approval gate. This glossary update does not create any such derivation — BT-110/111/112 are raw external measurements only.

## Schema Conformance

All three new terms use the exact same JSON schema as BT-001..BT-107 with all required fields populated:

- `term_id`, `name`, `definition`, `source`, `source_reference`, `synonyms`, `related_terms`, `category`, `owner`, `used_in_models`, `approval_status`.

JSON loads cleanly. Post-add term count = 110 (was 107). Last four IDs: BT-107, BT-110, BT-111, BT-112. BT-108 and BT-109 intentionally unused — the Silver pre-review noted they could be allocated for intermediate concepts but no such concepts surfaced during the Bronze cycle, so the numbering gap is preserved. BT-108/109 remain free for future allocation.

## Cross-Reference Integrity

- BT-110 ↔ BT-111 ↔ BT-112 all reciprocally linked via `related_terms` (each new term references the other two plus BT-001 UNITID for grain).
- BT-001 does not currently back-link to BT-110/111/112 in its `related_terms` array. This is consistent with how BT-001 was originally authored (which pre-dates these terms) and matches the non-retroactive pattern established by the BT-106/BT-107 audit. Back-linking can be revisited as a glossary hygiene pass if governance requests it.

## Bronze-to-Glossary Consistency

Cross-referenced the new glossary entries against the already-approved Bronze artifacts to confirm semantic alignment:

| Bronze artifact | BT-110 usage | BT-111 usage | BT-112 usage | Consistent? |
|-----------------|--------------|--------------|--------------|-------------|
| governance/data-contracts/raw-college-scorecard-institution.yaml | `business_term: BT-110` on costt4_a, costt4_p | `business_term: BT-111` on npt4_pub, npt4_priv | `business_term: BT-112` on all 10 quintile fields | YES |
| CDE registry (via contract `cde_fields:` block) | Listed with comment "# Cost of Attendance (COA)" | Listed with comment "# Net Price" | Listed with comment "# Net Price by Income Quintile" | YES |
| Spec §Business Glossary Terms (lines 222-226) | Matches definition | Matches definition | Matches definition | YES |

The new glossary definitions are a strict superset of the Bronze artifact descriptions — they add source-field enumeration, the ROI-denominator role, the monotonicity invariant, and the negative-value semantics that were implicit in the Bronze contract but never captured as glossary prose.

## Conflicts / Ambiguities

- **No ID collisions.** BT-110, BT-111, BT-112 confirmed absent from the pre-edit glossary (the file ended at BT-107 Adjusted Salary before this edit).
- **No name collisions.** None of "Cost of Attendance (COA)", "Net Price", or "Net Price by Income Quintile" appeared as an existing term or synonym. The only nearby existing term is BT-011 Median Debt at Completion (a different financial concept — what students borrow, not what they pay).
- **No definition conflicts.** The spec's usage, the Bronze contract's field-level descriptions, and the CDE registry's rationale fields all align with the definitions captured here.
- **Pre-existing validator warnings (NOT caused by this change):** `uv run python -m brightsmith.infra.glossary_validator validate` continues to report 9 category issues on BT-094, BT-095, BT-098, BT-100, BT-101, BT-102, BT-103, BT-104, BT-105 (categories `metric`, `descriptive`, `identifier`, `provenance`, `taxonomy` are not in the validator's allowed set `{regulatory, classification, temporal, entity, derived, measurement}`). These are pre-existing drift and are out of scope for this task. All three new terms use the validator-allowed `measurement` category and therefore pass the schema check cleanly — they do not add to the warning count.

## Artifacts

- Updated: `governance/business-glossary.json` (BT-110, BT-111, BT-112 appended; term count 107 → 110)
- Written: `governance/audit-trail/2026-04-14-data-steward-silver-base-college-scorecard-institution.md` (this file)

## Unblocks

- Silver pre-implementation governance review item "Business Glossary Prerequisite — BT-110, BT-111, BT-112" (previously FAIL — dangling references)
- @semantic-modeler can now build the Silver conceptual model referencing these three terms
- @dq-rule-writer can now attribute the aid-monotonicity and range-check rules to BT-111 and BT-112
- All downstream Silver gates (logical model, physical model, DQ execution, chaos monkey, post-governance, staff engineer) are no longer blocked on glossary completeness for this spec.
