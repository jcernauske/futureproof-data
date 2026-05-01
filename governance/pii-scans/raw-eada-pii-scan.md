# PII Scan Report: bronze.eada (raw.eada)

**Date:** 2026-04-30
**Agent:** @pii-scanner
**Spec Reference:** `docs/specs/full-pipeline-eada.md` §4 (raw zone)
**Domain:** U.S. higher-education intercollegiate athletics financial reporting (institution-level public disclosure under §485g of the Higher Education Act / Equity in Athletics Disclosure Act, 1994)
**Dataset Path:** `data/bronze/iceberg_warehouse/bronze/eada/data/00000-0-82a082ef-60bf-4b61-aebd-f069e1aa61d2.parquet`
**Records Scanned:** 2,040
**Columns Scanned:** 10
**PII Instances Found:** 0

---

## Scope and Method

EADA is a public-domain federal disclosure published annually by the U.S. Department of Education's Office of Postsecondary Education at `https://ope.ed.gov/athletics/`. The bronze table holds **institution-level totals only** — the per-team / per-sport `Schools.xlsx` detail is explicitly out of scope for FutureProof per `governance/domain-context.md` EADA section. Every row represents an institution's grand-total athletic finance figures; no row represents a person.

`governance/domain-context.md` explicitly states: *"PII reaffirmed as none (institution-level public data)."* This scan independently confirms that claim against the materialized parquet.

### Detection Methods Applied

| Method | Coverage |
|---|---|
| Schema inspection | All 10 columns (3 string, 4 numeric, 1 int identifier, 2 datetime) |
| Regex pattern matching on every string column | email, SSN, phone (NANP), credit-card-like 13–16 digit runs, IPv4, US street address, US ZIP-5/ZIP+4, person-title prefix (Mr./Mrs./Ms./Dr./Prof. + capitalized name) |
| Field-name heuristic | No column name suggests PII (no `name`, `email`, `phone`, `ssn`, `dob`, `address`, `gender`, `race` for individual persons; `institution_name` is an organization name, not a person name) |
| Domain calibration | EADA expectation per `governance/domain-context.md`: zero PII expected; sensitivity Level 1 (Public) for all fields |
| Cardinality / value sampling | `institution_name` distinct-value check: 2,022 unique values across 2,040 rows — consistent with institution-level grain |

---

## Column Inventory

| # | Column | Type | Nature | PII Risk |
|---|--------|------|--------|---------|
| 1 | `unitid` | int64 | IPEDS institution identifier (organization, not person) | None — public org ID |
| 2 | `institution_name` | string | Institution legal name (e.g., "University of Alabama at Birmingham") | None — public org name |
| 3 | `reporting_year` | int32 | Award/reporting year (e.g., 2022) | None |
| 4 | `total_athletic_expenses` | float64 | Institution-level grand total expense (USD) | None — org financial aggregate, publicly disclosed |
| 5 | `total_athletic_revenue` | float64 | Institution-level grand total revenue (USD) | None — same |
| 6 | `recruiting_expenses` | float64 | Institution-level recruiting expense (USD) | None — same |
| 7 | `source_url` | string | Static value: `https://ope.ed.gov/athletics/` | None — public URL |
| 8 | `source_method` | string | Ingestor lineage tag (e.g., `csv_cache`) | None — pipeline metadata |
| 9 | `ingested_at` | datetime | Pipeline ingestion timestamp | None — pipeline metadata |
| 10 | `load_date` | datetime | Pipeline load partition date | None — pipeline metadata |

---

## Findings

| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|--------------------|
| — | — | — | — | — | — | **No findings.** |

### Regex Pattern Hits (per column, per pattern)

```
{}
```

Zero matches across **all** patterns on **all** string columns. The numeric columns (`unitid`, financial totals) were inspected by type — `unitid` is a 6-digit IPEDS institution code by federal definition, not an SSN; financial totals are continuous USD values, not card numbers (no Luhn-valid 13–16 digit constructions, and the column is `float64`).

