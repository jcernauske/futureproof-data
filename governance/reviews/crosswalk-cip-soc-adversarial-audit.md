# Adversarial Audit: crosswalk-cip-soc

**Spec:** crosswalk-cip-soc
**Auditor:** @adversarial-auditor
**Date:** 2026-04-08
**Tables:** raw.cip_soc_crosswalk (Bronze, 6,097 rows), base.cip_soc_crosswalk (Silver, 5,903 rows)
**Verdict:** PASS with findings (3 Critical, 2 High, 3 Medium, 2 Low)

---

## Risk Register

### RISK-01: Physical model lists 22 SOC major groups but code has 23 [CRITICAL]

**Finding:** The physical model DDL CHECK constraint at `/Users/jcernauske/code/bright/futureproof-data/governance/models/crosswalk-cip-soc-physical.md` line 381 lists only 22 SOC major groups and omits group 55 (Military). However, the transformer code at `/Users/jcernauske/code/bright/futureproof-data/src/silver/cip_soc_crosswalk_transformer.py` line 41-45 correctly includes all 23 groups (including 55). The DQ rule SLV-XW-006 also correctly includes 55. The physical model description on line 152 also says "22 valid major group codes" but the DQ scorecard says "23 valid SOC major group codes (22 civilian + 55 Military)."

The physical model is the single-source-of-truth for schema constraints. It is wrong. A downstream developer reading the physical model DDL would implement a constraint that silently drops 55 military rows from the Silver table.

**Evidence demanded:** The physical model DDL must be corrected to include '55' in the soc_major_group CHECK constraint and update "22" to "23" throughout.

**Assessment:** WEAK -- The code is correct, the DQ rules are correct, but the canonical reference document is wrong. This is exactly the kind of drift that AI-generated artifacts produce: each agent got a slightly different version of the truth. The code happens to be right because the chaos monkey caught the original omission and it was fixed in code, but nobody updated the physical model.

---

### RISK-02: has_scorecard_match is 0% TRUE -- the bridge table cannot bridge [CRITICAL]

**Finding:** Verified via direct query: has_scorecard_match is FALSE for all 5,903 Silver rows. match_quality is "no_scorecard" for 100% of rows. The crosswalk uses 6-digit CIP codes (XX.XXXX, e.g., "52.0201") while College Scorecard stores 4-digit CIP codes (XX.XX, e.g., "52.02"). Zero direct matches exist.

This means the entire purpose of this table -- bridging College Scorecard programs to BLS/O*NET occupations -- does not work at the Silver zone level. The spec acknowledges this and defers to the Gold zone, but the spec's original DQ expectations (60-90% has_scorecard_match) were wrong and had to be corrected by the EDA findings. The DQ rules were updated to expect 0-5% TRUE, but this means the "match quality" system is vestigial -- it classifies nothing useful.

**What I verified:**
- College Scorecard CIPs are 100% XX.XX format (390 distinct, confirmed by query)
- Crosswalk CIPs are 100% XX.XXXX format (1,949 distinct after filtering)
- Truncating crosswalk CIPs to 4 digits would match 355 of 390 Scorecard CIPs (91.0%)

**Assessment:** ADEQUATE -- The team knows about this and has documented it extensively. The EDA caught it, the DQ rules were corrected, and the spec explicitly defers resolution to Gold. But a regulator would ask: "You built a bridge table that cannot bridge. Why did you ship it?" The answer -- "the Gold zone will resolve it" -- is acceptable only if the Gold spec is written and the resolution plan is concrete. That Gold spec does not yet exist.

---

### RISK-03: DQ rule SLV-XW-011 is failing in production [CRITICAL]

**Finding:** The DQ scorecard shows SLV-XW-011 (has_bls_match 90-97% TRUE) as FAIL. Actual value is 97.39%, which exceeds the upper bound of 97%. The scorecard explains this as "better than expected" and recommends widening the threshold.

This is not a data quality issue -- the data is better than predicted. But the rule is FAILING. In a regulated environment, a failing P1 DQ rule that nobody has fixed is an audit finding. Either the threshold needs to be updated or the rule needs a documented exception.

**Assessment:** WEAK -- The failure is documented in the scorecard with correct analysis, but the rule itself has not been updated. The gap between "we know it should pass" and "it actually passes" is exactly what auditors flag. Fix the threshold.

---

### RISK-04: Three DQ rules cannot execute in chaos monkey shadow mode [HIGH]

