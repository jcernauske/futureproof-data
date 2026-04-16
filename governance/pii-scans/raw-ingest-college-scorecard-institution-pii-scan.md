# PII Scan Report: raw-ingest-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @pii-scanner
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Domain Context:** domain/raw-ingest-college-scorecard-institution-context.md
**Ingestor:** src/raw/college_scorecard_institution_ingestor.py
**Domain:** Higher Education Outcomes — Institution-Level Cost of Attendance
**Records Scanned:** ~3,039 institution rows (post PREDDEG=3 OR ICLEVEL=1 filter)
**PII Instances Found:** 0

---

## Overall Classification: NO PII

This is a **public federal dataset** published by the U.S. Department of Education (College Scorecard, Most-Recent-Cohorts-Institution.csv). Every field in the Bronze schema is either (a) an institution-level aggregate statistic, (b) an institution identifier, or (c) institution metadata / classification code. No individual-level data is present. No PII is possible from this source.

**Source provenance:**
- **Publisher:** U.S. Department of Education (ed.gov / College Scorecard)
- **License:** U.S. Government Work — public domain
- **Download URL:** `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Institution.csv`
- **Upstream suppression:** All individual student privacy protections are applied upstream by the Department of Education via IPEDS aggregation before publication
- **FERPA:** Not directly applicable — student-level data is already aggregated/suppressed at source

---

## Field-by-Field Classification

All fields below were scanned. All are classified as **Level 1 — Public** with **No PII**.

| # | Field (Bronze) | CSV Source | Type | PII Category | Sensitivity | Rationale |
|---|---------------|-----------|------|-------------|-------------|-----------|
| 1 | unitid | UNITID | long | None | Level 1 — Public | 6-digit IPEDS institutional identifier. Identifies an institution, not a person. Publicly published by NCES. |
| 2 | instnm | INSTNM | string | None | Level 1 — Public | Institution name (e.g., "Massachusetts Institute of Technology"). Organization name, not a personal name. Already fully public. |
| 3 | stabbr | STABBR | string | None | Level 1 — Public | 2-letter state abbreviation for the institution's state (e.g., "MA"). Aggregate geographic identifier at state granularity — not an address, not personal. |
| 4 | control | CONTROL | int | None | Level 1 — Public | Institution governance classification (1=Public, 2=Private nonprofit, 3=Private for-profit). Institutional metadata. |
| 5 | preddeg | PREDDEG | int | None | Level 1 — Public | Predominant degree awarded (0=Not classified, 1=Certificate, 2=Associate's, 3=Bachelor's, 4=Graduate). Institutional metadata. |
| 6 | costt4_a | COSTT4_A | double | None | Level 1 — Public | Average cost of attendance (academic-year programs). Institution-level aggregate across all students. |
| 7 | costt4_p | COSTT4_P | double | None | Level 1 — Public | Average cost of attendance (program-year programs). Institution-level aggregate. |
| 8 | npt4_pub | NPT4_PUB | double | None | Level 1 — Public | Average net price for public institutions. Aggregate across students. |
| 9 | npt4_priv | NPT4_PRIV | double | None | Level 1 — Public | Average net price for private institutions. Aggregate across students. |
| 10 | npt41_pub | NPT41_PUB | double | None | Level 1 — Public | Aggregate average net price for families earning $0–$30K at public institutions. Bucketed aggregate — not individual. |
| 11 | npt42_pub | NPT42_PUB | double | None | Level 1 — Public | Aggregate net price, $30K–$48K income bracket, public. |
| 12 | npt43_pub | NPT43_PUB | double | None | Level 1 — Public | Aggregate net price, $48K–$75K income bracket, public. |
| 13 | npt44_pub | NPT44_PUB | double | None | Level 1 — Public | Aggregate net price, $75K–$110K income bracket, public. |
| 14 | npt45_pub | NPT45_PUB | double | None | Level 1 — Public | Aggregate net price, $110K+ income bracket, public. |
| 15 | npt41_priv | NPT41_PRIV | double | None | Level 1 — Public | Aggregate net price, $0–$30K income bracket, private. |
| 16 | npt42_priv | NPT42_PRIV | double | None | Level 1 — Public | Aggregate net price, $30K–$48K income bracket, private. |
| 17 | npt43_priv | NPT43_PRIV | double | None | Level 1 — Public | Aggregate net price, $48K–$75K income bracket, private. |
| 18 | npt44_priv | NPT44_PRIV | double | None | Level 1 — Public | Aggregate net price, $75K–$110K income bracket, private. |
| 19 | npt45_priv | NPT45_PRIV | double | None | Level 1 — Public | Aggregate net price, $110K+ income bracket, private. |
| 20 | tuitionfee_in | TUITIONFEE_IN | double | None | Level 1 — Public | Published in-state tuition and fees. Institutional published rate. |
| 21 | tuitionfee_out | TUITIONFEE_OUT | double | None | Level 1 — Public | Published out-of-state tuition and fees. Institutional published rate. |
| 22 | roomboard_on | ROOMBOARD_ON | double | None | Level 1 — Public | Published on-campus room and board rate. Institutional aggregate. |
| 23 | roomboard_off | ROOMBOARD_OFF | double | None | Level 1 — Public | Published off-campus room and board estimate. Institutional aggregate. |
| 24 | booksupply | BOOKSUPPLY | double | None | Level 1 — Public | Published estimate of annual books and supplies cost. Institutional aggregate. |
| 25 | ingested_at | (metadata) | timestamp | None | Level 1 — Public | Pipeline metadata — ingestion timestamp. Not source data. |
| 26 | source_url | (metadata) | string | None | Level 1 — Public | Pipeline metadata — the public download URL. Not source data. |
| 27 | source_method | (metadata) | string | None | Level 1 — Public | Pipeline metadata — literal "bulk_csv_download". Not source data. |
| 28 | load_date | (metadata) | date | None | Level 1 — Public | Pipeline metadata — load date. Not source data. |

