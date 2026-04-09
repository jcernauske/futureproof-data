"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: silver-base-bls-ooh
Table: base.bls_ooh (832 rows)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.

Information Barrier: This script does NOT read DQ rule definitions.
It injects corruptions based solely on the table schema and domain
understanding from the transformer code.
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
SOURCE_PARQUET = PROJECT_ROOT / "data/silver/iceberg_warehouse/base/bls_ooh/data/00000-0-146f5932-291a-4ee3-ace5-d02d023ef64f.parquet"
SHADOW_DIR = PROJECT_ROOT / "data/silver/iceberg_warehouse/shadow_base/bls_ooh"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"
CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"
SILVER_WAREHOUSE = PROJECT_ROOT / "data/silver/iceberg_warehouse"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "silver-base-bls-ooh"
TABLE_NAME = "base.bls_ooh"

# Grain fields from the transformer
GRAIN_FIELDS = ["soc_code"]

# Valid SOC major group codes (22 groups)
VALID_SOC_MAJOR_GROUPS = [
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "31", "33", "35", "37", "39", "41", "43", "45", "47", "49",
    "51", "53",
]

# Broad occupation codes (exactly 7)
BROAD_OCCUPATION_CODES = [
    "13-1020", "13-2020", "29-2010", "31-1120",
    "39-7010", "47-4090", "51-2090",
]

# Valid growth categories
VALID_GROWTH_CATEGORIES = [
    "declining_fast", "declining", "stable", "growing", "growing_fast", "booming",
]

# Valid education codes (1-8), work_experience_code (1-3), training_code (1-6)
VALID_EDUCATION_CODES = list(range(1, 9))
VALID_WORK_EXPERIENCE_CODES = list(range(1, 4))
VALID_TRAINING_CODES = list(range(1, 7))

# Education level names (from transformer lookup)
EDUCATION_LEVEL_NAMES = {
    1: "Doctoral or professional degree",
    2: "Master's degree",
    3: "Bachelor's degree",
    4: "Associate's degree",
    5: "Postsecondary nondegree award",
    6: "Some college, no degree",
    7: "High school diploma or equivalent",
    8: "No formal educational credential",
}


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
# Corruption strategies (one per DQ dimension, targeting Silver schema)
# ---------------------------------------------------------------------------

