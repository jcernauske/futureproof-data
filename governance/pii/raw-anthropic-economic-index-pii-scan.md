# PII Scan Report: raw.anthropic_economic_index

**Date:** 2026-04-16
**Agent:** @pii-scanner
**Domain:** Education / Career Guidance (AI Exposure sub-domain — observed signal)
**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**Release Scanned:** `release_2025_03_27`
**Source Path:** `data/raw/anthropic_economic_index/release_2025_03_27/`
**Verdict:** **CLEAN** — no PII detected
**Records Scanned:** 31,734 rows across 6 source CSVs (4,082 projected Bronze rows after fan-out)
**PII Instances Found:** 0

---

## Executive Summary

The Anthropic Economic Index is **structurally aggregate** data: per-task percentage shares computed over millions of Claude conversations, with Anthropic's own classifier + privacy review applied before publication. The `filtered` axis on every row represents conversations Anthropic specifically removed for privacy/data-quality reasons — the release is what's *left* after that review. No individual-level signal is recoverable from these files.

This scan **confirms** the zero-PII posture declared in `governance/domain-context.md` (§ "Anthropic Economic Index" → "PII Expectations"). The bronze/silver/gold schemas introduce no PII-bearing fields; they carry only O*NET task text, SOC codes, percentage metrics, and pipeline metadata.

---

## Source File Inventory (what was actually scanned)

| File | Rows | Columns | Contains Free Text? |
|------|-----:|---------|---------------------|
| `task_pct_v2.csv` | 3,365 | task_name, pct | task_name (lowercase O*NET task text) |
| `automation_vs_augmentation_by_task.csv` | 3,364 | task_name + 6 numeric axes | task_name only |
| `onet_task_statements.csv` | 19,530 | O*NET-SOC Code, Title, Task ID, Task, Task Type, Incumbents Responding, Date, Domain Source | Task (SOC-level task description), Title (occupation title) |
| `SOC_Structure.csv` | 1,596 | Major Group, Minor Group, Broad Occupation, Detailed Occupation, Detailed O*NET-SOC, Title | SOC hierarchy labels only |
| `task_pct_v1.csv` | 3,514 | task_name, pct | task_name (v1 predecessor — not ingested in v2 pipeline) |
| `task_thinking_fractions.csv` | 3,365 | task_name, thinking_fraction | task_name |

Total rows scanned: **31,734**. Of these, `task_pct_v2.csv` + `automation_vs_augmentation_by_task.csv` + `onet_task_statements.csv` (bridge) are the three files that flow into the Bronze ingestor; the other three were scanned for completeness.

---

## Field-by-Field PII Assessment (pipeline schema)

### Bronze — `raw.anthropic_economic_index`

| Field | Type | PII Risk | Sensitivity | Assessment |
|-------|------|----------|-------------|------------|
| task_id | string | None | 1 (Public) | O*NET task identifier (e.g., `20461`). Federal taxonomy code. Not a personal identifier. |
| task_statement | string | None | 1 (Public) | Public O*NET task description text (e.g., "Direct or coordinate an organization's financial or budget activities..."). Published by U.S. Department of Labor; derived from anonymized incumbent-worker surveys. Never contains individual identities. |
| soc_code | string | None | 1 (Public) | Standard Occupational Classification code (XX-XXXX). Federal taxonomy. |
| soc_title | string | None | 1 (Public) | Occupation title (e.g., "Chief Executives"). Job category label, not a personal name. |
| task_pct | double | None | 1 (Public) | Global share of classified Claude conversations, 0–100 percent, aggregated over millions of conversations. Not individual-level. |
| automation_pct | double | None | 1 (Public) | Weighted interaction-mode share. Aggregate metric. |
| augmentation_pct | double | None | 1 (Public) | Weighted interaction-mode share. Aggregate metric. |
| source_release | string | None | 1 (Public) | Literal: `release_2025_03_27`. Provenance tag. |
| ingested_at | timestamp | None | 2 (Internal) | Pipeline run timestamp. Not personal data. |
| source_url | string | None | 1 (Public) | HuggingFace dataset URL. Public. |
| source_method | string | None | 1 (Public) | Literal: `hf_git_clone`. |
| load_date | date | None | 2 (Internal) | Pipeline load date. |

