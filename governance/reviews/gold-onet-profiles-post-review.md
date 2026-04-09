## Governance Review: gold-onet-profiles
**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-08
**Verdict:** CHANGES REQUESTED

### Post-Implementation Governance Completeness Checklist

| # | Item | Status | Details |
|---|------|--------|---------|
| 1 | Lineage exists for every transformation | PASS | `governance/lineage/gold-onet-profiles-20260408T180000Z.json` contains 2 OpenLineage COMPLETE events (one per table), with full column-level lineage for all 27 + 14 fields. Sources, outputs, and transformation descriptions are complete. |
| 2 | DQ rules exist for every new table | PASS | `governance/dq-rules/gold-onet-profiles.json` contains 43 rules (29 for work profiles, 14 for career transitions). Coverage spans all DQ dimensions: grain uniqueness, row counts, value ranges, JSON validity, cross-column consistency, cross-table FK, format checks, and distribution checks. |
| 3 | DQ rules executed against real Iceberg data | PASS | `governance/dq-results/gold-onet-profiles-20260409T041511Z.json` confirms execution at 2026-04-09T04:15:11Z. Run ID fdc05592. 43 rules executed, 0 errors. |
| 4 | DQ P0 gate | PASS | `p0_passed: true` in results JSON. All 28 P0 rules passed. Scorecard confirms 43/43 passing (100%). |
| 5 | DQ scorecard produced from real execution | PASS | `governance/dq-scorecards/gold-onet-profiles-scorecard.md` references run ID fdc05592 and execution timestamp, matching the results file. Not test-based. |
| 6 | CDE/PII tags set on data contracts | PASS | Both contracts have is_cde/is_pii flags on every column. Work profiles: bls_soc_code, hmn_score, burnout_score, burnout_drivers marked CDE. Career transitions: bls_soc_code, related_bls_soc_code marked CDE. No PII fields (correct for aggregated occupation data). |
| 7 | Data dictionary entries exist | PASS | `governance/data-dictionary.json` contains entries for both `consumable.onet_work_profiles` (27 columns) and `consumable.career_transitions` (14 columns). Each column has type, description, is_cde, is_pii, source_column, business_term, and DQ rule references. |
| 8 | Data contracts exist for Gold tables | PASS | `governance/data-contracts/consumable-onet-work-profiles.yaml` (553 lines) and `governance/data-contracts/consumable-career-transitions.yaml` (323 lines). Both have version 1.0.0, draft status, grain definitions, column schemas, quality thresholds, consumer definitions, and lineage references. |
| 9 | Audit trail entries exist | PASS | 8 audit trail files exist under `governance/audit-trail/gold-onet-profiles-*`: glossary, eda, dq-rules, dq-execution, entity-resolution, temporal-assessment, lineage, doc-generator. |
| 10 | Schema matches spec and physical model | PASS | Implementation schemas (Iceberg NestedField definitions in both .py files) match the physical model column-for-column: 27 fields for work profiles, 14 fields for career transitions. Field names, types, and nullability all align. |
| 11 | Data models exist (all 3 stages) | PASS | Conceptual (`governance/models/gold-onet-profiles-conceptual.md`), logical (`governance/models/gold-onet-profiles-logical.md`), and physical (`governance/models/gold-onet-profiles-physical.md`) all exist. All three include Mermaid erDiagram blocks. |
| 12 | Physical model matches implementation | PASS | Physical model specifies 27 columns for work profiles and 14 for career transitions. Implementation matches. HMN min/max rescaling is documented in the physical model's derivation section and implemented correctly in code. |
| 13 | No orphaned artifacts | PASS | All governance artifacts reference tables and fields that exist in the implementation. Lineage references real Silver table names. DQ rules reference real Gold table names. Contracts reference real columns. |
| 14 | Consistency across artifacts | PASS (with exceptions noted below) | Lineage, CDE tags, data dictionary, and DQ rules all reference the same field names and table names. One consistency exception identified (Issue #1). |
| 15 | Golden dataset exists | PASS | `governance/golden-datasets/gold-onet-profiles-golden.json` contains 4 verification chains (Software Developers, Registered Nurses, Court Reporters, career transition) with expected values and derivation steps. |
| 16 | Chaos monkey ran (5 cycles) | PASS | `governance/chaos-manifests/gold-onet-profiles-chaos.md` documents 5 cycles at 5-10% corruption rates. Detection rate: 86-91%. 2 rules (GLD-ONP-010, GLD-ONP-011) never fired (statistical aggregates, expected behavior). |
| 17 | Business glossary updated | PASS | BT-066 (HMN Score), BT-067 (Human-Intensive Activities), BT-068 (Burnout Score), BT-069 (Burnout Drivers), BT-070 (Work Profile Availability), BT-071 (Confidence Tier), BT-072 (Activity Importance Mean) all present. |
| 18 | CAB review skipped with justification | PASS | Pipeline state records skip reason: "New tables (greenfield) -- no existing schema to modify." Correct for greenfield mode. |
| 19 | Entity resolver executed/skipped with justification | PASS | `governance/audit-trail/gold-onet-profiles-entity-resolution.md` documents SKIP CONFIRMED with detailed rationale: single-source, exact-key joins on bls_soc_code, no cross-source matching needed. |
| 20 | PII scanner executed/skipped with justification | FAIL | See Issue #2. |
| 21 | Temporal modeler executed/skipped with justification | PASS | `governance/audit-trail/gold-onet-profiles-temporal-assessment.md` documents SKIP CONFIRMED: single-snapshot, full table replace, no bitemporal requirements. |
| 22 | Adversarial auditor ran | FAIL | See Issue #3. |

### Pipeline Agent Execution Summary

| Agent | Pipeline Status | Artifact Verified |
|-------|----------------|-------------------|
| @governance-reviewer (pre) | COMPLETED | governance/reviews/gold-onet-profiles-pre-review.md |
| @data-steward | COMPLETED | governance/business-glossary.json (BT-066 through BT-072) |
| @semantic-modeler (conceptual) | COMPLETED | governance/models/gold-onet-profiles-conceptual.md |
| @semantic-modeler (logical) | COMPLETED | governance/models/gold-onet-profiles-logical.md |
| @data-analyst | COMPLETED | governance/eda/gold-onet-profiles-eda.md |
| @dq-rule-writer | COMPLETED | governance/dq-rules/gold-onet-profiles.json (43 rules) |
| @semantic-modeler (physical) | COMPLETED | governance/models/gold-onet-profiles-physical.md |
| @primary-agent | COMPLETED | src/gold/onet_work_profiles.py, src/gold/onet_career_transitions.py |
| @cab-agent | SKIPPED | Justified: greenfield |
| @dq-engineer | COMPLETED | governance/dq-scorecards/gold-onet-profiles-scorecard.md |
| @chaos-monkey | COMPLETED | governance/chaos-manifests/gold-onet-profiles-chaos.md (5 cycles) |
| @entity-resolver | COMPLETED (skip) | governance/audit-trail/gold-onet-profiles-entity-resolution.md |
| @pii-scanner | COMPLETED (skip) per pipeline | **Missing artifact** -- see Issue #2 |
| @temporal-modeler | COMPLETED (skip) | governance/audit-trail/gold-onet-profiles-temporal-assessment.md |
| @lineage-tracker | COMPLETED | governance/lineage/gold-onet-profiles-20260408T180000Z.json |
| @cde-tagger | COMPLETED | governance/data-contracts/consumable-onet-work-profiles.yaml |
| @doc-generator | COMPLETED | governance/data-contracts/ + governance/data-dictionary.json |
| @adversarial-auditor | COMPLETED per pipeline | **Missing artifact** -- see Issue #3 |

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | **Data contract confidence_tier distribution does not match actual warehouse data.** The data contract (`consumable-onet-work-profiles.yaml`, line 475-477) specifies `confidence_tier_high_count: 773`, `confidence_tier_medium_count: 1`, `confidence_tier_low_count: 24`. However, actual DQ execution (GLD-ONP-019) and the scorecard confirm 772 high / 2 medium / 24 low (SOC 51-2061 crossed the 5% suppression threshold). The DQ rule was correctly updated to 772/2/24, but the data contract was not. The physical model (line 156) also still says "773 high, 1 medium". The doc-generator explicitly noted this discrepancy in `governance/audit-trail/gold-onet-profiles-doc-generator.md` but did not resolve it. **Resolution:** Update the data contract quality thresholds and the physical model description to reflect the actual 772/2/24 distribution. |
| 2 | CHANGES REQUESTED | **PII scanner skip artifact missing.** Pipeline state records `@pii-scanner` as COMPLETED with output `governance/audit-trail/gold-onet-profiles-pii-scanner-skip.md`, but this file does not exist on disk. The spec designates PII scanner as SKIP with justification "Aggregated occupation-level data." A skip decision must be documented in an audit trail artifact. **Resolution:** Create the PII scanner skip audit trail file, or point to an existing artifact that documents the PII assessment. |
| 3 | CHANGES REQUESTED | **Adversarial auditor artifact missing.** Pipeline state records `@adversarial-auditor` as COMPLETED with output `governance/reviews/gold-onet-profiles-adversarial-audit.md`, but this file does not exist on disk. The spec explicitly requires the adversarial auditor to RUN (not skip) because "HMN and Burnout score formulas need adversarial testing -- these directly produce FutureProof stat values. Activity classification (human-intensive vs. automatable) is a subjective judgment that needs scrutiny." This is a mandatory agent for this spec. **Resolution:** The adversarial audit must be produced and saved to disk. The pipeline state claims completion at 2026-04-09T04:34:08Z, so the audit may have been generated but not persisted. Re-run or locate the output. |
| 4 | ADVISORY | **Burnout element ID comments in code do not match spec.** In `src/gold/onet_work_profiles.py` lines 64-74, the BURNOUT_ELEMENT_IDS constant has comments that differ from the spec: code says `4.C.3.b.7` = "Importance of Repeating Same Tasks" but spec says "Responsibility for Outcomes and Results"; code says `4.C.3.d.4` = "Work Schedules" but spec says "Importance of Repeating Same Tasks"; code says `4.C.3.a.2.a` = "Impact of Decisions on Co-workers" but spec says "Responsibility for Others' Health and Safety". The implementation correctly uses `is_burnout_element` flag from Silver (not these constants), so the runtime behavior is correct. The constant is documentation-only. This does not block but should be corrected for maintainability. |
| 5 | ADVISORY | **Pipeline state output paths do not match actual file names.** Pipeline state references `gold-onet-profiles-entity-resolver-skip.md`, `gold-onet-profiles-pii-scanner-skip.md`, and `gold-onet-profiles-temporal-modeler-skip.md`, but actual files are named `gold-onet-profiles-entity-resolution.md`, `gold-onet-profiles-temporal-assessment.md`, and (missing) for PII. The pipeline state should reference the actual artifact paths for traceability. |
| 6 | ADVISORY | **Spec status is still DRAFT.** The spec at `docs/specs/gold-onet-profiles.md` line 3 still shows `Status: DRAFT`. After successful post-implementation review and staff engineer sign-off, this should be updated to COMPLETE. |

### Insight Traceability

The insight reports at `governance/insights/silver-to-gold-insights.md` and `governance/insights/silver-bls-ooh-to-gold-insights.md` reference O*NET integration as a future data product (recommendation #4: CIP-SOC crosswalk, recommendation #6: career projections). These recommendations are for future specs (crosswalk-cip-soc, unified Gold product), not for this spec. No insight recommendations are directly actionable for gold-onet-profiles. This check passes.

### HMN Formula Deviation Assessment

The spec defines `hmn_score = 1.0 + 9.0 * human_ratio`, but the implementation uses min/max rescaling: `hmn_score = 1.0 + 9.0 * (human_ratio - observed_min) / (observed_max - observed_min)`. This deviation was:
1. Identified by EDA (human_ratio range 0.273-0.438 would compress HMN to 3.46-4.94)
2. Recommended by @data-analyst as a design change
3. Documented in the physical model (section "HMN Score Derivation (UPDATED: Min/Max Rescaling)")
4. Reflected in the golden dataset (Software Developers HMN = 2.11, not ~4.3)
5. Reflected in the lineage column descriptions

The deviation is properly governed. The spec itself should ideally be updated to reflect the approved formula, but this is tracked under Issue #6 (spec still DRAFT).

### Cross-Agent Consistency Check

| Check | Result |
|-------|--------|
| Lineage field names match contract field names | PASS -- all 27 + 14 field names consistent |
| DQ rules reference correct table names | PASS -- consumable.onet_work_profiles and consumable.career_transitions |
| Dictionary CDE flags match contract CDE flags | PASS -- bls_soc_code, hmn_score, burnout_score, burnout_drivers marked CDE in both |
| Physical model column count matches implementation | PASS -- 27 and 14 columns respectively |
| Golden dataset expected values align with DQ rules | PASS -- row counts, null counts, score ranges all consistent |
| Scorecard run ID matches results file | PASS -- fdc05592 in both |

### Decision Rationale

**Verdict: CHANGES REQUESTED** based on three blocking issues:

1. **Issue #1 (confidence_tier distribution mismatch):** The data contract is the authoritative quality specification for downstream consumers. A contract that claims 773 high-confidence rows when the actual data has 772 creates a false expectation. The DQ rule was correctly updated, proving the discrepancy was known, but the contract was not corrected. This is a governance gap -- the contract must reflect reality.

2. **Issue #2 (PII scanner skip artifact missing):** Every agent decision must be documented. The pipeline state claims the PII scanner ran but the output file does not exist. Even for a SKIP decision, the audit trail must contain the justification.

3. **Issue #3 (Adversarial auditor artifact missing):** The adversarial auditor was explicitly marked as REQUIRED (not skippable) in the spec because the HMN and Burnout formulas are subjective derivations that produce student-facing stat values. The pipeline state claims completion, but the output file is missing. Without the adversarial audit, we cannot verify that the activity classification and score formulas were scrutinized.

**None of these issues indicate implementation defects.** The code, DQ rules, lineage, models, and golden dataset are all high quality and internally consistent. The 43/43 DQ pass rate and 5-cycle chaos monkey hardening demonstrate robust data quality. The issues are documentation/artifact gaps that must be resolved before final sign-off.

### Resolution Path

1. Update `governance/data-contracts/consumable-onet-work-profiles.yaml` quality thresholds to 772/2/24
2. Update `governance/models/gold-onet-profiles-physical.md` confidence_tier description to 772/2/24
3. Create or locate the PII scanner skip audit trail file
4. Create or locate the adversarial auditor review file
5. Once resolved, re-submit for post-implementation review
