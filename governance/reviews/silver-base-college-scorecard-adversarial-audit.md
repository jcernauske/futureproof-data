# Adversarial Audit: silver-base-college-scorecard

**Date:** 2026-04-06
**Auditor:** Adversarial Auditor Agent
**Spec:** docs/specs/silver-base-college-scorecard.md
**Scope:** All Silver zone governance artifacts, implementation, and tests
**Standard:** Would a regulator accept this explanation?

---

## Executive Summary

This audit examined 14 artifacts produced by AI agents for the `silver-base-college-scorecard` pipeline. The pipeline demonstrates strong structural governance -- the artifacts are internally consistent, the EDA is thorough, and the DQ rules trace back to evidence. However, I found **7 confirmed defects** (including one that will cause silent data corruption in production), **4 hallucination risks** that lack adequate mitigation, and **several governance gaps** where the appearance of control exceeds the reality of control.

The most serious finding is that the CIP family lookup table is missing 7 of the 45 families the EDA explicitly identified, meaning 61+ rows will receive "Unknown CIP Family" labels in production despite the DQ scorecard reporting 100% pass on cip_family_name completeness. The DQ rules check for NULL, not for "Unknown" fallback values -- so the defect is invisible to the quality gate.

---

## 1. Risk Register

### CRITICAL

**RISK-001: CIP Family Lookup Table Missing 7 Families -- Silent Data Corruption**
- Severity: CRITICAL
- Category: AI Hallucination / Implementation Defect
- The EDA explicitly states "All 45 families are valid CIP 2020 two-digit codes" and warns "Families 32, 33, 34, 35, 36, and 53 are unusual at bachelor's level (combined: 52 rows, 0.07%) and represent edge cases in the CIP taxonomy. The lookup table must include these."
- The transformer's `CIP_FAMILIES` dictionary contains only **34 entries** (I counted every key in the source). Missing families: **32** (Basic Skills/Remedial Education, 3 rows), **33** (Citizenship Activities, 2 rows), **34** (Health-Related Knowledge and Skills, 10 rows), **35** (Interpersonal and Social Skills, 1 row), **36** (Leisure and Recreational Activities, 33 rows), **48** (Precision Production, 9 rows), **53** (High School/Secondary Programs, 4 rows).
- The code handles this with a fallback: `CIP_FAMILIES.get(cip_family, f"Unknown CIP Family ({cip_family})")`. So these 62 rows will receive labels like "Unknown CIP Family (32)" instead of failing.
- DQ rule SLV-CS-012 checks `WHERE cip_family_name IS NULL OR TRIM(cip_family_name) = ''` -- it checks for NULL and empty, but NOT for the "Unknown" fallback. The rule passes because the fallback string is non-null and non-empty.
- **This is the exact hallucination pattern I worry about:** The AI agent wrote the EDA correctly identifying 45 families, the DQ rule writer was told to ensure "all 45 families must resolve," and the implementer created a fallback that makes the DQ rule pass while the data is wrong. Every artifact individually looks correct. The defect is in the gap between them.
- **Evidence:** Compare lines 31-68 of `src/silver/college_scorecard_transformer.py` (34 entries) against the EDA table at lines 66-115 of `governance/eda/silver-college-scorecard-eda.md` (45 families listed). The code at line 137 uses `.get()` with a fallback string.

**RISK-002: institution_control Is NULL in Production Despite NOT NULL Contract**
- Severity: CRITICAL
- Category: Schema / Contract Violation
- The physical model declares `institution_control VARCHAR NOT NULL`. The data contract declares `required: true`. DQ rule SLV-CS-027 checks `WHERE institution_control NOT IN ('Public', 'Private nonprofit', 'Private for-profit')` and **passes**.
- But the Iceberg schema in the transformer (line 93) declares `required=False` for institution_control. The EDA confirms the CONTROL field is missing from the Bronze parquet. The transformer sets `institution_control = None` when control is absent (line 141-142).
- So in production: every row has `institution_control = NULL`. The DQ rule passes because SQL `NULL NOT IN (...)` evaluates to NULL (falsy), not True -- so NULL rows are not returned by the WHERE clause. This is a well-known SQL gotcha.
- The DQ scorecard shows SLV-CS-027 as PASS with actual=0. This is technically correct SQL behavior but semantically wrong -- the rule is supposed to validate that institution_control contains only valid values, but it silently ignores NULL.
- **The data contract says required:true. The schema says required:false. The DQ rule says PASS. The actual data is 100% NULL. A regulator would not accept this.**
- **Evidence:** Scorecard line 39 shows PASS with actual=0. Transformer line 93 shows `required=False`. Physical model line 72 shows `NOT NULL`.

