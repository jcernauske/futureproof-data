"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: raw-ingest-bls-ooh
Table: raw.bls_ooh

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.
"""

import json
import random
import datetime
import copy
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SAMPLE_XLSX = PROJECT_ROOT / "tests/raw/bls_ooh_sample.xlsx"
SHADOW_DIR = PROJECT_ROOT / "data/bronze/iceberg_warehouse/shadow_raw/bls_ooh"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42

# ---------------------------------------------------------------------------
# Load source data via ingestor
# ---------------------------------------------------------------------------

sys.path.insert(0, str(PROJECT_ROOT / "src"))


def load_source_data():
    """Load and flatten data from sample XLSX using the real ingestor."""
    from raw.bls_ooh_ingestor import BlsOohIngestor

    ingestor = BlsOohIngestor.__new__(BlsOohIngestor)
    raw_rows = ingestor._read_xlsx(SAMPLE_XLSX)
    flat_rows = ingestor.flatten(raw_rows, "bls_ooh")

    # Add metadata fields (normally added by the framework)
    now = datetime.datetime.utcnow()
    today = datetime.date.today()
    for row in flat_rows:
        row["ingested_at"] = now
        row["source_url"] = "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm"
        row["source_method"] = "xlsx_download"
        row["load_date"] = today

    return flat_rows


# ---------------------------------------------------------------------------
# Corruption strategies (one per DQ dimension)
# ---------------------------------------------------------------------------


def corrupt_completeness(rows, indices, rng):
    """Null out required grain fields: soc_code, occupation_title."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(["soc_code", "occupation_title", "median_wage_capped"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null",
        })
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid SOC codes, out-of-range education/experience/training codes."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_soc_format", "bad_education_code", "bad_work_experience_code",
            "bad_training_code", "negative_employment", "wage_out_of_range",
        ])
        if strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice([
                "151252", "15.1252", "XX-XXXX", "15-12520", "1-1252", "", "abc",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
            })
        elif strategy == "bad_education_code":
            old_val = rows[i]["education_code"]
            rows[i]["education_code"] = rng.choice([0, -1, 9, 10, 99, -5])
            manifest.append({
                "row": i, "dimension": "validity", "field": "education_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["education_code"]),
            })
        elif strategy == "bad_work_experience_code":
            old_val = rows[i]["work_experience_code"]
            rows[i]["work_experience_code"] = rng.choice([0, -1, 4, 5, 99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "work_experience_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["work_experience_code"]),
            })
        elif strategy == "bad_training_code":
            old_val = rows[i]["training_code"]
            rows[i]["training_code"] = rng.choice([0, -1, 7, 8, 99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "training_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["training_code"]),
            })
        elif strategy == "negative_employment":
            field = rng.choice([
                "employment_current", "employment_projected", "openings_annual_avg",
            ])
            old_val = rows[i][field]
            rows[i][field] = rng.randint(-500000, -1)
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "wage_out_of_range":
            old_val = rows[i]["median_annual_wage"]
            rows[i]["median_annual_wage"] = rng.choice([
                5000.0, 15000.0, 250000.0, 500000.0, -10000.0,
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"]),
            })
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows (same SOC code)."""
    manifest = []
    n_dupes = max(1, len(indices) // 3)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "soc_code",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx} (soc={rows[src_idx]['soc_code']})",
            "new_value": f"duplicate at position {insert_pos}",
        })
    return manifest


def corrupt_consistency(rows, indices, rng):
    """Contradictory field combinations: capped=true but wage != 239200."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "capped_wrong_wage", "uncapped_at_cap", "capped_null_wage",
            "employment_change_mismatch",
        ])
        if strategy == "capped_wrong_wage":
            old_capped = rows[i]["median_wage_capped"]
            old_wage = rows[i]["median_annual_wage"]
            rows[i]["median_wage_capped"] = True
            rows[i]["median_annual_wage"] = rng.choice([100000.0, 50000.0, 200000.0])
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "median_wage_capped,median_annual_wage",
                "strategy": strategy,
                "old_value": f"capped={old_capped},wage={old_wage}",
                "new_value": f"capped=True,wage={rows[i]['median_annual_wage']}",
            })
        elif strategy == "uncapped_at_cap":
            old_capped = rows[i]["median_wage_capped"]
            old_wage = rows[i]["median_annual_wage"]
            rows[i]["median_wage_capped"] = False
            rows[i]["median_annual_wage"] = 239200.0
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "median_wage_capped,median_annual_wage",
                "strategy": strategy,
                "old_value": f"capped={old_capped},wage={old_wage}",
                "new_value": "capped=False,wage=239200.0",
            })
        elif strategy == "capped_null_wage":
            old_capped = rows[i]["median_wage_capped"]
            old_wage = rows[i]["median_annual_wage"]
            rows[i]["median_wage_capped"] = True
            rows[i]["median_annual_wage"] = None
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "median_wage_capped,median_annual_wage",
                "strategy": strategy,
                "old_value": f"capped={old_capped},wage={old_wage}",
                "new_value": "capped=True,wage=None",
            })
        elif strategy == "employment_change_mismatch":
            old_change = rows[i]["employment_change"]
            # Make change wildly inconsistent with projected - current
            rows[i]["employment_change"] = rng.randint(5000000, 9999999)
            manifest.append({
                "row": i, "dimension": "consistency", "field": "employment_change",
                "strategy": strategy,
                "old_value": str(old_change),
                "new_value": str(rows[i]["employment_change"]),
            })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: subtly wrong SOC codes, swapped fields."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["summary_soc_code", "swapped_employment"])
        if strategy == "summary_soc_code":
            old_val = rows[i]["soc_code"]
            # Inject a summary code (XX-0000) which should have been filtered
            prefix = old_val[:2] if old_val and len(old_val) >= 2 else "11"
            rows[i]["soc_code"] = f"{prefix}-0000"
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
            })
        elif strategy == "swapped_employment":
            old_current = rows[i]["employment_current"]
            old_projected = rows[i]["employment_projected"]
            if old_current and old_projected:
                rows[i]["employment_current"] = old_projected
                rows[i]["employment_projected"] = old_current
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "employment_current,employment_projected",
                    "strategy": strategy,
                    "old_value": f"current={old_current},projected={old_projected}",
                    "new_value": f"current={old_projected},projected={old_current}",
                })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: impossibly high/low wages, employment."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_wage", "extreme_employment", "extreme_change_pct",
        ])
        if strategy == "extreme_wage":
            old_val = rows[i]["median_annual_wage"]
            rows[i]["median_annual_wage"] = float(rng.choice([
                1, 100, 999999, 5000000, -50000,
            ]))
            # Also need to keep capped flag consistent with new value to avoid
            # mixing this with consistency dimension
            rows[i]["median_wage_capped"] = False
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"]),
            })
        elif strategy == "extreme_employment":
            field = rng.choice(["employment_current", "employment_projected"])
            old_val = rows[i][field]
            rows[i][field] = rng.randint(500000000, 999999999)  # 500M+ workers
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "extreme_change_pct":
            old_val = rows[i]["employment_change_pct"]
            rows[i]["employment_change_pct"] = float(rng.choice([
                -99.9, 500.0, 1000.0, -200.0,
            ]))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "employment_change_pct",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["employment_change_pct"]),
            })
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2030, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-01-01",
            })
        elif strategy == "stale_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2020, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2020-01-01",
            })
        elif strategy == "future_ingested_at":
            old_val = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(2030, 6, 15, 12, 0, 0)  # noqa: DTZ001
            manifest.append({
                "row": i, "dimension": "freshness", "field": "ingested_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-06-15T12:00:00",
            })
    return manifest


def corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-duplicate to inflate count.

    Note: We only duplicate (never delete) so that other corruption
    dimensions' injected rows survive. The sample data is only 10 rows,
    so deletion would wipe out previously-injected corruptions.
    """
    manifest = []
    # Duplicate existing rows to inflate count (but count still won't reach 750-900)
    n_extras = max(3, len(rows) // 2)
    source_rows = rng.choices(range(len(rows)), k=n_extras)
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "strategy": "mass_duplicate",
        "old_value": str(len(rows) - n_extras),
        "new_value": str(len(rows)),
    })
    return manifest


def corrupt_referential_integrity(rows, indices, rng):
    """Orphan SOC codes: codes that look valid but reference nonexistent occupations."""
    manifest = []
    valid_indices = [i for i in indices if i < len(rows)]
    if not valid_indices:
        return manifest
    targets = rng.sample(valid_indices, min(len(valid_indices), max(1, len(valid_indices) // 4)))
    for i in targets:
        old_val = rows[i]["soc_code"]
        # Generate valid-format but nonexistent SOC codes
        fake_soc = f"{rng.randint(90,99)}-{rng.randint(1000,9999)}"
        rows[i]["soc_code"] = fake_soc
        rows[i]["occupation_title"] = f"FAKE OCCUPATION {fake_soc}"
        manifest.append({
            "row": i, "dimension": "referential_integrity", "field": "soc_code",
            "strategy": "orphan_soc", "old_value": str(old_val),
            "new_value": fake_soc,
        })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: null out education codes to create gaps.

    Note: With only 10 rows in the sample, we cannot afford to remove rows
    (it would wipe out other dimensions' corruptions). Instead, we null out
    education codes to create coverage gaps in the education_code distribution.
    """
    manifest = []
    # Null out education codes on some rows to break expected distribution
    valid_indices = [i for i in range(len(rows)) if rows[i].get("education_code") is not None]
    if valid_indices:
        targets = rng.sample(valid_indices, min(2, len(valid_indices)))
        for i in targets:
            old_val = rows[i]["education_code"]
            rows[i]["education_code"] = None
            rows[i]["education_typical"] = None
            manifest.append({
                "row": i, "dimension": "coverage", "field": "education_code",
                "strategy": "null_education_coverage",
                "old_value": f"education_code={old_val}",
                "new_value": "null",
            })
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
    corrupt_referential_integrity,
    # These can change row count, so run last:
    corrupt_volume,
    corrupt_coverage,
]


