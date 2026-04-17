# PII Scan Report: raw.onet_experience

**Date:** 2026-04-16
**Agent:** bs:pii-scanner
**Spec:** `docs/specs/onet-experience-requirements.md`
**Domain:** Occupational taxonomy — public labor-market reference data (O*NET 30.2 "Education, Training, and Experience" publication)
**Target table:** `raw.onet_experience`
**Expected grain:** `onet_soc_code × element_id × scale_id × category`
**Expected rows:** ~35,881 (spec §Source Data); row-count DQ band 30,000–45,000
**Records scanned in evidence:** 27 rows from the canonical O*NET sample fixture `tests/raw/onet_samples/Education, Training, and Experience.txt` (5 occupations × 4 scales, representative coverage)
**PII instances found:** 0

---

## Verdict

**NO PII DETECTED.** The spec's declared "PII Risk: NONE" is confirmed. O*NET's ETE publication carries exclusively occupation-level aggregate statistics; no column — narrative or numeric — carries individual-level data, survey-respondent identifiers, or free-text PII.

---

## Scanning Method

The production Iceberg table `raw.onet_experience` has not yet been materialized (Phase 2 Bronze ingest is pending — `data/raw/iceberg/` is empty). Verification therefore ran against:

1. **Spec schema declaration** — §Zone 1 > Raw Schema (17 columns, spec lines 91–109).
2. **Canonical sample fixture** — `tests/raw/onet_samples/Education, Training, and Experience.txt` (27 rows, 13 source columns), queried via DuckDB to enumerate distinct values in every narrative-ish column.
3. **O*NET public methodology** — documented inputs to the ETE program are (a) statistically sampled incumbents from sampled establishments and (b) certified occupational experts, both reported only as aggregate percent-frequency distributions across duration categories per occupation. No respondent-level microdata is ever published.
4. **Existing precedent scans** — `raw-ingest-onet-pii-scan.md` (same publisher, same grain convention, cleared NONE).

---

## Per-Column PII Disposition

Columns as declared in spec §Zone 1. The 13 source columns from the O*NET text file map 1:1 onto the first 13 rows; the last 4 columns are pipeline-added provenance fields.

| # | Column | Type | Source | PII Class | Rationale |
|---|--------|------|--------|-----------|-----------|
| 1 | `onet_soc_code` | string | O*NET | NONE | Public occupational taxonomy key (XX-XXXX.XX). Denotes a job category, never an individual. |
| 2 | `element_id` | string | O*NET | NONE | Content Model element identifier ("3.A.1", "2.D.1", etc.). Controlled vocabulary. |
| 3 | `element_name` | string | O*NET | NONE | Human-readable element label. Sample-verified controlled vocabulary: {`On-Site or In-Plant Training`, `On-the-Job Training`, `Related Work Experience`, `Required Level of Education`}. Not free text. |
| 4 | `scale_id` | string | O*NET | NONE | 2-letter enum: {`OJ`, `PT`, `RL`, `RW`}. Fully closed vocabulary. |
| 5 | `category` | int | O*NET | NONE | Ordinal duration bucket (1–12 depending on scale). Dimensional. |
| 6 | `data_value` | double | O*NET | NONE | Percent frequency (0.0–100.0). Aggregate statistic. |
| 7 | `n` | int | O*NET | NONE | **Sample size** (count of survey respondents contributing to the aggregate). Verified: distinct values in sample are {12, 15, 29, 42, 55} — all plausible small-group counts, none resembling any identifier format (not SSN, not EIN, not employee-ID-shaped). Count, not identifier. Confirmed per spec task item #2. |
| 8 | `standard_error` | double | O*NET | NONE | Statistical dispersion measure. Aggregate. |
| 9 | `lower_ci_bound` | double | O*NET | NONE | 95% CI lower bound on the aggregate percent. |
| 10 | `upper_ci_bound` | double | O*NET | NONE | 95% CI upper bound on the aggregate percent. |
| 11 | `recommend_suppress` | string | O*NET | NONE | Two-value flag {`Y`, `N`}. Quality/DQ marker. Confirmed via sample. |
| 12 | `date` | string | O*NET | NONE | **Data collection month** ("MM/YYYY"). Sample-verified single value {`08/2023`}. Publication-wave date at the occupation level; NOT an individual event date, NOT a birth date, NOT connected to any person. Confirmed per spec task item #4. |
| 13 | `domain_source` | string | O*NET | NONE | **Respondent-role label**, not an identifier. Controlled vocabulary per O*NET ETE methodology: {`Incumbent`, `Occupational Expert`} — a role classification, not a person. Sample contains only `Incumbent`; the spec documents both values at §Source Data. Equivalent in risk profile to a column saying "survey_track = phone". Confirmed per spec task item #3. |
| 14 | `ingested_at` | timestamp | pipeline | NONE | Pipeline ingest timestamp. Operational metadata. |
| 15 | `source_url` | string | pipeline | NONE | `https://www.onetcenter.org/dl_files/database/db_30_2_text.zip`. Public URL. |
| 16 | `source_method` | string | pipeline | NONE | Constant `"bulk_zip_download"`. |
| 17 | `load_date` | date | pipeline | NONE | Pipeline load calendar date. Operational. |

