# Audit Trail: DQ Rules for raw-ingest-bls-ooh

**Date:** 2026-04-07
**Agent:** @dq-rule-writer
**Spec:** raw-ingest-bls-ooh
**Zone:** Bronze/Raw
**Evidence Source:** governance/eda/raw-bls-ooh-eda.md
**Domain Context:** governance/domain-context.md (BLS OOH section, lines 369-528)
**Output:** governance/dq-rules/raw-ingest-bls-ooh.json

---

## Rules Written (18 total)

### Validity (7 rules)
| Rule ID | Name | Priority | Rationale |
|---------|------|----------|-----------|
| RAW-OOH-001 | SOC code format XX-XXXX | P0 | EDA: 10/10 match pattern. SOC 2018 standard. Structural constraint. |
| RAW-OOH-002 | SOC code not summary (no XX-0000) | P0 | EDA: ingestor filters 1 summary row correctly. ~22 expected in full XLSX. |
| RAW-OOH-005 | Education code range 1-8 | P0 | BLS defines exactly 8 levels. EDA sample shows 3 of 8. |
| RAW-OOH-006 | Work experience code range 1-3 | P0 | BLS defines exactly 3 levels. EDA sample shows 2 of 3. |
| RAW-OOH-007 | Training code range 1-6 | P0 | BLS defines exactly 6 levels. EDA sample shows 4 of 6. |
| RAW-OOH-011 | Employment current must be positive | P0 | EDA min 36,600. Domain-impossible to have zero/negative. |
| RAW-OOH-012 | Employment projected must be positive | P0 | EDA min 38,500. Same domain logic. |
| RAW-OOH-013 | Openings annual avg must be positive | P0 | EDA min 2,100. Even declining occupations have replacement openings. |
| RAW-OOH-016 | Median wage range $20k-$239,200 | P1 | EDA range $33,530-$239,200. Floor from federal minimum wage; ceiling from BLS cap. |

### Uniqueness (1 rule)
| Rule ID | Name | Priority | Rationale |
|---------|------|----------|-----------|
| RAW-OOH-003 | Grain uniqueness: soc_code | P0 | EDA: 0 duplicates in 10 rows. Grain is one row per SOC code. |

### Consistency (2 rules)
| Rule ID | Name | Priority | Rationale |
|---------|------|----------|-----------|
| RAW-OOH-004 | Wage cap flag consistency | P0 | EDA: 100% consistent in sample. Domain context marks as HARD rejection. |
| RAW-OOH-018 | Employment change consistency | P1 | EDA: verified in all 10 rows. +/- 1000 tolerance for rounding. |

### Completeness (3 rules)
| Rule ID | Name | Priority | Rationale |
|---------|------|----------|-----------|
| RAW-OOH-008 | Median wage null rate < 5% | P1 | EDA: 10% null in sample (over-represents N/A). Expect 2-4% in full data. |
| RAW-OOH-009 | Occupation title completeness 0% null | P0 | EDA: 0% null. Required field. |
| RAW-OOH-014 | soc_code completeness 0% null | P0 | EDA: 0% null. Required grain field. |
| RAW-OOH-015 | median_wage_capped completeness 0% null | P0 | EDA: 0% null. Required boolean field. |

### Volume (1 rule)
| Rule ID | Name | Priority | Rationale |
|---------|------|----------|-----------|
| RAW-OOH-010 | Row count 750-900 | P0 | EDA: BLS documents ~832 occupations. 10% variation buffer. |

### Freshness (1 rule)
| Rule ID | Name | Priority | Rationale |
|---------|------|----------|-----------|
| RAW-OOH-017 | load_date within 30 days | P1 | Consistent with RAW-CS-017 pattern. |

---

## Rules Considered But Not Written

### Employment change allows negative values (intentionally NOT a rule)
**Rationale:** EDA notes: "All values positive in sample. Full dataset will contain negative values for declining occupations. This field can legitimately be negative." Domain context confirms: "MUST allow negative values for employment_change and employment_change_pct." Writing a positivity rule for these fields would produce false positives on the full dataset. This is explicitly documented to prevent future rule writers from adding one.

### Employment change percentage allows negative values (intentionally NOT a rule)
**Rationale:** Same as above. EDA notes expected range of roughly -30% to +30% in full dataset.

### Code-to-text determinism (education_code <-> education_typical, etc.)
**Rationale:** Considered writing a consistency rule verifying that the same code always maps to the same text label. EDA confirms 100% consistency in the 10-row sample. Deferred to Silver zone rules because: (1) the raw zone has only 10 rows making the check trivial, and (2) this is fundamentally a business rule better validated after more data is present. Will be written as a Silver zone rule.

### Statistical distribution rules (mean wage range, capped wage rate, negative change rate)
**Rationale:** EDA provides preliminary statistical expectations but explicitly marks them as based on a 10-row sample. These are P3 monitoring rules that should be written after the full ~832-row dataset is ingested and profiled. Writing them now with sample-biased thresholds would produce false alerts.

### Employment current/projected/openings completeness (0% null)
**Rationale:** Not written as separate rules because: (1) the spec marks these as "no" (not required), and (2) while EDA shows 0% null in sample, the full dataset might have edge cases. The positivity rules (RAW-OOH-011/012/013) already catch any populated-but-invalid values. If completeness monitoring is needed, it should be added after full dataset profiling.

---

## Threshold Methodology

All thresholds are evidence-based, citing the EDA report and domain context document:

- **P0 rules (100% pass):** Used only where EDA shows 0 violations AND domain logic confirms the constraint is absolute (structural or domain-impossible). Examples: SOC format, grain uniqueness, code ranges, wage cap consistency.
- **P1 rules (99%+ pass):** Used where EDA shows high conformance but domain context identifies known edge cases. Examples: wage null rate (known N/A occupations), wage range (known floor/ceiling).
- **No P2/P3 rules written** in this batch. Statistical/distribution rules deferred until full dataset is available.

## Notes

- All thresholds labeled PRELIMINARY in the EDA must be re-validated against the full ~832-row dataset.
- The row count rule (RAW-OOH-010) will fail against the current 10-row sample data. This is expected and should be relaxed during development or skipped until full data is loaded.
- The DQ runner has not been executed because the table `raw.bls_ooh` may not yet exist. Execution should be performed by @dq-engineer after the ingestor has run.
