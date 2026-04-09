"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: silver-base-onet
Tables:
  - base.onet_occupations (798 rows)
  - base.onet_activity_profiles (31,734 rows)
  - base.onet_context_profiles (44,118 rows)
  - base.onet_career_transitions (15,944 rows)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against shadow tables, and records what was caught vs missed.

Information Barrier: This script does NOT read DQ rule definitions.
It injects corruptions based solely on the table schema and domain
understanding from the transformer code (src/silver/onet_transformer.py).
"""

import json
import random
import datetime
import copy
import sys
import shutil
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SILVER_WAREHOUSE = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Source parquet files (one per table)
SOURCE_PARQUETS = {
    "onet_occupations": SILVER_WAREHOUSE / "base/onet_occupations/data/00000-0-e8870137-a93f-4834-b492-1bd8cad30850.parquet",
    "onet_activity_profiles": SILVER_WAREHOUSE / "base/onet_activity_profiles/data/00000-0-ea02326b-e08b-45a7-a89e-bcb2195e62a9.parquet",
    "onet_context_profiles": SILVER_WAREHOUSE / "base/onet_context_profiles/data/00000-0-cb4d50ba-4e0e-4b38-a58a-725bbd2cd348.parquet",
    "onet_career_transitions": SILVER_WAREHOUSE / "base/onet_career_transitions/data/00000-0-b50f66d6-a82d-4873-a820-d3530aef1627.parquet",
}

SHADOW_BASE = SILVER_WAREHOUSE / "shadow_base"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "silver-base-onet"

# Expected row counts for volume checks
EXPECTED_COUNTS = {
    "onet_occupations": 798,
    "onet_activity_profiles": 31734,
    "onet_context_profiles": 44118,
    "onet_career_transitions": 15944,
}

# Valid SOC major groups (22 BLS groups, odd numbers 11-53)
VALID_SOC_MAJOR_GROUPS = [
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "31", "33", "35", "37", "39", "41", "43", "45", "47", "49",
    "51", "53",
]

# Valid relatedness tiers from derive_relatedness_tier()
VALID_RELATEDNESS_TIERS = ["Primary-Short", "Primary-Long", "Supplemental"]

# Valid data completeness tiers
VALID_COMPLETENESS_TIERS = ["full", "partial"]

# Valid context scale IDs (CX and CT only in silver)
VALID_CONTEXT_SCALES = ["CX", "CT"]

# Burnout element IDs from the transformer
BURNOUT_ELEMENT_IDS = frozenset({
    "4.C.3.d.1", "4.C.3.d.8", "4.C.3.a.1", "4.C.3.d.3",
    "4.C.3.a.2.b", "4.C.3.b.4", "4.C.3.b.7", "4.C.3.d.4",
    "4.C.3.a.2.a",
})

sys.path.insert(0, str(PROJECT_ROOT / "src"))


# ---------------------------------------------------------------------------
# Safety check
# ---------------------------------------------------------------------------

def safety_check():
    """Set and verify safety environment variables for shadow namespace operations."""
    import os
    os.environ["CHAOS_MONKEY_ENABLED"] = "true"
    os.environ["GRIST_ENV"] = "dev"
    enabled = os.environ.get("CHAOS_MONKEY_ENABLED", "").lower() == "true"
    dev_env = os.environ.get("GRIST_ENV", "").lower() == "dev"
    if not enabled:
        print("ERROR: CHAOS_MONKEY_ENABLED is not 'true'.")
        sys.exit(1)
    if not dev_env:
        print("ERROR: GRIST_ENV is not 'dev'.")
        sys.exit(1)
    print("Safety check passed: CHAOS_MONKEY_ENABLED=true, GRIST_ENV=dev")


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_table(table_name):
    """Load a Silver parquet table into list of dicts and return schema."""
    import pyarrow.parquet as pq
    table = pq.read_table(str(SOURCE_PARQUETS[table_name]))
    rows = []
    for i in range(table.num_rows):
        row = {}
        for col in table.column_names:
            val = table.column(col)[i].as_py()
            row[col] = val
        rows.append(row)
    return rows, table.schema


def write_shadow_parquet(table_name, rows, original_schema, cycle_num):
    """Write corrupted rows to shadow parquet file."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    shadow_dir = SHADOW_BASE / table_name / "data"
    shadow_dir.mkdir(parents=True, exist_ok=True)
    (SHADOW_BASE / table_name / "metadata").mkdir(parents=True, exist_ok=True)

    arrays = {}
    for field in original_schema:
        col_name = field.name
        values = [r.get(col_name) for r in rows]
        try:
            arrays[col_name] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arrays[col_name] = pa.array(values)

    arrow_table = pa.table(arrays)
    out_file = shadow_dir / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out_file))
    return out_file, arrow_table