**All 17 columns: PII class = NONE.**

---

## Cross-Check Against the 4 Scales (RL, RW, PT, OJ)

Spec task item #5 — confirm none of the scales carry individual survey responses.

| Scale | Element | What it contains | Individual responses? |
|-------|---------|------------------|-----------------------|
| `RL` | Required Level of Education (element `2.D.1`) | % of respondents choosing each of ~12 education-level categories, per occupation | NO — aggregated percent frequencies only |
| `RW` | Related Work Experience (element `3.A.1`) | % of respondents choosing each of 11 duration categories, per occupation | NO — the Silver target metric; still fully aggregated |
| `PT` | On-Site or In-Plant Training (element `3.B.1`) | % of respondents choosing each of ~9 duration categories, per occupation | NO — aggregated |
| `OJ` | On-the-Job Training (element `3.B.2`) | % of respondents choosing each of 11 duration categories, per occupation | NO — aggregated |

Every row in the table is "for occupation X, Y% of the N respondents gave answer Z on scale S" — a per-cell aggregate with a sample size, not a per-respondent record. Confirmed against all 27 rows of the fixture.

---

## Evidence: Distinct-Value Enumeration on Narrative Columns

Executed via DuckDB `read_csv_auto` against the canonical fixture. All narrative-ish columns are controlled vocabularies, not free text.

### `element_name` — 4 distinct values (from 27-row sample)
- `On-Site or In-Plant Training`
- `On-the-Job Training`
- `Related Work Experience`
- `Required Level of Education`

### `scale_id` — 4 distinct values (matches spec DQ rule `scale_id IN ('RL','RW','PT','OJ')`)
- `OJ`, `PT`, `RL`, `RW`

### `domain_source` — 1 value present in sample; 2 total per methodology
- `Incumbent` (sample)
- `Occupational Expert` (per spec §Raw Schema and O*NET ETE methodology — not present in this 5-occupation slice but expected at full scale)

### `date` — 1 distinct value
- `08/2023` (MM/YYYY publication-wave label)

### `recommend_suppress` — 2 distinct values
- `Y`, `N`

### `n` (sample size) — 5 distinct values, all small integers
- 12, 15, 29, 42, 55 — plausible per-occupation respondent counts; none identifier-shaped.

### `onet_soc_code` — 5 distinct values in sample
- `11-1011.00` (Chief Executives), `15-1252.00` (Software Developers), `29-1069.01` (Physicians — other), `41-2031.00` (Retail Salespersons), `49-9071.00` (Maintenance/Repair Workers). Public SOC-format taxonomy keys.

---

## Summary by Sensitivity

| Level | Label | Count | Fields Affected |
|-------|-------|-------|-----------------|
| 1 | Public | 17 | All columns — entirely sourced from a CC BY 4.0 public-record publication |
| 2 | Internal | 0 | — |
| 3 | Confidential | 0 | — |
| 4 | Restricted | 0 | — |

---

## False Positive Candidates