### HIGH

**RISK-003: Grain Hash Computed on Silver Field Names, Not Raw Field Names as Documented**
- Severity: HIGH
- Category: Documentation / Implementation Mismatch
- The spec (line 36), physical model (line 151), and lineage document (line 102) all say: `compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='cs')` -- using the raw field name `credlev`.
- The actual code (line 82, 166) uses `GRAIN_FIELDS = ["unitid", "cipcode", "credential_level"]` and computes the hash on the Silver record dict which has the key `credential_level`, not `credlev`.
- This means: (a) The record_id values in production are computed using `credential_level` as the dict key, not `credlev`. (b) The grain hash is still deterministic and unique -- it works. (c) But any downstream system or verification tool that tries to reproduce the hash using the documented field names `['unitid', 'cipcode', 'credlev']` will compute a DIFFERENT hash and fail to match.
- The lineage document (line 102) says `compute_grain_id(row, ['unitid', 'cipcode', 'credential_level'], prefix='cs')` -- this matches the code, BUT the lineage's input description says `"field": "credlev"` in the inputFields array. The spec and physical model use `credlev`. So there are three versions of the truth.
- **This is not yet causing failures but will cause confusion and verification failures when someone tries to reproduce the hash externally.**

**RISK-004: SLV-CS-028 Has Been Broken Since Creation -- Never Tested Successfully**
- Severity: HIGH
- Category: DQ Coverage Gap
- SLV-CS-028 checks row count consistency between Silver and raw zones. It errors on every execution (scorecard line 40: "Catalog Error: Table with name raw_college_scorecard does not exist").
- The chaos monkey confirms it errored in all 5 cycles (chaos manifest line 82-84).
- This rule was "approved_by: human" (DQ rules line 399) despite never producing a valid result. The human approved a rule that has never successfully executed.
- **This means the 1:1 row mapping guarantee between raw and Silver has never been verified.** The spec says "no row-level filtering" and the transformation is supposed to be 1:1. Without this rule, a subtle bug that drops rows (e.g., the `return None` path in transform_row for null grain fields) would go undetected.
- **Evidence:** DQ rules line 395: SQL references `raw.college_scorecard` which doesn't exist as `raw_college_scorecard` in DuckDB. Scorecard line 40 shows ERROR.

**RISK-005: Physical Model Derivation Rule for institution_control Contradicts Implementation**
- Severity: HIGH
- Category: Documentation Hallucination
- Physical model (line 157): `{1: 'Public', 2: 'Private nonprofit', 3: 'Private for-profit'}[int(raw_control)]` -- maps from integers.
- EDA Critical Finding #3 (line 22-24): "The source CSV stores CONTROL as text labels (e.g., 'Public', not '1'). The derivation expression must be updated."
- Actual code (lines 72-80): `CONTROL_MAP` handles BOTH numeric strings ("1", "2", "3") AND text labels ("Public", "Private nonprofit", "Private for-profit", "Private not-for-profit"). The code also handles a variant "Private not-for-profit" that appears nowhere in the spec, EDA, or physical model.
- **The physical model still documents the wrong derivation rule.** The EDA identified this as CRITICAL. The implementer fixed it in code. But the physical model was never updated. A future developer reading the physical model would implement the wrong logic.
- **Where did "Private not-for-profit" come from?** This value appears in CONTROL_MAP (line 78) but is not documented in any governance artifact. It is not in the physical model CHECK constraint. It is not in the data contract. If it appears in the data, it maps to "Private nonprofit" silently. If it does NOT appear in the data, it is dead code. Either way, it is undocumented.