---

## Detection Methods Used

1. **Spec + domain context review** — confirmed source provenance (public federal dataset) and documented absence of individual-level data
2. **Field-by-field review of ingestor COLUMN_MAP** — each of the 24 source fields classified against the PII category framework
3. **Grain verification** — grain is institution (UNITID), not person; this structurally rules out personal data
4. **Cross-reference with sibling scans** — aligns with `raw-ingest-college-scorecard-pii-scan.md` (field-of-study file from same source), which also found no PII

---

## Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|-----------------|
| Level 1 — Public | 28 | All fields (24 source + 4 metadata) |
| Level 2 — Internal | 0 | — |
| Level 3 — Confidential | 0 | — |
| Level 4 — Restricted | 0 | — |

---

## False Positive Candidates

None. Fields that could superficially trigger PII heuristics were evaluated:

| Field | Could Look Like | Why It's Not PII |
|-------|-----------------|------------------|
| instnm | Personal name (NER) | This is an organization name ("MIT", "Ohio State University"). Field name `instnm` and source semantics confirm it is institution-level. |
| stabbr | Address component | 2-letter state code at institution level. Not a street address, not personal, not geolocation. Published alongside the institution for ~3,039 rows, not tied to any individual. |
| unitid | Identifier | 6-digit integer IPEDS institutional ID — identifies a school, not a person. Publicly cataloged by NCES. |
| npt41_pub … npt45_priv | Financial / income data | These are **aggregate averages by income bracket**, not individual income records. Each value is computed across many students per institution per bracket. No individual is linkable. |
| costt4_a / tuitionfee_in / etc. | Financial data | Institutional published rates and aggregates — not individual financial records. |

---

## Regulatory Implications

| Regulation | Applies? | Rationale |
|-----------|----------|-----------|
| FERPA | No | Student-level privacy protections were applied upstream by the Department of Education through IPEDS aggregation before publication. This pipeline receives only aggregate institution-level data. |
| GDPR | No | No personal data (no identifiable natural persons). GDPR scope is not triggered. |
| CCPA / CPRA | No | No personal information about California consumers. Institutional aggregates only. |
| HIPAA | No | Not health data. |
| PCI DSS | No | No payment account data. |
| Higher Education Act (HEA) | Source authority only | HEA mandates institutional reporting to IPEDS which feeds College Scorecard. FutureProof is a downstream consumer of public data — no reporting obligation. |

---

## Recommendations for @policy-engineer

- **No RLS policies required** for `raw.college_scorecard_institution`. All fields are Level 1 — Public.
- **No column masking required.** No field is sensitive.
- **No access logging required beyond standard pipeline audit.** Public data.
- **Standard pipeline governance applies** — data contracts, DQ rules, lineage. These are quality/integrity controls, not privacy controls.
- **Downstream consistency:** The Silver (`base.college_scorecard_institution`) and Gold (`consumable.career_outcomes` enrichment) layers inherit the Level 1 — Public classification. No upgrade in sensitivity occurs through transformation.

---

## Conclusion

`raw.college_scorecard_institution` contains **no PII**. All 24 source fields plus 4 pipeline metadata fields are classified **Level 1 — Public**. This matches the domain-context.md assessment (PII Assessment: NONE) and is consistent with the scan of the sibling field-of-study source from the same provider.

**Scan confidence:** High. Source is well-documented, publicly licensed, and structurally aggregate (institution grain). There is no ambiguity.

**Recommended next step:** Proceed with Bronze ingest. No blocking PII concerns.
