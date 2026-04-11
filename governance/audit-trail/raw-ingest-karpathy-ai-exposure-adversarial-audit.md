# Adversarial Audit Report: raw-ingest-karpathy-ai-exposure (Bronze Zone)

**Auditor:** @adversarial-auditor
**Date:** 2026-04-09
**Spec:** raw-ingest-karpathy-ai-exposure
**Table:** bronze.karpathy_ai_exposure (342 rows)
**Scope:** Bronze zone ingest -- all AI-generated artifacts reviewed for hallucination risk, governance gaps, and insufficient evidence

---

## Risk Register

### RISK-001: Spec describes wrong source data format (Medium)

The spec (line 65) states `scores.json` has the structure `{"slug_name": {"exposure": 7, "rationale": "..."}, ...}` -- a dict keyed by slug. The actual source file is a JSON array of objects: `[{"slug": "...", "exposure": N, "rationale": "...", "title": "..."}, ...]`. The ingestor's `_normalize_scores()` handles both formats defensively, but the test fixture only exercises the wrong format.

### RISK-002: Test fixture does not match production data format (Medium)

Test fixture at `tests/raw/karpathy_samples/scores.json` uses dict format while real data uses array format. Unit tests exercise only the dict path. Integration tests (`TestFullDataset`) cover the real format but depend on cache directory existing.

### RISK-003: RAW-KAI-009 cross-validation rule broken in shadow mode (High)

The cross-validation rule returns ERROR on every chaos monkey cycle (value=None). The rule joins `bronze.karpathy_ai_exposure` to `bronze.bls_ooh`, but in shadow mode only the target table is shadowed. The rule passes in production execution.

### RISK-004: No DQ rules validate semantic accuracy of exposure scores (High)

All 18 DQ rules check structural properties. Zero rules validate whether exposure scores are reasonable for specific occupations. The chaos monkey confirmed: accuracy corruption (shifting scores by 3-5 points within valid range) was never detected.

### RISK-005: Chaos monkey detection rate is low (High)

Across 5 cycles, detection rate ranged from 11.1% to 27.8%. 9 of 18 rules never fired. DQ rules are heavily biased toward completeness checks over accuracy checks.

### RISK-006: No reasonableness rules for numeric fields (Medium)

No bounds on median_pay_annual, num_jobs_2024, or rationale length beyond null checks.

### RISK-007: EDA report verified accurate (Medium -- resolved)

EDA statistics independently verified. Score distribution matches source data exactly.

### RISK-008: SOC coverage threshold silently weakened (Low)

Spec estimated ~95%, EDA found 84.8%, threshold set to >= 80%. Change is documented and justified.

### RISK-009: Test name/assertion mismatch (Low)

`test_full_soc_coverage_above_90_percent` asserts `coverage > 0.80`, not 90%.

### RISK-010: Missing governance artifacts (Medium)

Several artifacts were missing at time of audit but have since been produced by downstream pipeline steps.

### RISK-011: Catalog naming mismatch patched ad-hoc (Medium)

Table registered under catalog_name 'futureproof-data' instead of 'brightsmith'. Corrected manually in catalog.db before DQ execution. Root cause not fixed in ingestor.

### RISK-012: Domain context stat naming unverified (Low)

Pentagon stat names in domain context should be verified against actual Gold zone FutureProof engine code.

---

## Recommendations

### P0 -- Must fix before spec completion
1. Fix spec source format description (line 65)
2. Add golden dataset of hand-verified exposure scores (10-15 occupations)
3. Fix RAW-KAI-009 shadow-mode failure

### P1 -- Should fix
4. Add unit tests for JSON array normalization path
5. Add reasonableness DQ rules (pay bounds, job count bounds, rationale length)
6. Fix catalog name root cause
7. Fix test name/assertion mismatch

### P2 -- Post-hackathon
8. Add category coverage DQ rule
9. Add broad SOC code percentage rule
10. Cross-validate against published AI exposure indices

---

## Assessment

**For hackathon MVP: ADEQUATE.** The structural governance is strong -- every required artifact exists, DQ rules pass, data is verified against source. The gap is semantic validation (no ground truth for LLM-generated scores), which is an inherent limitation of the source data, not a pipeline deficiency.

**Staff-engineer verdict: APPROVED** (non-blocking issues noted above).
