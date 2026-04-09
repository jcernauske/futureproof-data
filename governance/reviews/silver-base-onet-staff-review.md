## Staff Engineer Review

### Date: 2026-04-08
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is production-quality work. The transformer is clean, correct, and does exactly what the spec asks for. Four transformation functions, each focused on one table, no god functions, no abstraction astronautics. The aggregation logic (multi-detail averaging, best-index selection, self-reference removal) is straightforward and verified against Bronze source data. 65 tests with meaningful assertions. 37 DQ rules all passing against real Iceberg tables. I would put my name on this.

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| 15-1252 Software Developers | Top WA (Working with Computers) importance | O*NET 30.2 | 4.61 | 4.61 | Bronze raw.onet_work_activities | Yes |
| 29-1141 Registered Nurses | Time Pressure (CX) context_value | O*NET 30.2 | 4.12 | 4.12 (avg of 5 details: 3.99, 4.52, 4.35, 4.25, 3.48) | Bronze raw.onet_work_context | Yes |
| 29-1229 Physicians, All Other | onet_detail_count | O*NET 30.2 | 7 | 7 (29-1229.00 through .04 + 2 more) | Bronze raw.onet_occupations | Yes |
| 15-1252 Software Developers | Top career transition | O*NET 30.2 | 15-1299 (index=1) | 15-1299 | Bronze raw.onet_related_occupations | Yes |
| All tables | Row counts | O*NET 30.2 | 798 / 31,734 / 44,118 / 15,944 | 798 / 31,734 / 44,118 / 15,944 | DQ rules SLV-ONET-003/015/027/037 | Yes |

All 5 spot-checks pass. Multi-detail averaging verified manually for 29-1141 (5 O*NET details averaged correctly).

### Code Quality

**src/silver/onet_transformer.py** -- Good.

- Four transform functions, each under 80 lines, each doing one thing. Clean separation.
- `truncate_to_bls_soc` and `derive_relatedness_tier` extracted as pure functions. Testable in isolation. Fine.
- `BURNOUT_ELEMENT_IDS` as a module-level frozenset with the EDA-corrected IDs. Correct decision to use frozenset (immutable, hashable, O(1) lookup).
- The `_build_child_data_sets` helper computes presence sets once, avoids repeated iteration. Efficient.
- Multi-detail aggregation uses simple dict accumulation with averaging. No pandas, no unnecessary dependencies. Appropriate for the data volume.
- Career transitions correctly keeps best (lowest) index per BLS pair. Self-references excluded early.
- `transform()` orchestrator reads Bronze once, computes occupations first to get `valid_bls_socs`, then passes that set to child transforms. Correct dependency ordering.
- Promote pattern uses `id_field="record_id"` for idempotency. Correct.
- No `except: pass`. No swallowed exceptions. Errors propagate with context from the infrastructure layer.
- Rounding to 2 decimal places on averaged values. Reasonable for importance/context scores.

One minor note: the spec mentions "concatenate titles/descriptions" for multi-detail codes, but the implementation takes the .00 base title only. This is actually the better decision -- concatenated titles would be unreadable garbage. The spec itself contradicts this in the schema section where it says "Title of the .00 base code, or first detailed code if no .00 exists." Implementation follows the schema section, which is correct.

### Test Quality

65 tests. Not theater. Specific assertions on specific values.

- `test_multi_detail_averaging`: asserts `importance == 3.5` (average of 4.0 and 3.0), not `> 0`. Good.
- `test_importance_rank`: asserts exact rank ordering across 3 activities with known importance values. Good.
- `test_dedup_keeps_best_index`: 3 rows with indices 8, 3, 12 -- asserts `best_index == 3`. Good.
- `test_removes_self_references`: two O*NET details of same BLS SOC relating to each other -- asserts 0 results. Good.
- `test_directional_pairs_both_preserved`: A->B and B->A are distinct. Asserts both present. Good edge case.
- `test_burnout_element_correct_ids`: exact frozenset comparison with all 9 EDA-corrected IDs. Good.
- `test_no_spec_incorrect_burnout_ids`: explicitly verifies the spec's original IDs (which were wrong) are NOT in the set. Good defensive test.
- `test_filters_cxp_ctp`: 3 input rows (CX, CXP, CTP), asserts only 1 output. Good.
- `test_suppress_flag_propagates`: multi-detail where one is "Y" -- asserts flag is True. Good.
- Schema tests verify exact field counts (14, 11, 11, 9) and that all fields are required. Good structural assertions.

