# Adversarial Audit: silver-base-bls-ooh

**Spec:** silver-base-bls-ooh
**Zone:** Silver (Base)
**Auditor:** @adversarial-auditor
**Date:** 2026-04-07
**Artifacts Reviewed:** 9 (spec, transformer, tests, physical model, DQ rules, DQ scorecard, chaos manifest, business glossary, data contract)

---

## Risk Register

### RISK-001: Test fixture data does not match real data (Severity: HIGH)

The test fixture for Software Developers (15-1252) uses `employment_current: 1795500` and `median_annual_wage: 130160.0`. The EDA golden dataset section -- which was profiled from actual Bronze data -- reports `employment_current: 1,693,800` and `median_annual_wage: $133,080`. These are different numbers.

This means the unit tests validate transformation logic against fabricated data, not against data the pipeline actually processes. The tests prove the code handles a row shaped like real data, but they do not prove it produces correct output from real data. If a bug silently corrupted a wage value during Bronze ingestion, these tests would not catch it because they never compare against known-correct source values.

**Evidence demand:** Show me a test or golden dataset verification that asserts the actual output for SOC 15-1252 after running the full pipeline against the real Bronze table matches the EDA-profiled values ($133,080 wage, 1,693,800 employment).

**Assessment: Weak.** The tests validate transformation logic in isolation, which is necessary but not sufficient. There is no integration test or golden dataset that validates end-to-end correctness against real data for this Silver table. The spec calls for golden dataset verification in the success criteria but no golden dataset artifact exists at `governance/golden-datasets/` for this spec.

---

### RISK-002: Catchall count discrepancy -- spec says 46, reality is 70, data contract says 46 (Severity: HIGH)

The spec states "46 true 'all other' catch-all categories" in two places (schema table line 71 and DQ rules section line 285). The EDA found 70. The DQ rule (SLV-OOH-011) was corrected to 70. The DQ rule passes. But:

- The **data contract** (`governance/data-contracts/base-bls-ooh.yaml` line 410) still says `catchall_flag_true_count_approx: 46`.
- The **logical model** (`governance/models/silver-base-bls-ooh-logical.md` line 96) still says "approximately 46 occupations."
- The **conceptual model** still references the old count.
- The **spec itself** was never corrected.

This is a documentation integrity failure. A downstream consumer reading the data contract would expect 46 catchall categories and see 70. A regulator reviewing governance artifacts would find conflicting counts across documents. The DQ rule is correct, but the governance documentation is internally inconsistent.

**Evidence demand:** Show me that the spec, data contract, logical model, and conceptual model all agree on the catchall count of 70.

**Assessment: Weak.** The DQ rule was correctly updated by the rule writer based on EDA evidence, but the correction did not propagate back to the spec, data contract, or logical model. This is a systemic issue: when EDA findings contradict the spec, who is responsible for updating the spec? The pipeline has no mechanism to enforce consistency between EDA corrections and upstream governance documents.

---

### RISK-003: Data contract claims 31 DQ rules but 36 exist (Severity: MEDIUM)

The data contract (`governance/data-contracts/base-bls-ooh.yaml` lines 425-428) claims:
- `total_rules: 31`
- `p0_rules: 15`
- `p1_rules: 10`
- `p2_rules: 6`

The actual DQ rules file contains 36 rules (SLV-OOH-001 through SLV-OOH-036). The DQ scorecard confirms 36 rules. The data contract is wrong.

Furthermore, the priority breakdown does not add up. 15 + 10 + 6 = 31, not 36. The 5 additional rules (SLV-OOH-032 through SLV-OOH-036) were apparently added after the data contract was generated. This means the data contract was not regenerated after DQ rule finalization.

**Evidence demand:** Show me the actual priority breakdown of all 36 rules and a corrected data contract.

**Assessment: Weak.** The data contract is a machine-readable artifact that downstream systems may consume programmatically. An incorrect rule count undermines trust in the contract's accuracy. The contract generation process should be re-run after DQ rules are finalized.

---

### RISK-004: Projection cycle inconsistency -- 2024-2034 vs 2023-2033 (Severity: MEDIUM)

The Bronze architecture review (`governance/reviews/bronze-bls-ooh-architecture-review.md` line 116) already identified this: the domain context says "2023-2033" while the spec, data contract, and actual XLSX headers say "2024-2034." The Bronze reviewer recommended updating the domain context. If this was not done, the canonical domain context -- the document every agent reads for domain knowledge -- contains incorrect information about the data vintage.

The business glossary definitions for Employment Current and Employment Projected reference "the current 2023-2033 cycle" -- also wrong if the actual data is 2024-2034.

**Evidence demand:** Show me the current `governance/domain-context.md` BLS section and confirm whether it says 2023-2033 or 2024-2034. Show me the business glossary definitions for BT-031 and BT-032 and confirm the cycle year.

