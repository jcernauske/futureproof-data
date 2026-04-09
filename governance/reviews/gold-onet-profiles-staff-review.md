## Staff Engineer Review

### Date: 2026-04-08
### Reviewer: @staff-engineer
### Status: APPROVED

### Verdict

This is solid work. The transformers are clean, the test suite is thorough with meaningful assertions, the DQ rules have real thresholds tied to EDA findings, and the golden dataset values check out against the actual warehouse tables. The two-phase HMN computation (ratio then min/max rescale) is the right call for the domain -- it produces a usable 1-10 spread rather than the cramped 3.46-4.94 range the original linear formula would have produced. The burnout score computation is straightforward and correct. I would put my name on this.

One spec discrepancy in burnout element naming (see Issues) is cosmetic -- the code and Silver data agree, the spec had stale names. Not blocking.

### Code Quality

**src/gold/onet_work_profiles.py** -- Good structure. The `derive_gold_rows` function is long but justified: it computes per-occupation metrics in Phase 1, then rescales across all occupations in Phase 2. Splitting it further would obscure the two-phase dependency. Constants are at module top. The `_normalize_context_value` helper is clean. The `_round_half_up` function exists because Python's `round()` uses banker's rounding -- the WHY comment would be helpful there but the docstring covers it adequately. Uses `is_burnout_element` flag from Silver rather than reimplementing element ID matching -- correct defensive choice.

**src/gold/onet_career_transitions.py** -- Simple enrichment transformer. Title lookup defaults to "Unknown" for missing SOCs, which is the right choice over raising. Work profile availability lookup uses `activity_profile_available` from the work profiles table. Clean.

No god functions. No unnecessary abstractions. No `except: pass`. No `utils` modules.

### Test Quality

42 tests across 2 files (30 + 12). Exceeds the 15-test minimum for consumable zone.

These are real tests. Specific observations:

- `test_burnout_score_formula`: Computes the expected value by hand (7 CX elements normalized + 2 CT elements normalized, averaged, mapped to 1-10) and asserts `== pytest.approx(7.375, abs=0.01)`. This is how you test a formula.
- `test_hmn_rescale_min_gets_1` and `test_hmn_rescale_max_gets_10`: Construct two occupations with different human ratios and assert the extremes land at 1.0 and 10.0 exactly. Tests the rescaling, not just the range.
- `test_hmn_two_phase_required`: Verifies the middle occupation gets a score strictly between 1 and 10 -- this would catch a bug where rescaling was applied per-occupation instead of across the population.
- `test_medium_confidence_high_suppression`: Constructs context rows with >5% suppression and asserts "medium" tier -- tests the threshold boundary, not just that a tier is assigned.
- `test_unknown_scale_raises`: Verifies the normalization function raises ValueError on unknown scale IDs.

No test theater. No `assert True`. No `assert len > 0` where exact values are available.

### Spec Compliance

Implementation matches the spec with documented deviations:

1. **HMN formula**: Spec says `hmn_score = 1.0 + 9.0 * human_ratio`. Implementation uses min/max rescaling of human_ratio first. This deviation was approved by human and documented in the EDA report and physical model. Correct decision -- the original formula produced a 3.46-4.94 range, which is useless for a 1-10 pentagon stat.

2. **13 of 14 human-intensive element IDs corrected**: Spec acknowledged its element IDs were likely wrong. EDA validated the corrections against actual Silver data. The 14 activities are correctly identified by element_id in the code.

3. **Burnout element names**: Spec says `4.C.3.b.7` is "Responsibility for Outcomes and Results" and `4.C.3.d.4` is "Importance of Repeating Same Tasks". Actual Silver data: `4.C.3.b.7` = "Importance of Repeating Same Tasks", `4.C.3.d.4` = "Work Schedules". Similarly, `4.C.3.a.2.a` is "Impact of Decisions on Co-workers or Company Results" in data, not "Responsibility for Others' Health and Safety" as spec states. Code comments match the data. The element IDs are correct; the spec had wrong human-readable names. Non-blocking because the code uses `is_burnout_element` flag from Silver rather than hardcoding element IDs for burnout computation.

