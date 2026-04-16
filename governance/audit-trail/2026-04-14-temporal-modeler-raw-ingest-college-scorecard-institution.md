# Audit Trail: Temporal Modeler — raw-ingest-college-scorecard-institution

**Date:** 2026-04-14
**Agent:** @temporal-modeler
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Domain Context:** domain/raw-ingest-college-scorecard-institution-context.md
**Output:** governance/temporal-models/raw-ingest-college-scorecard-institution-temporal.md

## Decision

**SKIP bitemporal modeling.** Standard Iceberg snapshot metadata (`ingested_at`, `load_date`) is sufficient for the initial load.

## Rationale

1. **Single-snapshot source.** College Scorecard Most-Recent-Cohorts-Institution.csv is a point-in-time file with no embedded period or year column. All 3,039 rows share the same load event.
2. **No valid-time semantics in source.** The publisher reports "the most recent reporting year" without identifying which year. Fabricating valid_from/valid_to would invent semantics the source does not support.
3. **No downstream PIT query requirement.** `consumable.career_outcomes`, the MCP server, and the backend all consume current state only. ROI formula needs one value per institution.
4. **Annual full-replace is the amendment model.** Future refreshes overwrite the whole file; Iceberg snapshot history already handles this without per-row supersession columns.
5. **Domain context explicitly directs SKIP.** The domain-context document (lines 85–102 and lines 199–208) flags @temporal-modeler as SKIP based on EDA findings.

## Trade-offs Considered

- Add synthetic `effective_date`: Rejected — duplicates `load_date` meaning while implying validity semantics.
- Add SCD Type 2 scaffolding now: Rejected — YAGNI for hackathon MVP; no consumer needs year-over-year comparisons.
- Add row-level supersession flags: Rejected — Iceberg snapshots are the correct mechanism for full-replace semantics.

## Future Trigger for Reassessment

Any spec that requests year-over-year cost trend analysis, cohort-historical ROI, or "cost at time of matriculation" semantics. At that point, choose between SCD Type 1 (overwrite) and SCD Type 2 (bitemporal) based on whether the new consumer needs historical values in the data itself or can be served by Iceberg time travel.

## Schema Impact

None. Bronze and Silver schemas in the spec already include the required provenance fields (`ingested_at`, `load_date`, `source_url`, `source_method`, `source_load_date`).

## Handoff

No downstream action required from @temporal-modeler. The spec proceeds to @dq-rule-writer and @primary-agent for Silver transform implementation without temporal schema work.
