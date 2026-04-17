# Governance Review: silver-base-college-scorecard-institution

**Review Type:** Pre-Implementation (Silver Zone)
**Reviewer:** @governance-reviewer
**Date:** 2026-04-14
**Verdict:** CHANGES REQUESTED

---

## Scope Statement

This review is scoped to **Zone 2: Silver** of the spec `docs/specs/raw-ingest-college-scorecard-institution.md` (lines 138–228). The Bronze zone is already APPROVED WITH ADVISORIES (see `raw-ingest-college-scorecard-institution-post-review.md`). Gold zone (Zone 3) is a future review gate and is out of scope here.

Target table: `base.college_scorecard_institution` — **greenfield** (does not yet exist).

Review covers:
1. Silver schema completeness and field typing (§2, lines 185–207)
2. Silver transformation SQL pseudocode and edge-case coverage (§2, lines 146–181)
3. Silver DQ rule set (§2, lines 210–218)
4. Business glossary terms BT-110, BT-111, BT-112 prerequisite check
5. Greenfield Data Model Gate (conceptual → logical → physical) applicability
6. Cross-artifact consistency with the approved Bronze deliverable

---

## Pre-Implementation Checklist Results

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Problem statement & success criteria | PASS | Clear in §Problem Statement; success criteria explicitly list a Silver base table with unified net-price field (line 61). |
| 2 | Input data source identified | PASS | `raw.college_scorecard_institution` (3,039 rows, 28 fields, 17 CDE) — Bronze deliverable is APPROVED. |
| 3 | Output artifact defined (path + format) | PASS | Iceberg table `base.college_scorecard_institution`; full field list in the spec. |
| 4 | Transformations described | PARTIAL | Six named transformations with SQL pseudocode, but edge cases are under-specified (see Issues 1–3). |
| 5 | Zone assignment correct | PASS | Silver / base zone is correct — normalizing and unifying Bronze data, no cross-source joins. |
| 6 | Primary implementation agent identified | PASS | Spec §Agent Workflow identifies `@primary-agent` for Silver transformer. |
| 7 | DQ rule categories specified | PARTIAL | 8 rules listed but priority tagging and EDA-informed thresholds need strengthening (see Issues 4–6). |
| 8 | CDE mapping impact assessed | PARTIAL | Bronze CDE registry lists downstream Silver column names (`net_price_annual`, `cost_of_attendance_annual`, `net_price_q1..q5`) and tags them CDE. Silver spec does not yet call out which Silver columns inherit CDE status explicitly — acceptable to resolve during @cde-tagger run, but worth noting. |
| 9 | Lineage scope defined | PASS (implicit) | Source = `raw.college_scorecard_institution`; sink = `base.college_scorecard_institution`. Column-level transforms enumerated. |
| 10 | Breaking-change flag | N/A | Greenfield table — no existing schema to break. |
| 11 | Testing approach defined | FAIL | Spec does not specify testing approach for the Silver transformer (no mention of `tests/silver/test_college_scorecard_institution_transformer.py`, no target test count). See Issue 7. |

### Greenfield Data Model Gate — Base Zone

This is a greenfield Silver (base) table in the Base zone. Per CLAUDE.md governance policy ("Models must be complete BEFORE implementation begins. This gate is blocking at pre-implementation review."), **all three model stages must be approved before Silver implementation starts**.

| Model | Required Path | Status |
|-------|---------------|--------|
| Conceptual | `governance/models/silver-base-college-scorecard-institution-conceptual.md` | MISSING |
| Logical | `governance/models/silver-base-college-scorecard-institution-logical.md` | MISSING |
| Physical | `governance/models/silver-base-college-scorecard-institution-physical.md` | MISSING |

All three absent. Reference precedent: the original `silver-base-college-scorecard-*` triad (field-of-study file) exists and should be the template.

### Business Glossary Prerequisite — BT-110, BT-111, BT-112

**FAIL.** The spec and the already-approved Bronze artifacts (CDE registry, data contract, data dictionary) reference glossary terms **BT-110 (Cost of Attendance)**, **BT-111 (Net Price)**, and **BT-112 (Net Price by Income Quintile)**. Direct inspection of `governance/business-glossary.json` confirms the file ends at **BT-107 (Adjusted Salary)**. BT-108, BT-109, BT-110, BT-111, BT-112 **do not exist** in the glossary.

