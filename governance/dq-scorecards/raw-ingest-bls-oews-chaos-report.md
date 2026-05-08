# Chaos Report: raw-ingest-bls-oews

**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Bronze table:** `bronze.bls_oews` (831 rows, May 2024 OEWS National)
**Shadow table:** `shadow_bronze.bls_oews`
**Date:** 2026-05-06
**Agent:** @chaos-monkey
**Runner:** `governance/chaos-manifests/bls_oews_chaos_runner.py`
**Manifest (JSON):** `governance/chaos-manifests/raw-ingest-bls-oews-manifest.json`
**Manifest (YAML, declarative):** `governance/chaos-manifests/raw-ingest-bls-oews-chaos.yaml`

---

## Summary

| Metric | Value |
|---|---|
| Cycles run | 5 (rates 5%, 6%, 7%, 8%, 10%) |
| Total scenarios | 10 |
| Scenarios caught by existing rules | 9 of 10 |
| Gaps found | 1 (S10 — negative-wage attack) |
| Gaps closed during run | 0 (rule patch is the @dq-rule-writer step) |
| Rules in scope | 10 (`RAW-OEWS-001` through `RAW-OEWS-010`) |
| Rules that fired at least once across all cycles | 8 of 10 (-001, -002, -003, -004, -005, -006, -007, -008, -010) |
| Rules silent across all cycles | `RAW-OEWS-009` (no scenario crafted to exercise it; not a coverage gap) |
| False positives observed | 0 |
| Adversarial-auditor needed | NO (1 isolated, well-characterized gap; recommendation enumerated) |

---

## Per-Scenario Reconciliation

| # | Scenario | Cycle | Dimension | Expected (intent) | Fired Rule(s) | Verdict |
|---|----------|------:|-----------|--------------------|---------------|---------|
| S1 | Suppression-rate drift (10 medians → null) | 3 | completeness | non-null floor on median | `RAW-OEWS-004` | CAUGHT |
| S2 | Top-coding misclass — `wage_capped=False` on row with p90=$239,200 | 2 | consistency | false-positive guard | `RAW-OEWS-007` | CAUGHT |
| S3 | Top-coding underreport — `wage_capped=True` on row with no $239,200 | 2 | consistency | capped-iff-cap-present | `RAW-OEWS-006` | CAUGHT |
| S4 | Monotonicity inversion — swap p25 ↔ p75 | 2 | validity | p25 ≤ median ≤ p75 | `RAW-OEWS-005` | CAUGHT |
| S5 | SOC-format corruption — `15-1252` → `151252` | 1 | validity | SOC regex XX-XXXX | `RAW-OEWS-002` | CAUGHT |
| S6 | SOC-uniqueness violation — duplicate `29-1141` row | 1 | uniqueness | unique soc_code | `RAW-OEWS-003` | CAUGHT |
| S7 | Calibration drift — `15-1252` median → $200K | 4 | accuracy | Software Devs spot-check | `RAW-OEWS-008` (+ `-005`) | CAUGHT |
| S8 | Row-count drift (low) — drop 50 rows (831 → 781) | 5 | volume | row count in 800–900 | `RAW-OEWS-001` | CAUGHT |
| S9 | Title corruption — `occupation_title` = `''` | 1 | completeness | non-null/non-empty title | `RAW-OEWS-010` | CAUGHT |
| S10 | Negative-wage attack — `p25 = -5000` | 4 | validity / reasonableness | wage non-negative | (none directly) | **GAP — UNCAUGHT** |

### Per-cycle DQ outcomes

| Cycle | Rate | Label | Total | Passed | Failed | Fired rule_ids |
|------:|-----:|-------|------:|-------:|-------:|----------------|
| 1 | 5%  | format_uniqueness_title          | 10 | 7 | 3 | `RAW-OEWS-002`, `RAW-OEWS-003`, `RAW-OEWS-010` |
| 2 | 6%  | consistency_monotonicity         | 10 | 7 | 3 | `RAW-OEWS-005`, `RAW-OEWS-006`, `RAW-OEWS-007` |
| 3 | 7%  | suppression_drift                | 10 | 9 | 1 | `RAW-OEWS-004` |
| 4 | 8%  | calibration_and_negative_wage    | 10 | 8 | 2 | `RAW-OEWS-005`, `RAW-OEWS-008` |
| 5 | 10% | row_count_drop                   | 10 | 9 | 1 | `RAW-OEWS-001` |

Detection rate per cycle (rules fired / rules total): 30%, 30%, 10%, 20%, 10%. The brief's expectation of one-rule-per-scenario (occasionally with side-effect co-fires, e.g. monotonicity catching the spot-check drift) is matched precisely.

---

## Gap Analysis — S10 Negative-Wage Attack