**RISK-006: EDA Null Rate for earnings_2yr_median Contradicts Physical Model**
- Severity: HIGH
- Category: Hallucinated/Inconsistent Statistics
- Physical model (line 252): "earnings_2yr_median: ~64% null"
- EDA (line 307): "earnings_2yr_median | Max Null Rate: 65% | Source: 60.4% null"
- DQ scorecard (line 29): "actual=60.4, threshold=result <= 65.0" -- PASS
- The physical model says ~64% but the actual data and EDA say 60.4%. These are different numbers. The physical model number appears to have been copied from earnings_1yr_median (which IS ~64%) or rounded carelessly. This is a minor hallucination but it demonstrates that the AI agent did not maintain perfect consistency across artifacts.
- **The same section in the physical model also says "earnings_1yr_median: ~64% null" and "debt_median: ~60% null".** The EDA says 1yr is 64.0%, 2yr is 60.4%, debt is 63.1%. So the physical model has 2yr and debt wrong.

### MEDIUM

**RISK-007: CIP Code Format Discrepancy Between Spec and Reality**
- Severity: MEDIUM
- Category: Documentation Inconsistency
- The spec (line 45, 75), business glossary BT-003, logical model (line 86), and data contract (line 90-91) all describe cipcode as "XX.XXXX format" (7 characters, e.g., "52.0200").
- The EDA (line 20, 46-47) correctly identifies that the actual output is XX.XX (5 characters, e.g., "52.02") because source codes are 4-digit, not 6-digit.
- The physical model CHECK constraint was corrected to `^\d{2}\.\d{2,4}$` per the EDA recommendation.
- The DQ rule SLV-CS-002 uses `^\d{2}\.\d{2,4}$` (corrected).
- **But the spec, glossary, and logical model still say "XX.XXXX".** Multiple artifacts describe a format that does not match the data. The physical model and DQ rules are correct, but the upstream documentation is stale.
- A downstream Gold zone developer reading the spec or glossary would expect 7-character codes and might write joins or regex that fail on 5-character codes.

**RISK-008: Business Glossary Term BT-003 (CIP Code) Definition Says XX.XXXX**
- Severity: MEDIUM
- Category: Glossary Hallucination
- BT-003 definition: "Standard format is XX.XXXX (2-digit family code followed by a dot and 4-digit detail code)."
- This is technically correct for the CIP 2020 standard (which does use XX.XXXX). But in this dataset, CIP codes are 4-digit (producing XX.XX after normalization). The glossary definition describes the standard, not the data.
- A data consumer reading BT-003 would expect "52.0201" but would receive "52.02". This could cause join failures with external reference tables that DO use full 6-digit CIP codes (e.g., the NCES CIP-SOC crosswalk).
- **This is actually a REAL domain problem:** The College Scorecard uses 4-digit CIP series codes, not 6-digit detailed codes. The CIP-to-SOC crosswalk uses 6-digit codes. A future join will require handling this mismatch. The glossary masks this issue.

**RISK-009: No DQ Rule Validates CIP Family Name Correctness (Only Non-Null)**
- Severity: MEDIUM
- Category: DQ Coverage Gap
- SLV-CS-012 checks: `WHERE cip_family_name IS NULL OR TRIM(cip_family_name) = ''`
- There is no rule that validates cip_family_name against a reference list.
- The transformer could assign "Agriculture" to CIP family 52 (Business) and the DQ rules would pass.
- The EDA recommends "cip_family referential integrity rules: all 45 observed families must be in the CIP 2020 lookup table" but this recommendation resulted in SLV-CS-003 (which checks the CODE format, not the NAME correctness) and SLV-CS-032 (which checks the COUNT of distinct families, not their content).
- **Semantic correctness of derived fields is never validated.** This is a general pattern: the DQ rules check structure (not null, right format, right count) but not meaning.

**RISK-010: Chaos Monkey Detection Rate of 71-74% Means 26-29% of Corruptions Go Undetected**
- Severity: MEDIUM
- Category: DQ Effectiveness
- 8 of 35 rules never fired across 5 chaos cycles.
- The chaos report identifies that percentage-threshold rules (SLV-CS-016/017/018) are too loose -- they accommodate 10% corruption without triggering.
- Three rules (SLV-CS-029/032/035) always return 0 regardless of corruption. These rules check conditions like distinct institution count (2200-3000), distinct CIP families (40-50), and small_cohort_flag true rate (70-80%). The chaos monkey removes CIP families and duplicates rows, but these operations apparently do not push the metrics outside the wide thresholds.
- **The DQ ruleset is optimized for structural completeness, not for corruption detection.** This is expected for a base table, but should be documented as a known limitation.