The Bronze post-review (line 55) asserts these terms are "CONSISTENT — BT-110, BT-111, BT-112 referenced in both" the contract and CDE registry. That check verified the Bronze artifacts reference the terms consistently with each other, but **neither the Bronze post-review nor any prior gate confirmed the terms actually exist in the glossary JSON**. This is a dangling-reference defect inherited from the Bronze cycle.

Impact: @data-steward must create BT-110, BT-111, BT-112 (and decide whether to allocate BT-108/109 for any intermediate concepts) before @semantic-modeler can build the conceptual model that references them. This is a blocking prerequisite for the Silver data-model gate.

---

## Silver Schema Review (lines 185–207)

| Check | Finding |
|-------|---------|
| `record_id` present with deterministic grain (prefix `csi`) | PASS |
| Grain key `unitid` present and typed `long` | PASS |
| Dedup grain `[unitid]` documented | PASS (line 143) |
| Nullability flags on every column | PASS |
| Cost/price fields typed `double` | PASS |
| Control label typed `string` with enumerated values | PASS |
| Timestamps for `source_load_date` + `ingested_at` | PASS |
| All 17 raw cost fields carried through OR their transforms | MIXED — See Issue 2 |

**Issue 2 detail.** Bronze schema has 24 source fields. Silver schema lists 20 output fields (5 are unified derivations of 15 raw fields: `net_price_annual` subsumes `npt4_pub`/`npt4_priv`; `cost_of_attendance_annual` subsumes `costt4_a`/`costt4_p`; `net_price_q1..q5` subsume the 10 quintile fields). The spec says (line 181) "All raw cost fields carried through for receipt/provenance display" — but the Silver schema (lines 185–207) does **not** include the raw fields `costt4_a`, `costt4_p`, `npt4_pub`, `npt4_priv`, `npt41_pub`..`npt45_pub`, `npt41_priv`..`npt45_priv`. This contradicts transformation #6. Either the schema is missing 15 pass-through fields, or transformation #6 is wrong. Must be reconciled.

Also missing from Silver schema relative to Bronze:
- `preddeg` (needed for provenance — which filter branch selected this row?)
- `other_expense_on` / `other_expense_off` (Bronze has these; Silver drops them silently)

**Issue 3 detail.** Spec §4 (4-year totals, line 166) says `net_price_4yr = net_price_annual × 4` and `cost_of_attendance_4yr = cost_of_attendance_annual × 4`. The schema includes `net_price_4yr` (line 194) and `cost_of_attendance_4yr` (line 195). Good. However, the DQ rule (line 216) asserts "within $1 tolerance" — but pure `× 4` of a `double` should be exact under IEEE-754 for the input magnitudes involved. The tolerance hedge is either unnecessary or hints that the transformer might round intermediate values; clarify.

---

## Silver Transformation Review