**Finding:** SLV-XW-018, SLV-XW-019, SLV-XW-020 (referential integrity rules for BLS, O*NET, and Scorecard cross-table joins) ERROR in all 5 chaos monkey cycles. The shadow infrastructure cannot load the referenced tables alongside the shadow crosswalk table.

This means the referential integrity of the match flags has never been tested under adversarial conditions. The chaos monkey exercises 25 of 28 rules; the 3 that cannot run are the ones that validate the most critical feature of this table (cross-table lookups).

**Assessment:** WEAK -- The chaos manifest correctly identifies this as a framework limitation and recommends a fix. But until the fix is implemented, the claim that "chaos monkey validates the pipeline" is incomplete. The most important DQ rules for this spec are exactly the ones that cannot be chaos-tested.

---

### RISK-05: No data contract exists [HIGH]

**Finding:** The spec lists `governance/data-contracts/base-cip-soc-crosswalk.yaml` as a required artifact. No such file exists. The data contract is the formal guarantee to downstream consumers about schema stability, SLAs, and breaking change policies.

**Assessment:** MISSING -- This is a checklist item in the spec that has not been completed. Without a data contract, the Gold zone consumer has no formal guarantee about what this table provides.

---

### RISK-06: Coverage gap report does not exist [MEDIUM]

**Finding:** The spec lists `governance/reviews/crosswalk-coverage-gaps.md` as a required artifact. No such file exists. The EDA contains coverage gap analysis inline, but there is no standalone report that a stakeholder could review.

**Assessment:** WEAK -- The information exists in the EDA but not in the dedicated artifact location the spec specifies. This is a documentation gap, not a data gap.

---

### RISK-07: Chaos monkey detection rate is 75-79%, not 90%+ [MEDIUM]

**Finding:** Across 5 chaos cycles, the detection rate ranges from 71.4% to 78.6% (22-25 of 28 rules firing). Two rules (SLV-XW-010, SLV-XW-013) never fired despite corruption. These are the has_scorecard_match and match_quality consistency rules -- they never fire because has_scorecard_match is always FALSE (see RISK-02), so corruption cannot change the expected outcome.

This is not a gap in the DQ rules per se -- the rules are correctly written. The problem is that the chaos monkey cannot exercise these rules because the underlying data state (0% has_scorecard_match) makes them untestable. If the Gold zone ever resolves the CIP granularity mismatch and has_scorecard_match starts returning TRUE, these rules have never been validated under adversarial conditions.

**Assessment:** ADEQUATE -- The chaos manifest correctly identifies and explains these gaps. The rules will become testable when has_scorecard_match is non-trivial. But this means 2 rules are currently flying blind.

---

### RISK-08: Row count estimates in physical model are wrong [MEDIUM]

**Finding:** The physical model states "Expected row count: 3,000-5,000" for both Bronze and Silver tables (lines 42 and 123). Actual counts are 6,097 (Bronze) and 5,903 (Silver). The DQ rules were correctly updated to reflect actuals (5,500-6,500 for Bronze, 5,500-6,200 for Silver), but the physical model was not updated.

**Assessment:** WEAK -- Same pattern as RISK-01: the code and DQ rules are correct, but the reference documentation is stale. The physical model should be the authoritative spec, not a historical artifact.

---

### RISK-09: Test fixture uses 6-digit CIP in scorecard_cips set [LOW]

**Finding:** The test fixture `scorecard_cips` at `/Users/jcernauske/code/bright/futureproof-data/tests/silver/test_cip_soc_crosswalk_transformer.py` line 38 uses `{"52.0201", "11.0101", "26.0101", "13.0101"}` -- these are 6-digit CIPs. In production, College Scorecard CIPs are 4-digit (e.g., "52.02"). The test therefore exercises a code path (has_scorecard_match = TRUE) that never occurs in production.

This is not a bug -- the test is validating the lookup logic correctly, and the code works for any format in the set. But it means the tests do not model the production data reality. A test that used 4-digit CIPs in the scorecard set would correctly show has_scorecard_match = FALSE for all crosswalk rows, which is the actual production behavior.

**Assessment:** ADEQUATE -- The tests validate the logic correctly. Using 6-digit CIPs in the test fixture is actually more thorough because it exercises both TRUE and FALSE code paths. But it could mislead someone reading the tests into thinking scorecard matches actually occur.

---