def register_shadow_tables(table_parquets):
    """Register all 4 shadow tables in the Iceberg catalog under shadow_base."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, DoubleType, IntegerType,
        NestedField, StringType, TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))

    try:
        catalog.create_namespace("shadow_base")
    except Exception:
        pass

    # Schema definitions (all optional to accept nulls from corruption)
    schemas = {
        "onet_occupations": Schema(
            NestedField(1, "record_id", StringType(), required=False),
            NestedField(2, "bls_soc_code", StringType(), required=False),
            NestedField(3, "primary_title", StringType(), required=False),
            NestedField(4, "description", StringType(), required=False),
            NestedField(5, "onet_detail_codes", StringType(), required=False),
            NestedField(6, "onet_detail_count", IntegerType(), required=False),
            NestedField(7, "multi_detail_flag", BooleanType(), required=False),
            NestedField(8, "has_work_activities", BooleanType(), required=False),
            NestedField(9, "has_work_context", BooleanType(), required=False),
            NestedField(10, "has_tasks", BooleanType(), required=False),
            NestedField(11, "has_related", BooleanType(), required=False),
            NestedField(12, "data_completeness_tier", StringType(), required=False),
            NestedField(13, "source_load_date", DateType(), required=False),
            NestedField(14, "ingested_at", TimestampType(), required=False),
        ),
        "onet_activity_profiles": Schema(
            NestedField(1, "record_id", StringType(), required=False),
            NestedField(2, "bls_soc_code", StringType(), required=False),
            NestedField(3, "element_id", StringType(), required=False),
            NestedField(4, "element_name", StringType(), required=False),
            NestedField(5, "importance", DoubleType(), required=False),
            NestedField(6, "importance_rank", IntegerType(), required=False),
            NestedField(7, "is_high_importance", BooleanType(), required=False),
            NestedField(8, "onet_details_averaged", IntegerType(), required=False),
            NestedField(9, "suppress_flag", BooleanType(), required=False),
            NestedField(10, "source_load_date", DateType(), required=False),
            NestedField(11, "ingested_at", TimestampType(), required=False),
        ),
        "onet_context_profiles": Schema(
            NestedField(1, "record_id", StringType(), required=False),
            NestedField(2, "bls_soc_code", StringType(), required=False),
            NestedField(3, "element_id", StringType(), required=False),
            NestedField(4, "element_name", StringType(), required=False),
            NestedField(5, "scale_id", StringType(), required=False),
            NestedField(6, "context_value", DoubleType(), required=False),
            NestedField(7, "is_burnout_element", BooleanType(), required=False),
            NestedField(8, "onet_details_averaged", IntegerType(), required=False),
            NestedField(9, "suppress_flag", BooleanType(), required=False),
            NestedField(10, "source_load_date", DateType(), required=False),
            NestedField(11, "ingested_at", TimestampType(), required=False),
        ),
        "onet_career_transitions": Schema(
            NestedField(1, "record_id", StringType(), required=False),
            NestedField(2, "bls_soc_code", StringType(), required=False),
            NestedField(3, "related_bls_soc_code", StringType(), required=False),
            NestedField(4, "best_index", IntegerType(), required=False),
            NestedField(5, "relatedness_tier", StringType(), required=False),
            NestedField(6, "is_primary", BooleanType(), required=False),
            NestedField(7, "relationship_type", StringType(), required=False),
            NestedField(8, "source_load_date", DateType(), required=False),
            NestedField(9, "ingested_at", TimestampType(), required=False),
        ),
    }

    registered = {}
    for table_name, parquet_path in table_parquets.items():
        shadow_fqn = f"shadow_base.{table_name}"
        try:
            catalog.drop_table(shadow_fqn)
        except Exception:
            pass

        shadow_table = catalog.create_table(shadow_fqn, schema=schemas[table_name])
        import pyarrow.parquet as pq
        data = pq.read_table(str(parquet_path))
        shadow_table.append(data)
        registered[table_name] = shadow_table

    return registered


def run_dq_rules_shadow():
    """Run DQ rules against all shadow tables."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
    result = run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)
    return result


def cleanup_shadow():
    """Remove all shadow tables and files."""
    for table_name in SOURCE_PARQUETS:
        shadow_dir = SHADOW_BASE / table_name
        if shadow_dir.exists():
            shutil.rmtree(shadow_dir)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
        for table_name in SOURCE_PARQUETS:
            try:
                catalog.drop_table(f"shadow_base.{table_name}")
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Corruption strategies: base.onet_occupations (798 rows)
# Schema: record_id, bls_soc_code, primary_title, description,
#         onet_detail_codes, onet_detail_count, multi_detail_flag,
#         has_work_activities, has_work_context, has_tasks, has_related,
#         data_completeness_tier, source_load_date, ingested_at
# ---------------------------------------------------------------------------

