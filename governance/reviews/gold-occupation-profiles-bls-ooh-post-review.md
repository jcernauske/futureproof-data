## Governance Review: gold-occupation-profiles-bls-ooh
**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-07
**Verdict:** CHANGES REQUESTED

---

### Checklist Results

#### Post-Implementation Governance Completeness

| # | Item | Path | Status | Notes |
|---|------|------|--------|-------|
| 1 | Business glossary updated (BT-047 through BT-054) | `governance/business-glossary.json` | PASS | All 8 terms present (GRW Score, Wage Percentile Overall, Wage Percentile Education Tier, Wage Tier, Market Score, Occupation Confidence Tier, Data Completeness, FutureProof Stat Mapping). All have `approval_status: "approved"`. |
| 2 | Conceptual model | `governance/models/gold-occupation-profiles-bls-ooh-conceptual.md` | FAIL | File exists. Includes Mermaid erDiagram block. References glossary terms. **Status is PROPOSED, not APPROVED. Approval: "Pending human review (REQUIRE_HUMAN_APPROVAL = true)".** |
| 3 | Logical model | `governance/models/gold-occupation-profiles-bls-ooh-logical.md` | FAIL | File exists. Includes Mermaid erDiagram block. **Status is PROPOSED, not APPROVED. Approval: "Pending human review".** |
| 4 | Physical model | `governance/models/gold-occupation-profiles-bls-ooh-physical.md` | FAIL | File exists. Includes Mermaid erDiagram block. 31 columns defined. PyIceberg schema matches implementation exactly. **Status is PROPOSED, not APPROVED. Approval: "Pending human review".** |
| 5 | EDA report | `governance/eda/gold-occupation-profiles-eda.md` | PASS | Comprehensive EDA with GRW score distribution, market score distribution, wage percentile analysis, confidence tier distribution, data completeness, golden dataset verification (including spec error identification for 29-1215), edge cases, and DQ threshold recommendations. |
| 6 | DQ rules | `governance/dq-rules/gold-occupation-profiles-bls-ooh.json` | PASS (partial) | 54 rules defined. 53 executable, 1 deferred (GLD-OP-048 golden dataset validation). See Issue #5 and #6 below. |
| 7 | DQ execution results | `governance/dq-results/gold-occupation-profiles-bls-ooh-20260407T202420Z.json` | PASS | Executed against real Iceberg data. `p0_passed: true`. 52/53 rules passing. 1 P1 failure (GLD-OP-039). |
| 8 | DQ scorecard | `governance/dq-scorecards/gold-occupation-profiles-bls-ooh-scorecard.md` | PASS | Produced from real execution results (run ID acb62160). Overall score 52/53 (98%). P0 Gate: PASS. 1 P1 warning. |
| 9 | P0 Gate | DQ results JSON | PASS | `p0_passed: true` confirmed. All 31 P0 rules passed. |
| 10 | Chaos manifest | `governance/chaos-manifests/gold-occupation-profiles-bls-ooh-chaos.md` | PASS | 5 adversarial cycles completed. Detection rate 67.9%-77.4%. Gaps identified (GLD-OP-039 broken SQL, freshness rules absent, record_id hash validation absent). |
| 11 | Golden dataset | `governance/golden-datasets/gold-occupation-profiles-bls-ooh-golden.json` | PASS | 3 verification chains: Software Developers (15-1252), Registered Nurses (29-1141), Anesthesiologists (29-1211). EDA spec error for 29-1215 was correctly resolved by using 29-1211 instead. |
| 12 | Lineage | `governance/lineage/gold-occupation-profiles-bls-ooh-20260407T230000Z.json` | PASS | OpenLineage event with COMPLETE eventType. Covers all 31 output fields with column-level lineage (DIRECT or DERIVED). Documents 7 dropped fields with justification. Input schema (25 Silver fields) and output schema (31 Gold fields) fully specified. Runtime metrics: 832 read, 832 promoted. |
| 13 | Data contract | `governance/data-contracts/consumable-occupation-profiles.yaml` | PASS | Contract exists. Status: draft. Version 1.0.0. 31 columns with is_cde/is_pii flags. Quality thresholds defined. Consumers documented (5 planned). Breaking change policy documented. |
| 14 | CDE/PII tags on contract | `governance/data-contracts/consumable-occupation-profiles.yaml` | PASS | All 31 columns have explicit `is_cde` and `is_pii` flags. 9 CDE columns flagged (soc_code, occupation_title, employment_current, employment_change_pct, median_annual_wage, grw_score, wage_percentile_overall, wage_percentile_education_tier, market_score). 0 PII columns (expected for aggregate occupation data). CDE rationale provided for each flagged column. |
| 15 | PII scan | `governance/pii-scans/gold-occupation-profiles-bls-ooh-pii-scan.md` | PASS | All 31 fields scanned. Zero PII detected. Re-identification risk assessment completed (all vectors: None). Regulatory analysis confirms no applicable regulations (FERPA, HIPAA, CCPA, GDPR). |
| 16 | Entity resolution | `governance/reviews/gold-occupation-profiles-bls-ooh-entity-resolution.md` | PASS | Single-source Gold product. SOC code entity integrity confirmed (832 unique, all valid XX-XXXX format). Cross-source readiness documented for future CIP-SOC crosswalk and O*NET integration. |
| 17 | Temporal assessment | `governance/audit-trail/gold-occupation-profiles-bls-ooh-temporal-assessment.md` | PASS | No bitemporal modeling required. Single-snapshot projection cycle. Full table replace strategy confirmed. source_load_date + promoted_at + Iceberg snapshots provide three-layer temporal trace. Future projection_cycle dimension documented for multi-cycle support. |
| 18 | Adversarial audit | `governance/reviews/gold-occupation-profiles-bls-ooh-adversarial-audit.md` | FAIL | **File does not exist.** The spec lists @adversarial-auditor as RUN (not SKIP). The chaos manifest exists at `governance/chaos-manifests/gold-occupation-profiles-bls-ooh-chaos.md` but the formal adversarial audit review document was never produced. |
| 19 | Data dictionary | `governance/data-dictionary.json` | PASS | `consumable.occupation_profiles` entry exists with 31 column definitions. |
| 20 | Implementation | `src/gold/bls_ooh_occupation_profiles.py` | PASS | Implementation matches approved physical model schema (31 columns, same types, same nullability). Uses idempotent promote pattern. Deterministic record_id via compute_grain_id with 'op' prefix. Null-safe wage percentile computation (filter before PERCENT_RANK, LEFT JOIN back). Custom _round_half_up function to match DuckDB ROUND behavior. |
| 21 | Tests | `tests/gold/test_bls_ooh_occupation_profiles.py` | PASS | 63 tests, all passing (verified via `uv run pytest`). Covers GRW piecewise function (all 8 segments + boundaries), market score, wage percentile null handling, confidence tier logic, data completeness, static fields, record IDs, and end-to-end transform. |
| 22 | Row count | Iceberg table | PASS | 832 rows promoted per lineage event runtime metrics. Matches spec expectation. |
| 23 | Audit trail | `governance/audit-trail/` | PASS | 10 audit trail entries exist for this spec covering pre-review, glossary, logical model, physical model, EDA, DQ rules, DQ execution, lineage, temporal assessment, and doc-generator. |

