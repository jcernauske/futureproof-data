# CDE/PII Tagging Audit: raw-ingest-karpathy-ai-exposure
**Date:** 2026-04-09
**Agent:** @cde-tagger
**Spec:** raw-ingest-karpathy-ai-exposure
**Contract:** governance/data-contracts/raw-karpathy-ai-exposure.yaml

## Domain Context Referenced
- governance/domain-context.md — Karpathy AI Exposure section (added 2026-04-09)
- Concept Mapping Guidance: soc_code auto-approved as CDE; exposure_score is the primary analytical payload; slug is the source grain identifier
- SOC coverage: 84.8% (290 of 342 rows have SOC codes); 52 rows require Silver-zone title-match resolution
- Cross-source integration: SOC code bridges Karpathy to BLS OOH, O*NET, and College Scorecard (via CIP-to-SOC crosswalk)
- PII expectations: NO PII — all fields are occupation-level aggregates from public BLS descriptions scored by an LLM
- Applicable regulations: None directly applicable. Public BLS data + LLM-generated scores. No FERPA/HIPAA/GLBA/GDPR concerns.

## Columns Flagged as CDE

| Column | Rationale |
|--------|-----------|
| slug | Grain field and source-level unique key. Required for SOC resolution in Silver (slug-to-SOC mapping) and provenance anchor for all downstream exposure data. |
| occupation_title | Human-readable identifier for consumer-facing outputs AND fallback join key for null-SOC resolution in Silver via title-match against BLS OOH. Dual role makes it critical. |
| soc_code | Primary cross-source join key. Bridges Karpathy to BLS OOH, O*NET, and College Scorecard programs. Without it, exposure scores cannot populate stat_res/boss_ai_score in Gold. |
| exposure_score | Primary analytical payload — the entire reason this dataset exists. Directly derives stat_res (AI Resilience) and boss_ai_score (Fight AI difficulty) in Gold zone. |
| rationale | Display field served via MCP and Fight AI boss narrative. Domain context identifies it as "the single most valuable field for LLM-to-user communication." |

## Columns Flagged as PII

None. Per governance/domain-context.md Karpathy PII Assessment: all fields are occupation-level aggregate data sourced from public BLS descriptions and scored by an LLM. No personal names, worker identifiers, individual compensation, or other personal data. Confirmed by pii-scanner.

## Columns Evaluated -- Not Flagged

| Column | Reason Not Critical |
|--------|---------------------|
| category | Project-specific grouping (25 Karpathy categories). Not a standard BLS taxonomy, not a join key, not a decision driver. Display grouping only. |
| median_pay_annual | Cross-validation field only. BLS OOH median_annual_wage is the authoritative source for wage data in this pipeline. This field is redundant validation, not a primary data feed. |
| num_jobs_2024 | Cross-validation field and tiebreaker for duplicate SOC resolution in Silver. Not a primary analytical field — BLS OOH employment_current is authoritative. |
| entry_education | Cross-validation field only. BLS OOH education_code/education_typical is the authoritative source for education requirements. |
| source_url | Pipeline metadata — provenance tracking only. |
| ingested_at | Pipeline metadata — no business criticality. |
| source_method | Pipeline metadata — provenance tracking only. |
| load_date | Pipeline metadata — freshness tracking only. |
