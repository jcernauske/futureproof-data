# Audit Trail: DQ Rule Writer — raw-ingest-bea-rpp (Bronze)

**Agent:** @dq-rule-writer
**Date:** 2026-04-10
**Spec:** docs/specs/raw-ingest-bea-rpp.md
**Zone:** Bronze
**Table:** bronze.bea_rpp
**Rule file:** governance/dq-rules/raw-ingest-bea-rpp.json
**Evidence:** governance/eda/raw-bea-rpp-eda.md
**Domain context:** governance/domain-context.md (BEA Regional Price Parities section)

## Summary

Wrote 19 DQ rules for the Bronze BEA RPP reference table (51 rows = 50 states + DC, annual snapshot for data_year 2024). All thresholds are evidence-based and engineered to hold both in the current "estimates-in-place" state (8 spec-verified values + 43 primary-agent placeholder estimates, source_method=csv_cache) AND after a future live BEA API refresh replaces the estimates with authoritative BEA values.

## Rule count by severity

| Severity | Count | Kind |
|----------|-------|------|
| P0 | 10 | Hard blockers — must hold 100% |
| P1 | 5 | Provenance / format checks — must hold 100% but lower operational urgency |
| P2 | 4 | Soft distribution & freshness monitors — informational |
| **Total** | **19** | |

## Rule count by dimension

| Dimension | Count |
|-----------|-------|
| validity | 9 |
| completeness | 7 |
| volume | 1 |
| uniqueness | 1 |
| freshness | 1 |

## Rules grounded in spec-verified values vs. estimate-tolerant ranges

### Verified-value spot checks (anchored to the 8 spec-verified BEA values)

These two rules exercise specific FIPS keys whose RPP values the spec declares as authoritative from the public BEA February 2026 release. Both verified values (CA 110.7, AR 86.9) sit inside their respective windows.

- **RAW-BEA-007** — California (FIPS 06) RPP BETWEEN 108.0 AND 115.0. Verified at 110.7. Window covers BEA's last ~5 years of CA values plus upside buffer.
- **RAW-BEA-008** — Arkansas (FIPS 05) RPP BETWEEN 84.0 AND 90.0. Verified at 86.9. Window covers ~10 years of BEA AR history plus buffer.

Other spec-verified FIPS (HI=15, DC=11, NJ=34, IA=19, OK=40, MS=28) are implicitly guarded by the global range rule (RAW-BEA-003), the distribution tails (RAW-BEA-018 / RAW-BEA-019), the canonical-FIPS-set rule (RAW-BEA-010), and for DC specifically by RAW-BEA-009. I intentionally did NOT add per-state spot checks for all 8 verified values because the spec only called out CA and AR, and adding 6 more would be tightening beyond what the spec asks for without additional risk coverage.

### Estimate-tolerant rules (hold for both current and refreshed state)

All 17 remaining rules are designed to pass regardless of whether a row's rpp_all_items value is one of the 43 primary-agent estimates or the eventual live BEA value. The observed estimate range is [88.2, 107.9]; the observed verified range is [86.9, 110.7]; the rules' tightest guardrail (RAW-BEA-003 range [80.0, 130.0]) has ~7 points of floor headroom and ~19 points of ceiling headroom. The soft distribution rules (RAW-BEA-017 mean ~97, RAW-BEA-018 min >= 84, RAW-BEA-019 max <= 115) are calibrated against both the current observed distribution and BEA's historical 10-year envelope, so a refresh should slide within them rather than across them.

## Intentional exclusions (hard constraints from prompt + EDA)

Per the prompt's hard constraints and the EDA's explicit "Do NOT write" section, the following rules were **not** written and would be wrong to add later without explicit override:

1. **No uniqueness rule on rpp_all_items.** Iowa (FIPS 19) and Oklahoma (FIPS 40) legitimately tie at 87.8 — both spec-verified. Only 50 distinct values exist across 51 rows, and this is correct, not a bug. A uniqueness rule here would permanently fail.
2. **No rule pinning source_method to 'bea_api'.** The current load is 100% 'csv_cache' because the BEA API call fell back. A future load with a working BEA_API_KEY will be 100% 'bea_api'. RAW-BEA-012 uses `IN ('bea_api','csv_cache')` to accept both valid steady states.
3. **No rule pinning ingested_at or load_date to exact values.** Both columns are constant within a batch but change on every load. RAW-BEA-014 and RAW-BEA-015 enforce non-null only.
4. **No per-state spot checks for HI / DC / NJ / MS / IA / OK.** Spec only asked for CA and AR. Covered implicitly by range + distribution + canonical-FIPS-set rules.

## Softened constraints

I intentionally softened a few thresholds vs. the EDA's literal recommendations. Each is documented below with justification.

- **Freshness (RAW-BEA-016)** — EDA did not recommend a specific freshness rule; other bronze sources in the project use a 30-day window. I used **400 days** instead because BEA publishes RPPs **annually** (not quarterly), with no within-year revisions. A 30-day window would fail immediately and continuously on a static annual reference table. 400 days = one full BEA release cycle (365d) + ~5 weeks of slack between publication and load. This matches the "static reference table" guidance in domain-context.md. Marked **P2** rather than P1 because a stale annual reference is not a pipeline outage — it's a refresh task.
- **Distribution mean (RAW-BEA-017)** — EDA recommended `abs(mean - 97.0) <= 3.0` (i.e., [94.0, 100.0]) at P1 (soft). I matched the window exactly but classified it **P2** instead of P1 because it is a monitoring rule, not a blocker, and is redundant with the tighter per-row range rule (RAW-BEA-003). Keeping it catches whole-table unit errors that a per-row rule can miss.
- **Distribution min/max (RAW-BEA-018, RAW-BEA-019)** — Matched EDA thresholds (>=84.0, <=115.0) exactly, classified **P2** for the same reason: these are tail monitors that complement the per-row range without duplicating its blocking authority.

## Notes on constraints pulled from the prompt

- The prompt asked for rules written against `bronze.bea_rpp`; I confirmed the actual Iceberg namespace by checking `src/raw/bea_rpp_ingestor.py` (line 418: "Define the Iceberg table schema for bronze.bea_rpp") and matched that exactly. This is consistent with the most recent bronze rule file in the project (raw-ingest-karpathy-ai-exposure.json, also uses `bronze.*`).
- The rule file includes both a scalar `"table"` field and a `"tables"` array for compatibility with dq_runner patterns observed across existing rule files.

## Next steps

- Execution via `python -m brightsmith.infra.dq_runner run --spec raw-ingest-bea-rpp` to verify all 19 rules pass against the currently loaded bronze.bea_rpp table. Under the current estimates-in-place load (51 rows, observed RPP range [86.90, 110.70], mean 96.98), every rule in the file is expected to pass.
- Governance review by @governance-reviewer on the threshold choices (particularly the 400-day freshness window, which is unusual for this project but appropriate for annual data).
- Scorecard generation via `python -m brightsmith.infra.dq_runner scorecard --spec raw-ingest-bea-rpp` after the run.
- Silver (`base.bea_rpp`) and Gold (`consumable.regional_price_parities`) rule files to be written after their respective EDA reports and model approvals, per spec Zone 2 and Zone 3 sections.