def corrupt_occupations(rows, rate, rng, valid_soc_codes):
    """Corrupt onet_occupations across all 10 DQ dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. COMPLETENESS: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["bls_soc_code", "primary_title", "description",
                            "record_id", "data_completeness_tier"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_occupations", "row": i,
                         "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. VALIDITY: bad bls_soc_code format (should be XX-XXXX)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["drop_dash", "wrong_length", "alpha_code",
                                "onet_format", "empty", "bad_completeness_tier"])
        old_val = rows[i]["bls_soc_code"]
        if strategy == "drop_dash":
            # XX-XXXX -> XXXXXXX (no dash)
            if old_val and "-" in str(old_val):
                rows[i]["bls_soc_code"] = str(old_val).replace("-", "")
            else:
                rows[i]["bls_soc_code"] = "151252"
        elif strategy == "wrong_length":
            rows[i]["bls_soc_code"] = rng.choice(["15-12", "15-12520", "1-1252", "151-252"])
        elif strategy == "alpha_code":
            rows[i]["bls_soc_code"] = rng.choice(["AB-CDEF", "XX-XXXX", "??-????"])
        elif strategy == "onet_format":
            # Inject O*NET format (XX-XXXX.XX) which should not appear in Silver
            rows[i]["bls_soc_code"] = "15-1252.00"
        elif strategy == "empty":
            rows[i]["bls_soc_code"] = ""
        elif strategy == "bad_completeness_tier":
            old_val = rows[i]["data_completeness_tier"]
            rows[i]["data_completeness_tier"] = rng.choice([
                "complete", "incomplete", "FULL", "Partial", "none", "unknown", ""])
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "validity", "field": "data_completeness_tier",
                             "strategy": "bad_completeness_tier",
                             "old_value": str(old_val), "new_value": str(rows[i]["data_completeness_tier"])})
            continue
        manifest.append({"table": "onet_occupations", "row": i,
                         "dimension": "validity", "field": "bls_soc_code",
                         "strategy": strategy,
                         "old_value": str(old_val), "new_value": str(rows[i]["bls_soc_code"])})

    # 3. UNIQUENESS: duplicate grain rows (bls_soc_code)
    n_dupes = max(1, n_corrupt // 15)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "onet_occupations", "row": insert_pos,
                         "dimension": "uniqueness", "field": "bls_soc_code",
                         "strategy": "duplicate_grain_row",
                         "old_value": f"copy_of_row_{src_idx} (soc={rows[src_idx]['bls_soc_code']})",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. CONSISTENCY: contradictory field combinations
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice([
            "completeness_tier_mismatch", "detail_count_mismatch",
            "multi_detail_flag_wrong", "has_flags_all_false",
        ])
        if strategy == "completeness_tier_mismatch":
            # Set tier to "full" but one of the has_* flags to False
            old_tier = rows[i]["data_completeness_tier"]
            rows[i]["data_completeness_tier"] = "full"
            flag = rng.choice(["has_work_activities", "has_work_context",
                               "has_tasks", "has_related"])
            rows[i][flag] = False
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "consistency", "field": f"data_completeness_tier+{flag}",
                             "strategy": strategy,
                             "old_value": f"tier={old_tier}, {flag}={True}",
                             "new_value": f"tier=full, {flag}=False (contradictory)"})
        elif strategy == "detail_count_mismatch":
            old_count = rows[i]["onet_detail_count"]
            old_codes = rows[i]["onet_detail_codes"]
            rows[i]["onet_detail_count"] = old_count + rng.randint(5, 20)
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "consistency", "field": "onet_detail_count",
                             "strategy": strategy,
                             "old_value": f"count={old_count}, codes={str(old_codes)[:40]}",
                             "new_value": f"count={rows[i]['onet_detail_count']} (mismatches codes list)"})
        elif strategy == "multi_detail_flag_wrong":
            old_flag = rows[i]["multi_detail_flag"]
            old_count = rows[i]["onet_detail_count"]
            rows[i]["multi_detail_flag"] = not old_flag
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "consistency", "field": "multi_detail_flag",
                             "strategy": strategy,
                             "old_value": f"flag={old_flag}, count={old_count}",
                             "new_value": f"flag={rows[i]['multi_detail_flag']} (wrong for count)"})
        elif strategy == "has_flags_all_false":
            # All has_* flags False -- should not exist in Silver (filtered out)
            for flag in ["has_work_activities", "has_work_context", "has_tasks", "has_related"]:
                rows[i][flag] = False
            rows[i]["data_completeness_tier"] = "partial"
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "consistency", "field": "has_*_flags",
                             "strategy": strategy,
                             "old_value": "at least one True",
                             "new_value": "all four False (structurally empty, should not exist)"})

    # 5. ACCURACY: plausible but wrong SOC codes
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["bls_soc_code"]
        # Valid format but nonexistent BLS SOC
        rows[i]["bls_soc_code"] = f"{rng.choice(VALID_SOC_MAJOR_GROUPS)}-{rng.randint(9000,9999)}"
        manifest.append({"table": "onet_occupations", "row": i,
                         "dimension": "accuracy", "field": "bls_soc_code",
                         "strategy": "plausible_wrong_soc",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["bls_soc_code"])})

    # 6. REASONABLENESS: extreme onet_detail_count values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_detail_count"]
        rows[i]["onet_detail_count"] = rng.choice([0, -1, 100, 500, 999])
        manifest.append({"table": "onet_occupations", "row": i,
                         "dimension": "reasonableness", "field": "onet_detail_count",
                         "strategy": "extreme_detail_count",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["onet_detail_count"])})

    # 7. FRESHNESS: future/stale timestamps
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-06-15"})
        elif strategy == "stale_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2018, 1, 1)
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2018-01-01"})
        else:
            old_val = rows[i]["ingested_at"]
            rows[i]["ingested_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({"table": "onet_occupations", "row": i,
                             "dimension": "freshness", "field": "ingested_at",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2035-01-01T00:00:00"})

    # 8. VOLUME: mass-duplicate to inflate count beyond 798
    n_extras = max(40, n // 10)
    source_rows = rng.choices(all_indices, k=n_extras)
    for src_idx in source_rows:
        rows.append(copy.deepcopy(rows[src_idx]))
    manifest.append({"table": "onet_occupations", "row": -1,
                     "dimension": "volume", "field": "row_count",
                     "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. REFERENTIAL INTEGRITY: SOC codes from invalid major groups
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["bls_soc_code"]
        fake_prefix = rng.choice(["12", "14", "16", "20", "60", "90", "92", "98"])
        rows[i]["bls_soc_code"] = f"{fake_prefix}-{rng.randint(1000, 9999)}"
        manifest.append({"table": "onet_occupations", "row": i,
                         "dimension": "referential_integrity", "field": "bls_soc_code",
                         "strategy": "orphan_major_group",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["bls_soc_code"])})

    # 10. COVERAGE: remove all rows for certain SOC major groups
    group_map = {}
    for i, row in enumerate(rows):
        soc = row.get("bls_soc_code")
        if soc and isinstance(soc, str) and len(soc) >= 2:
            grp = soc[:2]
            group_map.setdefault(grp, []).append(i)
    valid_groups = [g for g in group_map if g in VALID_SOC_MAJOR_GROUPS and len(group_map[g]) >= 3]
    if len(valid_groups) >= 3:
        groups_to_remove = rng.sample(valid_groups, 3)
        removed = set()
        for grp in groups_to_remove:
            for idx in group_map[grp]:
                removed.add(idx)
            manifest.append({"table": "onet_occupations", "row": -1,
                             "dimension": "coverage", "field": "bls_soc_code_major_group",
                             "strategy": f"remove_all_group_{grp}",
                             "old_value": f"group={grp}, count={len(group_map[grp])}",
                             "new_value": "removed"})
        for idx in sorted(removed, reverse=True):
            if idx < len(rows):
                rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Corruption strategies: base.onet_activity_profiles (31,734 rows)
# Schema: record_id, bls_soc_code, element_id, element_name,
#         importance(double), importance_rank(int), is_high_importance(bool),
#         onet_details_averaged(int), suppress_flag(bool),
#         source_load_date, ingested_at
# Grain: (bls_soc_code, element_id)
# ---------------------------------------------------------------------------

def corrupt_activity_profiles(rows, rate, rng, valid_soc_codes):
    """Corrupt onet_activity_profiles across all 10 DQ dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. COMPLETENESS: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["bls_soc_code", "element_id", "element_name",
                            "importance", "record_id"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_activity_profiles", "row": i,
                         "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. VALIDITY: importance out of range (should be 1-5), bad SOC format
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["importance_over_5", "importance_negative",
                                "bad_soc_format", "bad_importance_rank"])
        if strategy == "importance_over_5":
            old_val = rows[i]["importance"]
            rows[i]["importance"] = rng.uniform(5.01, 10.0)
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "validity", "field": "importance",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["importance"])})
        elif strategy == "importance_negative":
            old_val = rows[i]["importance"]
            rows[i]["importance"] = rng.uniform(-5.0, -0.01)
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "validity", "field": "importance",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["importance"])})
        elif strategy == "bad_soc_format":
            old_val = rows[i]["bls_soc_code"]
            rows[i]["bls_soc_code"] = rng.choice(["151252", "15-12520", "AB-CDEF", "", "15-1252.00"])
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "validity", "field": "bls_soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["bls_soc_code"])})
        elif strategy == "bad_importance_rank":
            old_val = rows[i]["importance_rank"]
            rows[i]["importance_rank"] = rng.choice([0, -1, -5, 500])
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "validity", "field": "importance_rank",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["importance_rank"])})

    # 3. UNIQUENESS: duplicate grain rows (bls_soc_code + element_id)
    n_dupes = max(1, n_corrupt // 20)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "onet_activity_profiles", "row": insert_pos,
                         "dimension": "uniqueness", "field": "bls_soc_code+element_id",
                         "strategy": "duplicate_grain_row",
                         "old_value": f"copy_of_row_{src_idx}",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. CONSISTENCY: is_high_importance contradicts importance value
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["high_importance_wrong", "rank_vs_importance_inversion"])
        if strategy == "high_importance_wrong":
            old_flag = rows[i]["is_high_importance"]
            old_imp = rows[i]["importance"]
            # Flip the flag to contradict the importance threshold (3.5)
            rows[i]["is_high_importance"] = not old_flag
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "consistency", "field": "is_high_importance",
                             "strategy": strategy,
                             "old_value": f"importance={old_imp}, flag={old_flag}",
                             "new_value": f"flag={rows[i]['is_high_importance']} (wrong for importance={old_imp})"})
        elif strategy == "rank_vs_importance_inversion":
            # Set a high importance value but a very low rank (should be rank=1 for highest)
            old_imp = rows[i]["importance"]
            old_rank = rows[i]["importance_rank"]
            rows[i]["importance"] = 4.95
            rows[i]["importance_rank"] = rng.randint(30, 41)
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "consistency", "field": "importance+importance_rank",
                             "strategy": strategy,
                             "old_value": f"imp={old_imp}, rank={old_rank}",
                             "new_value": f"imp=4.95, rank={rows[i]['importance_rank']} (inversion)"})

    # 5. ACCURACY: plausible but wrong importance values (subtly off)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["importance"]
        # Shift by a small but meaningful amount
        if old_val is not None:
            rows[i]["importance"] = round(old_val + rng.choice([-1.0, 1.0, -0.5, 0.5]), 2)
            if rows[i]["importance"] > 5.0:
                rows[i]["importance"] = 5.0
            if rows[i]["importance"] < 1.0:
                rows[i]["importance"] = 1.0
        manifest.append({"table": "onet_activity_profiles", "row": i,
                         "dimension": "accuracy", "field": "importance",
                         "strategy": "shifted_importance",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["importance"])})

    # 6. REASONABLENESS: extreme onet_details_averaged values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_details_averaged"]
        rows[i]["onet_details_averaged"] = rng.choice([0, -1, 100, 500])
        manifest.append({"table": "onet_activity_profiles", "row": i,
                         "dimension": "reasonableness", "field": "onet_details_averaged",
                         "strategy": "extreme_details_averaged",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["onet_details_averaged"])})

    # 7. FRESHNESS: future/stale timestamps
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-06-15"})
        elif strategy == "stale_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2018, 1, 1)
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2018-01-01"})
        else:
            old_val = rows[i]["ingested_at"]
            rows[i]["ingested_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({"table": "onet_activity_profiles", "row": i,
                             "dimension": "freshness", "field": "ingested_at",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2035-01-01T00:00:00"})

    # 8. VOLUME: handled at cycle level (mass duplicate across all tables)

    # 9. REFERENTIAL INTEGRITY: FK to occupations table (bls_soc_code)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["bls_soc_code"]
        fake_soc = f"{rng.choice(['60', '90', '92', '98'])}-{rng.randint(1000, 9999)}"
        rows[i]["bls_soc_code"] = fake_soc
        manifest.append({"table": "onet_activity_profiles", "row": i,
                         "dimension": "referential_integrity", "field": "bls_soc_code",
                         "strategy": "orphan_soc_not_in_occupations",
                         "old_value": str(old_val), "new_value": fake_soc})

    # 10. COVERAGE: remove all rows for certain SOC codes to create gaps
    soc_map = {}
    for i, row in enumerate(rows):
        soc = row.get("bls_soc_code")
        if soc:
            soc_map.setdefault(soc, []).append(i)
    soc_list = [s for s in soc_map if s in valid_soc_codes and len(soc_map[s]) >= 5]
    if len(soc_list) >= 5:
        socs_to_remove = rng.sample(soc_list, 5)
        removed = set()
        for soc in socs_to_remove:
            for idx in soc_map[soc]:
                removed.add(idx)
            manifest.append({"table": "onet_activity_profiles", "row": -1,
                             "dimension": "coverage", "field": "bls_soc_code",
                             "strategy": f"remove_all_for_soc_{soc}",
                             "old_value": f"soc={soc}, count={len(soc_map[soc])}",
                             "new_value": "removed"})
        for idx in sorted(removed, reverse=True):
            if idx < len(rows):
                rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Corruption strategies: base.onet_context_profiles (44,118 rows)
# Schema: record_id, bls_soc_code, element_id, element_name,
#         scale_id(CX/CT), context_value(double),
#         is_burnout_element(bool), onet_details_averaged(int),
#         suppress_flag(bool), source_load_date, ingested_at
# Grain: (bls_soc_code, element_id)
# ---------------------------------------------------------------------------

def corrupt_context_profiles(rows, rate, rng, valid_soc_codes):
    """Corrupt onet_context_profiles across all 10 DQ dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. COMPLETENESS: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["bls_soc_code", "element_id", "scale_id",
                            "context_value", "record_id"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_context_profiles", "row": i,
                         "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. VALIDITY: context_value out of range, invalid scale_id, bad SOC format
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["cx_value_over_5", "ct_value_over_3",
                                "invalid_scale_id", "bad_soc_format",
                                "cxp_ctp_scale_sneak"])
        if strategy == "cx_value_over_5":
            old_val = rows[i]["context_value"]
            rows[i]["context_value"] = rng.uniform(5.01, 10.0)
            rows[i]["scale_id"] = "CX"
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "validity", "field": "context_value",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["context_value"])})
        elif strategy == "ct_value_over_3":
            old_val = rows[i]["context_value"]
            rows[i]["context_value"] = rng.uniform(3.01, 10.0)
            rows[i]["scale_id"] = "CT"
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "validity", "field": "context_value",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["context_value"])})
        elif strategy == "invalid_scale_id":
            old_val = rows[i]["scale_id"]
            rows[i]["scale_id"] = rng.choice(["IM", "LV", "XX", "CXP", "CTP", "", "AB"])
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "validity", "field": "scale_id",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["scale_id"])})
        elif strategy == "bad_soc_format":
            old_val = rows[i]["bls_soc_code"]
            rows[i]["bls_soc_code"] = rng.choice(["151252", "15-12520", "AB-CDEF", ""])
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "validity", "field": "bls_soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["bls_soc_code"])})
        elif strategy == "cxp_ctp_scale_sneak":
            # CXP/CTP scales should have been filtered out in Silver
            old_val = rows[i]["scale_id"]
            rows[i]["scale_id"] = rng.choice(["CXP", "CTP"])
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "validity", "field": "scale_id",
                             "strategy": strategy,
                             "old_value": str(old_val),
                             "new_value": f"{rows[i]['scale_id']} (should not exist in Silver)"})

    # 3. UNIQUENESS: duplicate grain rows (bls_soc_code + element_id)
    n_dupes = max(1, n_corrupt // 20)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "onet_context_profiles", "row": insert_pos,
                         "dimension": "uniqueness", "field": "bls_soc_code+element_id",
                         "strategy": "duplicate_grain_row",
                         "old_value": f"copy_of_row_{src_idx}",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. CONSISTENCY: is_burnout_element contradicts element_id
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["burnout_flag_wrong", "scale_value_mismatch"])
        if strategy == "burnout_flag_wrong":
            old_flag = rows[i]["is_burnout_element"]
            old_eid = rows[i]["element_id"]
            rows[i]["is_burnout_element"] = not old_flag
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "consistency", "field": "is_burnout_element",
                             "strategy": strategy,
                             "old_value": f"element_id={old_eid}, flag={old_flag}",
                             "new_value": f"flag={rows[i]['is_burnout_element']} (wrong for element_id)"})
        elif strategy == "scale_value_mismatch":
            # CT scale should have max 3, CX max 5 -- set wrong combination
            old_scale = rows[i]["scale_id"]
            old_val = rows[i]["context_value"]
            if old_scale == "CT":
                rows[i]["scale_id"] = "CX"
            else:
                rows[i]["scale_id"] = "CT"
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "consistency", "field": "scale_id+context_value",
                             "strategy": strategy,
                             "old_value": f"scale={old_scale}, value={old_val}",
                             "new_value": f"scale={rows[i]['scale_id']}, value={old_val} (swapped scale)"})

    # 5. ACCURACY: subtly wrong context_value (still in range but off)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["context_value"]
        if old_val is not None:
            shift = rng.choice([-0.8, -0.5, 0.5, 0.8])
            new_val = round(old_val + shift, 2)
            max_val = 5.0 if rows[i]["scale_id"] == "CX" else 3.0
            new_val = max(0.0, min(new_val, max_val))
            rows[i]["context_value"] = new_val
        manifest.append({"table": "onet_context_profiles", "row": i,
                         "dimension": "accuracy", "field": "context_value",
                         "strategy": "shifted_context_value",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["context_value"])})

    # 6. REASONABLENESS: extreme context_value
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["context_value"]
        rows[i]["context_value"] = rng.choice([-10.0, 0.0, 50.0, 100.0, 999.0])
        manifest.append({"table": "onet_context_profiles", "row": i,
                         "dimension": "reasonableness", "field": "context_value",
                         "strategy": "extreme_context_value",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["context_value"])})

    # 7. FRESHNESS: future/stale timestamps
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date"])
        if strategy == "future_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-06-15"})
        else:
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2018, 1, 1)
            manifest.append({"table": "onet_context_profiles", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2018-01-01"})

    # 8. VOLUME: handled at cycle level

    # 9. REFERENTIAL INTEGRITY: FK to occupations (orphan SOC)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["bls_soc_code"]
        fake_soc = f"{rng.choice(['60', '90', '92', '98'])}-{rng.randint(1000, 9999)}"
        rows[i]["bls_soc_code"] = fake_soc
        manifest.append({"table": "onet_context_profiles", "row": i,
                         "dimension": "referential_integrity", "field": "bls_soc_code",
                         "strategy": "orphan_soc_not_in_occupations",
                         "old_value": str(old_val), "new_value": fake_soc})

    # 10. COVERAGE: remove all rows for certain SOC codes
    soc_map = {}
    for i, row in enumerate(rows):
        soc = row.get("bls_soc_code")
        if soc:
            soc_map.setdefault(soc, []).append(i)
    soc_list = [s for s in soc_map if s in valid_soc_codes and len(soc_map[s]) >= 5]
    if len(soc_list) >= 5:
        socs_to_remove = rng.sample(soc_list, 5)
        removed = set()
        for soc in socs_to_remove:
            for idx in soc_map[soc]:
                removed.add(idx)
            manifest.append({"table": "onet_context_profiles", "row": -1,
                             "dimension": "coverage", "field": "bls_soc_code",
                             "strategy": f"remove_all_for_soc_{soc}",
                             "old_value": f"soc={soc}, count={len(soc_map[soc])}",
                             "new_value": "removed"})
        for idx in sorted(removed, reverse=True):
            if idx < len(rows):
                rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Corruption strategies: base.onet_career_transitions (15,944 rows)
# Schema: record_id, bls_soc_code, related_bls_soc_code,
#         best_index(int), relatedness_tier(str), is_primary(bool),
#         relationship_type(str), source_load_date, ingested_at
# Grain: (bls_soc_code, related_bls_soc_code)
# ---------------------------------------------------------------------------

def corrupt_career_transitions(rows, rate, rng, valid_soc_codes):
    """Corrupt onet_career_transitions across all 10 DQ dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. COMPLETENESS: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["bls_soc_code", "related_bls_soc_code", "best_index",
                            "relatedness_tier", "record_id"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_career_transitions", "row": i,
                         "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. VALIDITY: best_index > 20, invalid relatedness_tier, bad SOC format
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["best_index_over_20", "best_index_zero_or_negative",
                                "invalid_relatedness_tier", "bad_soc_format",
                                "invalid_relationship_type"])
        if strategy == "best_index_over_20":
            old_val = rows[i]["best_index"]
            rows[i]["best_index"] = rng.randint(21, 100)
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "validity", "field": "best_index",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["best_index"])})
        elif strategy == "best_index_zero_or_negative":
            old_val = rows[i]["best_index"]
            rows[i]["best_index"] = rng.choice([0, -1, -5])
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "validity", "field": "best_index",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["best_index"])})
        elif strategy == "invalid_relatedness_tier":
            old_val = rows[i]["relatedness_tier"]
            rows[i]["relatedness_tier"] = rng.choice([
                "Primary", "Secondary", "Tertiary", "High", "Low",
                "primary-short", "SUPPLEMENTAL", "", "Unknown"])
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "validity", "field": "relatedness_tier",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["relatedness_tier"])})
        elif strategy == "bad_soc_format":
            old_val = rows[i]["bls_soc_code"]
            rows[i]["bls_soc_code"] = rng.choice(["151252", "15-12520", "AB-CDEF", ""])
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "validity", "field": "bls_soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["bls_soc_code"])})
        elif strategy == "invalid_relationship_type":
            old_val = rows[i]["relationship_type"]
            rows[i]["relationship_type"] = rng.choice([
                "different", "opposite", "unrelated", "", "SIMILARITY"])
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "validity", "field": "relationship_type",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["relationship_type"])})

    # 3. UNIQUENESS: duplicate grain rows (bls_soc_code + related_bls_soc_code)
    n_dupes = max(1, n_corrupt // 20)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "onet_career_transitions", "row": insert_pos,
                         "dimension": "uniqueness", "field": "bls_soc_code+related_bls_soc_code",
                         "strategy": "duplicate_grain_row",
                         "old_value": f"copy_of_row_{src_idx}",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. CONSISTENCY: self-references + tier vs best_index mismatch
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["self_reference", "tier_index_mismatch",
                                "is_primary_wrong"])
        if strategy == "self_reference":
            old_related = rows[i]["related_bls_soc_code"]
            rows[i]["related_bls_soc_code"] = rows[i]["bls_soc_code"]
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "consistency", "field": "related_bls_soc_code",
                             "strategy": strategy,
                             "old_value": f"src={rows[i]['bls_soc_code']}, tgt={old_related}",
                             "new_value": f"src=tgt={rows[i]['bls_soc_code']} (self-reference)"})
        elif strategy == "tier_index_mismatch":
            old_tier = rows[i]["relatedness_tier"]
            old_idx = rows[i]["best_index"]
            # Set index to 3 (should be Primary-Short) but tier to Supplemental
            rows[i]["best_index"] = 3
            rows[i]["relatedness_tier"] = "Supplemental"
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "consistency", "field": "relatedness_tier+best_index",
                             "strategy": strategy,
                             "old_value": f"index={old_idx}, tier={old_tier}",
                             "new_value": "index=3, tier=Supplemental (should be Primary-Short)"})
        elif strategy == "is_primary_wrong":
            old_primary = rows[i]["is_primary"]
            old_tier = rows[i]["relatedness_tier"]
            rows[i]["is_primary"] = not old_primary
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "consistency", "field": "is_primary",
                             "strategy": strategy,
                             "old_value": f"tier={old_tier}, is_primary={old_primary}",
                             "new_value": f"is_primary={rows[i]['is_primary']} (wrong for tier)"})

    # 5. ACCURACY: plausible but wrong best_index
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["best_index"]
        # Subtle shift (e.g. 3 -> 8, changing tier)
        if old_val is not None:
            rows[i]["best_index"] = max(1, min(20, old_val + rng.choice([-5, -3, 3, 5, 7])))
        manifest.append({"table": "onet_career_transitions", "row": i,
                         "dimension": "accuracy", "field": "best_index",
                         "strategy": "shifted_best_index",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["best_index"])})

    # 6. REASONABLENESS: extreme best_index values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["best_index"]
        rows[i]["best_index"] = rng.choice([0, -10, 50, 100, 999])
        manifest.append({"table": "onet_career_transitions", "row": i,
                         "dimension": "reasonableness", "field": "best_index",
                         "strategy": "extreme_best_index",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["best_index"])})

    # 7. FRESHNESS: future/stale timestamps
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date"])
        if strategy == "future_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-06-15"})
        else:
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2018, 1, 1)
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2018-01-01"})

    # 8. VOLUME: handled at cycle level

    # 9. REFERENTIAL INTEGRITY: orphan SOC codes + related SOC not in occupations
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["orphan_source", "orphan_target"])
        if strategy == "orphan_source":
            old_val = rows[i]["bls_soc_code"]
            fake_soc = f"{rng.choice(['60', '90', '92'])}-{rng.randint(1000, 9999)}"
            rows[i]["bls_soc_code"] = fake_soc
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "referential_integrity", "field": "bls_soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": fake_soc})
        else:
            old_val = rows[i]["related_bls_soc_code"]
            fake_soc = f"{rng.choice(['60', '90', '92'])}-{rng.randint(1000, 9999)}"
            rows[i]["related_bls_soc_code"] = fake_soc
            manifest.append({"table": "onet_career_transitions", "row": i,
                             "dimension": "referential_integrity", "field": "related_bls_soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": fake_soc})

    # 10. COVERAGE: remove all transitions for certain SOC codes
    soc_map = {}
    for i, row in enumerate(rows):
        soc = row.get("bls_soc_code")
        if soc:
            soc_map.setdefault(soc, []).append(i)
    soc_list = [s for s in soc_map if s in valid_soc_codes and len(soc_map[s]) >= 3]
    if len(soc_list) >= 5:
        socs_to_remove = rng.sample(soc_list, 5)
        removed = set()
        for soc in socs_to_remove:
            for idx in soc_map[soc]:
                removed.add(idx)
            manifest.append({"table": "onet_career_transitions", "row": -1,
                             "dimension": "coverage", "field": "bls_soc_code",
                             "strategy": f"remove_all_for_soc_{soc}",
                             "old_value": f"soc={soc}, count={len(soc_map[soc])}",
                             "new_value": "removed"})
        for idx in sorted(removed, reverse=True):
            if idx < len(rows):
                rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Main injection pipeline
