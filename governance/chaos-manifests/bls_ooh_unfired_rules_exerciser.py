"""
Targeted Chaos Monkey Exerciser for 4 Unfired Rules
Spec: raw-ingest-bls-ooh
Table: raw.bls_ooh

Exercises the 4 rules that never fired in the initial 5-cycle hardening run:
  RAW-OOH-005: Education code range 1-8
  RAW-OOH-006: Work experience code range 1-3
  RAW-OOH-007: Training code range 1-6
  RAW-OOH-011: Employment current positive

Uses the full 832-row dataset for realistic coverage.
Each rule is tested individually with a targeted corruption.
"""

import copy
import datetime
import json
import shutil
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
FULL_XLSX = PROJECT_ROOT / "data/raw/xlsx_cache/bls_ooh.xlsx"
SHADOW_DIR = PROJECT_ROOT / "data/bronze/iceberg_warehouse/shadow_raw/bls_ooh"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

sys.path.insert(0, str(PROJECT_ROOT / "src"))


def load_full_dataset():
    """Load and flatten the full 832-row BLS OOH dataset."""
    from raw.bls_ooh_ingestor import BlsOohIngestor

    ingestor = BlsOohIngestor.__new__(BlsOohIngestor)
    raw_rows = ingestor._read_xlsx(FULL_XLSX)
    flat_rows = ingestor.flatten(raw_rows, "ooh")

    now = datetime.datetime.utcnow()
    today = datetime.date.today()
    for row in flat_rows:
        row["ingested_at"] = now
        row["source_url"] = "https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm"
        row["source_method"] = "xlsx_download"
        row["load_date"] = today

    return flat_rows


def rows_to_arrow(rows):
    """Convert list of dicts to a PyArrow table."""
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


def write_and_register_shadow(rows, label):
    """Write shadow table and register in Iceberg catalog."""
    SHADOW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHADOW_META_DIR.mkdir(parents=True, exist_ok=True)

    arrow_table = rows_to_arrow(rows)
    out_file = SHADOW_DATA_DIR / "chaos-targeted.parquet"
    pq.write_table(arrow_table, str(out_file))

    # Register in catalog
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, DoubleType, IntegerType,
        LongType, NestedField, StringType, TimestampType,
    )

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)

    try:
        catalog.create_namespace("shadow_raw")
    except Exception:
        pass

    try:
        catalog.drop_table("shadow_raw.bls_ooh")
    except Exception:
        pass

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
    data = pq.read_table(str(out_file))
    shadow_table.append(data)

    return shadow_table


def cleanup_shadow():
    """Remove shadow table and files."""
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
        catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
        catalog.drop_table("shadow_raw.bls_ooh")
    except Exception:
        pass


def run_dq_rules():
    """Run DQ rules against shadow table."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    return run_rules(spec="raw-ingest-bls-ooh", catalog=catalog, shadow=True)


# ---------------------------------------------------------------------------
# Targeted corruptions for each unfired rule
# ---------------------------------------------------------------------------

TARGETS = [
    {
        "rule_id": "RAW-OOH-005",
        "name": "Education code range 1-8",
        "field": "education_code",
        "corrupt_value": 99,
        "row_index": 5,
        "description": "Set education_code to 99 (outside valid range 1-8)",
    },
    {
        "rule_id": "RAW-OOH-006",
        "name": "Work experience code range 1-3",
        "field": "work_experience_code",
        "corrupt_value": 10,
        "row_index": 10,
        "description": "Set work_experience_code to 10 (outside valid range 1-3)",
    },
    {
        "rule_id": "RAW-OOH-007",
        "name": "Training code range 1-6",
        "field": "training_code",
        "corrupt_value": 99,
        "row_index": 15,
        "description": "Set training_code to 99 (outside valid range 1-6)",
    },
    {
        "rule_id": "RAW-OOH-011",
        "name": "Employment current positive",
        "field": "employment_current",
        "corrupt_value": -5000,
        "row_index": 20,
        "description": "Set employment_current to -5000 (negative, domain-impossible)",
    },
]


def main():
    """Test each unfired rule with a targeted corruption."""
    print("=" * 70)
    print("TARGETED EXERCISER FOR 4 UNFIRED RULES")
    print("Using full 832-row dataset")
    print("=" * 70)

    # Load the full dataset once
    print("\nLoading full dataset...")
    base_rows = load_full_dataset()
    print("  Loaded {} rows".format(len(base_rows)))

    results = []

    for target in TARGETS:
        print("\n" + "-" * 70)
        print("Testing {}: {}".format(target["rule_id"], target["name"]))
        print("  Corruption: {}".format(target["description"]))

        # Make a fresh copy with all 4 corruptions injected together
        rows = copy.deepcopy(base_rows)

        # Inject this specific corruption
        row_idx = target["row_index"]
        old_value = rows[row_idx][target["field"]]
        rows[row_idx][target["field"]] = target["corrupt_value"]
        print("  Row {}: {} = {} -> {}".format(
            row_idx, target["field"], old_value, target["corrupt_value"]
        ))

        # Write shadow table
        print("  Writing shadow table ({} rows)...".format(len(rows)))
        write_and_register_shadow(rows, target["rule_id"])

        # Run DQ rules
        print("  Running DQ rules...")
        dq_result = run_dq_rules()

        # Find the target rule result
        target_rule_result = None
        for r in dq_result.get("results", []):
            if r["rule_id"] == target["rule_id"]:
                target_rule_result = r
                break

        if target_rule_result is None:
            print("  ERROR: Rule {} not found in DQ results!".format(target["rule_id"]))
            fired = False
        else:
            fired = not target_rule_result["passed"]
            status = "FIRED (caught corruption)" if fired else "SILENT (missed corruption)"
            print("  Result: {} | raw_value={}".format(
                status, target_rule_result.get("raw_value", "?")
            ))

        results.append({
            "rule_id": target["rule_id"],
            "name": target["name"],
            "corruption": target["description"],
            "field": target["field"],
            "old_value": str(old_value),
            "new_value": str(target["corrupt_value"]),
            "fired": fired,
            "raw_value": target_rule_result.get("raw_value") if target_rule_result else None,
        })

        # Also print summary of all rules for this run
        failed_rules = [r["rule_id"] for r in dq_result.get("results", []) if not r["passed"]]
        print("  All rules that fired: {}".format(failed_rules))

        # Cleanup between tests
        cleanup_shadow()

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_fired = True
    for r in results:
        status = "FIRED" if r["fired"] else "MISSED"
        print("  {}: {} - {} ({} = {})".format(
            r["rule_id"], status, r["name"], r["field"], r["new_value"]
        ))
        if not r["fired"]:
            all_fired = False

    if all_fired:
        print("\nAll 4 unfired rules now confirmed FIRING.")
        print("Combined with 14 previously-fired rules: 18/18 rules exercised.")
    else:
        missed = [r["rule_id"] for r in results if not r["fired"]]
        print("\nStill unfired: {}".format(missed))

    # Write results JSON
    output = {
        "spec": "raw-ingest-bls-ooh",
        "run_type": "targeted_unfired_rules",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dataset_size": len(base_rows),
        "results": results,
        "all_fired": all_fired,
    }

    output_path = PROJECT_ROOT / "governance/chaos-manifests/raw-ingest-bls-ooh-unfired-results.json"
    output_path.write_text(json.dumps(output, indent=2, default=str) + "\n")
    print("\nResults written to: {}".format(output_path))

    return output


if __name__ == "__main__":
    main()
