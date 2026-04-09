# Adversarial Audit: gold-onet-profiles

**Auditor:** @adversarial-auditor
**Date:** 2026-04-08
**Spec:** gold-onet-profiles
**Tables:** consumable.onet_work_profiles (798 rows), consumable.onet_burnout_elements (6,984 rows)
**Zone:** Gold (Consumable)

## Summary

10 risks identified across 4 severity levels: 2 CRITICAL, 3 HIGH, 3 MEDIUM, 2 LOW. Must-fix items should be resolved before production deployment.

## CRITICAL Findings

### RISK-01: "Making Decisions and Solving Problems" Classification Debatable for AI

The activity "Making Decisions and Solving Problems" is classified as human-intensive in the AI/human activity split, but modern LLMs demonstrably perform well on structured decision-making and problem-solving tasks. This classification directly inflates hmn_score for occupations where this activity has high importance.

**Recommendation:** Review the human-intensive activity list with domain experts; consider reclassifying or weighting this activity as mixed.

### RISK-02: Min/Max Rescaling Fragility

The hmn_score uses min/max rescaling anchored to the current dataset extremes (Court Reporters at the low end, Choreographers at the high end). Future O*NET releases that shift these anchor occupations would cause score drift across all occupations without any underlying change in work characteristics.

**Recommendation:** Document anchor occupations explicitly. Add a DQ rule that alerts when the min/max anchor occupations change between pipeline runs.

## HIGH Findings

### RISK-03: Software Developers HMN=2/10 Will Face Credibility Challenges

Software Developers (15-1252) receive hmn_score_rounded = 2, which will appear counterintuitive to users who perceive software development as highly creative and human-driven. This is technically correct given the activity-importance methodology, but will undermine user trust.

**Recommendation:** Add Gemma narrative context explaining that hmn_score measures reliance on the 14 designated human-intensive activities, not general human skill requirement.

### RISK-04: No DQ Rule Verifies Formula Correctness (Chaos Monkey Gap)

No DQ rule independently verifies that hmn_score = 1.0 + 9.0 * human_ratio by recomputing from source data. If the formula implementation drifts, existing DQ rules (range checks, null checks) would not detect the error.

**Recommendation:** Add a golden dataset spot-check rule that recomputes hmn_score for at least 3 known occupations from their raw activity importance values.

### RISK-05: Equal Burnout Weighting Lacks Research Basis

All 9 burnout Work Context elements receive equal weight in the burnout_score composite. No published occupational health research supports equal weighting. Time Pressure and Consequence of Error likely contribute more to burnout than Physical Proximity or Exposed to Contaminants.

**Recommendation:** Document the equal-weighting assumption explicitly as a known limitation. Consider literature-based weighting in a future version.

## MEDIUM Findings

### RISK-06: No Freshness DQ Rules for source_load_date or promoted_at

No DQ rule validates that source_load_date and promoted_at are recent. Stale data could be served without detection.

### RISK-07: Burnout Element Normalization Assumes Static Scale Ranges

The burnout element normalization uses hardcoded O*NET scale ranges. If O*NET changes scale definitions in a future release, normalized values would be incorrect.

### RISK-08: Staff Review Artifact Pending

Expected -- next pipeline step. Not a defect.

## LOW Findings

### RISK-09: top_human_activities JSON Format Not Schema-Validated

The JSON arrays in top_human_activities and burnout_drivers are not validated against a JSON schema by any DQ rule.

### RISK-10: No Record ID Hash Integrity Validation Rule

No DQ rule verifies that record_id matches the expected hash of bls_soc_code.

## Strengths

- Comprehensive DQ rule set (43 rules, 100% pass rate)
- Clear confidence_tier derivation logic
- Proper null handling for 24 partial-data occupations
- Well-documented lineage from Silver source tables
