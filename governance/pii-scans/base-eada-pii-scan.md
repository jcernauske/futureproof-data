# PII Scan Report: base.eada

**Date:** 2026-04-30
**Agent:** @pii-scanner
**Spec Reference:** `docs/specs/full-pipeline-eada.md` §5 (base zone)
**Domain:** U.S. higher-education intercollegiate athletics financial reporting (institution-level public disclosure under §485g of the Higher Education Act / Equity in Athletics Disclosure Act, 1994)
**Predecessor scan:** `governance/pii-scans/raw-eada-pii-scan.md` (raw.eada — verdict: NO PII; all 10 cols Level 1)
**Sibling input scan:** `governance/pii-scans/raw-ipeds-finance-pii-scan.md` (the cross-source LEFT JOIN input — institution-level public data)
**Records Scanned:** N/A — table not yet materialized at scan time. Scan executed against the spec-frozen §5 schema, inherited raw-zone parquet, and predecessor verdicts.
**Columns Scanned:** 16 (all §5 fields)
**PII Instances Found:** 0

---

## Scope and Method

`base.eada` is the silver-zone passthrough-plus-derivation of `raw.eada` with a cross-source LEFT JOIN to `base.ipeds_finance` for FTE (Option-C COALESCE hybrid per §5 amendment 2026-04-30). The base zone introduces **no new fields sourced from outside data** — every column is either:

- a passthrough of a `raw.eada` field already cleared as Level 1 in the predecessor scan,
- a numeric derivation of those passthroughs and a public IPEDS Finance FTE value,
- a provenance enum / boolean stamped by the transformer itself, or
- a pipeline timestamp.

Both inputs (`raw.eada` and `base.ipeds_finance`) have already been independently PII-scanned and cleared. There is no path by which `base.eada` could acquire a PII surface that did not exist in either input. This scan therefore re-applies the full method and confirms.

### Detection Methods Applied

| Method | Coverage |
|---|---|
| Schema inspection | All 16 columns (3 string, 1 long, 1 int, 6 double, 2 boolean, 1 date, 1 timestamp, 1 string-enum) |
| Field-name heuristic | No column name suggests PII (no `name`, `email`, `phone`, `ssn`, `dob`, `address`, `gender`, `race` for individuals; `institution_name` is an organization name) |
| Predecessor inheritance | Every passthrough field carries the Level 1 classification from `raw-eada-pii-scan.md` |
| Cross-source delta inspection | The IPEDS-Finance LEFT JOIN contributes only `total_fte_enrollment` (a numeric institution headcount). Confirmed against `raw-ipeds-finance-pii-scan.md` — no PII. |
| Derivation analysis | All derived fields are `numeric / numeric` arithmetic on already-Level-1 inputs. Arithmetic on Level 1 cannot manufacture PII. |
| Provenance-column analysis | `fte_source`, `has_ipeds_finance_fte`, `has_eada_fte` are stamped by the transformer; values are pipeline-controlled and bounded — no user data |

---

## Column Inventory

| # | Column | Type | Origin | PII Risk |
|---|--------|------|--------|---------|
| 1 | `record_id` | string | Derived (`compute_grain_id` over `[unitid]`) | None — synthetic surrogate key |
| 2 | `unitid` | long | Passthrough from `raw.eada` | None — public IPEDS org ID (Level 1, prior scan) |
| 3 | `institution_name` | string | Passthrough from `raw.eada` | None — public organization name (Level 1, prior scan) |
| 4 | `reporting_year` | int | Passthrough from `raw.eada` | None |
| 5 | `total_athletic_expenses` | double | Passthrough from `raw.eada` | None — public org financial aggregate |
| 6 | `total_athletic_revenue` | double | Passthrough from `raw.eada` | None — same |
| 7 | `recruiting_expenses` | double | Passthrough from `raw.eada` | None — same |
| 8 | `eada_fte_headcount` | double | Passthrough from `raw.eada` (`EFTotalCount`) | None — institution-level headcount aggregate |
| 9 | `total_fte_enrollment` | double | COALESCE(`base.ipeds_finance.total_fte_enrollment`, `raw.eada.eada_fte_headcount`) | None — institution-level aggregate from two public sources |
| 10 | `fte_source` | string (enum: `ipeds_finance` / `eada_fte_headcount` / `none`) | Stamped by transformer | None — pipeline provenance |
| 11 | `has_ipeds_finance_fte` | boolean | Stamped by transformer | None — pipeline coverage flag |
| 12 | `has_eada_fte` | boolean | Stamped by transformer | None — pipeline coverage flag |
| 13 | `athletic_spend_per_fte` | double | Derived: `total_athletic_expenses / total_fte_enrollment` | None — derivation of public aggregates |
| 14 | `athletic_revenue_per_fte` | double | Derived: `total_athletic_revenue / total_fte_enrollment` | None — same |
| 15 | `recruiting_per_fte` | double | Derived: `recruiting_expenses / total_fte_enrollment` | None — same |
| 16 | `athletic_subsidy_ratio` | double | Derived: `(expenses - revenue) / expenses` | None — same |
| (+) | `source_load_date` | date | Provenance from raw | None — pipeline metadata |
| (+) | `ingested_at` | timestamp | Provenance from base promotion | None — pipeline metadata |