def rows_to_arrow(rows):
    """Convert list of dicts to a PyArrow table with appropriate types."""
    from pyiceberg.types import (
        BooleanType, DateType, DoubleType, IntegerType,
        LongType, StringType, TimestampType,
    )

    # Define schema matching the Iceberg table
    schema = pa.schema([
        pa.field("soc_code", pa.string()),
        pa.field("occupation_title", pa.string()),
        pa.field("employment_current", pa.int64()),
        pa.field("employment_projected", pa.int64()),
        pa.field("employment_change", pa.int64()),
        pa.field("employment_change_pct", pa.float64()),
        pa.field("openings_annual_avg", pa.int64()),
        pa.field("median_annual_wage", pa.float64()),
        pa.field("median_wage_capped", pa.bool_()),
        pa.field("education_typical", pa.string()),
        pa.field("education_code", pa.int32()),
        pa.field("work_experience", pa.string()),
        pa.field("work_experience_code", pa.int32()),
        pa.field("training_typical", pa.string()),
        pa.field("training_code", pa.int32()),
        pa.field("ingested_at", pa.timestamp("us")),
        pa.field("source_url", pa.string()),
        pa.field("source_method", pa.string()),
        pa.field("load_date", pa.date32()),
    ])

    arrays = {}
    for field in schema:
        col = field.name
        values = [r.get(col) for r in rows]
        try:
            arrays[col] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError):
            arrays[col] = pa.array(values)

    return pa.table(arrays, schema=schema)


def write_shadow_table(arrow_table, cycle_num):
    """Write corrupted data as a parquet file in the shadow directory."""
    SHADOW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHADOW_META_DIR.mkdir(parents=True, exist_ok=True)

    out_file = SHADOW_DATA_DIR / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out_file))
    return out_file