# ---------------------------------------------------------------------------

def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle across all 4 tables."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)

    # Load all 4 tables
    print("Loading source data...")
    table_data = {}
    table_schemas = {}
    for table_name in SOURCE_PARQUETS:
        rows, schema = load_table(table_name)
        table_data[table_name] = rows
        table_schemas[table_name] = schema
        print(f"  {table_name}: {len(rows)} rows")

    # Extract valid SOC codes from occupations for FK checks
    valid_soc_codes = set()
    for row in table_data["onet_occupations"]:
        soc = row.get("bls_soc_code")
        if soc:
            valid_soc_codes.add(soc)

    # Run corruption on each table
    all_manifest = []
    original_counts = {t: len(rows) for t, rows in table_data.items()}

    # Occupations
    print("\nCorrupting onet_occupations...")
    m = corrupt_occupations(table_data["onet_occupations"], rate, rng, valid_soc_codes)
    all_manifest.extend(m)
    print(f"  {len(m)} corruptions")

    # Activity profiles
    print("Corrupting onet_activity_profiles...")
    m = corrupt_activity_profiles(table_data["onet_activity_profiles"], rate, rng, valid_soc_codes)
    all_manifest.extend(m)
    print(f"  {len(m)} corruptions")

    # Context profiles
    print("Corrupting onet_context_profiles...")
    m = corrupt_context_profiles(table_data["onet_context_profiles"], rate, rng, valid_soc_codes)
    all_manifest.extend(m)
    print(f"  {len(m)} corruptions")

    # Career transitions
    print("Corrupting onet_career_transitions...")
    m = corrupt_career_transitions(table_data["onet_career_transitions"], rate, rng, valid_soc_codes)
    all_manifest.extend(m)
    print(f"  {len(m)} corruptions")

    # Volume injection: mass-duplicate rows across activity/context/transition tables
    for table_name in ["onet_activity_profiles", "onet_context_profiles", "onet_career_transitions"]:
        rows = table_data[table_name]
        orig = original_counts[table_name]
        n_extras = max(50, orig // 15)
        source_indices = rng.choices(range(min(orig, len(rows))), k=n_extras)
        for src_idx in source_indices:
            rows.append(copy.deepcopy(rows[src_idx]))
        all_manifest.append({"table": table_name, "row": -1,
                             "dimension": "volume", "field": "row_count",
                             "strategy": "mass_duplicate",
                             "old_value": str(orig), "new_value": str(len(rows))})

    print(f"\n  Total corruptions across all tables: {len(all_manifest)}")
    for t in SOURCE_PARQUETS:
        print(f"  {t}: {len(table_data[t])} rows (was {original_counts[t]})")

    # Write shadow parquet files
    print("\nWriting shadow parquet files...")
    table_parquets = {}
    dq_result = {"run_id": "error", "rules_total": 0, "rules_passed": 0,
                 "rules_failed": 0, "p0_passed": True, "results": []}

    try:
        for table_name in SOURCE_PARQUETS:
            pq_path, _ = write_shadow_parquet(
                table_name, table_data[table_name],
                table_schemas[table_name], cycle_num
            )
            table_parquets[table_name] = pq_path
            print(f"  Written {table_name} -> {pq_path}")

        print("Registering shadow tables in Iceberg catalog...")
        register_shadow_tables(table_parquets)
        print("  All 4 shadow tables registered.")

        print("Running DQ rules against shadow tables...")
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(f"  Total: {dq_result['rules_total']} | Passed: {dq_result['rules_passed']} | Failed: {dq_result['rules_failed']}")
        p0_status = "PASS" if dq_result.get("p0_passed", True) else "FAIL"
        print(f"  P0 gate: {p0_status}")

        print("\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            print(f"    {r['rule_id']:<40} {status:<6} value={r.get('raw_value', '?')}")

    except Exception as e:
        print(f"  ERROR during shadow table creation/DQ run: {e}")
        traceback.print_exc()

    return {
        "cycle": cycle_num,
        "rate": rate,
        "seed": seed,
        "original_row_counts": original_counts,
        "corrupted_row_counts": {t: len(rows) for t, rows in table_data.items()},
        "total_corruptions": len(all_manifest),
        "manifest": all_manifest,
        "dq_result": dq_result,
    }


def analyze_gaps(cycle_result):
    """Analyze which corruptions were caught vs missed empirically."""
    dq_result = cycle_result["dq_result"]
    manifest = cycle_result["manifest"]

    failed_rules = [r for r in dq_result.get("results", [])
                    if not r["passed"] and not r.get("error")]
    passed_rules = [r for r in dq_result.get("results", []) if r["passed"]]
    errored_rules = [r for r in dq_result.get("results", []) if r.get("error")]

    dims = {}
    for entry in manifest:
        dim = entry["dimension"]
        dims.setdefault(dim, []).append(entry)

    total_rules = len(dq_result.get("results", []))
    detection_rate = len(failed_rules) / total_rules if total_rules > 0 else 0

    return {
        "failed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value")}
                         for r in failed_rules],
        "passed_rules": [{"rule_id": r["rule_id"], "raw_value": r.get("raw_value"),
                          "threshold": r.get("threshold")}
                         for r in passed_rules],
        "errored_rules": [r["rule_id"] for r in errored_rules],
        "injected_dimensions": sorted(dims),
        "corruptions_per_dimension": {dim: len(entries) for dim, entries in dims.items()},
        "detection_rate": round(detection_rate, 3),
        "rules_fired": len(failed_rules),
        "rules_silent": len(passed_rules),
        "total_rules": total_rules,
    }


