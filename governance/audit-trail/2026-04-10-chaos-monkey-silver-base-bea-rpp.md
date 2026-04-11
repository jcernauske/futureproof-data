# Audit Trail — @chaos-monkey — silver-base-bea-rpp

- **Agent:** @chaos-monkey
- **Spec:** `silver-base-bea-rpp`
- **Zone:** Silver
- **Date:** 2026-04-10
- **Target table:** `base.bea_rpp` (51 rows, 11 columns)
- **Shadow namespace:** `shadow_base.bea_rpp` in `data/silver/iceberg_warehouse`
- **Catalog:** `data/catalog/catalog.db` (catalog name: `brightsmith`)
- **Safety:** `CHAOS_MONKEY_ENABLED=true`, `BRIGHTSMITH_ENV=dev`. The
  real `base.bea_rpp` was never touched.

## Information barrier (enforced)

The following paths were NOT read by this agent during the run:

- `governance/dq-rules/silver-base-bea-rpp.json`
- `governance/dq-results/*`
- `governance/dq-scorecards/*`
- `tests/**`
- `src/brightsmith.infra/dq_runner.py`
- `src/brightsmith.infra/dq_scorecard.py`

`brightsmith.infra.dq_runner.run_rules` was imported as an opaque
function only and invoked with `spec="silver-base-bea-rpp"`,
`shadow=True`, and a catalog handle pointed at the Silver warehouse.

## Inputs used (allowed)

- `docs/specs/silver-base-bea-rpp.md` — derivation semantics and
  declared rules list (column names only, no rule IDs from the JSON).
- `src/silver/bea_rpp_transformer.py` — row transform, derivation
  helpers, grain fields.
- `src/silver/_us_state_reference.py` — FIPS→USPS, FIPS→region,
  BEA-verified FIPS allow-list.
- `data/silver/iceberg_warehouse/base/bea_rpp/data/*.parquet` —
  source data for shadow copy.
- `governance/chaos-manifests/bea_rpp_chaos_runner.py` — Bronze chaos
  template (pattern reuse only; scenarios are Silver-specific).
- `governance/chaos-manifests/silver_bls_ooh_chaos_runner.py` —
  Silver shadow/catalog wiring template.

## Artifacts produced

- `governance/chaos-manifests/silver_bea_rpp_chaos_runner.py` — 5-cycle
  + 2 negative control runner.
- `governance/chaos-manifests/silver_bea_rpp_probes.py` — per-scenario
  isolated probe runner (20 probes).
- `governance/chaos-manifests/silver_bea_rpp_extra_probes.py` — 8
  extra targeted probes (E1–E8).
- `governance/chaos-manifests/silver-base-bea-rpp-manifest.json` —
  full cycle manifest with DQ reconciliation per cycle.
- `governance/chaos-manifests/silver-base-bea-rpp-probes.json` —
  per-scenario → fired-rule-id matrix (main pack).
- `governance/chaos-manifests/silver-base-bea-rpp-extra-probes.json` —
  per-scenario → fired-rule-id matrix (extra probes).
- `governance/chaos-reports/silver-base-bea-rpp-chaos.md` — final
  report: cycles, matrix, gaps, proposals, verdict.
- `governance/audit-trail/2026-04-10-chaos-monkey-silver-base-bea-rpp.md`
  — this file.

## Actions taken (chronological)

1. Read the spec (`docs/specs/silver-base-bea-rpp.md`) and the
   transformer (`src/silver/bea_rpp_transformer.py`). Confirmed the
   11-column Silver schema, the 8-state `BEA_VERIFIED_FIPS` allow-list,
   the 9/12/17/13 Northeast/Midwest/South/West distribution, and the
   single `data_year=2024` vintage.
2. Verified the silver parquet contents directly via pyarrow: 51 rows,
   8 `bea_official` + 43 `estimate`, correct region distribution.
