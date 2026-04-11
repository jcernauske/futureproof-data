"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: raw-ingest-karpathy-ai-exposure
Table: bronze.karpathy_ai_exposure (342 rows)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.

INFORMATION BARRIER: This file was written WITHOUT reading DQ rule definitions.
Corruption strategies are derived from schema introspection and domain knowledge only.
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
DATA_FILE = PROJECT_ROOT / "data/bronze/iceberg_warehouse/bronze/karpathy_ai_exposure/data/00000-0-3061fc44-4498-4954-8ac9-2e39ebadb81d.parquet"
SHADOW_DIR = PROJECT_ROOT / "data/bronze/iceberg_warehouse/shadow_bronze/karpathy_ai_exposure"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42

sys.path.insert(0, str(PROJECT_ROOT / "src"))

# ---------------------------------------------------------------------------
# Load source data
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Corruption strategies (one per DQ dimension)
# ---------------------------------------------------------------------------


def corrupt_completeness(rows, indices, rng):
    """Null out required fields: slug, occupation_title, exposure_score, rationale."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(["slug", "occupation_title", "exposure_score", "rationale", "category"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null",
        })
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid values: bad SOC codes, out-of-range exposure_score, empty strings."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_soc_format", "exposure_out_of_range", "empty_string_slug",
            "bad_exposure_negative", "bad_soc_summary_code",
        ])
        if strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice([
                "151252", "15.1252", "XX-XXXX", "15-12520", "1-1252", "abc", "00-0000",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
            })
        elif strategy == "exposure_out_of_range":
            old_val = rows[i]["exposure_score"]
            rows[i]["exposure_score"] = rng.choice([11, 15, 99, 100, 999])
            manifest.append({
                "row": i, "dimension": "validity", "field": "exposure_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["exposure_score"]),
            })
        elif strategy == "empty_string_slug":
            old_val = rows[i]["slug"]
            rows[i]["slug"] = ""
            manifest.append({
                "row": i, "dimension": "validity", "field": "slug",
                "strategy": strategy, "old_value": str(old_val), "new_value": "",
            })
        elif strategy == "bad_exposure_negative":
            old_val = rows[i]["exposure_score"]
            rows[i]["exposure_score"] = rng.choice([-1, -5, -10, 0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "exposure_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["exposure_score"]),
            })
        elif strategy == "bad_soc_summary_code":
            old_val = rows[i]["soc_code"]
            prefix = old_val[:2] if old_val and len(old_val) >= 2 else "11"
            rows[i]["soc_code"] = f"{prefix}-0000"
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
            })
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows (same slug)."""
    manifest = []
    n_dupes = max(1, len(indices) // 3)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "slug",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx} (slug={rows[src_idx]['slug']})",
            "new_value": f"duplicate at position {insert_pos}",
        })
    return manifest