#### Data Model Gate (Greenfield Mode)

| # | Item | Status | Notes |
|---|------|--------|-------|
| M1 | Business terms in glossary | PASS | BT-047 through BT-054, all approved. |
| M2 | Conceptual model exists with erDiagram | FAIL | Exists with erDiagram. **Not APPROVED (status: PROPOSED).** |
| M3 | Logical model exists with erDiagram | FAIL | Exists with erDiagram. **Not APPROVED (status: PROPOSED).** |
| M4 | Physical model exists, derived from logical | FAIL | Exists with erDiagram and PyIceberg schema definition. Correctly derived from logical model. **Not APPROVED (status: PROPOSED).** |
| M5 | Implementation matches physical model | PASS | `get_gold_schema()` in implementation exactly matches the PyIceberg schema in the physical model. All 31 fields, types, and nullability constraints match. |

#### Insight Traceability

| # | Insight Report | Recommendation | Implementation | DQ Validation | Status |
|---|---------------|---------------|----------------|---------------|--------|
| I1 | `governance/insights/silver-bls-ooh-to-gold-insights.md` | GRW score for 15-1252 should produce ~8.37 | compute_grw_score(15.8) = 8.37 | GLD-OP-005 (range), GLD-OP-008 (rounded match), golden dataset chain #1 | PASS |
| I2 | Same | GRW score for 29-1141 should produce ~6.46 | compute_grw_score(4.9) = 6.4625 | Golden dataset chain #2 | PASS |
| I3 | Same | wage_percentile null count = 23 | Implementation excludes nulls from PERCENT_RANK | GLD-OP-014, GLD-OP-016, GLD-OP-018 | PASS |
| I4 | Same | confidence_tier "low" = exactly 23 | wage_available=False check first in CASE | GLD-OP-022, GLD-OP-024 | PASS |
| I5 | Same | market_score null count = 0 | Both components have 0 nulls | GLD-OP-010 | PASS |
| I6 | Same | backs_stats = "ERN,GRW" for all 832 | Static assignment in derive_gold_rows | GLD-OP-025 | PASS |
| I7 | Same | backs_bosses = "Market,Ceiling" for all 832 | Static assignment in derive_gold_rows | GLD-OP-026 | PASS |