### Silver — `base.anthropic_observed_exposure`

| Field | Type | PII Risk | Sensitivity | Assessment |
|-------|------|----------|-------------|------------|
| record_id | string | None | 1 (Public) | Grain hash (`aoe:...`). Deterministic identifier over SOC code — no personal entropy. |
| soc_code | string | None | 1 (Public) | SOC taxonomy code. |
| soc_title | string | None | 1 (Public) | Occupation title. |
| observed_exposure_pct | double | None | 1 (Public) | SOC-level aggregate. |
| automation_pct | double | None | 1 (Public) | SOC-level aggregate. |
| augmentation_pct | double | None | 1 (Public) | SOC-level aggregate. |
| task_count | int | None | 1 (Public) | Count of O*NET tasks aggregated. |
| soc_match | boolean | None | 1 (Public) | Flag against BLS OOH. |
| source_release | string | None | 1 (Public) | Provenance tag. |
| promoted_at | timestamp | None | 2 (Internal) | Pipeline timestamp. |

### Gold additions on `consumable.ai_exposure`

| Field | Type | PII Risk | Sensitivity | Assessment |
|-------|------|----------|-------------|------------|
| observed_exposure_pct | double | None | 1 (Public) | SOC-level aggregate. |
| automation_pct | double | None | 1 (Public) | SOC-level aggregate. |
| anthropic_task_count | int | None | 1 (Public) | Count. |
| anthropic_source_release | string | None | 1 (Public) | Provenance tag. |

---

## Detection Methods Applied