def register_shadow_in_catalog(parquet_path, arrow_table):
    """Register the shadow table in the Iceberg catalog under shadow_raw namespace."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, DoubleType, IntegerType,
        LongType, NestedField, StringType, TimestampType,
    )

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)

    # Create shadow_raw namespace if needed
    try:
        catalog.create_namespace("shadow_raw")
    except Exception:
        pass

    # Drop existing shadow table
    try:
        catalog.drop_table("shadow_raw.bls_ooh")
    except Exception:
        pass

    # Define schema matching the real table
    iceberg_schema = Schema(
        NestedField(1, "soc_code", StringType(), required=False),
        NestedField(2, "occupation_title", StringType(), required=False),
        NestedField(3, "employment_current", LongType(), required=False),
        NestedField(4, "employment_projected", LongType(), required=False),
        NestedField(5, "employment_change", LongType(), required=False),
        NestedField(6, "employment_change_pct", DoubleType(), required=False),
        NestedField(7, "openings_annual_avg", LongType(), required=False),
        NestedField(8, "median_annual_wage", DoubleType(), required=False),
        NestedField(9, "median_wage_capped", BooleanType(), required=False),
        NestedField(10, "education_typical", StringType(), required=False),
        NestedField(11, "education_code", IntegerType(), required=False),
        NestedField(12, "work_experience", StringType(), required=False),
        NestedField(13, "work_experience_code", IntegerType(), required=False),
        NestedField(14, "training_typical", StringType(), required=False),
        NestedField(15, "training_code", IntegerType(), required=False),
        NestedField(16, "ingested_at", TimestampType(), required=False),
        NestedField(17, "source_url", StringType(), required=False),
        NestedField(18, "source_method", StringType(), required=False),
        NestedField(19, "load_date", DateType(), required=False),
    )

    shadow_table = catalog.create_table("shadow_raw.bls_ooh", schema=iceberg_schema)

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
    result = run_rules(spec="raw-ingest-bls-ooh", catalog=catalog, shadow=True)
    return result


def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)

    # Load fresh source data
    print("Loading source data from sample XLSX...")
    rows = load_source_data()
    original_count = len(rows)
    print(f"  Loaded {original_count} rows")

    # Calculate how many rows to corrupt per dimension
    # For small datasets (like our 10-row sample), ensure at least 2 rows per function
    n_corrupt = max(1, int(original_count * rate))
    all_indices = list(range(original_count))

    per_function = max(2, n_corrupt // len(CORRUPTION_FUNCTIONS))

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
            import traceback
            traceback.print_exc()

    print(f"  Total corruptions: {len(all_manifest)}")
    print(f"  Final row count: {len(rows)} (was {original_count})")

    # Convert to arrow and write shadow table
    print("Writing shadow table...")
    try:
        arrow_table = rows_to_arrow(rows)
        parquet_path = write_shadow_table(arrow_table, cycle_num)
        print(f"  Written to {parquet_path}")

        # Register in Iceberg catalog
        print("Registering in Iceberg catalog...")
        register_shadow_in_catalog(parquet_path, arrow_table)
        print("  Registered as shadow_raw.bls_ooh")

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
        dq_result = {
            "run_id": "error", "rules_total": 0, "rules_passed": 0,
            "rules_failed": 0, "p0_passed": True, "results": [],
        }

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
    """Analyze which corruptions were caught vs missed."""
    dq_result = cycle_result["dq_result"]
    manifest = cycle_result["manifest"]

    failed_rules = [r for r in dq_result.get("results", []) if not r["passed"] and not r.get("error")]
    passed_rules = [r for r in dq_result.get("results", []) if r["passed"]]
    errored_rules = [r for r in dq_result.get("results", []) if r.get("error")]

    dims = {}
    for entry in manifest:
        dim = entry["dimension"]
        dims.setdefault(dim, []).append(entry)

    total_rules = len(dq_result.get("results", []))
    detection_rate = len(failed_rules) / total_rules if total_rules > 0 else 0

    return {
        "failed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value")} for r in failed_rules],
        "passed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value"), "threshold": r.get("threshold")} for r in passed_rules],
        "errored_rules": [r["rule_id"] for r in errored_rules],
        "injected_dimensions": sorted(dims),
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
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
        catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
        catalog.drop_table("shadow_raw.bls_ooh")
    except Exception:
        pass


def main():
    """Run 5-cycle adversarial hardening."""
    all_cycles = []
    all_gaps = []
    consecutive_no_new_gaps = 0
    previous_failed = set()

    for cycle_num, rate in enumerate(RATES, 1):
        seed = SEED_BASE + cycle_num
        cycle_result = run_cycle(cycle_num, rate, seed)
        gap_analysis = analyze_gaps(cycle_result)

        current_failed = set(r["rule_id"] for r in gap_analysis["failed_rules"])
        if current_failed == previous_failed and cycle_num > 1:
            consecutive_no_new_gaps += 1
        else:
            consecutive_no_new_gaps = 0
        previous_failed = current_failed

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

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": "raw-ingest-bls-ooh",
        "table": "raw.bls_ooh",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/raw-ingest-bls-ooh-manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2, default=str) + "\n")
    print(f"\nManifest written to: {manifest_path}")

    return manifest_data


if __name__ == "__main__":
    result = main()
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for c in result["cycles"]:
        ga = c["gap_analysis"]
        print(
            f"Cycle {c['cycle']} ({c['rate']*100:.0f}%): "
            f"{c['dq_failed']}/{c['dq_total']} rules failed, "
            f"detection rate: {ga['detection_rate']*100:.1f}%, "
            f"silent rules: {[r['rule_id'] for r in ga['passed_rules']]}"
        )