**Assessment: Weak.** This was flagged in a prior review and there is no evidence it was corrected. If the domain context is wrong, every AI agent that reads it for domain knowledge inherits incorrect vintage information. This is precisely the kind of error that "looks right" but produces subtly wrong outputs.

---

### RISK-005: No golden dataset artifact for Silver table (Severity: HIGH)

The spec (lines 312-320) explicitly requires golden dataset verification with 3 independently verifiable occupations: Software Developers (15-1252), Registered Nurses (29-1141), and a declining occupation. The EDA provides expected values for all three. But:

- No file exists at `governance/golden-datasets/` for this spec.
- No integration test harness validates these golden values against the actual Silver output.
- The unit test fixtures use fabricated data that does not match the EDA golden values.

The success criteria checklist is not met. The spec says "Each golden value must be traceable: Bronze row -> Silver derivation -> expected output." This traceability does not exist.

**Evidence demand:** Show me a golden dataset file and an integration test that validates Software Developers wage = $133,080, employment_current = 1,693,800, growth_category = "growing_fast" in the actual `base.bls_ooh` table.

**Assessment: Missing.** No golden dataset artifact exists for this spec. This is a gap, not a weakness -- the control simply does not exist yet.

---

### RISK-006: Broad occupation hardcoded list -- correctness depends on Bronze SOC audit (Severity: MEDIUM)

The 7 broad occupation codes are hardcoded in the transformer based on the Bronze SOC audit (`governance/reviews/raw-bls-ooh-soc-codes.md`). The spec explicitly says to hardcode rather than pattern-match. The question is: is the Bronze SOC audit correct?

The Bronze audit identifies 7 codes "ending in 0 that represent aggregated occupations." But the audit was produced by an AI agent profiling the data. How was this list validated? The BLS SOC 2018 classification system defines broad occupation groups at the minor group level (XX-XXX0), but not all codes ending in 0 are broad codes (as the spec correctly notes). The audit lists these specific 7 codes, and the spec carries them forward.

I note that the Bronze SOC audit also says "134 of 832 SOC codes (16.1%) follow the '9X' pattern" for catch-all categories -- a different counting methodology than the Silver spec's "all other" substring match (which finds 70). The Bronze audit's 134 count uses a structural pattern (positions 5-6 are 9X) while the Silver uses a semantic pattern (title contains "all other"). Neither methodology is wrong, but they measure different things. The spec conflates them by saying "46 'all other' catch-all categories" when neither method produces 46.

**Evidence demand:** Cross-reference the 7 broad codes against the official BLS SOC 2018 classification structure at bls.gov/soc/2018/. Confirm each is classified as a "broad" occupation group, not a detailed occupation.

**Assessment: Adequate.** The hardcoded list approach is correct per the spec rationale (pattern matching produces false positives). The list itself appears plausible based on the Bronze audit. But the validation is one AI agent (Bronze auditor) trusting another AI agent's data profiling. A human who understands SOC taxonomy structure should verify the 7 codes against the official BLS SOC classification.

---

### RISK-007: growth_category spec-vs-code inconsistency on nullability (Severity: LOW)

The spec schema table (line 81) marks `growth_category` as `required: yes`. The code (`NestedField(13, "growth_category", StringType(), required=False)`) marks it nullable. The growth category derivation rules (line 144) say null when `employment_change_pct` is null. The physical model marks it NULLABLE. The DQ rules allow null growth_category when pct is null.

The code, physical model, and DQ rules are internally consistent -- growth_category is nullable. The spec schema table is wrong. In practice this does not matter because current data has 0 null pct values, so growth_category is never null. But if future data introduces null pct values, the spec would be violated even though the code, model, and rules handle it correctly.

**Evidence demand:** Correct the spec schema table to mark growth_category as `required: no`.

**Assessment: Adequate.** The code and enforcement are correct. The spec schema table has a documentation error that does not affect runtime behavior. But a downstream developer reading only the spec would incorrectly believe growth_category cannot be null.

---

### RISK-008: occupation_title silent empty-string substitution (Severity: MEDIUM)

In the transformer (lines 163-165):

```python
occupation_title = raw.get("occupation_title", "")
if occupation_title is None:
    occupation_title = ""
```

If Bronze provides a null `occupation_title`, the transformer silently converts it to an empty string. This means:
- `catchall_flag` will be False (empty string does not contain "all other") -- correct but for the wrong reason.
- The DQ rule SLV-OOH-009 checks for null OR empty occupation_title, which should catch this -- but only after the data has been written.
- The `occupation_title` field is marked `required=True` (NOT NULL) in the schema, which would reject null at the Iceberg level. But by converting null to empty string, the transformer bypasses this protection. The row would be written with an empty title.

The spec says `occupation_title` is required and non-null. A null title from Bronze should be a hard failure (like a null SOC code), not silently coerced to empty string.

