# Audit Trail: @temporal-modeler — BLS OEWS

**Date:** 2026-05-06
**Agent:** @temporal-modeler
**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Artifact produced:** `governance/temporal-models/raw-bls-oews-temporal-assessment.md`
**Verdict:** NON_TEMPORAL

---

## Decisions Made

1. **Verdict: NON_TEMPORAL** for `bronze.bls_oews`, `base.bls_oews`, and the four new OEWS columns added to `consumable.occupation_profiles` / `consumable.program_career_paths`.
2. **Spec schema is sufficient as written.** No new temporal columns added. `source_load_date` and `ingested_at` are batch stamps / provenance, not per-row event times.
3. **No bitemporal modeling, no SCD2, no supersession metadata, no point-in-time query support** required at any zone for the hackathon scope.
4. **Recommended future upgrade path** (when a May 2025+ vintage lands and a downstream multi-vintage need is real): append-with-`reference_period`, partition-overwrite by `reference_period`, Gold transformer hard-codes `MAX(reference_period)` to keep the consumable single-vintage. Reject SCD2 even at upgrade time. Documented in the assessment §"Question 3".
5. **Optional v1 DQ hardening:** add `COUNT(DISTINCT source_load_date) = 1` rule to force an explicit decision when the single-vintage contract is broken. Mirrors the BEA RPP `data_year cardinality = 1` rule. Recommendation only — not implemented in this artifact; flagged for @dq-rule-writer.

---

## Rationale

- Domain context (`governance/domain-context.md` §"Temporal Patterns (BLS OEWS)" lines 2672-2686) explicitly authorizes skipping bitemporal modeling: *"Treat as a non-temporal snapshot table for now."*
- Spec §"Future Enhancements" items 1 (ERN v2 from OEWS spread) and 3 (OEWS time series) are explicitly out of scope, so no current consumer needs cross-vintage queries.
- Iceberg snapshots provide all needed transaction-time history for free. `AT (TIMESTAMP => ...)` time travel recovers the May 2024 vintage from any future point without schema work.
- Strong precedent in this repo for non-temporal verdict on annual-snapshot reference data: `governance/temporal/raw-ingest-bea-rpp.md` (BEA RPP single-year, full-replace) and `governance/temporal-models/raw-ipeds-finance-temporal-assessment.md` (IPEDS Finance single-fiscal-year, NOT APPLICABLE).

---

## Trade-offs Considered

| Option | Pros | Cons | Selected? |
|---|---|---|---|
| Non-temporal flat snapshot (selected) | Simple, matches domain authority, matches precedent, zero migration cost for v1 | Requires future migration if multi-vintage analysis lands | YES |
| Bitemporal (`valid_from`/`valid_to`/`is_correction`) | Maximally flexible | No per-row validity variation in the data; no per-cell amendments to model; pure overhead today | NO |
| SCD2 (`valid_from`/`valid_to`/`is_current`) | Standard SCD pattern | No within-vintage fact evolution to track; cross-vintage is a discrete attribute (`reference_period`), not an interval; SCD2 buys nothing over partition-by-`reference_period` | NO (rejected even at upgrade time) |
| Append-with-`reference_period` from v1 | Pre-empts future migration | Premature complexity; v1 only has one vintage, so `WHERE reference_period = 'May 2024'` is equivalent to "all rows"; DQ rules become more complex for no current benefit | NO (recommended only as a future migration path) |

---

## Domain-Specific Considerations

- **Top-code floor drift:** When BLS raises the top-code floor (2023's $208K -> $239,200), the set of capped SOCs and the value of capped percentiles changes simultaneously. Year-over-year wage-distribution trend analyses will need to account for this discontinuity. Out of scope for v1; flagged in the assessment for the future-migration spec.
- **Hourly-vs-annual asymmetry:** For salaried-only occupations BLS surveys annual directly and suppresses hourly. Not a temporal concern; documented in domain context.
- **OEWS ≠ OOH median reconciliation:** Domain context warns *"never write a DQ rule that compares OOH median to OEWS median — methodology drift is intrinsic, not a quality issue."* Not a temporal concern but worth noting for any future cross-source temporal join.

---

## Files Touched

- `governance/temporal-models/raw-bls-oews-temporal-assessment.md` — created (full assessment).
- `governance/audit-trail/2026-05-06-temporal-modeler-bls-oews.md` — this file.

No source code, no schema files, no DQ rule files, no contract files were modified. The verdict is **non-implementation** — the spec already carries the correct minimal schema.

---

*— End of Audit Trail —*
