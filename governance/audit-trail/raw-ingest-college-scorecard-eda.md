# Audit Trail: EDA — raw.college_scorecard

**Date:** 2026-04-05  
**Agent:** @data-analyst  
**Spec:** raw-ingest-college-scorecard  
**Pipeline Step:** Bronze Zone — Step 3 (Post-Ingest EDA + Domain Discovery)

## What Was Analyzed

Exploratory data analysis of the `raw.college_scorecard` Iceberg table containing 69,947 rows of bachelor's-degree-level College Scorecard field-of-study data. This is the first analysis of this data source, so domain discovery was performed in addition to standard EDA.

## Key Findings

1. **CRITICAL: md_earn_wne is 100% null.** This field contains no data whatsoever. Root cause investigation is needed before silver zone processing. Possible causes: column name mismatch, field not present in field-of-study file, or complete privacy suppression.

2. **CIP codes use non-standard format.** All codes are 4-digit strings without the standard dot separator (e.g., "5202" instead of "52.02"). Silver zone transformation required.

3. **Privacy suppression drives null rates.** Earnings and debt fields are 60-64% null, strongly correlated with low completions counts. Programs with ipedscount1 >= 30 have 88.7% earnings availability vs. 6.8% for ipedscount1 1-9.

4. **No grain duplicates.** All 69,947 rows have unique unitid x cipcode x credlev combinations.

5. **Data quality is generally strong** for non-suppressed fields. All identity/grain fields are 100% complete. Earnings distributions are plausible for U.S. bachelor's degree outcomes.

## Domain Discovery Conclusions

- **Domain:** U.S. higher education — program-level career outcomes
- **Grain:** Institution x Program x Credential Level (bachelor's only in this load)
- **Entities:** 2,559 institutions, 390 CIP programs, 69,947 institution-program combinations
- **Temporal pattern:** Single snapshot load (2026-04-06)
- **Key taxonomy:** CIP codes (Classification of Instructional Programs), IPEDS institution IDs

## Threshold Recommendations

See full report at `governance/eda/raw-college-scorecard-eda.md` for detailed, evidence-based threshold recommendations covering:
- Row count bounds (60k-80k)
- Completeness thresholds per field (0% for grain fields, 65-70% max null for earnings/debt)
- Value range bounds for all numeric fields
- Format validation patterns for cipcode
- Statistical distribution monitors for earnings and debt means

## Output

- EDA Report: `governance/eda/raw-college-scorecard-eda.md`