| Field | Could Be Mistaken For | Why It Is Not PII |
|-------|-----------------------|---------------------|
| `n` | Employee count / identifier number | It is a sample-size integer (count of survey respondents whose answers formed this aggregate). Distinct values {12,15,29,42,55} in sample confirm small-group-count scale, never ID-shaped. Spec schema annotation explicitly labels as "Sample size". |
| `date` | Birth date / individual event date | It is a publication-wave month (`MM/YYYY`) labeling when O*NET collected a batch of responses for an occupation. Not tied to a person. Single value `08/2023` across all 27 sample rows. |
| `domain_source` | Person name / organization name | A **role label** drawn from a 2-value vocabulary {`Incumbent`, `Occupational Expert`}. No name, no ID, no free text. |
| `element_id` / `element_name` | Free-text descriptor that could leak PII | Controlled vocabulary derived from the O*NET Content Model. 4 distinct values observed. |
| `onet_soc_code` | Employee ID, account number | Public occupational code format `XX-XXXX.XX` — published by the U.S. Department of Labor. |

---

## Cross-Linking Risk Analysis (Silver/Gold reintroduction)

Per spec deliverable — does downstream joining reintroduce PII risk?

| Downstream table | Joined to | Join key | Reintroduction risk |
|------------------|-----------|----------|---------------------|
| `base.onet_experience_profiles` | self-aggregation from `raw.onet_experience` | `bls_soc_code` (truncated from `onet_soc_code`) | NO — aggregates an already-aggregate; joins on SOC taxonomy keys, never on a person |
| `consumable.career_branches` | `base.onet_experience_profiles` + existing `career_branches` | `bls_soc_code` ↔ `related_soc_code` / `soc_code` | NO — `career_branches` is itself SOC×SOC with no person-level fields (per prior `raw-ingest-onet-pii-scan.md` and `gold-occupation-profiles-bls-ooh-pii-scan.md`) |
| BLS OOH / O*NET occupation profiles | via SOC taxonomy | `bls_soc_code` | NO — BLS OOH is also occupation-level aggregates (cleared NONE in `raw-ingest-bls-ooh-pii-scan.md`) |

**Verdict on cross-linking:** NO increase in PII risk. Every adjacent table in the FutureProof pipeline is keyed on the same SOC/CIP occupational taxonomies, which are categorical by construction. There is no customer table, user table, or survey-respondent table anywhere in the pipeline to link against — and O*NET itself does not publish respondent identifiers that could be re-identified downstream.

---

## Regulatory Implications

| Regulation | Applies? | Rationale |
|------------|----------|-----------|
| GDPR | No | No personal data under Article 4(1); subject is "occupations," not natural persons. |
| CCPA / CPRA | No | No "personal information" about California residents. |
| HIPAA | No | No health/clinical data; no covered entity. |
| FERPA | No | No student records. |
| PCI DSS | No | No payment data. |
| COPPA | No | No child/minor data. |

The data is published under **CC BY 4.0** by O*NET (U.S. Department of Labor, Employment and Training Administration) and is explicitly intended for public use with attribution. Standard attribution handling already specified in the spec.

---

## Recommendations for `bs:policy-engineer` / `bs:cde-tagger`

1. **No RLS needed** on `raw.onet_experience` — treat as fully public.
2. **No column masking** required on any of the 17 columns.
3. **CDE tagging** per spec §CDE & PII Assessment (lines 412–419) is unaffected by this scan — all `is_pii = ❌` dispositions stand; `is_cde` dispositions reflect join-key / Silver-derivation importance, not PII.
4. **Access controls**: standard read-open, write-restricted-to-pipeline. No audit logging for PII compliance required.
5. **Spec compliance**: the spec's `bs:pii-scanner` skip justification at Phase 2 step 11 is hereby affirmed — this report serves as the registered justification artifact. `pipeline_gate skip` may proceed.

---

## Audit Trail Reference

Decision log: `governance/audit-trail/onet-experience-pii-scan-2026-04-16.md` (to be written if the orchestrator expects a separate audit artifact — this scan report itself contains full decision rationale).

---

## One-Line Verdict

**NO PII DETECTED.** `raw.onet_experience` contains exclusively occupation-level aggregate statistics from a CC BY 4.0 public-record publication; all 17 columns classify as Level 1 (Public); downstream SOC-keyed joins do not reintroduce risk.
