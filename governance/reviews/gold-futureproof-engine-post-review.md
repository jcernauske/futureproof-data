## Governance Review: gold-futureproof-engine
**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-09
**Verdict:** CHANGES REQUESTED

### Checklist Results

#### Governance Artifacts Existence

| # | Artifact | Path | Status |
|---|----------|------|--------|
| 1 | Business glossary | `governance/business-glossary.json` | PASS -- exists |
| 2 | Conceptual model | `governance/models/gold-futureproof-engine-conceptual.md` | FAIL -- exists but status is PROPOSED, not APPROVED |
| 3 | Logical model | `governance/models/gold-futureproof-engine-logical.md` | FAIL -- exists but status is PROPOSED, not APPROVED |
| 4 | Physical model | `governance/models/gold-futureproof-engine-physical.md` | PASS -- exists, APPROVED |
| 5 | EDA report | `governance/eda/gold-futureproof-engine-eda.md` | PASS -- exists |
| 6 | DQ rules | `governance/dq-rules/gold-futureproof-engine.json` | PASS -- 45 rules, all active |
| 7 | DQ results | `governance/dq-results/gold-futureproof-engine-20260409T144408Z.json` | PASS -- latest run exists, 44/45 passing |
| 8 | DQ scorecard | `governance/dq-scorecards/gold-futureproof-engine-scorecard.md` | FAIL -- stale, references run cdfb115c from 06:11:11Z, not latest run 08e351f2 from 14:44:08Z |
| 9 | Chaos manifest | `governance/chaos-manifests/gold-futureproof-engine-chaos.md` | PASS -- exists |
| 10 | Golden dataset | `governance/golden-datasets/gold-futureproof-engine-golden.json` | PASS -- 3 verification chains, all independently verifiable |
| 11 | Lineage | `governance/lineage/gold-futureproof-engine-20260409T120000Z.json` | PASS -- exists |
| 12 | Data contract (program_career_paths) | `governance/data-contracts/consumable-program-career-paths.yaml` | PASS -- exists, draft status, CDE/PII flags set on all 40 columns |
| 13 | Data contract (career_branches) | `governance/data-contracts/consumable-career-branches.yaml` | PASS -- exists, draft status, CDE/PII flags set on all 24 columns |
| 14 | Audit trail entries | `governance/audit-trail/` | PASS -- 14 entries for this spec |
| 15 | Data dictionary entries | `governance/data-dictionary.json` | FAIL -- no entries for program_career_paths or career_branches tables |

#### DQ Gate

| Check | Status | Details |
|-------|--------|---------|
| P0 Gate | PASS | `p0_passed: true` in latest results (run 08e351f2) |
| GLD-FE-044 (golden dataset) | PASS | All 3 verification chains pass in latest run |
| GLD-FE-040 (branch full data >= 95%) | FAIL (P1) | Below 95% threshold. P1 = warning, not blocking |
| Total | 44/45 passing | 1 P1 failure, 0 P0 failures |

#### Data Model Gate (Greenfield, Gold zone)

| Check | Status | Details |
|-------|--------|---------|
| Conceptual model exists | PASS | File exists with Mermaid erDiagram |
| Conceptual model APPROVED | FAIL | Status is "PROPOSED", approval line says "Pending human review" |
| Logical model exists | PASS | File exists with Mermaid erDiagram |
| Logical model APPROVED | FAIL | Status is "PROPOSED", approval line says "Pending human review" |
| Physical model exists | PASS | File exists with Mermaid erDiagram |
| Physical model APPROVED | PASS | Auto-approved (derived from logical) |
| All three include Mermaid erDiagram | PASS | Confirmed in all three files |
| Physical model matches implementation | PASS | 40 columns in program_career_paths, 24 in career_branches, types and names match contract |

#### Consistency Checks

| Check | Status | Details |
|-------|--------|---------|
| Contract columns match spec schema | PASS | All 40 program_career_paths columns and 24 career_branches columns present |
| Contract columns match physical model | PASS | Column names, types, and nullability align |
| Lineage references correct source tables | PASS | Lists career_outcomes, cip_soc_crosswalk, occupation_profiles, onet_work_profiles, career_transitions |
| CDE flags set on contracts | PASS | 12 CDEs identified on program_career_paths, 2 on career_branches, all with rationales |
| DQ rules cover both tables | PASS | Rules GLD-FE-001 through GLD-FE-031 cover program_career_paths, GLD-FE-032 through GLD-FE-045 cover career_branches |
| Contract row_count_range vs actual | ADVISORY | Contract says [150000, 500000] but actual is 626,406. DQ rule GLD-FE-003 uses correct range [580000, 700000]. Contract threshold is stale. |

#### Insight Traceability

