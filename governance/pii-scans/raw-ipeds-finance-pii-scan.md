# PII Scan Report: raw-ipeds-finance

**Date:** 2026-04-30
**Agent:** @pii-scanner
**Spec:** docs/specs/full-pipeline-ipeds-finance.md
**Domain Context:** governance/domain-context.md (IPEDS Finance section, 2026-04-30 entry)
**Target Table:** `bronze.ipeds_finance` (logically `raw.ipeds_finance` per spec §4)
**Domain:** Higher Education Outcomes — Institution-Level Public Finance
**Records Scanned:** ~2,675 institution rows (post `ICLEVEL=1 AND HLOFFER>=5` filter, FY23)
**PII Instances Found:** 0

---

## Overall Classification: NO PII

This is **public-domain federal survey data** published by the U.S. Department of Education / National Center for Education Statistics (NCES) via the Integrated Postsecondary Education Data System (IPEDS). The schema is institution-level only — every row is an institutional aggregate keyed by UNITID, and there is no individual-level data path through the ingest. No PII is possible from this source under the v1.3-locked column list.

**Source provenance:**
- **Publisher:** U.S. Department of Education / NCES / IPEDS
- **License:** U.S. Government Work — public domain
- **Surveys consumed:** IPEDS Finance (F1A public/GASB, F2 private nonprofit/FASB, F3 for-profit), EFIA (12-Month Instructional Activity), HD (Header / Institutional Characteristics)
- **Acquisition method:** Bulk CSV download per form, UNION of three finance forms, LEFT JOIN EFIA on UNITID, filtered via HD `ICLEVEL=1 AND HLOFFER>=5`
- **Upstream privacy posture:** All data is published at institution grain by NCES — no student-level, employee-level, donor-level, or transactional data is published in any of the source files. Bureau-imputed values (`X*` flag columns) are themselves an institution-level statistical operation by NCES, not a re-identification surface.
- **FERPA:** Not applicable — no student records are present in any source file.
- **GLBA / financial-account exposure:** Not applicable — `endowment_value`, `instruction_expenses`, `institutional_support_expenses` are institution-level GAAP-reported aggregates, not bank or account numbers.

---

## Field-by-Field Classification

All 8 v1.3-locked columns plus the 4 provenance columns were scanned. All are classified as **Level 1 — Public** with **No PII**.

| # | Field (Bronze) | Source Survey | Type | PII Category | Sensitivity | Rationale |
|---|---------------|---------------|------|-------------|-------------|-----------|
| 1 | unitid | IPEDS HD / Finance | long | None | Level 1 — Public | 6-digit IPEDS institutional identifier. Identifies an institution, not a person. Stable, public, authoritative. |
| 2 | institution_name | IPEDS HD (`INSTNM`) | string | None — organization name | Level 1 — Public | Institution name (e.g., "Indiana University-Bloomington"). Organization name, not a personal name. Already fully public via IPEDS. **Most-likely false-positive surface for naive NER scanners — confirmed not PII.** |
| 3 | report_form | (derived) | string | None | Level 1 — Public | Discriminator literal (`F1A` / `F2` / `F3`) — survey instrument tag, not data about a person or institution beyond GAAP reporting framework. |
| 4 | fiscal_year | (derived) | int | None | Level 1 — Public | Reporting cycle (e.g., 2023). Calendar metadata. |
| 5 | institutional_support_expenses | F1C071 / F2E061 / F3E03C1 | double | None | Level 1 — Public | Institution-level GAAP expense aggregate. Dollar total, not an account, not transactional. |
| 6 | instruction_expenses | F1C011 / F2E011 / F3E011 | double | None | Level 1 — Public | Institution-level GAAP expense aggregate. Dollar total, not an account, not transactional. |
| 7 | endowment_value | F1H02 / F2H02 / (NULL on F3) | double | None | Level 1 — Public | Institution-level balance-sheet aggregate. Total endowment value, not a fund-level or donor-level breakdown. F3 rows are structurally NULL (no F3H family). |
| 8 | total_fte_enrollment | EFIA (`FTEUG + FTEGD + FTEDPP`, NULL-safe) | double | None | Level 1 — Public | Institution-level enrollment count expressed as full-time-equivalent. Aggregate, not a roster. |
| 9 | source_url | (metadata) | string | None | Level 1 — Public | Pipeline metadata — public NCES download URL(s). Not source data. |
| 10 | source_method | (metadata) | string | None | Level 1 — Public | Pipeline metadata — literal "bulk_csv_download". Not source data. |
| 11 | load_date | (metadata) | date | None | Level 1 — Public | Pipeline metadata — ingestion date. Not source data. |
| 12 | ingested_at | (metadata) | timestamp | None | Level 1 — Public | Pipeline metadata — ingestion timestamp. Not source data. |

---

## Detection Methods Used

