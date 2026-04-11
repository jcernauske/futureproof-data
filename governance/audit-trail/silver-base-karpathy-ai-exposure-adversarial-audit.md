# Adversarial Audit Report: silver-base-karpathy-ai-exposure (Silver Zone)

**Auditor:** @adversarial-auditor
**Date:** 2026-04-09
**Table:** base.karpathy_ai_exposure (419 rows)
**Scope:** All Silver zone artifacts

---

## Risk Register

### RISK-01: SLV-KAI-022 broken in shadow mode (CRITICAL)
Cross-table referential integrity rule errors on every chaos monkey cycle. The rule validates bls_match=true rows exist in base.bls_ooh, but shadow namespace doesn't include the BLS table. Passes in production but untested adversarially.

### RISK-02: Title matching false positive risk (HIGH)
Bidirectional substring matching (`if bls_title in title or title in bls_title`) produces uncontrolled false positives. No negative test cases exist. ~36 rows (8.6%) produced by this logic.

### RISK-03: Row count discrepancy 412 predicted vs 419 actual (HIGH)
EDA predicted ~412 rows, actual is 419. 7-row delta unexplained.

### RISK-04: Broad expansion inherits scores without domain validation (MEDIUM)
110 rows (26%) inherit parent exposure scores. All sub-specialties get identical scores, which may not reflect actual AI exposure differences.

### RISK-05: No golden dataset (MEDIUM)
No point-verification of specific row values. Structural DQ only.

### RISK-06: Domain context factual error (MEDIUM)
Claims "All 46 broad codes have at least one detailed BLS match" but EDA documents 6 that don't. Actual count is 50 broad codes (40 expandable + 4 broad-to-broad + 6 unmatched).

### RISK-07: Synthetic test data for title matching (MEDIUM)
Tests use 16 hand-picked BLS rows vs 832 in production. More BLS titles = more false positive candidates.

### RISK-08: No freshness DQ rules (LOW)
No validation of source_load_date or ingested_at temporal bounds.

### RISK-09: Low chaos monkey detection rate 13-22% (LOW)
11 of 23 rules never fired across any cycle.

### RISK-10: AI-authored EDA prediction accuracy (LOW)
EDA predictions close but not exact (412 vs 419).

---

## Recommendations

**P1 (Must-fix before Gold):**
1. Fix SLV-KAI-022 for reliable cross-table execution
2. Audit all title-match assignments manually (~36 rows)
3. Reconcile 419 vs 412 row count

**P2 (Should-fix):**
4. Create golden dataset (20-30 rows)
5. Add negative title-match tests
6. Correct domain context broad code claims
7. Add freshness DQ rules

---

## Assessment
For hackathon MVP: ADEQUATE. Structural governance is comprehensive. Semantic validation gaps exist but are inherent to LLM-generated source data. Staff engineer should review P1 items.