def corrupt_consistency(rows, indices, rng):
    """Contradictory field combinations: slug doesn't match occupation_title pattern,
    exposure_score high but rationale says low impact, etc."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "slug_title_mismatch", "category_title_mismatch",
            "source_method_url_mismatch",
        ])
        if strategy == "slug_title_mismatch":
            old_title = rows[i]["occupation_title"]
            # Set a completely mismatched title for the slug
            rows[i]["occupation_title"] = rng.choice([
                "Plumber", "Astronaut", "Deep Sea Welder", "Space Janitor",
            ])
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "occupation_title",
                "strategy": strategy,
                "old_value": str(old_title),
                "new_value": rows[i]["occupation_title"],
            })
        elif strategy == "category_title_mismatch":
            old_cat = rows[i]["category"]
            rows[i]["category"] = rng.choice([
                "INVALID_CATEGORY", "zzzz-nonexistent", "123numeric",
            ])
            manifest.append({
                "row": i, "dimension": "consistency", "field": "category",
                "strategy": strategy,
                "old_value": str(old_cat),
                "new_value": rows[i]["category"],
            })
        elif strategy == "source_method_url_mismatch":
            old_method = rows[i].get("source_method")
            rows[i]["source_method"] = "manual_entry"
            manifest.append({
                "row": i, "dimension": "consistency", "field": "source_method",
                "strategy": strategy,
                "old_value": str(old_method),
                "new_value": "manual_entry",
            })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: subtly wrong SOC codes, swapped median_pay."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "wrong_soc_prefix", "swapped_pay_jobs", "plausible_wrong_score",
        ])
        if strategy == "wrong_soc_prefix":
            old_val = rows[i]["soc_code"]
            if old_val and len(old_val) >= 7:
                # Change just the major group -- plausible but wrong
                new_prefix = rng.choice(["11", "13", "15", "17", "19", "21", "23", "25", "27"])
                rows[i]["soc_code"] = new_prefix + old_val[2:]
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "soc_code",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": rows[i]["soc_code"],
                })
        elif strategy == "swapped_pay_jobs":
            old_pay = rows[i].get("median_pay_annual")
            old_jobs = rows[i].get("num_jobs_2024")
            if old_pay is not None and old_jobs is not None:
                # Swap pay and jobs -- structurally valid, semantically wrong
                rows[i]["median_pay_annual"] = float(old_jobs)
                rows[i]["num_jobs_2024"] = int(old_pay)
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "median_pay_annual,num_jobs_2024",
                    "strategy": strategy,
                    "old_value": f"pay={old_pay},jobs={old_jobs}",
                    "new_value": f"pay={float(old_jobs)},jobs={int(old_pay)}",
                })
        elif strategy == "plausible_wrong_score":
            old_val = rows[i]["exposure_score"]
            # Shift score by 3-5 points but keep in valid range
            delta = rng.choice([-4, -3, 3, 4, 5])
            new_val = max(1, min(10, old_val + delta))
            if new_val != old_val:
                rows[i]["exposure_score"] = new_val
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "exposure_score",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(new_val),
                })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: impossibly high pay, negative jobs count."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_pay", "negative_pay", "extreme_jobs", "negative_jobs",
        ])
        if strategy == "extreme_pay":
            old_val = rows[i].get("median_pay_annual")
            rows[i]["median_pay_annual"] = float(rng.randint(5000000, 99000000))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "median_pay_annual",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_pay_annual"]),
            })
        elif strategy == "negative_pay":
            old_val = rows[i].get("median_pay_annual")
            rows[i]["median_pay_annual"] = float(rng.randint(-500000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "median_pay_annual",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_pay_annual"]),
            })
        elif strategy == "extreme_jobs":
            old_val = rows[i].get("num_jobs_2024")
            rows[i]["num_jobs_2024"] = rng.randint(500000000, 999999999)
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "num_jobs_2024",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["num_jobs_2024"]),
            })
        elif strategy == "negative_jobs":
            old_val = rows[i].get("num_jobs_2024")
            rows[i]["num_jobs_2024"] = rng.randint(-1000000, -1)
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "num_jobs_2024",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["num_jobs_2024"]),
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
    """Row count anomalies: mass-duplicate to inflate count."""
    manifest = []
    # Add a large batch of duplicates to trigger volume rules
    # Original is 342 rows -- add ~100 to push way above threshold
    n_extras = max(50, len(rows) // 5)
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
    """Orphan SOC codes: valid-format but nonexistent codes."""
    manifest = []
    valid_indices = [i for i in indices if i < len(rows) and rows[i].get("soc_code")]
    if not valid_indices:
        return manifest
    targets = rng.sample(valid_indices, min(len(valid_indices), max(1, len(valid_indices) // 3)))
    for i in targets:
        old_val = rows[i]["soc_code"]
        fake_soc = f"{rng.randint(90, 99)}-{rng.randint(1000, 9999)}"
        rows[i]["soc_code"] = fake_soc
        manifest.append({
            "row": i, "dimension": "referential_integrity", "field": "soc_code",
            "strategy": "orphan_soc", "old_value": str(old_val),
            "new_value": fake_soc,
        })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove all rows for entire categories."""
    manifest = []
    # Find categories and remove all rows for 2-3 of them
    cat_counts = {}
    for i, row in enumerate(rows):
        cat = row.get("category")
        if cat:
            cat_counts.setdefault(cat, []).append(i)

    # Remove rows for 2 random categories
    if len(cat_counts) >= 3:
        targets = rng.sample(list(cat_counts.keys()), 2)
        removed_indices = set()
        for cat in targets:
            for idx in cat_counts[cat]:
                removed_indices.add(idx)
            manifest.append({
                "row": -1, "dimension": "coverage", "field": "category",
                "strategy": f"remove_all_category_{cat}",
                "old_value": f"category={cat}, count={len(cat_counts[cat])}",
                "new_value": "removed",
            })

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
    corrupt_referential_integrity,
    # These change row count, so run last:
    corrupt_volume,
    corrupt_coverage,
]