**RISK-011: small_cohort_flag Derivation Rule Differs Between Logical Model and Implementation**
- Severity: MEDIUM
- Category: Documentation Inconsistency
- Logical model (line 127): "True when `completions_count_1` is not null and `completions_count_1 < 30`"
- Spec (line 78): "`completions_count_1 is not null and completions_count_1 < 30` -> True"
- Physical model (line 119): "True when completions_count_1 IS NULL OR completions_count_1 < 30"
- Code (line 145): `completions_1 is None or completions_1 < 30`
- The logical model and spec say `IS NOT NULL AND < 30` (flag only when count is known and small). The physical model and code say `IS NULL OR < 30` (flag when count is unknown OR small).
- These produce DIFFERENT results for the 6,098 rows where completions_count_1 IS NULL. The physical model/code flag them True (conservative). The logical model/spec would flag them False (non-conservative).
- The physical model's Implementation Notes section (line 266-267) documents the resolution: "Per human approval: when completions_count_1 is NULL, small_cohort_flag is set to True." So the code is correct and the logical model/spec are stale.
- DQ rule SLV-CS-026 validates the physical model/code version and passes.
- **But the logical model and spec still document the wrong rule.** This is a governance failure: the approved models were updated but the upstream spec and logical model were not.

**RISK-012: BT-014 (Small Cohort Flag) Definition Omits NULL Handling**
- Severity: MEDIUM
- Category: Glossary Incompleteness
- BT-014 definition: "A derived boolean flag indicating that a program has fewer than 30 completers (completions_count_1 < 30)."
- This omits the NULL case. The actual behavior is: True when completions_count_1 IS NULL OR < 30. The 6,098 rows with NULL completions are flagged True. The glossary definition does not cover this.
- BT-014 source_reference points to the spec, which also has the wrong definition.

### LOW

**RISK-013: Data Contract Owner Is "@doc-generator" -- Not a Human**
- Severity: LOW
- Category: Governance Process
- The data contract (line 19) lists `owner: "@doc-generator"` -- an AI agent. Data contracts should be owned by a human or a human-accountable team.

**RISK-014: Lineage Claims CONTROL Is in Input Schema But It Is Not in Parquet**
- Severity: LOW
- Category: Lineage Accuracy
- The lineage input schema (line 48) lists `{"name": "control", "type": "STRING"}` as an input field, and the column lineage (line 119-124) describes the institution_control derivation from `raw.college_scorecard.control`.
- But the EDA confirms control is not in the parquet. The lineage describes a data flow that does not exist yet.

**RISK-015: Conceptual Model Status Is "PROPOSED" But Physical Model Says "APPROVED"**
- Severity: LOW
- Category: Governance Process
- Conceptual model (line 10): "Approval: Pending human review"
- Logical model (line 10): "Approval: Pending human review"
- Physical model (line 2): "APPROVED (generated from approved logical model)"
- If the logical model is not approved, the physical model cannot be approved. The approval chain is inconsistent.

---

## 2. Evidence Demands (Satisfied and Unsatisfied)