| Insight Report | Relevant Recommendations | DQ Validation | Status |
|----------------|--------------------------|---------------|--------|
| silver-to-gold-insights.md | CIP-SOC crosswalk integration (P0), cross-source join coverage | GLD-FE-004 (CIP coverage >= 90%), GLD-FE-005 (row coverage >= 95%) | PASS |
| silver-bls-ooh-to-gold-insights.md | GRW score piecewise function, wage percentile excluding nulls, confidence tier | Covered by upstream gold-occupation-profiles DQ rules | PASS |

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | CHANGES REQUESTED | Conceptual model status is PROPOSED, not APPROVED. Greenfield Gold zone requires APPROVED conceptual model before spec can be marked complete. `REQUIRE_HUMAN_APPROVAL = true` per project config. | Human must approve the conceptual model and update status line in `governance/models/gold-futureproof-engine-conceptual.md` |
| 2 | CHANGES REQUESTED | Logical model status is PROPOSED, not APPROVED. Same requirement as above. | Human must approve the logical model and update status line in `governance/models/gold-futureproof-engine-logical.md` |
| 3 | CHANGES REQUESTED | DQ scorecard is stale. It references run `cdfb115c` from `2026-04-09T06:11:11Z` which showed GLD-FE-044 as FAIL (DEFERRED). The latest run `08e351f2` from `2026-04-09T14:44:08Z` shows GLD-FE-044 as PASS. The scorecard must be regenerated from the latest results. | @dq-engineer must regenerate the scorecard from the latest DQ results file (`governance/dq-results/gold-futureproof-engine-20260409T144408Z.json`) |
| 4 | CHANGES REQUESTED | Data dictionary has no entries for `consumable.program_career_paths` or `consumable.career_branches`. Post-implementation checklist requires new fields to have data dictionary entries. | @doc-generator must add entries for all 64 columns (40 + 24) to `governance/data-dictionary.json` |
| 5 | ADVISORY | Data contract `consumable-program-career-paths.yaml` has `row_count_range: [150000, 500000]` under quality thresholds, but the actual table has 626,406 rows and the DQ rule uses [580000, 700000]. The contract volume threshold should be updated to match reality. | Update contract quality.volume.row_count_range to [580000, 700000] to match DQ rule GLD-FE-003 |
| 6 | ADVISORY | GLD-FE-040 (career_branches branch_has_full_data >= 95%) is failing as a P1 warning. This is non-blocking but should be investigated. The actual full-data rate is slightly below 95%. | Investigate whether this is expected given upstream O*NET or BLS coverage gaps, and either adjust the threshold or document as known limitation |

### Decision Rationale

**Verdict: CHANGES REQUESTED** -- Four blocking issues prevent sign-off:

1. **Model approval gap (Issues 1-2):** The project has `REQUIRE_HUMAN_APPROVAL = true`. The Brightsmith framework's greenfield data model gate requires all three models to be APPROVED before a spec can be marked complete. The conceptual and logical models remain at PROPOSED status. The physical model was auto-approved as derived from the logical, but the logical itself is not yet approved. This is a governance process gap -- implementation proceeded before model approval was obtained. The models themselves appear to be well-structured (both contain Mermaid erDiagrams, reference glossary terms, and align with the spec), so approval should be straightforward, but it must happen.

2. **Stale scorecard (Issue 3):** The DQ scorecard incorrectly reports GLD-FE-044 as a P0 FAIL with "DEFERRED" threshold. The latest DQ execution (run 08e351f2) shows this rule now PASSES with the proper golden dataset SQL. The scorecard must be regenerated to accurately reflect the current state. A stale scorecard that reports false P0 failures is misleading and blocks the staff engineer's ability to make an informed review decision.

3. **Missing data dictionary entries (Issue 4):** The data dictionary at `governance/data-dictionary.json` contains zero references to either `program_career_paths` or `career_branches`. This is a required post-implementation artifact per the completeness checklist. All 64 columns across both tables need dictionary entries.

The two ADVISORY issues are non-blocking: the contract volume threshold is a housekeeping update, and the P1 DQ failure should be investigated but does not gate completion.

**What is working well:**
- All 45 DQ rules exist, are active, and have been executed against the persistent warehouse
- P0 gate passes cleanly (44/45 rules pass, the 1 failure is P1)
- Golden dataset with 3 independently verifiable chains all pass
- Both data contracts are thorough with CDE/PII flags and rationales on every column
- Lineage artifact exists with correct source table references
- Chaos manifest exists (5-cycle adversarial hardening)
- 14 audit trail entries document the full agent workflow
- Physical model matches implementation schema
- Insight traceability checks pass -- the CIP granularity fix from the silver-to-gold insight is validated by DQ rules

**Resolution path:** Fix the 4 CHANGES REQUESTED items, then request re-review. The fixes are all documentation/process -- no code changes required.