3. Wrote `silver_bea_rpp_chaos_runner.py` using the Bronze chaos
   runner as a structural template, adapted to:
   - point the catalog at `data/silver/iceberg_warehouse` instead of
     Bronze;
   - use the 11-column Silver shadow schema with all fields optional
     so corrupted/null data can land;
   - drop any dependency on `source_url` / `source_method` / raw
     Bronze columns (which don't exist in Silver);
   - encode 20 Silver-specific scenarios + 2 negative controls
     covering `state_abbr`, `census_region`,
     `purchasing_power_multiplier`, `verification_status`,
     Silver↔Bronze passthrough, spot-check drift, `data_year`,
     `record_id`, and swap negatives.
4. Ran the 7-cycle pack. All 5 real cycles fired at least one rule.
   Both negative controls fired zero rules. Noted that SIL-BEA-018
   is always in ERROR state, including on the noop.
5. Wrote `silver_bea_rpp_probes.py` to re-run each of the 20 distinct
   scenarios in isolation against a clean shadow copy, producing an
   unambiguous per-scenario → rule-id matrix. Every real scenario
   caught at least once; both negative controls silent.
6. Identified that `scenario_passthrough_break` (CA rpp 110.7 → 105.0)
   only fires SIL-BEA-021 (the inverse invariant), not any dedicated
   Silver↔Bronze rule. This raised a concrete hypothesis: there is no
   effectively-runnable cross-zone passthrough rule in shadow mode.
7. Wrote `silver_bea_rpp_extra_probes.py` with 8 targeted probes to
   test edge cases the main pack did not isolate:
   - E1 confirmed the passthrough gap: a self-consistent divergence
     on CA was caught only by the CA-row spot check (SIL-BEA-031).
   - E6 confirmed a second gap: `state_fips='99'` slipped through
     with zero fires.
   - E2–E5, E7, E8 were cleanly caught.
8. Wrote the chaos report with the caught/missed matrix, gaps,
   and hardening proposals.
9. Cleaned up all shadow state — the `shadow_base.bea_rpp` table was
   dropped from the catalog and the shadow directory removed at the
   end of every cycle (belt + suspenders cleanup in `main()`).

## Findings summary

- **Cycles run:** 5 real + 2 negative controls = 7 total.
- **Main-pack scenarios:** 20 total (18 real, 2 negative controls).
- **Main-pack caught:** 18 / 18 real scenarios caught; 2 / 2
  negative controls silent.
- **Extra probes:** 8 total. 6 cleanly caught; 2 real gaps.
- **Real gaps:**
  - **Gap 1:** self-consistent Silver↔Bronze `rpp_all_items`
    divergence is caught only by the CA and DC spot-check rules.
    A non-CA, non-DC divergence would ship silently.
  - **Gap 2:** an unknown `state_fips` value (e.g., `'99'`) passes
    every existing rule.
- **Pre-existing rule issue:** `SIL-BEA-018` errors on every cycle
  including the no-op. Most likely the Bronze passthrough rule that
  does not know how to handle shadow-mode rewriting of a cross-zone
  join. This is Gap 3 in the report and the root cause of Gap 1.
- **Proposed new rules:** listed in the report as hardening proposals
  1–7. NOT silently added. They require dq-rule-writer review.

## Decisions

- **Proceeded with scenario-based chaos rather than rate-based
  fuzzing** because the table is a 51-row closed-set reference table
  and numeric fuzzing on a 51-row corpus is useless.
- **Used the existing Silver shadow pattern from
  `silver_bls_ooh_chaos_runner.py`** so the catalog, shadow namespace,
  and DQ runner wiring match prior Silver chaos runs on this project.
- **Did NOT attempt to patch SIL-BEA-018** — chaos monkey does not
  write DQ rules, per the information barrier. The broken rule is
  flagged to dq-rule-writer in the chaos report.
- **Did NOT silently add new rules.** Gap 1, Gap 2, and hardening
  proposals 1–7 are listed as recommendations, not merged.
- **Classified SIL-BEA-018 ERRORs as a third state** (distinct from
  both PASS and FAIL) in the reconciler so per-scenario caught/missed
  attribution remains clean and the negative controls are not
  trivially flagged as false positives.

## Downstream recommendation

The "zero gaps in ≥5 cycles → adversarial-auditor can be skipped"
condition is **not met**. The adversarial-auditor should see this
report before staff review. Specifically, the auditor should
adjudicate:

1. Whether Gap 1 / Gap 3 (SIL-BEA-018) is a blocking defect or an
   acceptable shadow-mode carve-out.
2. Whether Gap 2 (state_fips canonical set) requires a spec
   amendment or is adequately covered by the transformer-side
   validator `_validate_state_fips`.
3. Whether any of the optional hardening proposals should be
   promoted into this release or deferred.

## Cleanup verification

- `shadow_base.bea_rpp` dropped from the catalog.
- `data/silver/iceberg_warehouse/shadow_base/bea_rpp/` removed.
- Real `base.bea_rpp` unchanged — verified by the 51-row / 8
  bea_official distribution still matching the snapshot loaded at
  the start of the run.