**Evidence demand:** Why does the transformer silently accept null occupation titles while rejecting null SOC codes? Both are required fields. The code should raise `ValueError` for null/empty occupation titles before transformation, consistent with SOC code handling.

**Assessment: Weak.** The silent coercion of null to empty string is a defensive pattern that masks data quality issues. The DQ rule would catch it post-hoc, but the transformer should fail-fast on bad input, not produce rows with empty titles.

---

### RISK-009: median_wage_capped defaults to False when missing from Bronze (Severity: LOW)

The transformer (line 200) uses `raw.get("median_wage_capped", False)`. If Bronze omits this field entirely, it defaults to False. This is probably fine since current Bronze data always provides this field. But it means a structural change in Bronze (removing the field) would produce silent incorrect data rather than a failure.

**Evidence demand:** Confirm that the Bronze schema guarantees `median_wage_capped` is always present. If not, the default should be removed in favor of a hard failure.

**Assessment: Adequate.** The default is reasonable given current data, but defensive coding against a missing required field should raise rather than default.

---

### RISK-010: Chaos monkey 14 rules never fired (Severity: MEDIUM)

The chaos manifest reports 14 of 36 DQ rules never fired across 5 cycles of adversarial corruption at 5-10% rates. The chaos monkey itself acknowledges this gap. Rules that never fire may be:

(a) Testing conditions not targeted by corruption strategies (benign).
(b) Testing conditions with thresholds too loose to detect 5-10% corruption.
(c) Tautological rules that always pass regardless of data state.

Notable unfired rules include:
- SLV-OOH-004 (valid 22 SOC major group codes) -- should have fired since Referential Integrity corruption injected "orphan SOC codes from invalid major groups (12, 14, 20, 90-98 ranges)."
- SLV-OOH-008 (soc_code not null) -- should have fired since Completeness corruption nulled required fields including soc_code.
- SLV-OOH-020 (growth_category null iff pct is null) -- should have fired since Consistency corruption introduced growth_category vs pct mismatches.

If corruption was injected for these dimensions but the rules did not fire, either the corruption did not reach these specific fields/rows, or the rules have a structural issue that prevents detection. The chaos monkey's "information barrier" means we cannot determine which.

**Evidence demand:** Re-run the chaos monkey with targeted corruption specifically for SLV-OOH-004, SLV-OOH-008, and SLV-OOH-020 and confirm they fire.

**Assessment: Adequate.** 22 of 36 rules (61%) fired, which is reasonable for cell-level corruption. The unfired rules are concerning but likely explained by the stochastic nature of corruption injection at low rates. A targeted re-test would resolve the ambiguity.

---

### RISK-011: DQ rules validate structure but not semantic accuracy of SOC major group names (Severity: MEDIUM)

DQ rule SLV-OOH-005 checks that `soc_major_group_name` is not null and not empty. DQ rule SLV-OOH-006 checks that `soc_major_group` equals `soc_code[:2]`. But no DQ rule validates that the `soc_major_group_name` is correct for the given `soc_major_group` code. If the lookup table in the code mapped "15" to "Legal" instead of "Computer and Mathematical," the DQ rules would pass because:
- The name is not null (SLV-OOH-005 passes).
- The major group code matches soc_code[:2] (SLV-OOH-006 passes).
- The name is a valid string (no enumeration check exists).

The lookup table was generated by an AI agent. A single mismatched name would propagate to every row in that major group.

**Evidence demand:** Show me a DQ rule that validates the (soc_major_group, soc_major_group_name) pair matches the BLS SOC 2018 taxonomy. Alternatively, show me the test that validates all 22 entries in SOC_MAJOR_GROUP_LOOKUP against the official BLS list.

**Assessment: Weak.** The test `test_all_22_groups_in_lookup` only checks that there are 22 entries. It does not validate the names. Three specific group tests exist (Management, Healthcare, Transportation) but 19 groups are untested. A lookup error in any of those 19 would not be detected.

---

### RISK-012: No test for education_code outside 1-8 range (Severity: LOW)

The transformer silently returns `None` for `education_level_name` if `education_code` is an unexpected value (e.g., 9 or 0) because it uses `EDUCATION_LEVEL_LOOKUP.get(education_code)`. This would produce a row where `education_code = 9` and `education_level_name = None` -- a valid-looking record with an invalid education code that gets no derived name. The DQ rule SLV-OOH-028 (education_code range 1-8) would catch this post-hoc, but the transformer does not fail-fast.

No unit test validates behavior for an out-of-range education code.

**Evidence demand:** Add a test that confirms the transformer handles education_code outside 1-8 (either by raising an error or by the specific behavior being intentional).

**Assessment: Adequate.** The DQ rule provides a safety net. But defensive coding would be stronger if the transformer rejected out-of-range codes rather than silently producing null derived names.