def rows_to_arrow(rows):
    """Convert list of dicts to a PyArrow table with appropriate types."""
    schema = pa.schema([
        pa.field("slug", pa.large_string()),
        pa.field("occupation_title", pa.large_string()),
        pa.field("category", pa.large_string()),
        pa.field("soc_code", pa.large_string()),
        pa.field("exposure_score", pa.int32()),
        pa.field("rationale", pa.large_string()),
        pa.field("median_pay_annual", pa.float64()),
        pa.field("num_jobs_2024", pa.int64()),
        pa.field("entry_education", pa.large_string()),
        pa.field("ingested_at", pa.timestamp("us")),
        pa.field("source_url", pa.large_string()),
        pa.field("source_method", pa.large_string()),
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


def register_shadow_in_catalog(parquet_path):
    """Register the shadow table in the Iceberg catalog under shadow_bronze namespace."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType, DoubleType, IntegerType, LongType,
        NestedField, StringType, TimestampType,
    )

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)

    # Create shadow_bronze namespace if needed
    try:
        catalog.create_namespace("shadow_bronze")
    except Exception:
        pass

    # Drop existing shadow table
    try:
        catalog.drop_table("shadow_bronze.karpathy_ai_exposure")
    except Exception:
        pass

    # Define schema matching the real table (all nullable for shadow)
    iceberg_schema = Schema(
        NestedField(1, "slug", StringType(), required=False),
        NestedField(2, "occupation_title", StringType(), required=False),
        NestedField(3, "category", StringType(), required=False),
        NestedField(4, "soc_code", StringType(), required=False),
        NestedField(5, "exposure_score", IntegerType(), required=False),
        NestedField(6, "rationale", StringType(), required=False),
        NestedField(7, "median_pay_annual", DoubleType(), required=False),
        NestedField(8, "num_jobs_2024", LongType(), required=False),
        NestedField(9, "entry_education", StringType(), required=False),
        NestedField(10, "ingested_at", TimestampType(), required=False),
        NestedField(11, "source_url", StringType(), required=False),
        NestedField(12, "source_method", StringType(), required=False),
        NestedField(13, "load_date", DateType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_bronze.karpathy_ai_exposure", schema=iceberg_schema
    )

    # Read the parquet and append to shadow table
    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)

    return shadow_table


def run_dq_rules_shadow():
    """Run DQ rules against the shadow table and return results."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    result = run_rules(
        spec="raw-ingest-karpathy-ai-exposure", catalog=catalog, shadow=True
    )
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

    # Calculate how many rows to corrupt per dimension
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
        register_shadow_in_catalog(parquet_path)
        print("  Registered as shadow_bronze.karpathy_ai_exposure")

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
            print(f"    {r['rule_id']:<45} {status:<6} value={r.get('raw_value', '?')}")

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

    failed_rules = [
        r for r in dq_result.get("results", [])
        if not r["passed"] and not r.get("error")
    ]
    passed_rules = [
        r for r in dq_result.get("results", []) if r["passed"]
    ]
    errored_rules = [
        r for r in dq_result.get("results", []) if r.get("error")
    ]

    dims = {}
    for entry in manifest:
        dim = entry["dimension"]
        dims.setdefault(dim, []).append(entry)

    total_rules = len(dq_result.get("results", []))
    detection_rate = len(failed_rules) / total_rules if total_rules > 0 else 0

    return {
        "failed_rules": [
            {"rule_id": r["rule_id"], "raw_value": r.get("raw_value")}
            for r in failed_rules
        ],
        "passed_rules": [
            {"rule_id": r["rule_id"], "raw_value": r.get("raw_value"),
             "threshold": r.get("threshold")}
            for r in passed_rules
        ],
        "errored_rules": [r["rule_id"] for r in errored_rules],
        "injected_dimensions": sorted(dims),
        "corruptions_per_dimension": {
            dim: len(entries) for dim, entries in dims.items()
        },
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
        catalog.drop_table("shadow_bronze.karpathy_ai_exposure")
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
        print(f"    Detection rate: {gap_analysis['detection_rate']*100:.1f}% "
              f"({gap_analysis['rules_fired']}/{gap_analysis['total_rules']} rules fired)")
        print(f"    Rules that fired: {[r['rule_id'] for r in gap_analysis['failed_rules']]}")
        print(f"    Rules silent: {[r['rule_id'] for r in gap_analysis['passed_rules']]}")

        if consecutive_no_new_gaps >= 2:
            print("\n  Stability detected: same rules firing for 2 consecutive cycles.")

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": "raw-ingest-karpathy-ai-exposure",
        "table": "bronze.karpathy_ai_exposure",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = (
        PROJECT_ROOT
        / "governance/chaos-manifests/raw-ingest-karpathy-ai-exposure-manifest.json"
    )
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