Test count by table:
- Occupations: 13
- Activity Profiles: 11
- Context Profiles: 10
- Career Transitions: 12
- Schemas: 5
- Utilities/Constants: 12
- Total: 65

Exceeds the 15-minimum for Base zone.

### Spec Compliance

Implementation matches the spec. Specific checks:

- [x] 4 Silver tables with correct schemas (14, 11, 11, 9 fields)
- [x] All tables use bls_soc_code (XX-XXXX) as primary identifier
- [x] Multi-detail aggregation: 76 BLS SOCs with multi_detail_flag=True
- [x] 93+ structurally empty occupations excluded (798 vs 1,016 Bronze)
- [x] Work Activities filtered to IM scale only
- [x] Work Context filtered to CX/CT scales only
- [x] 9 burnout-relevant elements flagged via is_burnout_element (EDA-corrected IDs)
- [x] Career transitions deduplicated at BLS level with best_index preserved
- [x] Self-references removed (0 found in production data)
- [x] Grain integrity enforced on all 4 tables (DQ rules confirm zero duplicates)
- [x] Idempotent promote pattern on all 4 tables
- [x] 37 DQ rules written, executed, all passing
- [x] Data contracts produced for all 4 tables

The burnout element IDs differ from the spec's proposed IDs. The spec itself noted "The exact element IDs need to be confirmed against the actual Bronze data." The EDA corrected 3 IDs that didn't exist in the data. This is the right behavior -- the spec anticipated this.

### DQ Scorecard

37/37 rules passing (100%). P0 gate passed. Rules cover:
- SOC code format validation (both tables)
- Grain uniqueness on all 4 tables
- Exact row counts (798, 31,734, 44,118, 15,944)
- Value range validation (importance 1-5, CX 1-5, CT 1-3, best_index 1-20)
- Cross-table referential integrity (3 FK checks)
- Enumerated value validation (tiers, scale_ids, relationship_type)
- Derived field consistency (is_primary vs tier, is_high_importance vs importance)
- Null checks on all required fields

The 37 rules cover the spec's DQ requirements comprehensively. No obvious gaps.

### Chaos Hardening

3-cycle adversarial hardening. 86.5% rule activation (32/37). 5 rules never fired. The chaos monkey correctly identifies these as rules checking structural invariants that cell-level corruption doesn't trigger (e.g., SLV-ONET-006 checks that no "none" tier exists, SLV-ONET-012 checks exactly 41 distinct element_ids). These are real rules that catch real bugs; they just aren't triggered by the corruption patterns used. Acceptable.

The recommendations from chaos monkey about adding rules for CXP/CTP scale filtering and self-reference detection are already covered by existing rules (SLV-ONET-025, SLV-ONET-031). The chaos monkey's "possible explanation" section could be more precise, but this is a minor documentation issue, not a quality gap.

### Data Contracts

All 4 contracts match the physical model:
- Field names, types, and required flags are consistent
- Grain definitions are correct
- Row counts match production data
- CDE tagging is present and has real rationale (not boilerplate)
- Quality sections specify concrete thresholds

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| None | -- | -- | No blocking issues identified | -- |

### Advisory Notes (Non-Blocking)

1. The spec's row count estimates (~867, ~35,547, ~49,419, ~18,000) differ from actuals (798, 31,734, 44,118, 15,944). The spec was written before EDA confirmed exact counts. The DQ rules use the correct actual counts. No fix needed.

2. No golden dataset exists at `governance/golden-datasets/silver-base-onet-golden.json`. This is not required for Silver/Base zone per the verification gate requirements (golden datasets are mandatory for consumable and MCP zones only). Noted for completeness.

### What's Acceptable

Clean transformer code. No over-engineering. Tests validate actual behavior with specific values. DQ rules are comprehensive and passing against real data. Multi-detail aggregation verified manually. The EDA-corrected burnout element IDs are properly documented and tested.
