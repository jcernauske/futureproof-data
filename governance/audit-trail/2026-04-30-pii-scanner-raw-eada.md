# Audit Trail: PII Scan — bronze.eada

**Timestamp:** 2026-04-30
**Agent:** @pii-scanner
**Spec:** `docs/specs/full-pipeline-eada.md` §4 (raw zone)
**Dataset:** `bronze.eada` — `data/bronze/iceberg_warehouse/bronze/eada/data/00000-0-82a082ef-60bf-4b61-aebd-f069e1aa61d2.parquet`

## Inputs Consulted
- `governance/domain-context.md` — EADA section (canonical, finalized 2026-04-30 by @bs:domain-context). Explicitly states "PII reaffirmed as none (institution-level public data)."
- `governance/eda/full-pipeline-eada-raw-eda.md` — referenced as the numeric backing for column distributions and overlap measurements.
- `docs/specs/full-pipeline-eada.md` §4 — confirms scope is institution-level totals (`InstLevel.xlsx`), per-team data out of scope.
- Materialized Iceberg parquet — read directly via DuckDB, 2,040 rows × 10 columns.

## Detection Methods Used
1. Schema inspection (column names, types).
2. Field-name heuristic (no person-PII-shaped column names).
3. Regex pattern matching across every string column for: email, SSN (dashed), NANP phone, 13–16 digit credit-card-like runs, IPv4, US street address, US ZIP-5/ZIP+4, person-title-prefix patterns.
4. Domain calibration against `governance/domain-context.md` EADA section.
5. Cardinality check on `institution_name` (2,022 unique / 2,040 rows — confirms institution-per-row grain).

## Decisions and Rationale
- **`unitid` (int64) classified Level 1 Public.** It is the IPEDS organization identifier, not an individual-level ID. Domain authority: NCES. Cited in domain context as auto-approve external standard.
- **`institution_name` (string) classified Level 1 Public.** Organization names; the field-of-origin in source files is IPEDS `INSTNM`. NER false-positive risk acknowledged and dismissed (institutions are not natural persons).
- **Three financial aggregates classified Level 1 Public.** EADA disclosure is mandated by §485g of the Higher Education Act and published at `https://ope.ed.gov/athletics/`.
- **Pipeline metadata columns (`source_url`, `source_method`, `ingested_at`, `load_date`) classified Level 1 Public.** No inherent PII; lineage tags only.
- **No false-positive flags raised.** All values matched expectations from domain context.

## Outcome
- **Verdict:** NO PII DETECTED.
- **Sensitivity classification:** All 10 columns → Level 1 (Public).
- **Regulations triggered:** None (GDPR/FERPA/HIPAA/CCPA/GLBA all not applicable).
- **Downstream guidance to @policy-engineer:** No RLS, no column masking, no special encryption, no access logging beyond project defaults required for `bronze.eada` or its derived Silver/Gold tables.
- **Caveat recorded:** rescan required if a future spec ingests `Schools.xlsx` per-team data.

## Artifacts Produced
- `governance/pii-scans/raw-eada-pii-scan.md` — full scan report.
- `governance/audit-trail/2026-04-30-pii-scanner-raw-eada.md` — this log.