| Risk | Evidence Needed | Evidence Found | Verdict |
|------|----------------|----------------|---------|
| RISK-001 | CIP_FAMILIES dict must contain all 45 EDA families | Dict has 34 entries; 7 families missing (32,33,34,35,36,48,53) | **UNSATISFIED -- confirmed defect** |
| RISK-002 | institution_control must be non-null per contract | Schema says required=False, all production values are NULL, DQ rule passes due to SQL NULL semantics | **UNSATISFIED -- confirmed defect** |
| RISK-003 | Grain hash documentation must match implementation | Spec says `credlev`, code uses `credential_level` | **UNSATISFIED -- documentation wrong** |
| RISK-004 | SLV-CS-028 must produce a valid result | ERROR in scorecard AND all 5 chaos cycles | **UNSATISFIED -- rule is broken** |
| RISK-005 | Physical model derivation must match code | Physical model says integer mapping, code handles both text and integer | **UNSATISFIED -- physical model stale** |
| RISK-006 | Null rate statistics must be consistent | Physical model says ~64% for 2yr, actual is 60.4% | **UNSATISFIED -- minor hallucination** |
| RISK-007 | CIP code format must be consistently documented | Spec says XX.XXXX, reality is XX.XX | **UNSATISFIED -- spec is stale** |
| RISK-008 | Glossary must describe actual data format | BT-003 describes the CIP standard, not this dataset's format | **PARTIALLY SATISFIED -- technically accurate but misleading** |
| RISK-009 | Semantic correctness of cip_family_name must be validated | No DQ rule checks name correctness, only non-null | **UNSATISFIED -- gap exists** |
| RISK-010 | DQ rules must detect corruptions at all tested levels | 8 of 35 rules never fired across 5 chaos cycles | **PARTIALLY SATISFIED -- documented as known limitation** |
| RISK-011 | small_cohort_flag must be consistently defined | Physical model/code say one thing, spec/logical model say another | **UNSATISFIED -- upstream docs stale** |
| RISK-012 | BT-014 must cover NULL case | Definition omits NULL handling | **UNSATISFIED -- incomplete** |

---

## 3. Assessment: Grading Existing Controls

### Strong Controls

1. **EDA quality.** The Silver EDA is thorough, specific, and well-evidenced. It identified the CIP CHECK constraint mismatch, the CONTROL field absence, and the CONTROL derivation error -- all BEFORE implementation. The EDA recommendations are actionable and trace to specific DQ rules. This is better than most human-produced EDA reports I have seen.

2. **DQ rule coverage breadth.** 35 rules covering 6 dimensions (completeness, validity, uniqueness, consistency, volume, coverage). Each rule has a documented evidence chain back to the EDA. The DQ rules are the strongest artifact in this pipeline.

3. **Chaos monkey methodology.** Five cycles, escalating corruption rates, 10 corruption dimensions, information barrier between chaos monkey and DQ rules. The after-action report is honest about gaps (8 silent rules, 1 broken rule). The chaos monkey did its job.

4. **Privacy suppression handling.** The treatment of FERPA suppression is correct throughout: NULL means suppressed, not missing. 1yr and 2yr suppress independently. The small_cohort_flag conservative default is well-reasoned. The PII scan correctly identifies aggregate data vs. individual data.

5. **Test coverage for core transformations.** The unit tests cover CIP normalization (including edge cases), small_cohort_flag at boundary values (29=True, 30=False), NULL handling, CONTROL mapping variants, and record_id determinism. 35 test cases for 4 test classes.

### Adequate Controls

6. **Physical model as source of truth.** The physical model is the most accurate artifact. It was corrected for the CIP CHECK constraint, it documents the conservative NULL handling for small_cohort_flag, and it carries open issues. The derivation rule for institution_control is stale (documented above), but the model is otherwise reliable.

7. **Data contract.** Covers all columns, constraints, quality thresholds, and lineage references. The institution_control discrepancy (required:true vs. actual NULL) is a defect, but the contract structure is sound.

### Weak Controls

8. **Cross-artifact consistency.** The logical model, spec, and glossary contain stale definitions that contradict the physical model and code. The approval chain is inconsistent. No automated check ensures these artifacts stay in sync. **This is the primary governance weakness: the AI agents updated downstream artifacts but did not propagate changes back to upstream documents.**

9. **Semantic validation of derived fields.** DQ rules check structural properties (non-null, right format, right count) but never check semantic correctness (is this the RIGHT name for this CIP family?). This is a fundamental limitation of automated DQ: it can check that a value exists, not that it is correct.

10. **Human approval effectiveness.** Every DQ rule is marked "approved_by: human." But SLV-CS-028 was approved despite never producing a valid result. SLV-CS-027 was approved despite not detecting NULL institution_control. The human approved what the AI presented, without independently verifying execution results.

### Missing Controls

11. **No golden dataset with manually verified records.** There is no reference dataset of hand-checked records that can be compared to pipeline output. Without this, there is no ground truth.

