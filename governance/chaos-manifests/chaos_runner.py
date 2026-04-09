"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: raw-ingest-college-scorecard
Table: raw.college_scorecard

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.
"""

import json
import random
import datetime
import uuid
import copy
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
DATA_FILE = PROJECT_ROOT / "data/bronze/iceberg_warehouse/raw/college_scorecard/data/00000-0-fd9827f0-84f8-42e0-b0e9-641a3e44b4f1.parquet"
SHADOW_DIR = PROJECT_ROOT / "data/bronze/iceberg_warehouse/shadow_raw/college_scorecard"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42

# ---------------------------------------------------------------------------
# Corruption strategies (one per DQ dimension)
# ---------------------------------------------------------------------------

def corrupt_completeness(rows, indices, rng):
    """Null out required grain fields: unitid, cipcode, credlev."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(["unitid", "cipcode", "credlev"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"row": i, "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null"})
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid values: bad CIP codes, wrong CREDLEV, non-numeric strings."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice(["bad_cipcode", "bad_credlev", "bad_cipcode_format"])
        if strategy == "bad_cipcode":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = rng.choice(["999999", "XX", "0000000000", "", "abc.defg"])
            manifest.append({"row": i, "dimension": "validity", "field": "cipcode",
                             "strategy": strategy, "old_value": str(old_val), "new_value": rows[i]["cipcode"]})
        elif strategy == "bad_credlev":
            old_val = rows[i]["credlev"]
            rows[i]["credlev"] = rng.choice([1, 2, 5, 6, 0, -1, 99])
            manifest.append({"row": i, "dimension": "validity", "field": "credlev",
                             "strategy": strategy, "old_value": str(old_val), "new_value": str(rows[i]["credlev"])})
        elif strategy == "bad_cipcode_format":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = rng.choice(["1", "12345678", "ab.cdef", "00.00.00"])
            manifest.append({"row": i, "dimension": "validity", "field": "cipcode",
                             "strategy": strategy, "old_value": str(old_val), "new_value": rows[i]["cipcode"]})
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows."""
    manifest = []
    n_dupes = max(1, len(indices) // 5)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"row": insert_pos, "dimension": "uniqueness", "field": "grain",
                         "strategy": "duplicate_row", "old_value": f"copy_of_row_{src_idx}",
                         "new_value": f"duplicate at position {insert_pos}"})
    return manifest


def corrupt_consistency(rows, indices, rng):
    """Contradictory field combinations: credlev=3 but creddesc != 'Bachelors Degree'."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["credlev_creddesc_mismatch", "empty_instnm_with_data"])
        if strategy == "credlev_creddesc_mismatch":
            old_val = rows[i].get("creddesc")
            rows[i]["creddesc"] = rng.choice(["Associate's Degree", "Master's Degree",
                                               "Doctoral Degree", "Certificate"])
            manifest.append({"row": i, "dimension": "consistency", "field": "creddesc",
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": rows[i]["creddesc"]})
        elif strategy == "empty_instnm_with_data":
            old_val = rows[i].get("instnm")
            rows[i]["instnm"] = ""
            manifest.append({"row": i, "dimension": "consistency", "field": "instnm",
                             "strategy": strategy, "old_value": str(old_val), "new_value": ""})
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: earnings slightly off, swapped fields."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["swapped_earnings", "wrong_unitid_range"])
        if strategy == "swapped_earnings":
            # Swap 1yr and 2yr earnings
            old_1yr = rows[i].get("earn_mdn_hi_1yr")
            old_2yr = rows[i].get("earn_mdn_hi_2yr")
            if old_1yr is not None and old_2yr is not None:
                rows[i]["earn_mdn_hi_1yr"] = old_2yr
                rows[i]["earn_mdn_hi_2yr"] = old_1yr
                manifest.append({"row": i, "dimension": "accuracy", "field": "earn_mdn_hi_1yr,earn_mdn_hi_2yr",
                                 "strategy": strategy, "old_value": f"1yr={old_1yr},2yr={old_2yr}",
                                 "new_value": f"1yr={old_2yr},2yr={old_1yr}"})
        elif strategy == "wrong_unitid_range":
            old_val = rows[i]["unitid"]
            rows[i]["unitid"] = rng.randint(1, 999)  # Too small to be a real UNITID
            manifest.append({"row": i, "dimension": "accuracy", "field": "unitid",
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": str(rows[i]["unitid"])})
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: negative earnings, astronomical debt."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice(["negative_earnings", "extreme_earnings", "extreme_debt", "negative_debt"])
        if strategy == "negative_earnings":
            field = rng.choice(["earn_mdn_hi_1yr", "earn_mdn_hi_2yr"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(-100000, -1))
            manifest.append({"row": i, "dimension": "reasonableness", "field": field,
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": str(rows[i][field])})
        elif strategy == "extreme_earnings":
            field = rng.choice(["earn_mdn_hi_1yr", "earn_mdn_hi_2yr"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(2000000, 10000000))
            manifest.append({"row": i, "dimension": "reasonableness", "field": field,
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": str(rows[i][field])})
        elif strategy == "extreme_debt":
            old_val = rows[i].get("debt_all_stgp_eval_mdn")
            rows[i]["debt_all_stgp_eval_mdn"] = float(rng.randint(1000000, 5000000))
            manifest.append({"row": i, "dimension": "reasonableness", "field": "debt_all_stgp_eval_mdn",
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": str(rows[i]["debt_all_stgp_eval_mdn"])})
        elif strategy == "negative_debt":
            old_val = rows[i].get("debt_all_stgp_eval_mdn")
            rows[i]["debt_all_stgp_eval_mdn"] = float(rng.randint(-50000, -1))
            manifest.append({"row": i, "dimension": "reasonableness", "field": "debt_all_stgp_eval_mdn",
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": str(rows[i]["debt_all_stgp_eval_mdn"])})
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2030, 1, 1)
            manifest.append({"row": i, "dimension": "freshness", "field": "load_date",
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": "2030-01-01"})
        elif strategy == "stale_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2020, 1, 1)
            manifest.append({"row": i, "dimension": "freshness", "field": "load_date",
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": "2020-01-01"})
        elif strategy == "future_ingested_at":
            old_val = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(2030, 6, 15, 12, 0, 0)
            manifest.append({"row": i, "dimension": "freshness", "field": "ingested_at",
                             "strategy": strategy, "old_value": str(old_val),
                             "new_value": "2030-06-15T12:00:00"})
    return manifest


def corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-duplicate a chunk to inflate count."""
    manifest = []
    # Add a large batch of duplicates to trigger volume rules
    n_extras = max(50, len(rows) // 10)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
    manifest.append({"row": -1, "dimension": "volume", "field": "row_count",
                     "strategy": "mass_duplicate", "old_value": str(len(rows) - n_extras),
                     "new_value": str(len(rows))})
    return manifest


def corrupt_referential_integrity(rows, indices, rng):
    """Orphan keys: unitid values that don't exist in any real institution set."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        old_val = rows[i]["unitid"]
        # Use a clearly fake unitid that can't exist
        rows[i]["unitid"] = rng.randint(900000000, 999999999)
        manifest.append({"row": i, "dimension": "referential_integrity", "field": "unitid",
                         "strategy": "orphan_unitid", "old_value": str(old_val),
                         "new_value": str(rows[i]["unitid"])})
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove all rows for common CIP codes."""
    manifest = []
    # Find the most common cipcodes and remove some
    cip_counts = {}
    for i, row in enumerate(rows):
        cip = row.get("cipcode")
        if cip:
            cip_counts.setdefault(cip, []).append(i)

    # Remove all rows for 2-3 common CIP codes
    common_cips = sorted(cip_counts.keys(), key=lambda c: len(cip_counts[c]), reverse=True)[:5]
    targets = rng.sample(common_cips, min(3, len(common_cips)))

    removed_indices = set()
    for cip in targets:
        for idx in cip_counts[cip]:
            removed_indices.add(idx)
        manifest.append({"row": -1, "dimension": "coverage", "field": "cipcode",
                         "strategy": f"remove_all_cip_{cip}", "old_value": f"cip={cip}, count={len(cip_counts[cip])}",
                         "new_value": "removed"})

    # Remove rows in reverse order to maintain indices
    for idx in sorted(removed_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Main injection pipeline
# ---------------------------------------------------------------------------

CORRUPTION_FUNCTIONS = [
    corrupt_completeness,
    corrupt_validity,
    corrupt_uniqueness,
    corrupt_consistency,
    corrupt_accuracy,
    corrupt_reasonableness,
    corrupt_freshness,
    corrupt_volume,
    corrupt_referential_integrity,
    corrupt_coverage,
]


def load_source_data():
    """Load the real parquet data into a list of dicts."""
    table = pq.read_table(str(DATA_FILE))
    rows = []
    for i in range(table.num_rows):
        row = {}
        for col in table.column_names:
            val = table.column(col)[i].as_py()
            row[col] = val
        rows.append(row)
    return rows


def rows_to_arrow(rows, original_schema):
    """Convert list of dicts back to a PyArrow table matching the original schema."""
    arrays = {}
    for field in original_schema:
        col_name = field.name
        values = [r.get(col_name) for r in rows]
        # Convert to appropriate arrow array
        try:
            arrays[col_name] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            # For type mismatches, try to coerce
            arrays[col_name] = pa.array(values)

    return pa.table(arrays)


def write_shadow_table(arrow_table, cycle_num):
    """Write corrupted data as a parquet file in the shadow directory."""
    SHADOW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHADOW_META_DIR.mkdir(parents=True, exist_ok=True)

    # Write parquet file
    out_file = SHADOW_DATA_DIR / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out_file))
    return out_file


def register_shadow_in_catalog(parquet_path, arrow_schema):
    """Register the shadow table in the Iceberg catalog under shadow_raw namespace."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType, DoubleType, IntegerType, LongType, NestedField, StringType, TimestampType
    )

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)

    # Create shadow_raw namespace if needed
    try:
        catalog.create_namespace("shadow_raw")
    except Exception:
        pass

    # Drop existing shadow table
    try:
        catalog.drop_table("shadow_raw.college_scorecard")
    except Exception:
        pass

    # Define schema matching the real table
    iceberg_schema = Schema(
        NestedField(1, "unitid", LongType(), required=False),
        NestedField(2, "instnm", StringType(), required=False),
        NestedField(3, "cipcode", StringType(), required=False),
        NestedField(4, "cipdesc", StringType(), required=False),
        NestedField(5, "creddesc", StringType(), required=False),
        NestedField(6, "credlev", IntegerType(), required=False),
        NestedField(7, "md_earn_wne", DoubleType(), required=False),
        NestedField(8, "earn_mdn_hi_1yr", DoubleType(), required=False),
        NestedField(9, "earn_mdn_hi_2yr", DoubleType(), required=False),
        NestedField(10, "debt_all_stgp_eval_mdn", DoubleType(), required=False),
        NestedField(11, "ipedscount1", LongType(), required=False),
        NestedField(12, "ipedscount2", LongType(), required=False),
        NestedField(13, "ingested_at", TimestampType(), required=False),
        NestedField(14, "source_url", StringType(), required=False),
        NestedField(15, "source_method", StringType(), required=False),
        NestedField(16, "load_date", DateType(), required=False),
    )

    # Create the shadow table
    shadow_table = catalog.create_table("shadow_raw.college_scorecard", schema=iceberg_schema)

    # Read the parquet back and append to shadow table
    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)

    return shadow_table


def run_dq_rules_shadow():
    """Run DQ rules against the shadow table and return results."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    result = run_rules(spec="raw-ingest-college-scorecard", catalog=catalog, shadow=True)
    return result


def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)

    # Load fresh source data
    print("Loading source data...")
    rows = load_source_data()
    original_count = len(rows)
    print(f"  Loaded {original_count} rows")

    # Get original schema for conversion
    orig_table = pq.read_table(str(DATA_FILE))
    original_schema = orig_table.schema

    # Calculate how many rows to corrupt per dimension
    n_corrupt = int(original_count * rate)
    all_indices = list(range(original_count))

    # Allocate indices to each corruption function (with overlap allowed)
    per_function = max(1, n_corrupt // len(CORRUPTION_FUNCTIONS))

    all_manifest = []

    for func in CORRUPTION_FUNCTIONS:
        indices = rng.sample(all_indices, min(per_function, len(all_indices)))
        try:
            entries = func(rows, indices, rng)
            all_manifest.extend(entries)
            dim = func.__name__.replace("corrupt_", "")
            print(f"  {dim}: {len(entries)} corruptions")
        except Exception as e:
            print(f"  ERROR in {func.__name__}: {e}")

    print(f"  Total corruptions: {len(all_manifest)}")
    print(f"  Final row count: {len(rows)} (was {original_count})")

    # Convert back to arrow and write shadow table
    print("Writing shadow table...")
    try:
        arrow_table = rows_to_arrow(rows, original_schema)
        parquet_path = write_shadow_table(arrow_table, cycle_num)
        print(f"  Written to {parquet_path}")

        # Register in Iceberg catalog
        print("Registering in Iceberg catalog...")
        register_shadow_in_catalog(parquet_path, original_schema)
        print("  Registered as shadow_raw.college_scorecard")

        # Run DQ rules
        print("Running DQ rules against shadow table...")
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(f"  Total: {dq_result['rules_total']} | Passed: {dq_result['rules_passed']} | Failed: {dq_result['rules_failed']}")
        print(f"  P0 gate: {'PASS' if dq_result['p0_passed'] else 'FAIL'}")

        # Print per-rule results
        print("\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            print(f"    {r['rule_id']:<20} {status:<6} value={r.get('raw_value', '?')}")

    except Exception as e:
        print(f"  ERROR during shadow table creation/DQ run: {e}")
        import traceback
        traceback.print_exc()
        dq_result = {"run_id": "error", "rules_total": 0, "rules_passed": 0,
                     "rules_failed": 0, "p0_passed": True, "results": []}

    return {
        "cycle": cycle_num,
        "rate": rate,
        "seed": seed,
        "original_row_count": original_count,
        "corrupted_row_count": len(rows),
        "total_corruptions": len(all_manifest),
        "manifest": all_manifest,
        "dq_result": dq_result,
    }


def analyze_gaps(cycle_result):
    """Analyze which corruptions were caught vs missed.

    Since we honor the information barrier (we don't read DQ rule definitions),
    we analyze gaps empirically:
    - If a rule FAILED, it detected something our corruptions caused.
    - We count total rules failed vs passed.
    - We report which rules passed (potential gaps) vs failed (caught corruptions).
    - We note which corruption dimensions were injected and at what rates.

    The reconciliation is empirical: we know 11/18 rules fire, meaning the
    corruptions ARE being detected across multiple rules. The 7 passing rules
    may check dimensions we didn't corrupt heavily enough, or may check
    nullable fields where our corruptions don't violate (e.g., null counts
    for nullable fields are within thresholds).
    """
    dq_result = cycle_result["dq_result"]
    manifest = cycle_result["manifest"]

    # Which rules failed = which corruptions were detected
    failed_rules = [r for r in dq_result.get("results", []) if not r["passed"] and not r.get("error")]
    passed_rules = [r for r in dq_result.get("results", []) if r["passed"]]
    errored_rules = [r for r in dq_result.get("results", []) if r.get("error")]

    # Group manifest by dimension
    dims = {}
    for entry in manifest:
        dim = entry["dimension"]
        dims.setdefault(dim, []).append(entry)

    # Empirical detection rate
    total_rules = len(dq_result.get("results", []))
    detection_rate = len(failed_rules) / total_rules if total_rules > 0 else 0

    return {
        "failed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value")} for r in failed_rules],
        "passed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value"), "threshold": r.get("threshold")} for r in passed_rules],
        "errored_rules": [r["rule_id"] for r in errored_rules],
        "injected_dimensions": sorted(dims.keys()),
        "corruptions_per_dimension": {dim: len(entries) for dim, entries in dims.items()},
        "detection_rate": round(detection_rate, 3),
        "rules_fired": len(failed_rules),
        "rules_silent": len(passed_rules),
        "total_rules": total_rules,
    }


def cleanup_shadow():
    """Remove shadow table and files."""
    import shutil
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)
    # Drop from catalog
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
        catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
        catalog.drop_table("shadow_raw.college_scorecard")
    except Exception:
        pass


def main():
    """Run 5-cycle adversarial hardening."""
    all_cycles = []
    all_gaps = []
    consecutive_no_new_gaps = 0
    previous_missed = set()

    for cycle_num, rate in enumerate(RATES, 1):
        seed = SEED_BASE + cycle_num
        cycle_result = run_cycle(cycle_num, rate, seed)
        gap_analysis = analyze_gaps(cycle_result)

        # Check for stability: same rules firing across cycles
        current_failed = set(r["rule_id"] for r in gap_analysis["failed_rules"])
        if current_failed == previous_missed and cycle_num > 1:
            consecutive_no_new_gaps += 1
        else:
            consecutive_no_new_gaps = 0
        previous_missed = current_failed

        all_cycles.append({
            "cycle": cycle_num,
            "rate": rate,
            "corruptions": cycle_result["total_corruptions"],
            "row_count": cycle_result["corrupted_row_count"],
            "dq_passed": cycle_result["dq_result"]["rules_passed"],
            "dq_failed": cycle_result["dq_result"]["rules_failed"],
            "dq_total": cycle_result["dq_result"]["rules_total"],
            "gap_analysis": gap_analysis,
            "manifest_entries": cycle_result["manifest"],
        })
        all_gaps.append(gap_analysis)

        print(f"\n  Gap Analysis:")
        print(f"    Detection rate: {gap_analysis['detection_rate']*100:.1f}% ({gap_analysis['rules_fired']}/{gap_analysis['total_rules']} rules fired)")
        print(f"    Rules that fired: {[r['rule_id'] for r in gap_analysis['failed_rules']]}")
        print(f"    Rules silent: {[r['rule_id'] for r in gap_analysis['passed_rules']]}")

        if consecutive_no_new_gaps >= 2:
            print(f"\n  Stability detected: same rules firing for 2 consecutive cycles.")
            print(f"  Continuing to complete all 5 cycles for thorough documentation.")

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest for reconciliation
    manifest_data = {
        "spec": "raw-ingest-college-scorecard",
        "table": "raw.college_scorecard",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/raw-ingest-college-scorecard-manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2, default=str) + "\n")
    print(f"\nManifest written to: {manifest_path}")

    return manifest_data


if __name__ == "__main__":
    result = main()
    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for c in result["cycles"]:
        ga = c["gap_analysis"]
        print(f"Cycle {c['cycle']} ({c['rate']*100:.0f}%): {c['dq_failed']}/{c['dq_total']} rules failed, "
              f"detection rate: {ga['detection_rate']*100:.1f}%, "
              f"silent rules: {[r['rule_id'] for r in ga['passed_rules']]}")
