# Audit Trail: PII Scan - crosswalk-cip-soc

**Timestamp:** 2026-04-08
**Agent:** @pii-scanner
**Spec:** docs/specs/crosswalk-cip-soc.md
**Dataset:** CIP2020_SOC2018_Crosswalk.xlsx (NCES/BLS CIP-to-SOC crosswalk)

## What Was Scanned

- **Source file:** data/raw/xlsx_cache/CIP2020_SOC2018_Crosswalk.xlsx
- **Primary sheet:** CIP-SOC (6,097 data rows, 4 columns: CIP2020Code, CIP2020Title, SOC2018Code, SOC2018Title)
- **Additional sheet reviewed:** Unmatched SOC Codes (180 rows, same 4-column structure, all CIP = 99.9999 / NO MATCH)
- **Unique CIP codes:** 2,143
- **Unique SOC codes:** 868
- **Silver derived fields reviewed:** record_id, cip_family, soc_major_group, has_scorecard_match, has_bls_match, has_onet_match, match_quality

## Detection Methods Used

1. **Field name heuristics** -- checked all column names for PII-indicative patterns (name, ssn, dob, address, email, phone, account). None found.
2. **Content pattern analysis** -- sampled data values across the full range of rows. All values are taxonomy codes (XX.XXXX, XX-XXXX) and standardized category names (program titles, occupation titles).
3. **Domain context calibration** -- reviewed governance/domain-context.md PII Expectations sections for all three source domains (College Scorecard, BLS OOH, O*NET). All confirm no PII.
4. **Spec review** -- spec marks @pii-scanner as conditionally skippable with justification "Public taxonomy crosswalk. No individual data."

## False Positive Decisions

| Field | Potential False Positive | Decision | Rationale |
|-------|------------------------|----------|-----------|
| CIP2020Title | Program names could trigger name detection | Confirmed non-PII | Standardized NCES taxonomy labels (e.g., "Agricultural Economics"), not personal names |
| SOC2018Title | Occupation names could trigger name detection | Confirmed non-PII | Standardized BLS taxonomy labels (e.g., "Software Developers"), not personal names |

## Classification Decisions

All fields classified as containing zero PII. This is a public-domain government taxonomy publication with no individual-level data of any kind.

## Outcome

- **PII found:** 0 instances
- **Report written to:** governance/pii-scans/crosswalk-cip-soc-pii-scan.md
- **Recommendation:** No PII remediation, masking, or RLS policies needed for privacy reasons
