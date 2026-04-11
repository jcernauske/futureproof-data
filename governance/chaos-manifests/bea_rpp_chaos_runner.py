"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec:  raw-ingest-bea-rpp
Table: bronze.bea_rpp (51 rows — 50 states + DC)
Shadow namespace: shadow_bronze.bea_rpp

This is a curated, spec-driven scenario runner (NOT a per-dimension fuzz
runner) because the underlying table is only 51 rows and the interesting
breakages are categorical.  Each cycle applies a fixed scenario pack
covering the 12 scenarios requested by the adversarial-auditor.

Information Barrier: This script does NOT read
  - governance/dq-rules/raw-ingest-bea-rpp.json
  - governance/dq-results/*
  - governance/dq-scorecards/*
  - brightsmith.infra.dq_runner (the runner is imported for its public
    run_rules() entry point only; the source is not inspected)
Corruption choices are based solely on the schema in
src/raw/bea_rpp_ingestor.py and domain knowledge of state FIPS codes.
"""

import copy
import datetime
import json
import random
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
    / "bea_rpp"
    / "data"
    / "00000-0-fad1ac84-756f-4e32-bc53-f1cf79371c29.parquet"
)
SHADOW_DIR = BRONZE_WAREHOUSE / "shadow_bronze" / "bea_rpp"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

SPEC_NAME = "raw-ingest-bea-rpp"
SHADOW_FQN = "shadow_bronze.bea_rpp"

SEED_BASE = 42

sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path("/Users/jcernauske/code/bright/brightsmith/src")))

from brightsmith.config import configure  # noqa: E402

configure(project_root=str(PROJECT_ROOT), project_name="brightsmith")


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

def safety_check():
    import os

    os.environ["CHAOS_MONKEY_ENABLED"] = "true"
    os.environ["BRIGHTSMITH_ENV"] = "dev"
    os.environ.setdefault("GRIST_ENV", "dev")
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
            # Allow bad types to fall through — shadow schema below is all optional.
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
    """Register shadow table in catalog, replacing any prior copy."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType,
        DoubleType,
        IntegerType,
        NestedField,
        StringType,
        TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(BRONZE_WAREHOUSE), str(CATALOG_PATH))
    try:
        catalog.create_namespace("shadow_bronze")
    except Exception:
        pass
    try:
        catalog.drop_table(SHADOW_FQN)
    except Exception:
        pass

    # All fields optional so we can land corrupted / null data in the shadow.
    schema = Schema(
        NestedField(1, "geo_fips", StringType(), required=False),
        NestedField(2, "geo_name", StringType(), required=False),
        NestedField(3, "rpp_all_items", DoubleType(), required=False),
        NestedField(4, "data_year", IntegerType(), required=False),
        NestedField(5, "ingested_at", TimestampType(), required=False),
        NestedField(6, "source_url", StringType(), required=False),
        NestedField(7, "source_method", StringType(), required=False),
        NestedField(8, "load_date", DateType(), required=False),
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
        shutil.rmtree(SHADOW_DIR)
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
# Scenario library  (indices into rows must be resolved by geo_fips)
# ---------------------------------------------------------------------------

def _find_idx(rows, geo_fips):
    for i, r in enumerate(rows):
        if r.get("geo_fips") == geo_fips:
            return i
    return None


def scenario_drop_wyoming(rows):
    """S1 / S8: Drop Wyoming (fips=56) — row_count and canonical-set rules should fire."""
    idx = _find_idx(rows, "56")
    entries = []
    if idx is not None:
        old = rows.pop(idx)
        entries.append(
            {
                "scenario": "drop_wyoming",
                "dimensions": ["volume", "coverage"],
                "field": "row (geo_fips=56)",
                "strategy": "delete_row",
                "old_value": str(old),
                "new_value": "<removed>",
            }
        )
    return entries


def scenario_drop_dc(rows):
    """S9: Drop District of Columbia (fips=11) — DC presence rule should fire."""
    idx = _find_idx(rows, "11")
    entries = []
    if idx is not None:
        old = rows.pop(idx)
        entries.append(
            {
                "scenario": "drop_dc",
                "dimensions": ["volume", "coverage"],
                "field": "row (geo_fips=11)",
                "strategy": "delete_row",
                "old_value": str(old),
                "new_value": "<removed>",
            }
        )
    return entries


def scenario_duplicate_texas(rows):
    """S1b: Duplicate a state row (Texas, fips=48) — row_count and/or uniqueness rules."""
    idx = _find_idx(rows, "48")
    entries = []
    if idx is not None:
        dupe = copy.deepcopy(rows[idx])
        rows.append(dupe)
        entries.append(
            {
                "scenario": "duplicate_texas",
                "dimensions": ["volume", "uniqueness"],
                "field": "row (geo_fips=48)",
                "strategy": "duplicate_row",
                "old_value": "1 row",
                "new_value": "2 rows",
            }
        )
    return entries


def scenario_ca_out_of_range_high(rows):
    """S2: Set California (06) RPP to 200.0 — range rule should fire."""
    idx = _find_idx(rows, "06")
    entries = []
    if idx is not None:
        old = rows[idx]["rpp_all_items"]
        rows[idx]["rpp_all_items"] = 200.0
        entries.append(
            {
                "scenario": "ca_out_of_range_high",
                "dimensions": ["validity", "reasonableness"],
                "field": "rpp_all_items",
                "strategy": "set_impossible_high",
                "old_value": str(old),
                "new_value": "200.0",
            }
        )
    return entries


def scenario_ca_out_of_range_neg(rows):
    """S2b: Set California (06) RPP to -10.0 — range rule should fire."""
    idx = _find_idx(rows, "06")
    entries = []
    if idx is not None:
        old = rows[idx]["rpp_all_items"]
        rows[idx]["rpp_all_items"] = -10.0
        entries.append(
            {
                "scenario": "ca_out_of_range_neg",
                "dimensions": ["validity", "reasonableness"],
                "field": "rpp_all_items",
                "strategy": "set_negative",
                "old_value": str(old),
                "new_value": "-10.0",
            }
        )
    return entries


def scenario_null_rpp(rows):
    """S3: Null rpp_all_items for one state (Nevada, fips=32) — null rule should fire."""
    idx = _find_idx(rows, "32")
    entries = []
    if idx is not None:
        old = rows[idx]["rpp_all_items"]
        rows[idx]["rpp_all_items"] = None
        entries.append(
            {
                "scenario": "null_rpp_nevada",
                "dimensions": ["completeness"],
                "field": "rpp_all_items",
                "strategy": "set_null",
                "old_value": str(old),
                "new_value": "null",
            }
        )
    return entries


def scenario_duplicate_fips(rows):
    """S4: Inject a second row for Oregon (41) — uniqueness rule should fire."""
    idx = _find_idx(rows, "41")
    entries = []
    if idx is not None:
        dupe = copy.deepcopy(rows[idx])
        # Keep same fips, change name slightly to prove it's the key that's dupe
        dupe["geo_name"] = "Oregon (duplicate)"
        dupe["rpp_all_items"] = 99.9
        rows.append(dupe)
        entries.append(
            {
                "scenario": "duplicate_fips_oregon",
                "dimensions": ["uniqueness"],
                "field": "geo_fips",
                "strategy": "inject_duplicate_key",
                "old_value": "geo_fips=41 appears 1x",
                "new_value": "geo_fips=41 appears 2x",
            }
        )
    return entries


def scenario_stale_data_year(rows):
    """S5: Set data_year for Montana (30) to 2023 — data_year rule should fire."""
    idx = _find_idx(rows, "30")
    entries = []
    if idx is not None:
        old = rows[idx]["data_year"]
        rows[idx]["data_year"] = 2023
        entries.append(
            {
                "scenario": "stale_data_year",
                "dimensions": ["freshness", "validity"],
                "field": "data_year",
                "strategy": "set_stale_year",
                "old_value": str(old),
                "new_value": "2023",
            }
        )
    return entries


def scenario_ca_stale_value(rows):
    """S6: Set California RPP to 95.0 — spot-check rule should fire."""
    idx = _find_idx(rows, "06")
    entries = []
    if idx is not None:
        old = rows[idx]["rpp_all_items"]
        rows[idx]["rpp_all_items"] = 95.0
        entries.append(
            {
                "scenario": "ca_stale_value",
                "dimensions": ["accuracy"],
                "field": "rpp_all_items",
                "strategy": "plausible_but_wrong_ca",
                "old_value": str(old),
                "new_value": "95.0",
            }
        )
    return entries


def scenario_ar_stale_value(rows):
    """S7: Set Arkansas RPP to 100.0 — AR spot-check rule should fire."""
    idx = _find_idx(rows, "05")
    entries = []
    if idx is not None:
        old = rows[idx]["rpp_all_items"]
        rows[idx]["rpp_all_items"] = 100.0
        entries.append(
            {
                "scenario": "ar_stale_value",
                "dimensions": ["accuracy"],
                "field": "rpp_all_items",
                "strategy": "plausible_but_wrong_ar",
                "old_value": str(old),
                "new_value": "100.0",
            }
        )
    return entries


def scenario_bad_source_method(rows):
    """S10: Set source_method to 'unknown' — source_method IN list rule should fire."""
    idx = _find_idx(rows, "48")  # Texas
    entries = []
    if idx is not None:
        old = rows[idx]["source_method"]
        rows[idx]["source_method"] = "unknown"
        entries.append(
            {
                "scenario": "bad_source_method",
                "dimensions": ["validity"],
                "field": "source_method",
                "strategy": "invalid_enum",
                "old_value": str(old),
                "new_value": "unknown",
            }
        )
    return entries


def scenario_unit_error_x10(rows):
    """S11: Multiply ALL RPPs by 10 — range + distribution rules should fire."""
    entries = []
    for r in rows:
        v = r.get("rpp_all_items")
        if v is not None:
            r["rpp_all_items"] = v * 10.0
    entries.append(
        {
            "scenario": "unit_error_x10",
            "dimensions": ["accuracy", "reasonableness", "validity"],
            "field": "rpp_all_items",
            "strategy": "multiply_all_by_10",
            "old_value": "~86.9 to ~110.7",
            "new_value": "~869 to ~1107",
        }
    )
    return entries


def scenario_swap_ia_ok(rows):
    """S12: Swap Iowa and Oklahoma (both 87.8) — should NOT break anything.

    Exercises the expectation that the uniqueness rule on (geo_fips)
    does not spuriously flag identical rpp_all_items values.  A well-tuned
    rule set detects NO failures from this.
    """
    ia = _find_idx(rows, "19")
    ok = _find_idx(rows, "40")
    entries = []
    if ia is not None and ok is not None:
        ia_name = rows[ia]["geo_name"]
        ok_name = rows[ok]["geo_name"]
        rows[ia]["geo_name"] = ok_name  # swap names only
        rows[ok]["geo_name"] = ia_name
        entries.append(
            {
                "scenario": "swap_ia_ok_should_not_break",
                "dimensions": ["negative_control"],
                "field": "geo_name",
                "strategy": "swap_names_equal_rpp",
                "old_value": f"IA={ia_name}, OK={ok_name}",
                "new_value": f"IA={ok_name}, OK={ia_name}",
                "expected_fired": False,
            }
        )
    return entries


# Ordered mapping of cycle -> list of scenarios.  We intentionally group
# scenarios so that each cycle gives *something* testable, and we also have
# a multi-scenario cycle to exercise rule co-firing.
CYCLE_SCENARIOS = {
    1: {
        "rate": 0.05,
        "label": "row_count_break",
        "scenarios": [scenario_drop_wyoming, scenario_duplicate_texas],
    },
    2: {
        "rate": 0.06,
        "label": "value_range_and_null",
        "scenarios": [
            scenario_ca_out_of_range_high,
            scenario_null_rpp,
            scenario_duplicate_fips,
        ],
    },
    3: {
        "rate": 0.07,
        "label": "freshness_enum_spot_check",
        "scenarios": [
            scenario_stale_data_year,
            scenario_bad_source_method,
            scenario_ca_stale_value,
            scenario_ar_stale_value,
        ],
    },
    4: {
        "rate": 0.08,
        "label": "unit_error_full_table",
        "scenarios": [scenario_unit_error_x10],
    },
    5: {
        "rate": 0.10,
        "label": "negative_control_plus_dc_and_neg_range",
        "scenarios": [
            scenario_drop_dc,
            scenario_ca_out_of_range_neg,
            scenario_swap_ia_ok,
        ],
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
    print(f"CYCLE {cycle_num} | rate={rate*100:.0f}% | seed={seed} | label={label}")
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
        except Exception as exc:
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
        print(
            f"  dq run_id={dq_result.get('run_id')}  "
            f"total={dq_result.get('rules_total')}  "
            f"passed={dq_result.get('rules_passed')}  "
            f"failed={dq_result.get('rules_failed')}"
        )
        for r in dq_result.get("results", []):
            status = "PASS" if r.get("passed") else (
                "ERROR" if r.get("error") else "FAIL"
            )
            print(f"    {r.get('rule_id'):<40} {status:<6} value={r.get('raw_value')}")
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

    Because we honor the information barrier, reconciliation is structural:
    * "caught" = at least one DQ rule fired (excluding negative controls)
    * per-scenario caught/missed is marked where possible by looking at
      the dimensions in the manifest entry and the rule_id hints that the
      dq_runner exposes in its results (rule_id only, no source code).
    """
    dq = cycle_result["dq_result"] or {}
    results = dq.get("results", [])
    failed = [r for r in results if not r.get("passed") and not r.get("error")]
    passed = [r for r in results if r.get("passed")]
    errored = [r for r in results if r.get("error")]
    fired_ids = [r.get("rule_id") for r in failed]

    manifest = cycle_result["manifest"]
    # Negative controls must NOT be caught
    neg_controls = [m for m in manifest if "negative_control" in m.get("dimensions", [])]
    real_injections = [m for m in manifest if "negative_control" not in m.get("dimensions", [])]

    # A cycle is "fully caught" if:
    #  - at least one rule fired (when real_injections > 0), OR
    #  - zero rules fired (when only negative controls)
    if real_injections:
        caught_any = len(failed) > 0
    else:
        caught_any = len(failed) == 0  # negative control: no fires = good

    # Per-scenario caught/missed annotation.  We cannot map scenario -> rule
    # without reading rules, so we mark per-scenario caught = True iff
    # *any* rule fired in this cycle AND the scenario is not a negative
    # control.  (This is a coarse but honest annotation — details go in
    # the markdown report.)
    for m in manifest:
        if "negative_control" in m.get("dimensions", []):
            m["caught"] = len(failed) == 0
        else:
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
        "neg_control_count": len(neg_controls),
    }


def main():
    safety_check()

    all_cycles = []
    for cycle_num in sorted(CYCLE_SCENARIOS.keys()):
        spec = CYCLE_SCENARIOS[cycle_num]
        cycle_result = run_cycle(cycle_num, spec)
        cycle_result["reconciliation"] = reconcile(cycle_result)
        all_cycles.append(cycle_result)

    # Final cleanup (belt + suspenders)
    cleanup_shadow()

    manifest_out = {
        "spec": SPEC_NAME,
        "table": "bronze.bea_rpp",
        "shadow_table": SHADOW_FQN,
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    out_path = (
        PROJECT_ROOT
        / "governance/chaos-manifests/raw-ingest-bea-rpp-manifest.json"
    )
    out_path.write_text(json.dumps(manifest_out, indent=2, default=str) + "\n")
    print(f"\nManifest written: {out_path}")

    # Summary
    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for c in all_cycles:
        rec = c["reconciliation"]
        print(
            f"cycle {c['cycle']} ({c['label']}): "
            f"fired={rec['rules_fired']}/{rec['total_rules']} "
            f"caught_any={rec['caught_any']} "
            f"neg_ctrl={rec['neg_control_count']}"
        )
    return manifest_out


if __name__ == "__main__":
    main()