12. **No cross-artifact consistency check.** No automated process verifies that the spec, logical model, physical model, DQ rules, data contract, and glossary are all in agreement. Discrepancies (like the small_cohort_flag definition) can persist indefinitely.

13. **No referential integrity check for CIP family name lookup.** The EDA recommended it. The DQ rules do not implement it.

14. **No record-count reconciliation between raw and Silver.** SLV-CS-028 was supposed to do this but has never worked.

---

## 4. Recommendations

### Immediate (Block Next Milestone)

**R-001:** Add the 7 missing CIP families to `CIP_FAMILIES` in `src/silver/college_scorecard_transformer.py`. Missing: 32 (Basic Skills and Remedial Education), 33 (Citizenship Activities), 34 (Health-Related Knowledge and Skills), 35 (Interpersonal and Social Skills), 36 (Leisure and Recreational Activities), 48 (Precision Production), 53 (High School/Secondary Diploma/Certificate Programs). Reference: NCES CIP 2020 taxonomy.

**R-002:** Add a DQ rule that checks `WHERE cip_family_name LIKE 'Unknown%'` with threshold `result_count = 0`. This catches the fallback path that the current rules miss.

**R-003:** Fix SLV-CS-027 to detect NULL institution_control: change to `WHERE institution_control IS NULL OR institution_control NOT IN ('Public', 'Private nonprofit', 'Private for-profit')`. Alternatively, if NULL is intentionally allowed during the CONTROL migration, change the data contract and physical model to `required: false` / `NULLABLE` and add an explicit note that this is a known gap with a timeline for resolution.

**R-004:** Fix SLV-CS-028. The table name in DuckDB is likely `base_college_scorecard` (underscores, not dots) for the Silver table. The raw table may need a different catalog reference or the rule needs to be restructured to work within the Silver DQ execution context.

### Short-Term (Before Gold Zone)

**R-005:** Update the spec (line 78) and logical model (line 127, 176) to match the approved small_cohort_flag derivation: `completions_count_1 IS NULL OR completions_count_1 < 30`.

**R-006:** Update the physical model derivation rule for institution_control (line 157) to match the actual code behavior (text-to-text mapping, not integer-to-text).

**R-007:** Update the spec, glossary BT-003, and data contract to clarify that cipcode in this dataset is XX.XX (5 chars), not XX.XXXX (7 chars). Add a note that the CIP-to-SOC crosswalk will require handling the 4-digit vs 6-digit CIP code mismatch.

**R-008:** Update the grain hash documentation in the spec and physical model to use `['unitid', 'cipcode', 'credential_level']` (Silver field names), matching the actual implementation.

**R-009:** Add a BT-018 term for "Institution Control Type" to close the pending business term gap.

### Medium-Term (Governance Maturity)

**R-010:** Create a golden dataset of 50-100 manually verified records. For each record, independently verify: (a) the CIP family name is correct per the NCES CIP taxonomy, (b) the institution name matches the UNITID per IPEDS, (c) the earnings and debt values match the source CSV, (d) the record_id hash can be reproduced. This is the only way to prove semantic correctness.

**R-011:** Implement a cross-artifact consistency checker that validates: (a) every column in the physical model has a matching DQ rule, (b) every DQ threshold traces to an EDA finding, (c) the spec, logical model, physical model, and glossary agree on field definitions, (d) the data contract matches the physical model.

**R-012:** Tighten the null-rate DQ thresholds (SLV-CS-016/017/018) per the chaos monkey recommendation. Current thresholds (65-70%) are too generous -- they accommodate 10% corruption without firing. Consider lowering to actual_rate + 3% (e.g., 67% for 1yr earnings where baseline is 64%).

**R-013:** Change the data contract owner from "@doc-generator" to a human-accountable owner.

---

## 5. Meta-Assessment: Can AI Agents Build Trustworthy Data Pipelines?

This pipeline is a serious test of the proposition. Here is my honest assessment:

**What the AI agents did well:**
- The EDA is genuinely excellent. It found real issues (CIP CHECK mismatch, CONTROL missing, CONTROL format mismatch) before they caused production failures. A human analyst might have missed the CIP CHECK regex discrepancy.
- The DQ rules are comprehensive and well-evidenced. 35 rules with explicit evidence chains is better than most human-built pipelines.
- The chaos monkey is an innovative verification layer that adds real value.
- The test suite covers edge cases (boundary values, NULL handling) that human developers often skip.
- The transformer code is clean, well-structured, and handles edge cases (already-normalized CIP codes, both numeric and text CONTROL values).