---

## Summary Assessment

| Risk ID | Severity | Assessment | Issue |
|---------|----------|------------|-------|
| RISK-001 | HIGH | Weak | Test fixtures use fabricated data, not real values |
| RISK-002 | HIGH | Weak | Catchall count 46 vs 70 -- spec, contract, model not corrected |
| RISK-003 | MEDIUM | Weak | Data contract says 31 rules, actually 36 |
| RISK-004 | MEDIUM | Weak | Projection cycle 2023-2033 vs 2024-2034 not corrected |
| RISK-005 | HIGH | Missing | No golden dataset artifact exists |
| RISK-006 | MEDIUM | Adequate | Broad occupation list trusts AI-produced Bronze audit |
| RISK-007 | LOW | Adequate | Spec says growth_category required, code says nullable |
| RISK-008 | MEDIUM | Weak | Null occupation_title silently coerced to empty string |
| RISK-009 | LOW | Adequate | median_wage_capped defaults to False when missing |
| RISK-010 | MEDIUM | Adequate | 14 of 36 chaos monkey rules never fired |
| RISK-011 | MEDIUM | Weak | No DQ rule validates major group name correctness |
| RISK-012 | LOW | Adequate | No test for out-of-range education codes |

**Controls rated Strong:** 0
**Controls rated Adequate:** 5
**Controls rated Weak:** 6
**Controls rated Missing:** 1

---

## Recommendations

### Must-Fix Before Spec Completion

1. **Create golden dataset artifact.** Add `governance/golden-datasets/silver-base-bls-ooh-golden.json` with at least 3 independently verifiable occupation records (Software Developers, Registered Nurses, a declining occupation). Values must come from the EDA profiling of real Bronze data, not from test fixtures. Run the Brightsmith integration test harness to validate these against the actual Silver table.

2. **Correct the catchall count everywhere.** Update the spec (2 locations), logical model, conceptual model, and data contract to state 70, not 46. The EDA and DQ rule already reflect the correct count. All governance documents must agree.

3. **Regenerate the data contract.** The DQ rule count (31 vs 36) and catchall count (46 vs 70) are both wrong. Re-run the contract generator after DQ rules and spec are finalized.

4. **Add a DQ rule for major group name referential integrity.** Write a rule that validates the (soc_major_group, soc_major_group_name) pair against the expected 22-entry lookup. This catches lookup table errors that the current rules miss entirely.

### Should-Fix

5. **Fail-fast on null/empty occupation_title.** Change the transformer to raise `ValueError` for null or empty occupation titles, consistent with SOC code validation. Do not silently coerce to empty string.

6. **Correct the projection cycle in domain context and business glossary.** If the data is 2024-2034, all governance artifacts should say 2024-2034.

7. **Add parameterized test for all 22 SOC major group lookup entries.** The current tests check 3 of 22 groups. A `@pytest.mark.parametrize` test covering all 22 (code, name) pairs would catch any lookup error.

8. **Update test fixture values to match real data.** The Software Developers fixture should use the actual EDA-profiled values (employment_current=1693800, median_annual_wage=133080.0) not fabricated numbers. Tests that use fake data for real entities create false confidence.

### Nice-to-Have

9. **Add a test for out-of-range education_code behavior.** Document whether the transformer should reject or silently accept codes outside 1-8.

10. **Re-run chaos monkey with targeted corruption** for the 14 unfired rules to confirm they can fire under appropriate conditions.

11. **Consider removing the `median_wage_capped` default.** If the field is required from Bronze, the transformer should fail rather than default when it is missing.

---

## Meta-Assessment: Can AI Agents Build Trustworthy Silver Zone Pipelines?

The transformation logic is correct. The `derive_growth_category()` function, the broad occupation flag, the catchall flag, the SOC major group derivation -- all of these are implemented correctly and tested at the boundary values. The DQ rules are comprehensive (36 rules covering 10 dimensions) and the chaos monkey hardening is a genuine adversarial exercise, not theater.

Where this pipeline falls short is **governance document consistency** and **end-to-end validation against known-correct values**. The EDA found that the spec's catchall count was wrong (70 vs 46), the DQ rule writer corrected the rule, but nobody corrected the spec, logical model, or data contract. This is the "telephone game" problem of AI agent pipelines: each agent does its job correctly in isolation, but corrections do not propagate backward through the document chain.

The absence of a golden dataset is the single biggest gap. Without it, this pipeline proves that the code logic is correct but does not prove that the actual output data is correct. Those are different claims. A regulator would ask: "Show me that the median wage for Software Developers in your Silver table is $133,080." The current test suite cannot answer that question.

**Verdict: The transformation logic and DQ controls are solid. The governance artifact consistency and end-to-end data validation are not yet at a level a regulator would accept. Fix the 4 must-fix items and this spec can be approved.**