| Transformation | Clarity | Edge Cases |
|----------------|---------|------------|
| 1. Unified net price by control | Clear SQL CASE, but see Issue 1 | Control=1/2/3 covered; `ELSE NULL` not explicit. If `control` is somehow NULL in Bronze (it shouldn't — Bronze rule enforces `control IN (1,2,3)`), the CASE returns NULL silently. Acceptable but make explicit. |
| 2. Unified COA via COALESCE | Clear | Both nulls → null output. Fine. |
| 3. Control label mapping | Clear | Same NULL gap as (1). |
| 4. 4-year totals | Clear | Null propagation: `NULL × 4 = NULL`. Fine. |
| 5. Unified quintile net price | Clear | Same NULL gap as (1). |
| 6. Raw pass-through | Stated but NOT reflected in schema | **Contradiction — see Issue 2.** |

**Issue 1 detail.** The CASE in transformation #1 silently routes `control=3` (for-profit) to `npt4_priv`. That's correct per IPEDS conventions but is a non-obvious business rule. The Bronze CDE registry already documents this, but the Silver spec should call out explicitly: "For private for-profit institutions (control=3), the public `NPT4_PRIV` field is the correct net-price source per IPEDS documentation." Same pattern applies to quintile mapping (transformation #5).

---

## Silver DQ Rules Review (lines 210–218)

| # | Rule | Priority | EDA-Informed? | Verdict |
|---|------|----------|---------------|---------|
| 1 | Row count matches Bronze | P0 | N/A | OK |
| 2 | `unitid` uniqueness | P0 | N/A | OK |
| 3 | `net_price_annual` non-null ≥85% | P0 | Needs confirmation from Silver EDA | OK pending EDA |
| 4 | `cost_of_attendance_annual` non-null ≥80% | P0 | Needs confirmation from Silver EDA | OK pending EDA |
| 5 | `net_price_annual ≤ cost_of_attendance_annual` | P0 | Derived invariant | OK |
| 6 | `net_price_4yr = net_price_annual × 4 ± $1` | P0 | See Issue 3 | Tolerance hedge — OK if justified |
| 7 | `institution_control` ∈ {"Public","Private nonprofit","Private for-profit"} | P0 | N/A | OK |
| 8 | `net_price_q1 ≤ net_price_q5` | P1 | Bronze RAW-CSI-013 uses "outlier count ≤ 50" | See Issue 4 |

**Issue 4 detail.** The Bronze already has rule `RAW-CSI-013` (per chaos manifest + scorecard discussion in the Bronze post-review, line 76) checking `net_price_q1 ≤ net_price_q5` tolerance count — Bronze EDA established 46 outliers against a threshold of 50. The Silver rule asserts the invariant directly ("net_price_q1 ≤ net_price_q5 where both non-null (P1)") with no tolerance. A strict invariant will fail for ~46 rows based on Bronze EDA. The rule should either (a) be written as a tolerance check with the same threshold posture as Bronze, (b) escalate to P0 if the Silver transformer actively filters those outliers, or (c) explicitly state the expected failure count and why P1 not P0.

**Issue 5 detail.** **Missing coverage — non-negativity.** No DQ rule asserts `net_price_annual ≥ 0`, `cost_of_attendance_annual ≥ 0`, or `net_price_q1..q5 ≥ 0`. Bronze has `npt4_pub ≥ 0` and `npt4_priv ≥ 0` range checks (lines 128–129 of spec). The Silver unified field inherits these properties but should have an explicit range/non-negativity rule for clarity.

**Issue 6 detail.** **Missing coverage — 4-year total sanity.** `net_price_4yr` and `cost_of_attendance_4yr` have no range check. A P1 range check ($0–$400,000) would catch arithmetic bugs without depending on the tolerance check (rule #6) firing.

**Issue 7 detail.** **Missing coverage — grain count vs Bronze with filter.** Rule #1 asserts row count equals Bronze. But Bronze has 3,039 rows post-filter (per Bronze post-review). Silver should either preserve all 3,039 or drop rows that fail the `control IN (1,2,3)` requirement. The spec does not indicate any Silver-level filtering. Add explicit rule: "Silver row count = Bronze row count = 3,039 exactly" — not a range.

**Issue 8 detail.** **Missing coverage — CDE completeness.** The most important Silver column (`net_price_annual`) has a non-null threshold (≥85%). The second-most-important (`cost_of_attendance_annual`) has ≥80%. But `institution_control` has no explicit non-null rule — spec says "required: yes" in the schema but no DQ guards this. Required-field non-null = 100% should be P0.

---

## Cross-Artifact Consistency With Bronze

| Check | Finding |
|-------|---------|
| Silver column names vs Bronze CDE registry's "downstream Silver column" annotations | CONSISTENT — `net_price_annual`, `cost_of_attendance_annual`, `net_price_q1..q5`, `net_price_4yr`, `cost_of_attendance_4yr`, `institution_control` all match. |
| Silver grain vs Bronze grain | CONSISTENT — both `unitid`. |
| Silver glossary-term references vs glossary file | **FAIL — BT-110/111/112 referenced in spec but not in `governance/business-glossary.json` (file ends at BT-107).** |
| Silver row-count expectation vs Bronze output | UNDERSPECIFIED — spec says "matches Bronze" but Bronze actual is 3,039 (post-filter); Silver expected row count should be stated exactly. |
| Silver schema types vs Bronze types | CONSISTENT where they overlap. |
| Silver DQ thresholds vs Bronze EDA findings | **UNVERIFIED — no Silver EDA exists yet.** Spec thresholds (85% / 80%) look defensible vs Bronze non-null rates (Bronze NPT4_PUB coverage for public ≥75%, NPT4_PRIV for private ≥65% per chaos manifest), but unified `net_price_annual` non-null rate has not been computed from the Bronze table. @data-analyst must produce a Silver EDA before @dq-rule-writer finalizes the 85% / 80% thresholds. |

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | Business glossary terms BT-110, BT-111, BT-112 referenced by the spec (and by the approved Bronze contract/CDE registry/data dictionary) **do not exist** in `governance/business-glossary.json` (file ends at BT-107). This is a dangling-reference defect inherited from Bronze and carried into Silver. | @data-steward must draft BT-110 (Cost of Attendance), BT-111 (Net Price), BT-112 (Net Price by Income Quintile) per the definitions in the spec (lines 222–226). Human approval required before Silver data-model gate passes. |
| 2 | CHANGES REQUESTED | Greenfield Data Model Gate unmet: no conceptual, logical, or physical model exists in `governance/models/` for `silver-base-college-scorecard-institution`. CLAUDE.md mandates all three APPROVED before Silver implementation begins. | @semantic-modeler must produce all three stages. Conceptual must reference BT-110/111/112 (prerequisite: Issue 1 resolved). Logical must abstract the six transformations. Physical must match the Silver schema (after Issue 3 resolved). |
| 3 | CHANGES REQUESTED | Silver schema contradicts transformation #6. The spec says (line 181) "All raw cost fields carried through for receipt/provenance display" but the schema (lines 185–207) omits `costt4_a`, `costt4_p`, `npt4_pub`, `npt4_priv`, and all 10 `npt4[1-5]_pub/_priv` quintile fields. Also omits `preddeg`, `other_expense_on`, `other_expense_off`. | Spec author: either (a) add 15+ raw pass-through fields to the schema, or (b) remove transformation #6 from the transformation list and accept that only unified fields are persisted. Must pick one and update both places. |
| 4 | CHANGES REQUESTED | Testing approach is not defined for the Silver transformer. Spec does not reference `tests/silver/test_college_scorecard_institution_transformer.py`, does not state a test target, and does not identify fixtures. Bronze has 41 tests — Silver needs comparable coverage. | Spec author: add §Testing subsection to Zone 2 listing required test file path, target test count (≥20 is reasonable for 6 transformations + 8 DQ invariants), and sample-fixture strategy (likely reuse or extend Bronze `tests/raw/college_scorecard_institution_sample.csv`). |
| 5 | CHANGES REQUESTED | Silver DQ thresholds (85% non-null for `net_price_annual`, 80% for `cost_of_attendance_annual`) are asserted without EDA evidence. No `governance/eda/silver-college-scorecard-institution-eda.md` exists. Per adversarial auditor's HR-7 finding on Bronze (EDA-as-sole-witness gap), Silver needs a reproducible EDA. | @data-analyst must produce Silver EDA against the actual Bronze 3,039-row table (once materialized) before @dq-rule-writer finalizes thresholds. If Iceberg materialization is blocked per Bronze HR-4 advisory, run EDA against the in-memory DuckDB reconstruction and document the substrate clearly. |
| 6 | CHANGES REQUESTED | DQ rule #8 (`net_price_q1 ≤ net_price_q5`) is a strict invariant, but Bronze EDA found 46 rows violate this. A strict Silver rule will fail. | Rewrite as tolerance-based (≤50 outliers, matching Bronze RAW-CSI-013), OR require the transformer to filter/flag violators, OR document expected failure count and keep as P1 informational. |
| 7 | CHANGES REQUESTED | DQ coverage gaps: (a) no non-negativity rule on unified net-price / COA / quintile fields; (b) no range check on 4-year totals; (c) no 100% non-null rule on required field `institution_control`; (d) row-count rule says "matches Bronze" without asserting the exact value (3,039). | @dq-rule-writer to add 4 rules before implementation: NEG non-negativity (P0), 4YR range (P1), CONTROL 100% non-null (P0), EXACT row count = Bronze count (P0). |
| 8 | ADVISORY | Transformation #1 and #5 silently route `control=3` (for-profit) to the `_priv` fields. Business rule is correct per IPEDS but not obvious. | Add inline comment / spec note: "Control=3 (private for-profit) uses NPT4_PRIV and NPT4[1-5]_PRIV per IPEDS convention." |
| 9 | ADVISORY | DQ rule #6 uses "$1 tolerance" for exact `× 4` arithmetic. Either the rule is unnecessarily loose or the transformer is expected to round — clarify. | Spec author: either tighten to "exact match" or document why tolerance exists. |
| 10 | ADVISORY | Silver spec does not call out which Silver columns are CDE / PII. Bronze CDE registry already implies most are CDE (Level 1 Public, no PII); Silver spec should state this explicitly for @cde-tagger. | Add §CDE Impact subsection to Zone 2. Expected outcome: all cost/price fields inherit CDE status from Bronze; `institution_control` + `institution_name` + `state_abbr` are low-CDE reference attributes. Zero PII. |
| 11 | ADVISORY | Spec does not reference which insights / recommendations from any existing insight reports the Silver transformer must honor. No `governance/insights/` report exists for this zone transition yet. | If @insight-manager produces an insight report during the Silver pipeline, the recommendations must each pair with a DQ rule per the Insight Traceability check. Track at post-review. |

---

## Decision Rationale

The Silver spec is **thoughtfully scoped and conceptually sound** — the six transformations are the right set, the schema shape is broadly correct, and the DQ-rule skeleton covers the important invariants (monotonicity, nullability, type constraints, unit multipliers). The spec does not require any architectural redesign.

However, **three blocking classes of issue** prevent approval:

1. **Glossary gap (Issue 1).** The Silver conceptual model cannot be produced because the terms it must reference (BT-110, BT-111, BT-112) do not exist in the glossary yet. This gap is inherited from an unnoticed Bronze defect — the Bronze post-review claimed cross-artifact consistency on these terms without verifying they existed in the source-of-truth glossary JSON. @data-steward must create the three terms first; this is a precondition for Issue 2.

2. **Data Model Gate unmet (Issue 2).** This is a greenfield Base-zone table and CLAUDE.md policy makes the 3-stage model progression **blocking** at pre-implementation review. None of the three models exist.

3. **Schema / transformation contradiction (Issue 3).** The Silver schema does not carry through the raw cost fields despite transformation #6 promising to. This is an internal inconsistency in the spec itself that must be resolved before anyone implements against it — otherwise the implementer has to guess which statement is normative.

Four additional CHANGES REQUESTED items (4, 5, 6, 7) are DQ / testing coverage gaps that should be closed before implementation starts — not because they block correctness, but because the spec-driven workflow expects thresholds to be EDA-informed, rules to cover required-field completeness and non-negativity, and testing strategy to be named before code is written.

Three ADVISORY items (8, 9, 10, 11) can be handled during implementation; they are clarity-and-documentation polish, not governance gaps.

**Verdict: CHANGES REQUESTED.** The spec must update Issues 1–7 before Silver implementation proceeds. Once those seven items are resolved (glossary entries drafted + approved, three data models produced + approved, schema/transformation contradiction reconciled, testing section added, Silver EDA produced, DQ rule #8 restated as tolerance, 4 additional DQ rules added), this reviewer will re-evaluate for APPROVED status.

Recommended resolution sequence:
1. @data-steward drafts BT-110, BT-111, BT-112 and obtains human approval.
2. Spec author reconciles Issue 3 (schema vs transformation #6) and adds §Testing + §CDE Impact.
3. @data-analyst produces Silver EDA from Bronze table.
4. @dq-rule-writer updates DQ rule set per Issues 6 + 7 (using EDA-informed thresholds).
5. @semantic-modeler produces conceptual → logical → physical models (using approved BT-110/111/112 + reconciled schema).
6. Re-submit for pre-implementation review.

---

## Audit Trail Entry

- **Spec:** docs/specs/raw-ingest-college-scorecard-institution.md (Zone 2: Silver)
- **Review type:** Pre-implementation, Silver zone
- **Date:** 2026-04-14
- **Reviewer:** @governance-reviewer
- **Verdict:** CHANGES REQUESTED
- **Blocking issues:** 7 (Issues 1–7)
- **Advisories:** 4 (Issues 8–11)
- **Dependencies blocked:** Silver implementation, Silver DQ rule finalization, Silver transformer tests, Silver data models
- **Next action:** @data-steward to draft BT-110/111/112

*— End of Review —*