---

## Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|----------------|
| 4 — Restricted | 0 | — |
| 3 — Confidential | 0 | — |
| 2 — Internal | 0 | — |
| 1 — Public | 10 | All columns. Institution-level disclosures mandated by federal law and published by USDOE. |

All ten columns classify as **Level 1 (Public)**. This includes the institution name and UNITID, which are organization identifiers (not personal), and the three financial aggregates, which are explicitly required to be made public under EADA.

---

## False Positive Candidates

| Field | Could Be Mistaken For | Why It's Not PII | Recommendation |
|-------|----------------------|------------------|----------------|
| `unitid` (int64, 6-digit) | A naive scanner could match SSN-shaped numbers (it does not — SSN is 9 digits and our regex requires the dashed form). UNITID range observed 100,654–497,268 is the IPEDS-standard 6-digit space. | UNITID is the federal IPEDS institution identifier — an **organization** ID, not a person ID. Domain authority: NCES. | No action. Document in glossary (already done in `governance/domain-context.md`). |
| `institution_name` (string) | NER could over-fire on substrings like "Alabama" and tag them as person names; "Saint Mary's" / "John Carroll University" contain canonical given names. | These are **organization** names by construction. The grain of the table is institution-per-row, the source field is the IPEDS-reported `INSTNM`, and the surrounding pipeline (`bronze.college_scorecard_institution`) confirms they are organizations. | No action. Treat as Level 1 public org name. |
| `recruiting_expenses == 0` (17.8% of rows) | Could read like a sentinel for missing data. | Per `governance/domain-context.md` and the EDA report at `governance/eda/full-pipeline-eada-raw-eda.md`, real zeros are valid for non-recruiting institutions; original sentinels (`-1`, `-2`, blank) were already converted to NULL by the ingestor. Not a PII concern in either case. | No action. |

---

## Regulatory Implications

| Regulation | Applies? | Reasoning |
|---|---|---|
| GDPR | No | No personal data under Art. 4(1) — institutions are legal persons in the corporate sense, but GDPR scope is **natural** persons. |
| FERPA | No | FERPA covers student education records. EADA's institution-level totals do not constitute education records of any identifiable student. |
| HIPAA | No | No health data. |
| CCPA / CPRA | No | No California consumer personal information. |
| GLBA | No | Not a financial institution's customer data. |
| State breach-notification laws | No | No PII whose breach would trigger notification. |
| **Public records / FOIA posture** | Yes (informational) | These figures are affirmatively disclosed under §485g HEA. Treating them as anything other than Level 1 Public would be incorrect. |

---

## Recommendations to @policy-engineer

1. **No row-level security required** for `bronze.eada` or downstream Silver/Gold tables derived from it (e.g., the proposed `consumable.institution_aura`).
2. **No column masking required.** All ten columns are publicly disclosed.
3. **No encryption-at-rest mandate beyond project default.** Standard storage protections suffice.
4. **No access logging mandate beyond project default.** This is reference-class data, not regulated.
5. **Caveat for the aura-score derivation:** when EADA is joined to IPEDS Finance to compute `endowment_per_fte` / `marketing_ratio` / `athletic_spend_per_fte`, the joined product remains Level 1 — both inputs are public.
6. **Forward note:** if a future spec adds the per-team `Schools.xlsx` (`SPORTSCODE`-keyed) data, **rescan**. That file is also public, but it carries finer grain (per-sport coach counts, gender splits) that warrants a fresh check rather than inheriting this verdict.

---

## Verdict

**NO PII DETECTED.** All ten columns of `bronze.eada` (2,040 rows, reporting year 2022) classify as Level 1 (Public) under the four-level sensitivity framework. The dataset contains institution-level totals from a federally mandated public disclosure and carries no individual-level information of any kind.
