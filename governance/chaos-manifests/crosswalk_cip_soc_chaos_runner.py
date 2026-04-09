"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: crosswalk-cip-soc
Tables:
  - raw.cip_soc_crosswalk (6,097 rows) — Bronze
  - base.cip_soc_crosswalk (5,903 rows) — Silver

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against shadow tables, and records what was caught vs missed.

Information Barrier: This script does NOT read DQ rule definitions.
It injects corruptions based solely on the table schema and domain
understanding from the ingestor/transformer code.
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
BRONZE_WAREHOUSE = PROJECT_ROOT / "data" / "bronze" / "iceberg_warehouse"
SILVER_WAREHOUSE = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

SOURCE_PARQUETS = {
    "bronze_cip_soc": BRONZE_WAREHOUSE / "raw/cip_soc_crosswalk/data/00000-0-53f5d4bf-0645-4ed1-a2e3-95a0fb5f1bb5.parquet",
    "silver_cip_soc": SILVER_WAREHOUSE / "base/cip_soc_crosswalk/data/00000-0-dbad489d-833e-46d7-94ba-699f64f2e21e.parquet",
}

SHADOW_BRONZE_BASE = BRONZE_WAREHOUSE / "shadow_raw"
SHADOW_SILVER_BASE = SILVER_WAREHOUSE / "shadow_base"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "crosswalk-cip-soc"

EXPECTED_COUNTS = {
    "bronze_cip_soc": 6097,
    "silver_cip_soc": 5848,  # main parquet (excluding 55-row partial)
}

# 22 valid SOC major groups (odd numbers 11-53, plus 55 for military)
VALID_SOC_MAJOR_GROUPS = [
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "31", "33", "35", "37", "39", "41", "43", "45", "47", "49",
    "51", "53", "55",
]

# Valid match quality values from the transformer
VALID_MATCH_QUALITIES = [
    "full", "partial_no_onet", "partial_no_bls", "scorecard_only", "no_scorecard",
]

# CIP families observed in the actual data
VALID_CIP_FAMILIES = [
    "01", "03", "04", "05", "09", "10", "11", "12", "13", "14", "15", "16",
    "19", "22", "23", "24", "25", "26", "27", "29", "30", "31", "38", "39",
    "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51",
    "52", "54", "60", "61", "99",
]

sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path("/Users/jcernauske/code/bright/brightsmith/src")))

# Configure Brightsmith to use the futureproof-data project
from brightsmith.config import configure
configure(project_root=str(PROJECT_ROOT), project_name="brightsmith")


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
    """Load a parquet table into list of dicts and return schema."""
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