**Where the AI agents failed:**
- **Cross-artifact consistency.** Each artifact is good in isolation, but they contradict each other in at least 5 places. The AI agents updated downstream artifacts without propagating changes back upstream. This is the #1 governance risk.
- **The CIP family lookup gap (RISK-001)** is the most damning finding. The EDA identified the problem. The EDA told the implementer to include all 45 families. The implementer included 34 and added a fallback. The DQ rules check for NULL but not for the fallback string. Every individual artifact looks correct. The defect exists in the gap between them. This is exactly the kind of error that is hard for a human reviewer to catch because you have to cross-reference three different artifacts simultaneously.
- **SQL NULL semantics (RISK-002)** caught the DQ rules off guard. The rule was written correctly for non-NULL data but fails to detect the actual problem (all NULLs). This is a subtle technical issue that an experienced SQL developer would catch but an AI agent did not.
- **Human approval was a rubber stamp.** SLV-CS-028 was approved despite never executing successfully. This suggests the human approved the rule definition, not the rule execution results.

**Bottom line:** This pipeline is approximately 85% of the way to being trustworthy for a regulated environment. The structural governance is strong. The semantic governance has gaps. The most critical gap -- proving that derived values are CORRECT, not just NON-NULL -- requires either manual verification (golden dataset) or referential integrity rules that do not yet exist. A regulator would ask for the golden dataset. Today, this pipeline cannot produce one.

---

## Artifacts Reviewed

| Artifact | Path | Status |
|----------|------|--------|
| Spec | `/Users/jcernauske/code/bright/futureproof-data/docs/specs/silver-base-college-scorecard.md` | Reviewed -- stale in 3 areas |
| Conceptual model | `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-college-scorecard-conceptual.md` | Reviewed -- approval status inconsistent |
| Logical model | `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-college-scorecard-logical.md` | Reviewed -- small_cohort_flag definition stale |
| Physical model | `/Users/jcernauske/code/bright/futureproof-data/governance/models/silver-base-college-scorecard-physical.md` | Reviewed -- most accurate artifact; institution_control derivation stale |
| Business glossary | `/Users/jcernauske/code/bright/futureproof-data/governance/business-glossary.json` | Reviewed -- BT-003 format misleading, BT-014 incomplete, BT-018 missing |
| DQ rules | `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/silver-base-college-scorecard.json` | Reviewed -- SLV-CS-027 NULL gap, SLV-CS-028 broken, no semantic validation |
| DQ scorecard | `/Users/jcernauske/code/bright/futureproof-data/governance/dq-scorecards/silver-base-college-scorecard-scorecard.md` | Reviewed -- masks RISK-001 and RISK-002 |
| Chaos manifest | `/Users/jcernauske/code/bright/futureproof-data/governance/chaos-manifests/silver-base-college-scorecard-chaos.md` | Reviewed -- honest about gaps |
| Data contract | `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/base-college-scorecard.yaml` | Reviewed -- institution_control required/nullable mismatch |
| EDA | `/Users/jcernauske/code/bright/futureproof-data/governance/eda/silver-college-scorecard-eda.md` | Reviewed -- strongest artifact |
| Lineage | `/Users/jcernauske/code/bright/futureproof-data/governance/lineage/silver-base-college-scorecard-20260406T200000Z.json` | Reviewed -- CONTROL lineage describes non-existent data flow |
| PII scan | `/Users/jcernauske/code/bright/futureproof-data/governance/pii-scans/silver-base-college-scorecard-pii-scan.md` | Reviewed -- correct |
| Implementation | `/Users/jcernauske/code/bright/futureproof-data/src/silver/college_scorecard_transformer.py` | Reviewed -- RISK-001 (missing CIP families), RISK-003 (grain field names) |
| Tests | `/Users/jcernauske/code/bright/futureproof-data/tests/silver/test_college_scorecard_transformer.py` | Reviewed -- good coverage, no test for unknown CIP family fallback count |