1. **Spec + domain-context review** — confirmed v1.3-locked column list (8 analytical columns + 4 provenance) matches the institution-grain finance/EFIA/HD schema documented in `governance/domain-context.md` (2026-04-30 IPEDS Finance entry) and `docs/specs/full-pipeline-ipeds-finance.md` §4 / §6.
2. **Grain verification** — grain is one row per `(UNITID, fiscal_year)`. This structurally precludes student, employee, donor, or transactional data.
3. **String-column inventory** — only two string columns exist: `institution_name` (organization name from IPEDS HD, public), `report_form` (`F1A`/`F2`/`F3` literal). Neither carries free-text user input or contact data.
4. **Pattern heuristics applied to the string columns:**
   - **Email regex** (`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`) — no possible matches in `institution_name` or `report_form` value space.
   - **SSN regex** (`\d{3}-\d{2}-\d{4}` / `\d{9}`) — no possible matches.
   - **Phone regex** (`\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}`) — no possible matches.
   - **Personal-name NER** — institution names contain organization tokens ("University", "College", "Institute", "Community"); these are organization entities, not PER entities. Three-letter dorm of false-positive ("Stanford" as a person name) was reviewed and rejected — context (UNITID-keyed institution roster) is dispositive.
   - **Government-ID format** (EIN/Tax ID) — not present in source surveys; UNITID is an IPEDS identifier, not an EIN.
   - **Financial-account / Luhn** — endowment/expense columns are `double`-typed dollar aggregates, not account numbers; no Luhn pass possible at the schema level.
   - **DOB / location-coordinate / biometric / health-vocabulary** — no candidate columns of any of these types in the schema.
5. **Cross-reference with sibling scans** — aligns with `raw-ingest-college-scorecard-institution-pii-scan.md` and `raw-eada-pii-scan.md` (both institution-level public-data sources, both NO PII). The IPEDS Finance schema is a strict subset of "institution-level totals" plus one organization-name string column, identical in PII posture.
6. **Domain-context PII Expectations consultation** — IPEDS Finance section in `governance/domain-context.md` reaffirms "PII reaffirmed as none (institution-level public data)" pattern established by the EADA section and used across the higher-education-outcomes domain.

---

## Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|-----------------|
| Level 1 — Public | 12 | All fields (8 analytical + 4 metadata) |
| Level 2 — Internal | 0 | — |
| Level 3 — Confidential | 0 | — |
| Level 4 — Restricted | 0 | — |

---

## False Positive Candidates

| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| `institution_name` | Possible NER PER hit on naive personal-name scanners (e.g., "Vincennes", "Wesleyan", named-after-a-person institutions like "Carnegie Mellon University", "Johns Hopkins University") | Field is sourced from IPEDS HD `INSTNM` and is an organization name. Eponymous schools include the donor/founder's surname inside the org name but the field describes the organization, not the person. Field name (`institution_name`) and grain (one per UNITID) are dispositive context. | Treat as organization name. No masking, no redaction. Confirmed not PII. |
| `report_form` | Possible regex hit on `F\d` patterns | Survey-form discriminator literal — only three values in the value space. | No action. |

---

## Regulatory Implications

| Regulation | Applicability | Notes |
|------------|---------------|-------|
| FERPA | Not applicable | No student records present. NCES applies all student-privacy aggregation upstream. |
| GLBA | Not applicable | No customer financial accounts; only institution-level GAAP totals. |
| HIPAA | Not applicable | No health data of any kind. |
| GDPR / CCPA | Not applicable | No data subjects (no natural persons) represented in any column. Institution-level aggregates with public-domain license. |
| State public-records statutes | Compatible | All data already published by federal agencies under public-domain license. |

---

## Recommendations for @policy-engineer

1. **No RLS / column-masking / row-level access policies needed** for `bronze.ipeds_finance`. The table is fully Level 1 — Public.
2. **No CDE-level PII tags** required at @bs:cde-tagger time. CDE candidates are economic / governance, not privacy.
3. **Downstream propagation:** `base.ipeds_finance` and `consumable.ipeds_finance_profile` (and the EADA-fused `consumable.institution_aura`) inherit the same Level 1 — Public posture. No new PII is introduced by Silver/Gold transforms — they compute ratios from public dollar totals and FTE counts, none of which are PII.
4. **Future-proofing:** If a future spec revision adds officer-level columns (e.g., president name from IPEDS HD `CHFNM`/`CHFNM2`), or contact columns (`GENTELE`, `WEBADDR`), or address fields (`ADDR`, `CITY`, `ZIP`), this scan must be re-run. Those columns ARE potential PII surfaces (officer name → Level 3 Confidential as personal name; institutional address → Level 1 Public business address; phone/web → Level 1 Public business contact). The current v1.3-locked column list does not include any of them.

---

## Audit Trail Summary

- **Spec reference:** `docs/specs/full-pipeline-ipeds-finance.md` (sections §3 column locks, §4 raw schema, §6 consumable schema)
- **Domain-context reference:** `governance/domain-context.md` (IPEDS Finance entry, 2026-04-30)
- **Sibling scans referenced for consistency:** `raw-ingest-college-scorecard-institution-pii-scan.md`, `raw-eada-pii-scan.md`, `raw-ingest-college-scorecard-pii-scan.md`
- **Verdict:** NO PII DETECTED. All 12 fields Level 1 — Public.
- **Re-scan trigger:** Any addition of officer-level, contact, address, or transactional columns to the IPEDS Finance / HD / EFIA pull list.