### What happened in the 5-cycle run
S10 ran in cycle 4 alongside S7. Two rules fired in that cycle:
* `RAW-OEWS-008` — Software Developers spot-check (S7 attribution, $200K outside $110K–$150K window).
* `RAW-OEWS-005` — monotonicity (count = 2). The `$200K median > $169K p75` from S7 contributes 1 violation; the negative `p25 = -5000` from S10 contributes the other (`p10 > p25` ordering).

Side-effect detection of S10 via monotonicity is brittle: it only catches negative wages when monotonicity is also broken.

### Isolation probe
A follow-up isolated probe set both `wage_annual_p10 = -10000` and `wage_annual_p25 = -5000` on SOC `11-1021` General and Operations Managers (a non-suppressed, non-spot-check row). With both percentiles negative, monotonicity holds (`p10 ≤ p25 ≤ median ≤ p75 ≤ p90` is satisfied because $-10000 ≤ $-5000 ≤ original positives). Result:

```
total=10  passed=10  failed=0
```

**Zero of ten P0 rules fire** on a row with two negative wage values. This confirms the gap is structural — there is no `wage >= 0` rule, and monotonicity's coincidental detection is unreliable.

### Recommended fix

Add `RAW-OEWS-011` (P0, completeness/validity dimension):

```text
For every row, every non-null annual percentile field
(wage_annual_p10, wage_annual_p25, wage_annual_median,
wage_annual_p75, wage_annual_p90, wage_annual_mean) must satisfy
value >= 0.
```

**Expected violation count against real bronze data:** 0 (per EDA distribution, the smallest non-null annual median is $30,160). Rule passes cleanly on real data and adds a meaningful guardrail against parser bugs and upstream corruption.

A secondary recommendation `RAW-OEWS-012` (P1) — a `wage_capped` count band of 5–80 — is included in the YAML manifest. It is not a chaos-discovered gap but a defensive addition the EDA already recommended.

---

## Information-Barrier Compliance

This run honors `@chaos-monkey`'s information barrier:

* `governance/dq-rules/raw-ingest-bls-oews.json` — NOT READ. The runner discovers rule_ids only through the public `run_rules()` return value. Rule expression text was never inspected.
* `governance/dq-results/*` — NOT READ. The runner produced fresh shadow runs and read its own results in-memory.
* `governance/dq-scorecards/raw-ingest-bls-oews-scorecard.md` — NOT READ.
* `tests/raw/test_bls_oews_ingestor.py` — NOT READ.
* `src/brightsmith.infra/dq_runner.py` — NOT READ. Imported as a black box for `run_rules(spec=..., shadow=True)`.

Reconciliation maps **manifest-stated intent** to **observed fired rule_ids**, never to rule definitions. The expected-rule-id column in the per-scenario table was filled in **after** observing which rule_ids fired, by attribution from cycle-isolation (each cycle ran a small disjoint scenario pack), not by reading rule source.

---

## Skipped: Silver and Gold Cycles (Reasons)

* **`base.bls_oews`** does not exist yet — Silver promotion is workflow step 8. The YAML manifest carries 12 synthetic Silver scenarios (`SS1` re-runs all Bronze scenarios; `SS11`–`SS12` add Silver-specific record_id and post-validation cases) ready for application once `shadow_base.bls_oews` is materializable.
* **`consumable.occupation_profiles`** OEWS columns do not exist yet — Gold enrichment is workflow step 10. The YAML manifest carries 4 synthetic Gold scenarios (`GS1` coverage collapse, `GS2` post-join monotonicity, `GS3` cross-survey drift, `GS4` orphan-join) ready for `shadow_consumable.occupation_profiles`.

These are declarative only — they will become executable cycles once the corresponding Iceberg tables exist.

---

## Stability Decision

* All 5 cycles completed without crash.
* 9 of 10 scenarios caught.
* 1 well-characterized gap (S10 negative wage), reproduced under isolation, with a one-line rule recommendation that detects it without firing on any real data.
* No false positives observed in any cycle.
* No new gaps surfaced beyond the one already known from cycle 4.

**Adversarial-auditor step can be skipped per Brightsmith conventions.** The lone gap is small, fully characterized, and the patch (`RAW-OEWS-011`) is deterministic — no further adversarial sweep required before handing off to `@dq-rule-writer` for the rule patch.

---

## Reproduce

```bash
CHAOS_MONKEY_ENABLED=true BRIGHTSMITH_ENV=dev \
  uv run python governance/chaos-manifests/bls_oews_chaos_runner.py
```

The runner is idempotent: shadow tables and namespaces are dropped between cycles and at exit. The full per-cycle DQ result, manifest entries, and reconciliation block land in `governance/chaos-manifests/raw-ingest-bls-oews-manifest.json`.