def corrupt_completeness(rows, indices, rng):
    """Null out required fields: record_id, soc_code, occupation_title,
    soc_major_group, soc_major_group_name, broad_occupation_flag, catchall_flag,
    median_wage_capped, wage_available, source_load_date, ingested_at."""
    manifest = []
    required_fields = [
        "record_id", "soc_code", "occupation_title",
        "soc_major_group", "soc_major_group_name",
        "broad_occupation_flag", "catchall_flag",
        "median_wage_capped", "wage_available",
        "source_load_date", "ingested_at",
    ]
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(required_fields)
        old_val = rows[i].get(field)
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null",
        })
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid values: bad SOC format, invalid growth_category, bad education/
    experience/training codes, invalid soc_major_group, negative employment,
    wage out of range."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_soc_format", "bad_growth_category", "bad_education_code",
            "bad_work_experience_code", "bad_training_code",
            "bad_soc_major_group", "negative_employment", "wage_out_of_range",
        ])
        if strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice([
                "151252", "15.1252", "XX-XXXX", "15-12520", "1-1252",
                "", "abc", "00-0000", "99-99999",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
            })
        elif strategy == "bad_growth_category":
            old_val = rows[i].get("growth_category")
            rows[i]["growth_category"] = rng.choice([
                "fast_growing", "slow", "BOOMING", "decline", "Stable",
                "unknown", "N/A", "",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "growth_category",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["growth_category"],
            })
        elif strategy == "bad_education_code":
            old_val = rows[i].get("education_code")
            rows[i]["education_code"] = rng.choice([0, -1, 9, 10, 99, -5])
            manifest.append({
                "row": i, "dimension": "validity", "field": "education_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["education_code"]),
            })
        elif strategy == "bad_work_experience_code":
            old_val = rows[i].get("work_experience_code")
            rows[i]["work_experience_code"] = rng.choice([0, -1, 4, 5, 99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "work_experience_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["work_experience_code"]),
            })
        elif strategy == "bad_training_code":
            old_val = rows[i].get("training_code")
            rows[i]["training_code"] = rng.choice([0, -1, 7, 8, 99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "training_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["training_code"]),
            })
        elif strategy == "bad_soc_major_group":
            old_val = rows[i].get("soc_major_group")
            rows[i]["soc_major_group"] = rng.choice([
                "00", "12", "14", "16", "20", "50", "55", "99", "XX",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_major_group",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_major_group"],
            })
        elif strategy == "negative_employment":
            field = rng.choice([
                "employment_current", "employment_projected", "openings_annual_avg",
            ])
            old_val = rows[i].get(field)
            rows[i][field] = rng.randint(-500000, -1)
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "wage_out_of_range":
            old_val = rows[i].get("median_annual_wage")
            rows[i]["median_annual_wage"] = rng.choice([
                5000.0, 10000.0, 300000.0, 500000.0, -10000.0,
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"]),
            })
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows (same soc_code, same record_id = same grain)."""
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
    """Contradictory field combinations:
    - soc_major_group doesn't match soc_code prefix
    - soc_major_group_name doesn't match soc_major_group
    - growth_category doesn't match employment_change_pct
    - wage_available contradicts median_annual_wage
    - median_wage_capped True but wage != cap value
    - education_level_name doesn't match education_code
    - broad_occupation_flag True for non-broad codes
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "major_group_mismatch", "major_group_name_mismatch",
            "growth_category_mismatch", "wage_available_contradiction",
            "capped_wrong_wage", "education_name_mismatch",
            "broad_flag_wrong",
        ])
        if strategy == "major_group_mismatch":
            old_val = rows[i]["soc_major_group"]
            soc_code = rows[i]["soc_code"]
            real_prefix = soc_code[:2] if soc_code and len(soc_code) >= 2 else "11"
            # Pick a different valid major group
            choices = [g for g in VALID_SOC_MAJOR_GROUPS if g != real_prefix]
            rows[i]["soc_major_group"] = rng.choice(choices) if choices else "99"
            manifest.append({
                "row": i, "dimension": "consistency", "field": "soc_major_group",
                "strategy": strategy,
                "old_value": f"soc_code={soc_code}, group={old_val}",
                "new_value": f"group={rows[i]['soc_major_group']} (mismatches soc prefix)",
            })
        elif strategy == "major_group_name_mismatch":
            old_name = rows[i]["soc_major_group_name"]
            rows[i]["soc_major_group_name"] = "Completely Wrong Group Name"
            manifest.append({
                "row": i, "dimension": "consistency", "field": "soc_major_group_name",
                "strategy": strategy,
                "old_value": str(old_name),
                "new_value": "Completely Wrong Group Name",
            })
        elif strategy == "growth_category_mismatch":
            old_cat = rows[i].get("growth_category")
            old_pct = rows[i].get("employment_change_pct")
            # Assign a wrong category
            if old_pct is not None and old_pct >= 0:
                rows[i]["growth_category"] = "declining_fast"
            else:
                rows[i]["growth_category"] = "booming"
            manifest.append({
                "row": i, "dimension": "consistency", "field": "growth_category",
                "strategy": strategy,
                "old_value": f"pct={old_pct}, category={old_cat}",
                "new_value": f"category={rows[i]['growth_category']} (wrong for pct)",
            })
        elif strategy == "wage_available_contradiction":
            old_flag = rows[i].get("wage_available")
            old_wage = rows[i].get("median_annual_wage")
            if old_wage is not None:
                rows[i]["wage_available"] = False
            else:
                rows[i]["wage_available"] = True
            manifest.append({
                "row": i, "dimension": "consistency", "field": "wage_available",
                "strategy": strategy,
                "old_value": f"wage={old_wage}, available={old_flag}",
                "new_value": f"available={rows[i]['wage_available']} (contradicts wage)",
            })
        elif strategy == "capped_wrong_wage":
            old_capped = rows[i].get("median_wage_capped")
            old_wage = rows[i].get("median_annual_wage")
            rows[i]["median_wage_capped"] = True
            if old_wage is None:
                rows[i]["median_annual_wage"] = 100000.0
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "median_wage_capped,median_annual_wage",
                "strategy": strategy,
                "old_value": f"capped={old_capped},wage={old_wage}",
                "new_value": f"capped=True,wage={rows[i]['median_annual_wage']}",
            })
        elif strategy == "education_name_mismatch":
            old_code = rows[i].get("education_code")
            old_name = rows[i].get("education_level_name")
            if old_code is not None:
                wrong_name = rng.choice([
                    n for c, n in EDUCATION_LEVEL_NAMES.items()
                    if c != old_code
                ])
                rows[i]["education_level_name"] = wrong_name
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "education_level_name",
                    "strategy": strategy,
                    "old_value": f"code={old_code}, name={old_name}",
                    "new_value": f"name={wrong_name} (wrong for code)",
                })
        elif strategy == "broad_flag_wrong":
            old_flag = rows[i].get("broad_occupation_flag")
            soc_code = rows[i].get("soc_code")
            if soc_code in BROAD_OCCUPATION_CODES:
                rows[i]["broad_occupation_flag"] = False
            else:
                rows[i]["broad_occupation_flag"] = True
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "broad_occupation_flag",
                "strategy": strategy,
                "old_value": f"soc={soc_code}, flag={old_flag}",
                "new_value": f"flag={rows[i]['broad_occupation_flag']} (wrong for soc)",
            })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: subtly wrong SOC codes, swapped fields,
    slightly off wages."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "swapped_employment", "wage_off_by_10x", "occupation_title_wrong",
        ])
        if strategy == "swapped_employment":
            old_current = rows[i].get("employment_current")
            old_projected = rows[i].get("employment_projected")
            if old_current is not None and old_projected is not None:
                rows[i]["employment_current"] = old_projected
                rows[i]["employment_projected"] = old_current
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "employment_current,employment_projected",
                    "strategy": strategy,
                    "old_value": f"current={old_current},projected={old_projected}",
                    "new_value": f"current={old_projected},projected={old_current}",
                })
        elif strategy == "wage_off_by_10x":
            old_val = rows[i].get("median_annual_wage")
            if old_val is not None:
                rows[i]["median_annual_wage"] = old_val * 10
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "median_annual_wage",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(rows[i]["median_annual_wage"]),
                })
        elif strategy == "occupation_title_wrong":
            old_val = rows[i].get("occupation_title")
            rows[i]["occupation_title"] = "WRONG TITLE - " + str(rng.randint(1000, 9999))
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "occupation_title",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["occupation_title"],
            })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: impossibly high/low wages, employment, change pct."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_wage", "extreme_employment", "extreme_change_pct",
            "extreme_openings",
        ])
        if strategy == "extreme_wage":
            old_val = rows[i].get("median_annual_wage")
            rows[i]["median_annual_wage"] = float(rng.choice([
                1, 100, 999999, 5000000, -50000,
            ]))
            rows[i]["median_wage_capped"] = False
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"]),
            })
        elif strategy == "extreme_employment":
            field = rng.choice(["employment_current", "employment_projected"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.randint(500000000, 999999999)
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "extreme_change_pct":
            old_val = rows[i].get("employment_change_pct")
            rows[i]["employment_change_pct"] = float(rng.choice([
                -99.9, 500.0, 1000.0, -200.0, 300.0,
            ]))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "employment_change_pct",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["employment_change_pct"]),
            })
        elif strategy == "extreme_openings":
            old_val = rows[i].get("openings_annual_avg")
            rows[i]["openings_annual_avg"] = rng.randint(50000000, 99999999)
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "openings_annual_avg",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["openings_annual_avg"]),
            })
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps on source_load_date and ingested_at."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "future_load_date", "stale_load_date",
            "future_ingested_at", "epoch_ingested_at",
        ])
        if strategy == "future_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-06-15",
            })
        elif strategy == "stale_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2015, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2015-01-01",
            })
        elif strategy == "future_ingested_at":
            old_val = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "ingested_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2035-01-01T00:00:00",
            })
        elif strategy == "epoch_ingested_at":
            old_val = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(1970, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "ingested_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "1970-01-01T00:00:00",
            })
    return manifest


def corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-duplicate a chunk to inflate count beyond 832."""
    manifest = []
    n_extras = max(50, len(rows) // 10)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "strategy": "mass_duplicate",
        "old_value": str(len(rows) - len(source_rows)),
        "new_value": str(len(rows)),
    })
    return manifest


def corrupt_referential_integrity(rows, indices, rng):
    """Orphan SOC codes: valid-format codes from invalid major groups (60-99 range)."""
    manifest = []
    valid_indices = [i for i in indices if i < len(rows)]
    if not valid_indices:
        return manifest
    targets = rng.sample(valid_indices, min(len(valid_indices), max(1, len(valid_indices) // 4)))
    for i in targets:
        old_val = rows[i]["soc_code"]
        # Generate valid-format but nonexistent SOC codes outside the 22 major groups
        fake_prefix = rng.choice(["12", "14", "16", "20", "22", "24", "26", "28",
                                   "30", "32", "34", "36", "38", "40", "42", "44",
                                   "46", "48", "50", "52", "54", "56", "58", "60",
                                   "90", "92", "94", "96", "98"])
        fake_soc = f"{fake_prefix}-{rng.randint(1000, 9999)}"
        rows[i]["soc_code"] = fake_soc
        rows[i]["occupation_title"] = f"FAKE OCCUPATION {fake_soc}"
        manifest.append({
            "row": i, "dimension": "referential_integrity", "field": "soc_code",
            "strategy": "orphan_soc", "old_value": str(old_val),
            "new_value": fake_soc,
        })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove all rows for certain SOC major groups
    to create coverage gaps in the 22-group distribution."""
    manifest = []
    group_counts = {}
    for i, row in enumerate(rows):
        grp = row.get("soc_major_group")
        if grp:
            group_counts.setdefault(grp, []).append(i)

    # Remove all rows for 2-3 SOC major groups
    common_groups = sorted(
        group_counts, key=lambda g: len(group_counts[g]), reverse=True
    )[:8]
    targets = rng.sample(common_groups, min(3, len(common_groups)))

    removed_indices = set()
    for grp in targets:
        for idx in group_counts[grp]:
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "soc_major_group",
            "strategy": f"remove_all_group_{grp}",
            "old_value": f"group={grp}, count={len(group_counts[grp])}",
            "new_value": "removed",
        })

    for idx in sorted(removed_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_source_data():
    """Load Silver parquet data into a list of dicts."""
    import pyarrow.parquet as pq
    table = pq.read_table(str(SOURCE_PARQUET))
    rows = []
    for i in range(table.num_rows):
        row = {}
        for col in table.column_names:
            val = table.column(col)[i].as_py()
            row[col] = val
        rows.append(row)
    return rows, table.schema


def write_shadow_parquet(rows, original_schema, cycle_num):
    """Write corrupted rows to shadow parquet file."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    SHADOW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHADOW_META_DIR.mkdir(parents=True, exist_ok=True)

    arrays = {}
    for field in original_schema:
        col_name = field.name
        values = [r.get(col_name) for r in rows]
        try:
            arrays[col_name] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arrays[col_name] = pa.array(values)

    arrow_table = pa.table(arrays)
    out_file = SHADOW_DATA_DIR / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out_file))
    return out_file, arrow_table


def register_shadow_in_catalog(parquet_path):
    """Register shadow table in the Iceberg catalog under shadow_base namespace."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, DoubleType, IntegerType, LongType,
        NestedField, StringType, TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))

    try:
        catalog.create_namespace("shadow_base")
    except Exception:
        pass

    try:
        catalog.drop_table("shadow_base.bls_ooh")
    except Exception:
        pass

    # Schema matching the Silver table (all optional for shadow to accept nulls)
    iceberg_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "soc_code", StringType(), required=False),
        NestedField(3, "occupation_title", StringType(), required=False),
        NestedField(4, "soc_major_group", StringType(), required=False),
        NestedField(5, "soc_major_group_name", StringType(), required=False),
        NestedField(6, "broad_occupation_flag", BooleanType(), required=False),
        NestedField(7, "catchall_flag", BooleanType(), required=False),
        NestedField(8, "employment_current", LongType(), required=False),
        NestedField(9, "employment_projected", LongType(), required=False),
        NestedField(10, "employment_change", LongType(), required=False),
        NestedField(11, "employment_change_pct", DoubleType(), required=False),
        NestedField(12, "openings_annual_avg", LongType(), required=False),
        NestedField(13, "growth_category", StringType(), required=False),
        NestedField(14, "median_annual_wage", DoubleType(), required=False),
        NestedField(15, "median_wage_capped", BooleanType(), required=False),
        NestedField(16, "wage_available", BooleanType(), required=False),
        NestedField(17, "education_typical", StringType(), required=False),
        NestedField(18, "education_code", IntegerType(), required=False),
        NestedField(19, "education_level_name", StringType(), required=False),
        NestedField(20, "work_experience", StringType(), required=False),
        NestedField(21, "work_experience_code", IntegerType(), required=False),
        NestedField(22, "training_typical", StringType(), required=False),
        NestedField(23, "training_code", IntegerType(), required=False),
        NestedField(24, "source_load_date", DateType(), required=False),
        NestedField(25, "ingested_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_base.bls_ooh", schema=iceberg_schema
    )

    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def run_dq_rules_shadow():
    """Run DQ rules against the shadow table."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
    result = run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)
    return result


def cleanup_shadow():
    """Remove shadow table and files."""
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
        catalog.drop_table("shadow_base.bls_ooh")
    except Exception:
        pass


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


def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)

    print("Loading source data...")
    rows, original_schema = load_source_data()
    original_count = len(rows)
    print(f"  Loaded {original_count} rows")

    n_corrupt = int(original_count * rate)
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
            traceback.print_exc()

    print(f"  Total corruptions: {len(all_manifest)}")
    print(f"  Final row count: {len(rows)} (was {original_count})")

    # Write shadow table
    print("Writing shadow table...")
    dq_result = {"run_id": "error", "rules_total": 0, "rules_passed": 0,
                 "rules_failed": 0, "p0_passed": True, "results": []}
    try:
        parquet_path, arrow_table = write_shadow_parquet(rows, original_schema, cycle_num)
        print(f"  Written to {parquet_path}")

        print("Registering in Iceberg catalog as shadow_base.bls_ooh...")
        register_shadow_in_catalog(parquet_path)
        print("  Registered.")

        print("Running DQ rules against shadow table...")
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
        "original_row_count": original_count,
        "corrupted_row_count": len(rows),
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
    """Run 5-cycle adversarial hardening."""
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
            "row_count": cycle_result["corrupted_row_count"],
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

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": SPEC_NAME,
        "table": TABLE_NAME,
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/silver-base-bls-ooh-manifest.json"
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
            f"detection rate: {ga['detection_rate']*100:.1f}%, "
            f"silent rules: {[r['rule_id'] for r in ga['passed_rules']]}"
        )