### RISK-10: Military SOC group 55 has zero BLS and O*NET matches [LOW]

**Finding:** All 55 military rows (SOC major group 55) have has_bls_match = FALSE and has_onet_match = FALSE. This is expected -- BLS OOH and O*NET do not cover military occupations. But these rows will never be useful for the FutureProof career outcomes pipeline. They exist in the crosswalk but are dead ends.

**Assessment:** ADEQUATE -- These are valid crosswalk entries from the authoritative NCES source. Keeping them preserves data fidelity. The match_quality = "no_scorecard" correctly identifies them as non-actionable.

---

## Evidence Verification Summary

| Claim | Evidence | Verified? |
|-------|----------|-----------|
| Bronze row count = 6,097 | Direct query | YES |
| Silver row count = 5,903 | Direct query | YES |
| 194 sentinel rows filtered | Bronze 6,097 - Silver 5,903 = 194 | YES |
| has_scorecard_match = 0% TRUE | Direct query: 0 of 5,903 | YES |
| has_bls_match = 97.39% TRUE | Direct query: 5,749 of 5,903 | YES |
| has_onet_match = 94.85% TRUE | Direct query: 5,599 of 5,903 | YES |
| match_quality = 100% no_scorecard | Direct query: 5,903 of 5,903 | YES |
| Zero sentinel rows in Silver | Direct query: 0 | YES |
| 23 SOC major groups including 55 | Direct query: confirmed | YES |
| Zero duplicate grains | Direct query: 0 duplicates | YES |
| Zero invalid record_ids | Direct query: all match xw-[a-f0-9]{16} | YES |
| College Scorecard CIPs are 4-digit | Direct query: 390 all XX.XX | YES |
| Crosswalk CIPs are 6-digit | Direct query: 1,949 all XX.XXXX | YES |
| 4-digit truncation yields 91% match | Direct query: 355 of 390 | YES |
| 52.0201 maps to 23 SOCs | Direct query: confirmed | YES |
| All 54 unit tests pass | pytest execution: 54 passed | YES |
| DQ scorecard: 27/28 passing | Scorecard review: SLV-XW-011 fails | YES |

## Recommendations

1. **IMMEDIATE: Fix the physical model.** Add SOC major group '55' to the CHECK constraint. Update row count estimates from 3,000-5,000 to 5,500-6,500 (Bronze) and 5,500-6,200 (Silver). Update "22 valid SOC major group codes" to "23" throughout.

2. **IMMEDIATE: Fix SLV-XW-011 threshold.** Widen the upper bound from 97% to 98% so the rule passes. The current failure is a calibration issue, not a data quality issue, but a failing rule is a failing rule.

3. **REQUIRED: Create the data contract.** `governance/data-contracts/base-cip-soc-crosswalk.yaml` is listed in the spec and does not exist.

4. **REQUIRED: Create the coverage gap report.** `governance/reviews/crosswalk-coverage-gaps.md` is listed in the spec and does not exist.

5. **RECOMMENDED: Add a framework enhancement for cross-table shadow mode.** The chaos monkey identified this correctly. Until SLV-XW-018/019/020 can be adversarially tested, the referential integrity of match flags is validated only by the DQ scorecard, not by chaos testing.

6. **RECOMMENDED: Document the Gold zone CIP resolution plan.** The entire value proposition of this table depends on resolving the 6-digit/4-digit CIP mismatch. The spec says "deferred to Gold zone" but no Gold spec for this resolution exists yet.

## Overall Assessment

The pipeline implementation is solid. The code is correct. The data matches expectations. The EDA findings are accurate and were verified by direct query. The DQ rules are well-designed and catch what they claim to catch. The chaos monkey found real issues (the SOC group 55 omission, the namespace bug) and documented them honestly.

The gaps are in documentation drift (physical model inconsistencies), missing artifacts (data contract, coverage gap report), and one known DQ rule failure that needs a threshold adjustment. These are fixable.

The harder question is whether a bridge table that bridges nothing (0% has_scorecard_match) should be considered "complete." The answer is yes, with a caveat: the table is structurally sound and will work correctly once the Gold zone resolves the CIP granularity mismatch. But that resolution is not yet built, and the table's primary value is deferred.

**Gate recommendation:** PASS -- conditional on fixing RISK-01 (physical model), RISK-03 (SLV-XW-011 threshold), RISK-05 (data contract), and RISK-06 (coverage gap report).