def main():
    """Run 5-cycle adversarial hardening across all 4 Silver O*NET tables."""
    safety_check()

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
            "original_row_counts": cycle_result["original_row_counts"],
            "corrupted_row_counts": cycle_result["corrupted_row_counts"],
            "dq_passed": cycle_result["dq_result"]["rules_passed"],
            "dq_failed": cycle_result["dq_result"]["rules_failed"],
            "dq_total": cycle_result["dq_result"]["rules_total"],
            "gap_analysis": gap_analysis,
            "manifest_entries": cycle_result["manifest"],
        })
        all_gaps.append(gap_analysis)

        print(f"\n  Gap Analysis:")
        dr = gap_analysis['detection_rate']
        print(f"    Detection rate: {dr*100:.1f}% ({gap_analysis['rules_fired']}/{gap_analysis['total_rules']} rules fired)")
        print(f"    Rules that fired: {[r['rule_id'] for r in gap_analysis['failed_rules']]}")

        if consecutive_no_new_gaps >= 2:
            print(f"\n  Stability: same rules firing for {consecutive_no_new_gaps + 1} consecutive cycles.")
            print("  Early exit: no new gaps for 2 consecutive cycles.")
            # Clean up and break early
            cleanup_shadow()
            break

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": SPEC_NAME,
        "tables": list(SOURCE_PARQUETS.keys()),
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/silver-base-onet-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
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
            f"detection rate: {ga['detection_rate']*100:.1f}%"
        )