#### Schema Consistency Check

| Artifact | Field Count | Consistent |
|----------|-------------|------------|
| Spec schema | 31 | Yes |
| Physical model | 31 | Yes |
| Implementation (get_gold_schema) | 31 | Yes |
| Lineage output schema | 31 | Yes |
| Data contract columns | 31 | Yes |
| Data dictionary entry | 31 | Yes |

All six artifacts reference the same 31 field names in the same order with the same types. No orphaned artifacts detected.

---

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | **Data models not approved.** All three data models (conceptual, logical, physical) have `Status: PROPOSED` and `Approval: Pending human review (REQUIRE_HUMAN_APPROVAL = true)`. Per the Greenfield Data Model Gate, models must be APPROVED before implementation begins. Implementation has proceeded despite unapproved models. The models must be reviewed and approved by a human. | Human must review and approve all three models, updating their Status from PROPOSED to APPROVED. |
| 2 | CHANGES REQUESTED | **Adversarial audit document missing.** The spec explicitly lists `@adversarial-auditor: RUN` with justification "First occupation-level Gold product. Score derivations (GRW, market) need adversarial testing." The chaos manifest exists but the formal adversarial audit review document at `governance/reviews/gold-occupation-profiles-bls-ooh-adversarial-audit.md` was never produced. This document should summarize adversarial findings, P0 items, and their resolution status. | @adversarial-auditor must produce the adversarial audit review document. |
| 3 | ADVISORY | **DQ rule GLD-OP-039 (P1) failing.** Market score formula consistency rule fails with actual=828.0 violations. The chaos manifest confirms this is a SQL definition bug: the correlated subquery with PERCENT_RANK is unsupported by DuckDB. The rule provides zero detection value. This is P1 (not P0) so it does not block the gate, but the rule should be rewritten using a CTE-based approach. | @dq-rule-writer should rewrite GLD-OP-039 SQL to use a CTE pattern. Non-blocking. |
| 4 | ADVISORY | **DQ rule GLD-OP-048 (P0) deferred.** The golden dataset validation rule is still in deferred status with placeholder SQL (`SELECT 'DEFERRED' AS status`). The golden dataset file now exists at `governance/golden-datasets/gold-occupation-profiles-bls-ooh-golden.json`. The rule should be updated with actual validation SQL and executed. | @dq-rule-writer should update GLD-OP-048 with validation SQL against the golden dataset. Non-blocking for this review but should be completed before staff review. |
| 5 | ADVISORY | **Spec status still DRAFT.** The spec at `docs/specs/gold-occupation-profiles-bls-ooh.md` still shows `Status: DRAFT`. If implementation is complete and this post-review passes, the spec status should be updated. | Spec owner should update status after all governance gates pass. |
| 6 | ADVISORY | **Chaos monkey identified missing DQ rule categories.** The chaos manifest flagged three gap areas: (a) no freshness rules for source_load_date or promoted_at, (b) no record_id hash validation rule, (c) no grw_score piecewise function spot-check rule. These represent coverage gaps in the DQ rule suite. | @dq-rule-writer should address these gaps in a follow-up iteration. Non-blocking. |
| 7 | ADVISORY | **Lineage confidence_tier expected distribution minor discrepancy.** The lineage event says "Expected distribution: majority 'high', ~77 'medium', 23 'low'" but the actual distribution is high=735, medium=74, low=23. The difference (77 vs 74 medium) is because 3 null-wage occupations are also catchall, and wage_available=False takes priority, placing them in "low" instead of "medium". The EDA, DQ rules, and implementation all correctly handle this. The lineage description is slightly imprecise but not incorrect (it says "~77"). | No action required. Minor documentation imprecision. |