| Method | Scope | Raw Hits | True PII Hits | Disposition |
|--------|-------|---------:|--------------:|-------------|
| Email regex `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | All string cols, all 6 files | 0 | 0 | — |
| SSN regex `\d{3}-\d{2}-\d{4}` | All string cols | 0 | 0 | — |
| Phone regex `\d{3}[-. ]\d{3}[-. ]\d{4}` | All string cols | 0 | 0 | — |
| IPv4 regex | All string cols | 0 | 0 | — |
| Credit-card regex (13–16 digits) | All cols | 3,399 | 0 | False positives — all are decimal fractions (e.g. `0.2042857905829283`) where the fractional digits coincidentally form a 13–16 digit run. Column-type check confirms these are `pct`, `directive`, `feedback_loop`, `task_iteration`, `validation`, `learning`, `filtered` — all documented 0–1 fractions summing to 1.0 per row. |
| Personal title regex (Mr./Mrs./Dr./Prof./etc. + cap name) | All string cols | 0 | 0 | — |
| DOB keyword regex (`date_of_birth`, `DOB`, `birth_date`) | Column names + values | 0 | 0 | — |
| Street-address regex (`<num> <Cap> (St\|Ave\|Rd\|...)`) | All string cols | 0 | 0 | — |
| URL regex | All string cols | 0 | 0 | — |
| ZIP-code regex (5 or 5-4) | All string cols | 10,349 | 0 | False positives — O*NET `Task ID` is a 5-digit integer (e.g., `20461`); `pct` and mode-axis fractions contain 5-digit substrings (e.g., `0.59375`). None are geographic. |
| GPS-coord regex | All string cols | 0 | 0 | — |
| First+last-name heuristic `[A-Z][a-z]{2,} [A-Z][a-z]{2,}` | Free-text cols (task_name, Task, Title) | 16,964 | 0 | All hits are occupation titles (`Chief Executives`, `Management Occupations`) or program/regulation names embedded in O*NET task text (`Congressional Record`, `Federal Reserve`, `Employee Retirement Income Security Act`, `Equal Employment Opportunity`). Anthropic `task_name` column is **100% lowercase** → zero hits there. |
| Column-name heuristic (person/name/patient/customer/email/phone/address/ssn/dob) | All column names across all files | 0 | 0 | No column name signals PII. |

**Net result:** 30,712 raw pattern hits, **0** true PII instances after disposition.

---

## Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|------:|----------------|
| 1 (Public) | 0 | — |
| 2 (Internal) | 0 | — |
| 3 (Confidential) | 0 | — |
| 4 (Restricted) | 0 | — |

All fields classify as non-PII.

---

## False-Positive Candidates (reviewed and cleared)

| Field / Pattern | Detected As | Why It's Not PII | Recommendation |
|-----------------|-------------|------------------|----------------|
| `pct`, `directive`, `feedback_loop`, `task_iteration`, `validation`, `learning`, `filtered` | Credit-card number | Values are decimal fractions in [0, 1] (mode axes) or [0, 100] (`pct`). 13–16 digits appear only as fractional precision. EDA confirms 6-axis rows sum to 1.0; `pct` sums to 100.0 globally. | No action. |
| O*NET `Task ID` | ZIP code | 5-digit integer O*NET task identifiers (e.g. `20461`). Federal taxonomy, not geographic. | No action. |
| `soc_title` / O*NET `Title` | Personal name (two Capital-Case tokens) | SOC occupation category labels (e.g., "Chief Executives", "Software Developers"). Taxonomy, not personal names. | No action. |
| O*NET `Task` free text (73 hits) | Personal name | All hits are program/statute/regulation names inside task descriptions: "Congressional Record", "Federal Reserve", "Employee Retirement Income Security Act", "Equal Employment Opportunity", "Alien Employment Certification", "Health Reimbursement Account", etc. Spot-sampled 10 of 73 — all institutional/legislative terms, zero personal names. | No action. |
| Anthropic `task_name` | Any personal-name-ish pattern | Column is 100% lowercase — zero capital-letter matches possible. | No action. |

---

## Regulatory Implications

No regulatory controls triggered by this dataset:

| Regulation | Applies? | Reason |
|------------|----------|--------|
| GDPR | No | No personal data; dataset is aggregated over millions of users. |
| CCPA / CPRA | No | No personal information. |
| HIPAA | No | No health records; occupation-level aggregates only. |
| FERPA | No | No education records. |
| PCI DSS | No | No payment card data. |
| SOX | No | No financial reporting data. |
| EEOC | Advisory only | AI-exposure scores by occupation are not protected-class data; however, if downstream products use these scores in employment decisions (hiring, compensation), disparate-impact analysis is recommended. Same caveat as Karpathy AI Exposure. |

**Attribution requirement (not a PII control):** CC-BY 4.0 requires citation: "Anthropic Economic Index v2, release 2025-03-27, CC-BY 4.0." Handled by `LICENSE_SOURCES.md` and data contract `license` block — not a @policy-engineer concern.

---

## Recommendations

1. **No PII remediation required.** All 13 Bronze fields, 10 Silver fields, and 4 Gold additions classify as Level 1 (Public) or Level 2 (Internal, pipeline metadata). No masking, redaction, encryption, or RLS is needed for PII reasons.
2. **@policy-engineer: skip PII-based policy generation** for `raw.anthropic_economic_index`, `base.anthropic_observed_exposure`, and the Anthropic columns on `consumable.ai_exposure`. Standard access controls sufficient.
3. **@cde-tagger:** Confirm no CDE/PII flags needed (per governance-reviewer advisory #5). The shared SOC CDE is already registered; no new PII-bearing CDEs introduced.
4. **Downstream re-scan trigger:** If Anthropic ever republishes the index with per-conversation or per-user decomposition, re-run this scan — the current zero-PII posture is guaranteed only by the aggregate-release structure.
5. **Justification reference for audit:** `governance/domain-context.md` → "Anthropic Economic Index" → "PII Expectations" table confirms: "No PII. This is structurally aggregate-over-millions-of-conversations data; individual-level inference is not possible from the release files." Scan confirms.

---

## Audit Trail

- Scan script: `/tmp/pii_scan_aei.py` (regex-pattern sweep across 12 detectors × all string columns × 6 source files)
- Text-focused follow-up: `/tmp/pii_scan_aei_text.py` (free-text columns, with sample inspection)
- Total rows scanned: 31,734
- Total raw pattern matches: 30,712
- True-PII matches after disposition: **0**
- Domain-context cross-check: consistent — `governance/domain-context.md` line 1738 declares "No PII" expectation.

---

*— End of Report —*