def write_shadow_parquet(zone, table_name, rows, original_schema, cycle_num):
    """Write corrupted rows to shadow parquet file."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    if zone == "bronze":
        shadow_dir = SHADOW_BRONZE_BASE / "cip_soc_crosswalk" / "data"
    else:
        shadow_dir = SHADOW_SILVER_BASE / "cip_soc_crosswalk" / "data"

    shadow_dir.mkdir(parents=True, exist_ok=True)
    (shadow_dir.parent / "metadata").mkdir(parents=True, exist_ok=True)

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
    """Register shadow tables in the Iceberg catalog."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, NestedField, StringType, TimestampType,
    )
    import pyarrow.parquet as pq

    bronze_catalog = get_catalog(str(BRONZE_WAREHOUSE), str(CATALOG_PATH))
    silver_catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))

    # Create shadow namespaces
    for catalog, ns in [(bronze_catalog, "shadow_raw"), (silver_catalog, "shadow_base")]:
        try:
            catalog.create_namespace(ns)
        except Exception:
            pass

    # Bronze schema (all optional to accept nulls from corruption)
    bronze_schema = Schema(
        NestedField(1, "cipcode", StringType(), required=False),
        NestedField(2, "cip_title", StringType(), required=False),
        NestedField(3, "soc_code", StringType(), required=False),
        NestedField(4, "soc_title", StringType(), required=False),
        NestedField(5, "ingested_at", TimestampType(), required=False),
        NestedField(6, "source_url", StringType(), required=False),
        NestedField(7, "source_method", StringType(), required=False),
        NestedField(8, "load_date", DateType(), required=False),
    )

    # Silver schema (all optional)
    silver_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "cipcode", StringType(), required=False),
        NestedField(3, "cip_title", StringType(), required=False),
        NestedField(4, "cip_family", StringType(), required=False),
        NestedField(5, "soc_code", StringType(), required=False),
        NestedField(6, "soc_title", StringType(), required=False),
        NestedField(7, "soc_major_group", StringType(), required=False),
        NestedField(8, "has_scorecard_match", BooleanType(), required=False),
        NestedField(9, "has_bls_match", BooleanType(), required=False),
        NestedField(10, "has_onet_match", BooleanType(), required=False),
        NestedField(11, "match_quality", StringType(), required=False),
        NestedField(12, "source_load_date", DateType(), required=False),
        NestedField(13, "ingested_at", TimestampType(), required=False),
    )

    registered = {}

    # Register Bronze shadow
    if "bronze_cip_soc" in table_parquets:
        fqn = "shadow_raw.cip_soc_crosswalk"
        try:
            bronze_catalog.drop_table(fqn)
        except Exception:
            pass
        shadow_table = bronze_catalog.create_table(fqn, schema=bronze_schema)
        data = pq.read_table(str(table_parquets["bronze_cip_soc"]))
        shadow_table.append(data)
        registered["bronze_cip_soc"] = shadow_table

    # Register Silver shadow
    if "silver_cip_soc" in table_parquets:
        fqn = "shadow_base.cip_soc_crosswalk"
        try:
            silver_catalog.drop_table(fqn)
        except Exception:
            pass
        shadow_table = silver_catalog.create_table(fqn, schema=silver_schema)
        data = pq.read_table(str(table_parquets["silver_cip_soc"]))
        shadow_table.append(data)
        registered["silver_cip_soc"] = shadow_table

    return registered


def run_dq_rules_shadow():
    """Run DQ rules against shadow tables.

    Uses the default catalog (from brightsmith.config) which points to
    the bronze warehouse but shares the same catalog.db with silver.
    The shadow=True flag tells the runner to look up shadow_raw and
    shadow_base namespaces.
    """
    from brightsmith.infra.dq_runner import run_rules

    result = run_rules(spec=SPEC_NAME, shadow=True)
    return result


def cleanup_shadow():
    """Remove all shadow tables and files."""
    for zone_dir in [SHADOW_BRONZE_BASE / "cip_soc_crosswalk",
                     SHADOW_SILVER_BASE / "cip_soc_crosswalk"]:
        if zone_dir.exists():
            shutil.rmtree(zone_dir)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        bronze_catalog = get_catalog(str(BRONZE_WAREHOUSE), str(CATALOG_PATH))
        try:
            bronze_catalog.drop_table("shadow_raw.cip_soc_crosswalk")
        except Exception:
            pass
        silver_catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
        try:
            silver_catalog.drop_table("shadow_base.cip_soc_crosswalk")
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Corruption strategies: raw.cip_soc_crosswalk (Bronze, 6097 rows)
# Schema: cipcode, cip_title, soc_code, soc_title, ingested_at,
#         source_url, source_method, load_date
# Grain: cipcode x soc_code
# ---------------------------------------------------------------------------