---

### Decision Rationale

**Verdict: CHANGES REQUESTED**

The implementation itself is sound. The transformer code matches the physical model schema exactly. All 63 unit tests pass. All 31 P0 DQ rules pass against real Iceberg data. The P0 gate is clear. The 832 rows were successfully promoted. The golden dataset verification chains are correct (including the fix for the spec error on SOC 29-1215). Cross-artifact consistency is verified -- lineage, data contract, data dictionary, DQ rules, and physical model all reference the same 31 fields. The insight report recommendations were all implemented and validated by corresponding DQ rules.

However, two governance gaps prevent approval:

1. **The data models were never approved by a human.** `REQUIRE_HUMAN_APPROVAL = true` is set in this project. The Greenfield Data Model Gate requires all three models to be APPROVED before implementation begins. All three models are still PROPOSED. This is a procedural gap -- the models are well-constructed and the implementation matches them, but the human approval step was skipped. This must be remediated.

2. **The adversarial audit review document is missing.** The spec explicitly scoped @adversarial-auditor as RUN (not SKIP). The chaos monkey ran 5 adversarial cycles and produced a detailed manifest, but the formal adversarial audit review was never written. This is a governance completeness requirement -- the chaos manifest documents what was tested, but the adversarial audit should document P0 findings and their resolution (e.g., the null-openings bug referenced in the review request).

Once these two items are resolved, this spec should pass post-implementation review. The four ADVISORY items are non-blocking but should be addressed before or during staff review.

---

### Summary of Governance Artifact Status

| Category | Artifacts | Status |
|----------|-----------|--------|
| Data Models (3) | Conceptual, Logical, Physical | EXISTS but NOT APPROVED |
| DQ Rules | 54 defined (53 executable, 1 deferred) | PASS (with advisories) |
| DQ Execution | Real data, P0 gate passed | PASS |
| DQ Scorecard | 52/53 passing (98%) | PASS |
| Lineage | OpenLineage event with column-level lineage | PASS |
| Data Contract | consumable-occupation-profiles.yaml | PASS |
| CDE/PII Tags | On contract, all 31 fields tagged | PASS |
| Data Dictionary | Entry exists, 31 columns | PASS |
| Golden Dataset | 3 verification chains | PASS |
| EDA Report | Comprehensive profiling | PASS |
| PII Scan | Zero PII, full regulatory analysis | PASS |
| Entity Resolution | Single-source, no resolution needed | PASS |
| Temporal Assessment | No bitemporal needed, documented | PASS |
| Chaos Manifest | 5 cycles, gaps identified | PASS |
| Adversarial Audit | **MISSING** | FAIL |
| Implementation | Matches physical model, 63 tests passing | PASS |
| Audit Trail | 10 entries for this spec | PASS |
| Insight Traceability | 7 recommendations verified | PASS |