(Two trailing provenance columns shown for completeness — they replicate the raw-scan classification.)

---

## Findings

| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|--------------------|
| — | — | — | — | — | — | **No findings.** |

Zero matches across all detection methods. The base zone neither introduces a new external data source carrying PII nor synthesizes a higher-grain projection of an existing field.

---

## Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|----------------|
| 4 — Restricted | 0 | — |
| 3 — Confidential | 0 | — |
| 2 — Internal | 0 | — |
| 1 — Public | 16 | All schema fields. Inherits predecessor classification; derivations and provenance fields cannot raise the level. |

---

## False Positive Candidates

| Field | Could Be Mistaken For | Why It's Not PII | Recommendation |
|-------|----------------------|------------------|----------------|
| `record_id` (string `ead-…`) | An opaque token that looks like a hashed personal identifier | It is a deterministic surrogate over `unitid` only — recoverable to the org ID, not to any person | No action |
| `eada_fte_headcount` / `total_fte_enrollment` (double) | Could read like an individual count of identifiable students | These are institution-level **aggregates** (total full-time-equivalent headcounts). No row, no field, identifies any individual student | No action |
| `fte_source` enum | Looks like a category that might leak a person attribute | The three legal values (`ipeds_finance` / `eada_fte_headcount` / `none`) are pipeline-controlled provenance, not user data | No action |
| `has_ipeds_finance_fte`, `has_eada_fte` | Boolean flags could in principle encode personal characteristics | These flag whether a particular **public** input was non-null for the institution. Pure pipeline-control | No action |
| `athletic_subsidy_ratio` extreme values (e.g., -2.92 for Binghamton) | A scanner unfamiliar with the data could flag the outlier as anomalous and route it for human review as if it were sensitive | Not a PII concern in either case — it's a public ratio of public dollar amounts. Already handled by BSE-EAD-007 / BSE-EAD-010 (DQ rules) | No action |

---

## Regulatory Implications

| Regulation | Applies? | Reasoning |
|---|---|---|
| GDPR | No | No natural-person personal data |
| FERPA | No | No identifiable student education records; FTE counts are aggregates |
| HIPAA | No | No health data |
| CCPA / CPRA | No | No California consumer PI |
| GLBA | No | Not financial-institution customer data |
| State breach-notification laws | No | No PII subject to notification |
| **Public records / FOIA posture** | Yes (informational) | All figures are affirmatively disclosed under §485g HEA (EADA) and IPEDS Finance public-use files |

---

## Recommendations to @policy-engineer

1. **No row-level security required** for `base.eada`.
2. **No column masking required.** All 16 schema fields are Level 1.
3. **No encryption-at-rest mandate beyond project default.** Standard storage protections suffice.
4. **No access logging mandate beyond project default.** Reference-class public data.
5. **Carry forward to consumable.** The downstream `consumable.institution_aura` FULL OUTER JOINs `base.ipeds_finance ⨝ base.eada` on UNITID. Both inputs are Level 1; the joined product remains Level 1. No new PII surface is created at the consumable zone — the consumable scan should confirm but is expected to inherit this verdict.

---

## Audit Trail

- Spec read: `docs/specs/full-pipeline-eada.md` §5 (full text reviewed)
- Schema source: §5 Base Schema table (lines 285–306) — frozen by the spec amendment 2026-04-30
- Predecessor scan: `governance/pii-scans/raw-eada-pii-scan.md` (NO PII verdict, 10 cols Level 1)
- Cross-source input scan: `governance/pii-scans/raw-ipeds-finance-pii-scan.md`
- Domain context: `governance/domain-context.md` (EADA section, 2026-04-30) — *"PII reaffirmed as none (institution-level public data)."*
- Note: `base.eada` not yet materialized in the Iceberg silver catalog at scan time; pyiceberg `load_table(('base','eada'))` raised `NoSuchTableError`. Scan executed against the spec-frozen schema and inherited raw parquet. Re-confirm against the materialized table after `bs:smelt` lands `base.eada`; verdict is not expected to change.

---

## Verdict

**NO PII DETECTED.** All 16 schema fields of `base.eada` classify as Level 1 (Public). The base zone is a passthrough + numeric-derivation + provenance-stamping layer over two public-domain federal disclosures (EADA and IPEDS Finance) and introduces no new PII surface beyond what was cleared in the predecessor scans.
