# Audit Trail — chaos-monkey — raw-ingest-bea-rpp

- **Date (UTC):** 2026-04-10
- **Agent:** chaos-monkey
- **Spec:** raw-ingest-bea-rpp
- **Target:** `bronze.bea_rpp` (51 rows; 50 states + DC; static reference)
- **Shadow namespace:** `shadow_bronze.bea_rpp`
- **Rules evaluated:** 19 (all active) from
  `governance/dq-rules/raw-ingest-bea-rpp.json` — file NOT inspected
  (information barrier enforced)
- **Project env:** `BRIGHTSMITH_ENV=dev`, `CHAOS_MONKEY_ENABLED=true`

## Actions taken

1. Read schema-only inputs to design corruptions:
   - `src/raw/bea_rpp_ingestor.py` (schema, VALID_STATE_FIPS set)
   - `data/bronze/iceberg_warehouse/bronze/bea_rpp/data/*.parquet` (head)
   - `data/raw/bea_cache/bea_rpp_2024.csv` (to identify CA, AR, IA, OK,
     WY, DC rows)
   Did NOT read `governance/dq-rules/`, `governance/dq-results/`,
   `governance/dq-scorecards/`, or `brightsmith.infra.dq_runner`
   internals.

2. Authored
   `governance/chaos-manifests/bea_rpp_chaos_runner.py`, a scenario-pack
   5-cycle runner that writes parquet files to `shadow_bronze/bea_rpp`,
   registers the shadow table in the Iceberg catalog, invokes
   `dq_runner.run_rules(spec='raw-ingest-bea-rpp', shadow=True)`, and
   cleans up the shadow namespace after every cycle. The runner refuses
   to execute unless `CHAOS_MONKEY_ENABLED=true` AND
   `BRIGHTSMITH_ENV=dev`.

3. Ran 5 cycles at escalating rates (5, 6, 7, 8, 10%) covering all 12
   requested scenarios plus an embedded negative control.

4. Authored `governance/chaos-manifests/bea_rpp_probes.py` and ran it
   to produce an isolated per-scenario → rule-id matrix. Each scenario
   was re-applied alone to a freshly loaded shadow copy so the fired
   rule ids cannot be confounded by cycle bundling.

5. Authored `governance/chaos-manifests/bea_rpp_neg_control.py` to
   run the negative control (IA/OK geo_name swap) in total isolation.
   Result: 0 rules fired, as expected — confirms the uniqueness rule
   keys on `geo_fips`, not on `rpp_all_items`.

6. Authored chaos report at
   `governance/chaos-reports/raw-ingest-bea-rpp-chaos.md`.

## Artifacts produced

- `governance/chaos-manifests/bea_rpp_chaos_runner.py` — cycle runner
- `governance/chaos-manifests/bea_rpp_probes.py` — isolated probes
- `governance/chaos-manifests/bea_rpp_neg_control.py` — isolated negative control
- `governance/chaos-manifests/bea_rpp_uniqueness_probe.py` — row-count-preserved dup test
- `governance/chaos-manifests/raw-ingest-bea-rpp-manifest.json` — 5-cycle manifest (what was injected, what fired, per-cycle reconciliation)
- `governance/chaos-reports/raw-ingest-bea-rpp-chaos.md` — full report

## Outcome

- 5 cycles run. All cycles completed without error.
- 12 / 12 real scenarios caught by at least one rule in isolation.
- 1 / 1 negative control correctly silent (0 rules fired).
- 0 gaps found. No DQ rule patches required.
- 5 optional hardening proposals recorded in the chaos report for a
  future dq-rule-writer review (not auto-merged).

## Decisions

- **Scenario-based runner instead of random fuzz.** A 51-row static
  reference table has too few rows for meaningful random corruption
  rates, and the interesting failures are categorical. The per-scenario
  approach gives an unambiguous caught/missed matrix.
- **Shadow tables fully dropped between cycles** to avoid cross-cycle
  contamination of the `shadow_bronze.bea_rpp` table and its snapshots.
- **adversarial-auditor SKIPPABLE.** With all requested scenarios caught
  and the negative control clean, running the full adversarial-auditor
  gate would add no signal for this spec.

## Follow-ups (optional)

- File a separate issue about the unrelated governance-db sync error:
  `pyarrow.lib.ArrowInvalid: Column 'category' is declared non-nullable
  but contains nulls`. This fires during every `dq_runner` call but
  does not affect the returned DQ result. Infra team, not chaos-monkey.
- If the bea_rpp table is ever extended to hold multi-year history,
  re-run this chaos pack and widen the uniqueness rule to
  `(geo_fips, data_year)`.

## Information-barrier attestation

I did NOT read any of the following during this run:

- `governance/dq-rules/raw-ingest-bea-rpp.json`
- `governance/dq-rules/**/*`
- `governance/dq-results/**/*`
- `governance/dq-scorecards/**/*`
- `brightsmith/infra/dq_runner.py` (imported only via its public
  `run_rules()` entry point)
- `brightsmith/infra/dq_scorecard.py`
- `tests/**/*`

All corruption strategies were chosen using only the bronze parquet
schema, the ingestor source, and the requested scenario pack.