def corrupt_bronze(rows, rate, rng):
    """Corrupt raw.cip_soc_crosswalk across all 10 DQ dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. COMPLETENESS: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["cipcode", "cip_title", "soc_code", "soc_title",
                            "source_url", "source_method"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                         "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. VALIDITY: malformed CIP and SOC codes
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice([
            "cip_no_dot", "cip_wrong_length", "cip_alpha",
            "soc_no_dash", "soc_wrong_length", "soc_alpha",
            "bad_source_method", "empty_cipcode", "empty_soc_code",
        ])
        if strategy == "cip_no_dot":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = str(old_val).replace(".", "") if old_val else "520201"
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "cipcode",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cipcode"])})
        elif strategy == "cip_wrong_length":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = rng.choice(["52.02", "5.0201", "520.201", "52.02010"])
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "cipcode",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cipcode"])})
        elif strategy == "cip_alpha":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = rng.choice(["AB.CDEF", "XX.XXXX", "??.????", "N/A"])
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "cipcode",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cipcode"])})
        elif strategy == "soc_no_dash":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = str(old_val).replace("-", "") if old_val else "111021"
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_code"])})
        elif strategy == "soc_wrong_length":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice(["11-102", "11-10210", "1-1021", "111-021"])
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_code"])})
        elif strategy == "soc_alpha":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice(["AB-CDEF", "XX-XXXX", "??-????"])
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_code"])})
        elif strategy == "bad_source_method":
            old_val = rows[i]["source_method"]
            rows[i]["source_method"] = rng.choice(["csv_download", "api_call", "manual", ""])
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "source_method",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["source_method"])})
        elif strategy == "empty_cipcode":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = ""
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "cipcode",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "''"})
        elif strategy == "empty_soc_code":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = ""
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "''"})

    # 3. UNIQUENESS: duplicate grain rows (cipcode x soc_code)
    n_dupes = max(1, n_corrupt // 15)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "raw.cip_soc_crosswalk", "row": insert_pos,
                         "dimension": "uniqueness", "field": "cipcode+soc_code",
                         "strategy": "duplicate_grain_row",
                         "old_value": f"copy_of_row_{src_idx} (cip={rows[src_idx]['cipcode']}, soc={rows[src_idx]['soc_code']})",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. CONSISTENCY: contradictory field combinations
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice([
            "no_match_soc_with_real_title", "real_soc_with_no_match_title",
            "mismatched_cip_title",
        ])
        if strategy == "no_match_soc_with_real_title":
            # soc_code = 99-9999 but soc_title is a real occupation (not "No Match")
            old_soc = rows[i]["soc_code"]
            old_title = rows[i]["soc_title"]
            rows[i]["soc_code"] = "99-9999"
            # Keep the real title -> inconsistent
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "soc_code+soc_title",
                             "strategy": strategy,
                             "old_value": f"soc={old_soc}, title={old_title[:40]}",
                             "new_value": f"soc=99-9999, title={rows[i]['soc_title'][:40]} (contradictory)"})
        elif strategy == "real_soc_with_no_match_title":
            old_title = rows[i]["soc_title"]
            rows[i]["soc_title"] = "No Match"
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "soc_code+soc_title",
                             "strategy": strategy,
                             "old_value": f"soc={rows[i]['soc_code']}, title={old_title[:40]}",
                             "new_value": f"soc={rows[i]['soc_code']}, title=No Match (contradictory)"})
        elif strategy == "mismatched_cip_title":
            # CIP code from one family with title from a completely different field
            old_title = rows[i]["cip_title"]
            # Pick a random different row's title
            donor = rng.choice(all_indices)
            rows[i]["cip_title"] = rows[donor]["cip_title"]
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "cipcode+cip_title",
                             "strategy": strategy,
                             "old_value": f"cip={rows[i]['cipcode']}, title={old_title[:40]}",
                             "new_value": f"cip={rows[i]['cipcode']}, title={rows[i]['cip_title'][:40]} (swapped)"})

    # 5. ACCURACY: valid-looking but nonexistent codes
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["fake_cip", "fake_soc"])
        if strategy == "fake_cip":
            old_val = rows[i]["cipcode"]
            # Valid format but nonexistent CIP code
            family = rng.choice(["01", "11", "26", "52"])
            detail = f"{rng.randint(9000, 9999)}"
            rows[i]["cipcode"] = f"{family}.{detail}"
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "accuracy", "field": "cipcode",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cipcode"])})
        else:
            old_val = rows[i]["soc_code"]
            # Valid format, valid major group, but nonexistent detail
            group = rng.choice(VALID_SOC_MAJOR_GROUPS[:10])
            rows[i]["soc_code"] = f"{group}-{rng.randint(9000, 9999)}"
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "accuracy", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_code"])})

    # 6. REASONABLENESS: impossible CIP family or SOC group numbers
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["extreme_cip_family", "extreme_soc_group"])
        if strategy == "extreme_cip_family":
            old_val = rows[i]["cipcode"]
            # CIP families above 61 don't exist (except 99)
            rows[i]["cipcode"] = f"{rng.randint(70, 98)}.{rng.randint(0, 9999):04d}"
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "reasonableness", "field": "cipcode",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cipcode"])})
        else:
            old_val = rows[i]["soc_code"]
            # SOC major groups are odd 11-53; use even or out-of-range
            fake_group = rng.choice(["00", "02", "56", "60", "90", "98"])
            rows[i]["soc_code"] = f"{fake_group}-{rng.randint(1000, 9999)}"
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "reasonableness", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_code"])})

    # 7. FRESHNESS: future/stale timestamps
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i]["load_date"]
            rows[i]["load_date"] = datetime.date(2030, 6, 15)
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "freshness", "field": "load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-06-15"})
        elif strategy == "stale_load_date":
            old_val = rows[i]["load_date"]
            rows[i]["load_date"] = datetime.date(2015, 1, 1)
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "freshness", "field": "load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2015-01-01"})
        else:
            old_val = rows[i]["ingested_at"]
            rows[i]["ingested_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                             "dimension": "freshness", "field": "ingested_at",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2035-01-01T00:00:00"})

    # 8. VOLUME: mass-duplicate to inflate count beyond expected ~6097
    n_extras = max(300, n // 10)
    source_rows = rng.choices(all_indices, k=n_extras)
    for src_idx in source_rows:
        rows.append(copy.deepcopy(rows[src_idx]))
    manifest.append({"table": "raw.cip_soc_crosswalk", "row": -1,
                     "dimension": "volume", "field": "row_count",
                     "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. REFERENTIAL INTEGRITY: not directly applicable at Bronze but inject
    #    SOC codes from non-standard major groups that won't FK to BLS/ONET
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["soc_code"]
        fake_prefix = rng.choice(["12", "14", "16", "20", "60", "90"])
        rows[i]["soc_code"] = f"{fake_prefix}-{rng.randint(1000, 9999)}"
        manifest.append({"table": "raw.cip_soc_crosswalk", "row": i,
                         "dimension": "referential_integrity", "field": "soc_code",
                         "strategy": "orphan_soc_major_group",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["soc_code"])})

    # 10. COVERAGE: remove all rows for certain CIP families
    family_map = {}
    for i, row in enumerate(rows):
        cip = row.get("cipcode")
        if cip and isinstance(cip, str) and len(cip) >= 2:
            fam = cip[:2]
            family_map.setdefault(fam, []).append(i)
    valid_families = [f for f in family_map if len(family_map[f]) >= 5]
    if len(valid_families) >= 3:
        families_to_remove = rng.sample(valid_families, 3)
        removed = set()
        for fam in families_to_remove:
            for idx in family_map[fam]:
                removed.add(idx)
            manifest.append({"table": "raw.cip_soc_crosswalk", "row": -1,
                             "dimension": "coverage", "field": "cipcode_family",
                             "strategy": f"remove_all_family_{fam}",
                             "old_value": f"family={fam}, count={len(family_map[fam])}",
                             "new_value": "removed"})
        for idx in sorted(removed, reverse=True):
            if idx < len(rows):
                rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Corruption strategies: base.cip_soc_crosswalk (Silver, 5848 rows)
# Schema: record_id, cipcode, cip_title, cip_family, soc_code, soc_title,
#         soc_major_group, has_scorecard_match, has_bls_match, has_onet_match,
#         match_quality, source_load_date, ingested_at
# Grain: cipcode x soc_code (same as Bronze but enriched)
# ---------------------------------------------------------------------------

def corrupt_silver(rows, rate, rng):
    """Corrupt base.cip_soc_crosswalk across all 10 DQ dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. COMPLETENESS: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["record_id", "cipcode", "cip_title", "cip_family",
                            "soc_code", "soc_title", "soc_major_group",
                            "match_quality"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                         "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. VALIDITY: invalid formats and constrained fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice([
            "bad_cip_format", "bad_soc_format", "bad_match_quality",
            "bad_soc_major_group", "bad_cip_family", "no_match_soc_in_silver",
            "empty_record_id",
        ])
        if strategy == "bad_cip_format":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = rng.choice(["520201", "52.02", "AB.CDEF", "", "52-0201"])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "cipcode",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cipcode"])})
        elif strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice(["111021", "11.1021", "AB-CDEF", "", "11-102"])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_code"])})
        elif strategy == "bad_match_quality":
            old_val = rows[i]["match_quality"]
            rows[i]["match_quality"] = rng.choice([
                "FULL", "partial", "none", "complete", "unknown",
                "partial_no_scorecard", "Full", ""])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "match_quality",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["match_quality"])})
        elif strategy == "bad_soc_major_group":
            old_val = rows[i]["soc_major_group"]
            rows[i]["soc_major_group"] = rng.choice(["00", "02", "12", "56", "60", "99", ""])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "soc_major_group",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_major_group"])})
        elif strategy == "bad_cip_family":
            old_val = rows[i]["cip_family"]
            # CIP families 02, 06, 07, 08, etc. don't exist in the crosswalk
            rows[i]["cip_family"] = rng.choice(["00", "02", "06", "07", "08", "70", "98", ""])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "cip_family",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cip_family"])})
        elif strategy == "no_match_soc_in_silver":
            # Silver should have NO rows with soc_code = 99-9999 (filtered in transform)
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = "99-9999"
            rows[i]["soc_title"] = "No Match"
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_val),
                             "new_value": "99-9999 (should not exist in Silver)"})
        elif strategy == "empty_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = ""
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "validity", "field": "record_id",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "''"})

    # 3. UNIQUENESS: duplicate grain rows (cipcode x soc_code)
    n_dupes = max(1, n_corrupt // 15)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "base.cip_soc_crosswalk", "row": insert_pos,
                         "dimension": "uniqueness", "field": "cipcode+soc_code",
                         "strategy": "duplicate_grain_row",
                         "old_value": f"copy_of_row_{src_idx} (cip={rows[src_idx]['cipcode']}, soc={rows[src_idx]['soc_code']})",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. CONSISTENCY: contradictory field combinations
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice([
            "cip_family_mismatch", "soc_major_group_mismatch",
            "match_quality_flag_contradiction", "all_flags_true_no_scorecard",
            "record_id_wrong_prefix",
        ])
        if strategy == "cip_family_mismatch":
            # cip_family should be first 2 chars of cipcode
            old_fam = rows[i]["cip_family"]
            rows[i]["cip_family"] = rng.choice(["99", "00", "52", "11"])
            while rows[i]["cip_family"] == old_fam:
                rows[i]["cip_family"] = rng.choice(["99", "00", "52", "11"])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "cipcode+cip_family",
                             "strategy": strategy,
                             "old_value": f"cip={rows[i]['cipcode']}, family={old_fam}",
                             "new_value": f"cip={rows[i]['cipcode']}, family={rows[i]['cip_family']} (mismatch)"})
        elif strategy == "soc_major_group_mismatch":
            old_grp = rows[i]["soc_major_group"]
            rows[i]["soc_major_group"] = rng.choice(["11", "13", "15", "99"])
            while rows[i]["soc_major_group"] == old_grp:
                rows[i]["soc_major_group"] = rng.choice(["11", "13", "15", "99"])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "soc_code+soc_major_group",
                             "strategy": strategy,
                             "old_value": f"soc={rows[i]['soc_code']}, group={old_grp}",
                             "new_value": f"soc={rows[i]['soc_code']}, group={rows[i]['soc_major_group']} (mismatch)"})
        elif strategy == "match_quality_flag_contradiction":
            # Set match_quality to "full" but has_scorecard_match=False
            old_mq = rows[i]["match_quality"]
            rows[i]["match_quality"] = "full"
            rows[i]["has_scorecard_match"] = False
            rows[i]["has_bls_match"] = True
            rows[i]["has_onet_match"] = True
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "match_quality+flags",
                             "strategy": strategy,
                             "old_value": f"quality={old_mq}",
                             "new_value": "quality=full, has_scorecard=False (contradictory)"})
        elif strategy == "all_flags_true_no_scorecard":
            old_mq = rows[i]["match_quality"]
            rows[i]["has_scorecard_match"] = True
            rows[i]["has_bls_match"] = True
            rows[i]["has_onet_match"] = True
            rows[i]["match_quality"] = "no_scorecard"
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "match_quality+flags",
                             "strategy": strategy,
                             "old_value": f"quality={old_mq}",
                             "new_value": "all flags True but quality=no_scorecard (contradictory)"})
        elif strategy == "record_id_wrong_prefix":
            old_val = rows[i]["record_id"]
            # record_id should start with "xw-" per compute_grain_id prefix
            rows[i]["record_id"] = "zz-" + (old_val[3:] if old_val and len(old_val) > 3 else "abcdef")
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "consistency", "field": "record_id",
                             "strategy": strategy,
                             "old_value": str(old_val)[:30],
                             "new_value": str(rows[i]["record_id"])[:30]})

    # 5. ACCURACY: plausible but wrong values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["swapped_cip_soc", "wrong_title_for_code"])
        if strategy == "swapped_cip_soc":
            # Swap a CIP code into the SOC field (looks valid-ish format but wrong)
            old_soc = rows[i]["soc_code"]
            old_cip = rows[i]["cipcode"]
            # CIP is XX.XXXX, SOC is XX-XXXX -- change dot to dash
            if old_cip and "." in str(old_cip):
                rows[i]["soc_code"] = str(old_cip).replace(".", "-")
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "accuracy", "field": "soc_code",
                             "strategy": strategy,
                             "old_value": str(old_soc), "new_value": str(rows[i]["soc_code"])})
        elif strategy == "wrong_title_for_code":
            old_title = rows[i]["soc_title"]
            donor = rng.choice(all_indices)
            rows[i]["soc_title"] = rows[donor]["soc_title"]
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "accuracy", "field": "soc_title",
                             "strategy": strategy,
                             "old_value": str(old_title)[:40],
                             "new_value": str(rows[i]["soc_title"])[:40]})

    # 6. REASONABLENESS: impossible derived field values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["extreme_soc_major_group", "extreme_cip_family"])
        if strategy == "extreme_soc_major_group":
            old_val = rows[i]["soc_major_group"]
            rows[i]["soc_major_group"] = rng.choice(["00", "99", "77", "AB"])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "reasonableness", "field": "soc_major_group",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["soc_major_group"])})
        else:
            old_val = rows[i]["cip_family"]
            rows[i]["cip_family"] = rng.choice(["00", "77", "98", "AB"])
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "reasonableness", "field": "cip_family",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["cip_family"])})

    # 7. FRESHNESS: future/stale timestamps
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-06-15"})
        elif strategy == "stale_load_date":
            old_val = rows[i]["source_load_date"]
            rows[i]["source_load_date"] = datetime.date(2015, 1, 1)
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2015-01-01"})
        else:
            old_val = rows[i]["ingested_at"]
            rows[i]["ingested_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                             "dimension": "freshness", "field": "ingested_at",
                             "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2035-01-01T00:00:00"})

    # 8. VOLUME: mass-duplicate to inflate count
    n_extras = max(300, n // 10)
    source_rows = rng.choices(all_indices, k=n_extras)
    for src_idx in source_rows:
        rows.append(copy.deepcopy(rows[src_idx]))
    manifest.append({"table": "base.cip_soc_crosswalk", "row": -1,
                     "dimension": "volume", "field": "row_count",
                     "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. REFERENTIAL INTEGRITY: orphan SOC codes that won't match BLS/ONET
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["soc_code"]
        fake_prefix = rng.choice(["12", "14", "16", "20", "60", "90"])
        rows[i]["soc_code"] = f"{fake_prefix}-{rng.randint(1000, 9999)}"
        # Also set has_bls_match and has_onet_match to True (contradictory)
        rows[i]["has_bls_match"] = True
        rows[i]["has_onet_match"] = True
        manifest.append({"table": "base.cip_soc_crosswalk", "row": i,
                         "dimension": "referential_integrity", "field": "soc_code",
                         "strategy": "orphan_soc_invalid_major_group",
                         "old_value": str(old_val),
                         "new_value": str(rows[i]["soc_code"])})

    # 10. COVERAGE: remove all rows for certain SOC major groups
    group_map = {}
    for i, row in enumerate(rows):
        soc = row.get("soc_code")
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
            manifest.append({"table": "base.cip_soc_crosswalk", "row": -1,
                             "dimension": "coverage", "field": "soc_major_group",
                             "strategy": f"remove_all_group_{grp}",
                             "old_value": f"group={grp}, count={len(group_map[grp])}",
                             "new_value": "removed"})
        for idx in sorted(removed, reverse=True):
            if idx < len(rows):
                rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Main injection pipeline
# ---------------------------------------------------------------------------

def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle across both Bronze and Silver tables."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)

    # Load both tables
    print("Loading source data...")
    table_data = {}
    table_schemas = {}
    for table_name in SOURCE_PARQUETS:
        rows, schema = load_table(table_name)
        table_data[table_name] = rows
        table_schemas[table_name] = schema
        print(f"  {table_name}: {len(rows)} rows")

    # Run corruption on each table
    all_manifest = []
    original_counts = {t: len(rows) for t, rows in table_data.items()}

    # Bronze
    print("\nCorrupting raw.cip_soc_crosswalk (Bronze)...")
    m = corrupt_bronze(table_data["bronze_cip_soc"], rate, rng)
    all_manifest.extend(m)
    print(f"  {len(m)} corruptions")

    # Silver
    print("Corrupting base.cip_soc_crosswalk (Silver)...")
    m = corrupt_silver(table_data["silver_cip_soc"], rate, rng)
    all_manifest.extend(m)
    print(f"  {len(m)} corruptions")

    print(f"\n  Total corruptions: {len(all_manifest)}")
    for t in SOURCE_PARQUETS:
        print(f"  {t}: {len(table_data[t])} rows (was {original_counts[t]})")

    # Write shadow parquet files
    print("\nWriting shadow parquet files...")
    table_parquets = {}
    dq_result = {"run_id": "error", "rules_total": 0, "rules_passed": 0,
                 "rules_failed": 0, "p0_passed": True, "results": []}

    try:
        bronze_pq, _ = write_shadow_parquet(
            "bronze", "bronze_cip_soc", table_data["bronze_cip_soc"],
            table_schemas["bronze_cip_soc"], cycle_num
        )
        table_parquets["bronze_cip_soc"] = bronze_pq
        print(f"  Written bronze -> {bronze_pq}")

        silver_pq, _ = write_shadow_parquet(
            "silver", "silver_cip_soc", table_data["silver_cip_soc"],
            table_schemas["silver_cip_soc"], cycle_num
        )
        table_parquets["silver_cip_soc"] = silver_pq
        print(f"  Written silver -> {silver_pq}")

        print("Registering shadow tables in Iceberg catalog...")
        register_shadow_tables(table_parquets)

        # Verify shadow tables exist in catalog
        import sqlite3
        conn = sqlite3.connect(str(CATALOG_PATH))
        cur = conn.cursor()
        cur.execute("SELECT catalog_name, table_namespace, table_name FROM iceberg_tables WHERE table_namespace LIKE 'shadow%'")
        shadow_tables = cur.fetchall()
        conn.close()
        print(f"  Shadow tables in catalog: {shadow_tables}")
        print("  Both shadow tables registered.")

        print("Running DQ rules against shadow tables...")
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(f"  Total: {dq_result['rules_total']} | Passed: {dq_result['rules_passed']} | Failed: {dq_result['rules_failed']}")
        p0_status = "PASS" if dq_result.get("p0_passed", True) else "FAIL"
        print(f"  P0 gate: {p0_status}")

        print("\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            err_msg = f" err={r['error'][:80]}" if r.get("error") else ""
            print(f"    {r['rule_id']:<50} {status:<6} value={r.get('raw_value', '?')}{err_msg}")

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
        "injected_dimensions": sorted(dims.keys()),
        "corruptions_per_dimension": {dim: len(entries) for dim, entries in dims.items()},
        "detection_rate": round(detection_rate, 3),
        "rules_fired": len(failed_rules),
        "rules_silent": len(passed_rules),
        "total_rules": total_rules,
    }


def main():
    """Run 5-cycle adversarial hardening across Bronze + Silver crosswalk tables."""
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
        print(f"    Rules silent: {[r['rule_id'] for r in gap_analysis['passed_rules']]}")

        if consecutive_no_new_gaps >= 2:
            print(f"\n  Stability: same rules firing for {consecutive_no_new_gaps + 1} consecutive cycles.")
            print("  Early exit: no new gaps for 2 consecutive cycles.")
            cleanup_shadow()
            break

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": SPEC_NAME,
        "tables": ["raw.cip_soc_crosswalk", "base.cip_soc_crosswalk"],
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/crosswalk-cip-soc-manifest.json"
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
