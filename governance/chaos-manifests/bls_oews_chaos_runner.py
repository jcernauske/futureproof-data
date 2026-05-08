"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec:  raw-ingest-bls-oews
Table: bronze.bls_oews (~831 detailed-occupation rows, May 2024 OEWS National)
Shadow namespace: shadow_bronze.bls_oews

Curated, spec-driven scenario runner — each cycle applies a fixed pack of
named OEWS-specific scenarios from the chaos brief.  We follow the same
pattern as governance/chaos-manifests/bea_rpp_chaos_runner.py (the modern
shadow_bronze namespace convention; bls_ooh_chaos_runner.py is the older
shadow_raw style).

Information Barrier
-------------------
This script does NOT read:
  - governance/dq-rules/raw-ingest-bls-oews.json
  - governance/dq-results/*
  - governance/dq-scorecards/*
  - tests/* or src/brightsmith.infra/dq_runner.py

The dq runner is invoked through its public ``run_rules()`` entry point
only and we observe rule_ids returned from that call — we do NOT inspect
rule definitions.  Reconciliation is structural (manifest dimensions vs
fired rule_ids).

Scenarios (per the user brief)
------------------------------
1.  Suppression-rate drift   — null 10 wage_annual_medians
2.  Top-coding misclass      — flip wage_capped=False on a $239,200 p90 row
3.  Top-coding underreport   — flip wage_capped=True on a row with no $239,200
4.  Monotonicity inversion   — swap p25 and p75 on one row
5.  SOC-format corruption    — replace 15-1252 with 151252 (no hyphen)
6.  SOC-uniqueness violation — duplicate one row preserving soc_code
7.  Calibration drift        — set 15-1252 (Software Devs) median to $200K
8.  Row-count drift (low)    — drop 50 rows (831 -> 781 falls below 800 floor)
9.  Title corruption         — set occupation_title = '' on one row
10. Negative-wage attack     — set p25 = -5000 on one row (gap probe; may be
                               uncovered today)
"""

from __future__ import annotations

import copy
import datetime
import json
import os
import shutil
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
BRONZE_WAREHOUSE = PROJECT_ROOT / "data" / "bronze" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"
SOURCE_PARQUET = (
    BRONZE_WAREHOUSE
    / "bronze"
    / "bls_oews"
    / "data"
    / "00000-0-0c40df8f-3c88-42af-83ed-922ced6804dd.parquet"
)
SHADOW_DIR = BRONZE_WAREHOUSE / "shadow_bronze" / "bls_oews"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

SPEC_NAME = "raw-ingest-bls-oews"
SHADOW_FQN = "shadow_bronze.bls_oews"

SEED_BASE = 42

sys.path.insert(0, str(PROJECT_ROOT / "src"))

from brightsmith.config import configure  # noqa: E402

configure(project_root=str(PROJECT_ROOT), project_name="brightsmith")


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def safety_check() -> None:
    os.environ["CHAOS_MONKEY_ENABLED"] = "true"
    os.environ["BRIGHTSMITH_ENV"] = "dev"
    enabled = os.environ.get("CHAOS_MONKEY_ENABLED", "").lower() == "true"
    dev_env = os.environ.get("BRIGHTSMITH_ENV", "").lower() == "dev"
    if not enabled:
        print("ERROR: CHAOS_MONKEY_ENABLED is not 'true'.")
        sys.exit(1)
    if not dev_env:
        print("ERROR: BRIGHTSMITH_ENV is not 'dev'.")
        sys.exit(1)
    print("Safety: CHAOS_MONKEY_ENABLED=true, BRIGHTSMITH_ENV=dev")


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_source_rows():
    import pyarrow.parquet as pq

    t = pq.read_table(str(SOURCE_PARQUET))
    rows = [dict(r) for r in t.to_pylist()]
    return rows, t.schema


def rows_to_arrow(rows, original_schema):
    import pyarrow as pa

    arrays = {}
    for field in original_schema:
        col_name = field.name
        values = [r.get(col_name) for r in rows]
        try:
            arrays[col_name] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError):
            arrays[col_name] = pa.array(values)
    return pa.table(arrays)


def write_shadow_parquet(arrow_table, cycle_num):
    import pyarrow.parquet as pq

    SHADOW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHADOW_META_DIR.mkdir(parents=True, exist_ok=True)
    out = SHADOW_DATA_DIR / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out))
    return out


def register_shadow(parquet_path):
    """Register shadow table in catalog, replacing any prior copy.

    All fields are declared optional in the shadow schema so corrupted /
    null / wrong-type values can land without failing the Iceberg writer.
    """
    from brightsmith.infra.iceberg_setup import get_catalog
    import pyarrow.parquet as pq
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType,
        DateType,
        DoubleType,
        LongType,
        NestedField,
        StringType,
        TimestampType,
    )

    catalog = get_catalog(str(BRONZE_WAREHOUSE), str(CATALOG_PATH))
    try:
        catalog.create_namespace("shadow_bronze")
    except Exception:
        pass
    try:
        catalog.drop_table(SHADOW_FQN)
    except Exception:
        pass

    schema = Schema(
        NestedField(1, "soc_code", StringType(), required=False),
        NestedField(2, "occupation_title", StringType(), required=False),
        NestedField(3, "total_employment", LongType(), required=False),
        NestedField(4, "wage_annual_p10", DoubleType(), required=False),
        NestedField(5, "wage_annual_p25", DoubleType(), required=False),
        NestedField(6, "wage_annual_median", DoubleType(), required=False),
        NestedField(7, "wage_annual_p75", DoubleType(), required=False),
        NestedField(8, "wage_annual_p90", DoubleType(), required=False),
        NestedField(9, "wage_annual_mean", DoubleType(), required=False),
        NestedField(10, "wage_hourly_median", DoubleType(), required=False),
        NestedField(11, "wage_capped", BooleanType(), required=False),
        NestedField(12, "ingested_at", TimestampType(), required=False),
        NestedField(13, "source_url", StringType(), required=False),
        NestedField(14, "source_method", StringType(), required=False),
        NestedField(15, "load_date", DateType(), required=False),
    )
    tbl = catalog.create_table(SHADOW_FQN, schema=schema)
    data = pq.read_table(str(parquet_path))
    tbl.append(data)
    return tbl


def run_dq_rules_shadow():
    from brightsmith.infra.dq_runner import run_rules

    return run_rules(spec=SPEC_NAME, shadow=True)


def cleanup_shadow():
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR, ignore_errors=True)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog

        catalog = get_catalog(str(BRONZE_WAREHOUSE), str(CATALOG_PATH))
        try:
            catalog.drop_table(SHADOW_FQN)
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_idx_by_soc(rows, soc_code):
    for i, r in enumerate(rows):
        if r.get("soc_code") == soc_code:
            return i
    return None


def _find_indices_with_p90_at_cap(rows):
    """Indices of rows where wage_annual_p90 == 239200 and wage_capped is True."""
    out = []
    for i, r in enumerate(rows):
        if r.get("wage_annual_p90") == 239200.0 and r.get("wage_capped") is True:
            out.append(i)
    return out


def _find_indices_no_cap(rows):
    """Indices of rows where NO annual percentile equals 239200 and wage_capped is False."""
    out = []
    for i, r in enumerate(rows):
        if r.get("wage_capped") is True:
            continue
        ps = [
            r.get("wage_annual_p10"),
            r.get("wage_annual_p25"),
            r.get("wage_annual_median"),
            r.get("wage_annual_p75"),
            r.get("wage_annual_p90"),
        ]
        if any(p == 239200.0 for p in ps):
            continue
        # Also require non-null core percentiles so the row is "real"
        if r.get("wage_annual_median") is None:
            continue
        out.append(i)
    return out


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_1_suppression_drift(rows, n=10):
    """S1 — suppression-rate drift: null wage_annual_median on n rows.

    Bronze EDA shows 5 rows already have null medians (the 27-2xxx
    performance-arts cluster).  Adding 10 more nulls drops the non-null
    rate from 99.40% to 98.20%, which should breach a "≥ 99% non-null"
    floor on wage_annual_median (the spec's tightened threshold).
    """
    entries = []
    # Pick rows that currently HAVE a non-null median; never re-null an
    # already-null row (the existing 5 suppressions).
    candidates = [
        i for i, r in enumerate(rows)
        if r.get("wage_annual_median") is not None
    ]
    if len(candidates) < n:
        n = len(candidates)
    targets = candidates[100:100 + n]  # deterministic slice
    for i in targets:
        old = rows[i]["wage_annual_median"]
        rows[i]["wage_annual_median"] = None
        entries.append(
            {
                "scenario": "S1_suppression_drift",
                "dimensions": ["completeness"],
                "field": "wage_annual_median",
                "strategy": "null_required_field",
                "soc_code": rows[i].get("soc_code"),
                "old_value": str(old),
                "new_value": "null",
                "expected_rule_intent": "non_null_floor_on_wage_annual_median",
            }
        )
    return entries


def scenario_2_topcode_misclass_false(rows):
    """S2 — top-coding misclass (false-positive guard).

    Find a row with p90 == 239200 and wage_capped=True; flip wage_capped
    to False.  A "wage_capped reflects reality" rule should fire because
    the row HAS a percentile at the cap but is no longer flagged.
    """
    entries = []
    candidates = _find_indices_with_p90_at_cap(rows)
    if not candidates:
        return entries
    i = candidates[0]
    old = rows[i]["wage_capped"]
    rows[i]["wage_capped"] = False
    entries.append(
        {
            "scenario": "S2_topcode_misclass_capped_false",
            "dimensions": ["consistency"],
            "field": "wage_capped",
            "strategy": "flip_capped_to_false_with_p90_at_cap",
            "soc_code": rows[i].get("soc_code"),
            "old_value": str(old),
            "new_value": "False",
            "expected_rule_intent": "wage_capped_iff_some_percentile_at_239200",
        }
    )
    return entries


def scenario_3_topcode_underreport_true(rows):
    """S3 — top-coding underreporting.

    Find a row with NO percentile at 239200 (and wage_capped=False);
    flip wage_capped to True.  A "wage_capped only when at least one
    percentile = 239200" rule should fire because the flag is now true
    without the underlying signal.
    """
    entries = []
    candidates = _find_indices_no_cap(rows)
    if not candidates:
        return entries
    # Use a row well-known to be uncapped (Software Developers if available
    # but not the spot-check SOC; use Registered Nurses 29-1141 instead)
    pref_idx = _find_idx_by_soc(rows, "29-1141")
    i = pref_idx if pref_idx in candidates else candidates[0]
    old = rows[i]["wage_capped"]
    rows[i]["wage_capped"] = True
    entries.append(
        {
            "scenario": "S3_topcode_underreport_capped_true",
            "dimensions": ["consistency"],
            "field": "wage_capped",
            "strategy": "flip_capped_to_true_without_239200_percentile",
            "soc_code": rows[i].get("soc_code"),
            "old_value": str(old),
            "new_value": "True",
            "expected_rule_intent": "wage_capped_only_when_some_percentile_at_239200",
        }
    )
    return entries


def scenario_4_monotonicity_swap(rows):
    """S4 — monotonicity inversion: swap p25 and p75 on one row.

    Pick a row with full annual data and swap p25 ↔ p75.  A
    "p25 ≤ median ≤ p75" rule should fire on this row.
    """
    entries = []
    # Use Nurse Practitioners 29-1171 — a known full-data row from the EDA
    i = _find_idx_by_soc(rows, "29-1171")
    if i is None:
        # fallback: first row with full annual data
        for k, r in enumerate(rows):
            if all(
                r.get(f) is not None
                for f in (
                    "wage_annual_p25",
                    "wage_annual_median",
                    "wage_annual_p75",
                )
            ):
                i = k
                break
    if i is None:
        return entries
    old_p25 = rows[i]["wage_annual_p25"]
    old_p75 = rows[i]["wage_annual_p75"]
    rows[i]["wage_annual_p25"] = old_p75
    rows[i]["wage_annual_p75"] = old_p25
    entries.append(
        {
            "scenario": "S4_monotonicity_swap_p25_p75",
            "dimensions": ["validity", "consistency"],
            "field": "wage_annual_p25,wage_annual_p75",
            "strategy": "swap_p25_p75",
            "soc_code": rows[i].get("soc_code"),
            "old_value": f"p25={old_p25},p75={old_p75}",
            "new_value": f"p25={old_p75},p75={old_p25}",
            "expected_rule_intent": "monotonic_p25_le_median_le_p75",
        }
    )
    return entries


def scenario_5_soc_format_corruption(rows):
    """S5 — SOC-format corruption: replace 15-1252 with 151252 (no hyphen)."""
    entries = []
    i = _find_idx_by_soc(rows, "15-1252")
    if i is None:
        return entries
    old = rows[i]["soc_code"]
    rows[i]["soc_code"] = "151252"
    entries.append(
        {
            "scenario": "S5_soc_format_corruption",
            "dimensions": ["validity"],
            "field": "soc_code",
            "strategy": "strip_hyphen",
            "soc_code": "151252",
            "old_value": old,
            "new_value": "151252",
            "expected_rule_intent": "soc_regex_XX-XXXX",
        }
    )
    return entries


def scenario_6_soc_uniqueness_violation(rows):
    """S6 — SOC-uniqueness violation: duplicate one row preserving soc_code."""
    entries = []
    i = _find_idx_by_soc(rows, "29-1141")
    if i is None:
        return entries
    dupe = copy.deepcopy(rows[i])
    rows.append(dupe)
    entries.append(
        {
            "scenario": "S6_soc_uniqueness_violation",
            "dimensions": ["uniqueness", "volume"],
            "field": "soc_code",
            "strategy": "duplicate_row_same_soc",
            "soc_code": "29-1141",
            "old_value": "1 row",
            "new_value": "2 rows (same soc_code)",
            "expected_rule_intent": "unique_soc_code",
        }
    )
    return entries


def scenario_7_calibration_drift(rows):
    """S7 — calibration drift: 15-1252 (Software Developers) median = $200K.

    Real value is $133,080.  $200K is well outside the spec's spot-check
    window of $110K–$150K.
    """
    entries = []
    i = _find_idx_by_soc(rows, "15-1252")
    if i is None:
        return entries
    old = rows[i]["wage_annual_median"]
    rows[i]["wage_annual_median"] = 200000.0
    entries.append(
        {
            "scenario": "S7_calibration_drift_softdev",
            "dimensions": ["accuracy"],
            "field": "wage_annual_median",
            "strategy": "spot_check_drift_softdev_to_200k",
            "soc_code": "15-1252",
            "old_value": str(old),
            "new_value": "200000.0",
            "expected_rule_intent": "spot_check_softdev_median_in_110k_150k",
        }
    )
    return entries


def scenario_8_rowcount_drop_50(rows):
    """S8 — row-count drift (low): drop 50 rows.

    831 - 50 = 781, which falls below the spec's lower bound of 800.
    Avoid dropping the spot-check SOCs (15-1252, 29-1141, 29-1171, 11-1011)
    so spot-check rules don't error out for "row not found".
    """
    entries = []
    spot_check_socs = {"15-1252", "29-1141", "29-1171", "11-1011"}
    deletable = [
        i for i, r in enumerate(rows)
        if r.get("soc_code") not in spot_check_socs
    ]
    targets = sorted(deletable[:50], reverse=True)
    n_drop = 0
    for i in targets:
        rows.pop(i)
        n_drop += 1
    entries.append(
        {
            "scenario": "S8_rowcount_drop_50",
            "dimensions": ["volume"],
            "field": "row_count",
            "strategy": "drop_50_rows",
            "old_value": str(n_drop + len(rows)),
            "new_value": str(len(rows)),
            "expected_rule_intent": "row_count_floor_800",
        }
    )
    return entries


def scenario_9_title_corruption(rows):
    """S9 — title corruption: occupation_title = '' on one row."""
    entries = []
    # Pick a non-spot-check row so other rules aren't disturbed.
    for i, r in enumerate(rows):
        if r.get("soc_code") not in {
            "15-1252",
            "29-1141",
            "29-1171",
            "11-1011",
        }:
            break
    else:
        return entries
    old = rows[i]["occupation_title"]
    rows[i]["occupation_title"] = ""
    entries.append(
        {
            "scenario": "S9_title_corruption_empty",
            "dimensions": ["completeness", "validity"],
            "field": "occupation_title",
            "strategy": "set_empty_string",
            "soc_code": rows[i].get("soc_code"),
            "old_value": str(old),
            "new_value": "''",
            "expected_rule_intent": "occupation_title_non_null_or_non_empty",
        }
    )
    return entries


def scenario_10_negative_wage(rows):
    """S10 — negative-wage attack: wage_annual_p25 = -5000 on one row.

    Probe — the brief notes there is currently no rule for this case.
    Pick a non-spot-check row.
    """
    entries = []
    spot_check_socs = {"15-1252", "29-1141", "29-1171", "11-1011"}
    for i, r in enumerate(rows):
        if (
            r.get("soc_code") not in spot_check_socs
            and r.get("wage_annual_p25") is not None
        ):
            break
    else:
        return entries
    old = rows[i]["wage_annual_p25"]
    rows[i]["wage_annual_p25"] = -5000.0
    entries.append(
        {
            "scenario": "S10_negative_wage_p25",
            "dimensions": ["validity", "reasonableness"],
            "field": "wage_annual_p25",
            "strategy": "set_negative_wage",
            "soc_code": rows[i].get("soc_code"),
            "old_value": str(old),
            "new_value": "-5000.0",
            "expected_rule_intent": "wage_annual_non_negative (likely_uncovered_today)",
            "is_gap_probe": True,
        }
    )
    return entries


# ---------------------------------------------------------------------------
# Cycle plan
#
# Cycle 1 (5%):  S5, S6, S9                             -- format / uniqueness / title
# Cycle 2 (6%):  S2, S3, S4                             -- consistency / monotonicity
# Cycle 3 (7%):  S1                                     -- suppression drift (10 nulls)
# Cycle 4 (8%):  S7, S10                                -- spot-check drift + neg wage probe
# Cycle 5 (10%): S8                                     -- row-count drop (volume)
#
# Spreading across cycles lets each scenario's rule fire-pattern be observed
# in isolation (or near-isolation), so reconciliation can attribute
# rule_id -> scenario by inspecting which cycle a rule first fired in.
# ---------------------------------------------------------------------------

CYCLE_SCENARIOS = {
    1: {
        "rate": 0.05,
        "label": "format_uniqueness_title",
        "scenarios": [
            scenario_5_soc_format_corruption,
            scenario_6_soc_uniqueness_violation,
            scenario_9_title_corruption,
        ],
    },
    2: {
        "rate": 0.06,
        "label": "consistency_monotonicity",
        "scenarios": [
            scenario_2_topcode_misclass_false,
            scenario_3_topcode_underreport_true,
            scenario_4_monotonicity_swap,
        ],
    },
    3: {
        "rate": 0.07,
        "label": "suppression_drift",
        "scenarios": [scenario_1_suppression_drift],
    },
    4: {
        "rate": 0.08,
        "label": "calibration_and_negative_wage",
        "scenarios": [
            scenario_7_calibration_drift,
            scenario_10_negative_wage,
        ],
    },
    5: {
        "rate": 0.10,
        "label": "row_count_drop",
        "scenarios": [scenario_8_rowcount_drop_50],
    },
}


# ---------------------------------------------------------------------------
# Cycle driver
# ---------------------------------------------------------------------------

def run_cycle(cycle_num, spec):
    rate = spec["rate"]
    label = spec["label"]
    seed = SEED_BASE + cycle_num

    print("\n" + "=" * 72)
    print(
        f"CYCLE {cycle_num} | rate={rate * 100:.0f}% | seed={seed} | label={label}"
    )
    print("=" * 72)

    rows, source_schema = load_source_rows()
    original_count = len(rows)
    print(f"  loaded {original_count} rows from {SOURCE_PARQUET.name}")

    manifest = []
    for fn in spec["scenarios"]:
        try:
            entries = fn(rows)
            manifest.extend(entries)
            print(f"  scenario {fn.__name__}: {len(entries)} manifest entries")
        except Exception as exc:  # pragma: no cover
            print(f"  ERROR in {fn.__name__}: {exc}")
            traceback.print_exc()

    print(f"  row count after corruption: {len(rows)} (was {original_count})")
    print(f"  total manifest entries: {len(manifest)}")

    dq_result = None
    try:
        arrow_table = rows_to_arrow(rows, source_schema)
        parquet_path = write_shadow_parquet(arrow_table, cycle_num)
        print(f"  wrote shadow parquet -> {parquet_path.name}")
        register_shadow(parquet_path)
        print(f"  registered {SHADOW_FQN}")

        dq_result = run_dq_rules_shadow()
        total = dq_result.get("rules_total", 0)
        passed = dq_result.get("rules_passed", 0)
        failed = dq_result.get("rules_failed", 0)
        print(
            f"  dq run_id={dq_result.get('run_id')} "
            f"total={total} passed={passed} failed={failed}"
        )
        for r in dq_result.get("results", []):
            status = (
                "PASS" if r.get("passed")
                else ("ERROR" if r.get("error") else "FAIL")
            )
            print(
                f"    {str(r.get('rule_id')):<48} {status:<6} "
                f"value={r.get('raw_value')}"
            )
    except Exception as exc:
        print(f"  ERROR during shadow/dq: {exc}")
        traceback.print_exc()
        dq_result = {
            "run_id": "error",
            "rules_total": 0,
            "rules_passed": 0,
            "rules_failed": 0,
            "p0_passed": False,
            "results": [],
            "error": str(exc),
        }
    finally:
        cleanup_shadow()

    return {
        "cycle": cycle_num,
        "label": label,
        "rate": rate,
        "seed": seed,
        "original_row_count": original_count,
        "corrupted_row_count": len(rows),
        "manifest": manifest,
        "dq_result": dq_result,
    }


def reconcile(cycle_result):
    """Pair manifest entries against fired rules.

    We honor the information barrier: reconciliation is structural and
    relies only on rule_ids returned by ``run_rules()``.
    """
    dq = cycle_result["dq_result"] or {}
    results = dq.get("results", [])
    failed = [r for r in results if not r.get("passed") and not r.get("error")]
    passed = [r for r in results if r.get("passed")]
    errored = [r for r in results if r.get("error")]
    fired_ids = [r.get("rule_id") for r in failed]

    manifest = cycle_result["manifest"]
    real_injections = [
        m for m in manifest if "negative_control" not in m.get("dimensions", [])
    ]
    if real_injections:
        caught_any = len(failed) > 0
    else:
        caught_any = len(failed) == 0

    # Per-scenario annotation: caught = at least one rule fired in the
    # cycle.  Gap probes (S10) keep their flag so they're easy to find
    # in the report.
    for m in manifest:
        m["caught"] = len(failed) > 0

    return {
        "fired_rule_ids": fired_ids,
        "passed_rule_ids": [r.get("rule_id") for r in passed],
        "errored_rule_ids": [r.get("rule_id") for r in errored],
        "total_rules": len(results),
        "rules_fired": len(failed),
        "rules_silent": len(passed),
        "rules_errored": len(errored),
        "caught_any": caught_any,
        "real_injection_count": len(real_injections),
    }


def main():
    safety_check()

    all_cycles = []
    for cycle_num in sorted(CYCLE_SCENARIOS.keys()):
        spec = CYCLE_SCENARIOS[cycle_num]
        cycle_result = run_cycle(cycle_num, spec)
        cycle_result["reconciliation"] = reconcile(cycle_result)
        all_cycles.append(cycle_result)

    cleanup_shadow()  # belt + suspenders

    manifest_out = {
        "spec": SPEC_NAME,
        "table": "bronze.bls_oews",
        "shadow_table": SHADOW_FQN,
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    out_path = (
        PROJECT_ROOT
        / "governance/chaos-manifests/raw-ingest-bls-oews-manifest.json"
    )
    out_path.write_text(json.dumps(manifest_out, indent=2, default=str) + "\n")
    print(f"\nManifest written: {out_path}")

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for c in all_cycles:
        rec = c["reconciliation"]
        print(
            f"cycle {c['cycle']} ({c['label']}): "
            f"fired={rec['rules_fired']}/{rec['total_rules']} "
            f"caught_any={rec['caught_any']} "
            f"injections={rec['real_injection_count']}"
        )
    return manifest_out


if __name__ == "__main__":
    main()