4. **Confidence tier 772/2/24**: Spec predicted 773/1/24 from EDA. Actual is 772/2/24 due to SOC 51-2061 edge case. DQ rule GLD-ONP-019 updated to reflect actual counts. Fine.

All spec success criteria are met. Both tables exist with correct schemas, row counts, and grain integrity.

### Data Correctness Spot-Check

| Entity | Metric | Period | Pipeline Value | Reference Value | Source | Match? |
|--------|--------|--------|---------------|-----------------|--------|--------|
| Software Developers (15-1252) | hmn_score | O*NET 30.2 | 2.11 | 2.11 | Golden dataset chain | YES |
| Software Developers (15-1252) | burnout_score | O*NET 30.2 | 4.80 | 4.80 | Golden dataset chain | YES |
| Registered Nurses (29-1141) | hmn_score | O*NET 30.2 | 5.84 | 5.84 | Golden dataset chain | YES |
| Registered Nurses (29-1141) | burnout_score | O*NET 30.2 | 6.47 | 6.47 | Golden dataset chain | YES |
| Court Reporters (27-3092) | hmn_score | O*NET 30.2 | 1.00 | 1.00 | Min-anchor occupation | YES |
| Choreographers (27-2032) | hmn_score | O*NET 30.2 | 10.00 | 10.00 | Max-anchor occupation | YES |
| Career transition 15-1252->15-1299 | source_title | O*NET 30.2 | Software Developers | Software Developers | Golden dataset | YES |
| Career transition 15-1252->15-1299 | source_has_work_profile | O*NET 30.2 | True | True | Golden dataset | YES |

Aggregate checks verified:
- Work profiles: 798 rows, 24 null HMN, 24 null burnout, HMN range 1.0-10.0, confidence 772/2/24
- Career transitions: 15,944 rows, 0 self-references, 0 null titles

### DQ Rules

43 rules, all passing. Good coverage across uniqueness, validity, volume, completeness, consistency. P0 rules cover grain uniqueness, row counts, score ranges, null counts, static field values, cross-table referential integrity. The chaos monkey achieved 86-91% detection rate across 5 cycles, which is reasonable -- the 2 never-firing rules (GLD-ONP-010, GLD-ONP-011) are population-level aggregate checks that correctly resist row-level corruption.

Adversarial auditor flagged 10 risks. The 2 CRITICAL risks (activity classification debate, min/max rescaling fragility) are methodological concerns, not implementation bugs. They should be tracked as technical debt for v2 but do not block this spec.

### Governance Artifacts

- Golden dataset: 4 verification chains with derivation steps. Values match warehouse.
- Data contracts: Both complete with schema, quality thresholds, lineage, consumer sections, CDE rationale.
- Chaos manifest: 5 cycles, escalating corruption, honest gap analysis.
- Adversarial audit: 10 risks identified with severity and recommendations. Not boilerplate.
- Pipeline state: All 20 steps completed or justified-skip. No orphan steps.
- Models: Conceptual, logical, physical all present and consistent with implementation.

### Issues

| # | Severity | File | Issue | Required Fix |
|---|----------|------|-------|-------------|
| 1 | LOW | docs/specs/gold-onet-profiles.md | Spec burnout element table has wrong human-readable names for 4.C.3.b.7, 4.C.3.d.4, 4.C.3.a.2.a. Code and Silver data agree with each other. | Non-blocking. Spec should be updated for accuracy but implementation is correct. |
| 2 | INFO | governance/reviews/gold-onet-profiles-adversarial-audit.md | Adversarial audit header references "consumable.onet_burnout_elements (6,984 rows)" -- this table does not exist. Likely a copy artifact. | Non-blocking cosmetic. |

### What's Acceptable

Clean separation between derivation logic and I/O. Two-phase HMN computation handles the min/max rescaling correctly. Test helpers construct realistic 41-activity and 14-context-element fixtures rather than trivial single-row mocks. The burnout formula test computes expected values by hand. Governance artifacts reference real tables, real thresholds, real rationale.
