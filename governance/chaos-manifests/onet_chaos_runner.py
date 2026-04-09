"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: raw-ingest-onet
Tables: raw.onet_occupations, raw.onet_task_statements,
        raw.onet_work_activities, raw.onet_work_context,
        raw.onet_related_occupations

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against shadow tables, and records what was caught vs missed.
"""

import json
import random
import datetime
import copy
import sys
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
WAREHOUSE = PROJECT_ROOT / "data" / "bronze" / "iceberg_warehouse"
CATALOG_DB = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42

# Table names in the raw namespace
ONET_TABLES = [
    "onet_occupations",
    "onet_task_statements",
    "onet_work_activities",
    "onet_work_context",
    "onet_related_occupations",
]

sys.path.insert(0, str(PROJECT_ROOT / "src"))


# ---------------------------------------------------------------------------
# Data loading — read from Iceberg via DuckDB
# ---------------------------------------------------------------------------

def get_table_metadata(table_name):
    """Get the Iceberg metadata location for a raw table."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import WAREHOUSE_PATH, CATALOG_PATH
    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    tbl = catalog.load_table(f"raw.{table_name}")
    return tbl.metadata_location


def load_table_data(table_name):
    """Load all rows from a raw Iceberg table as list of dicts."""
    meta = get_table_metadata(table_name)
    con = duckdb.connect()
    con.install_extension("iceberg")
    con.load_extension("iceberg")
    con.execute(f"CREATE VIEW tbl AS SELECT * FROM iceberg_scan('{meta}')")
    result = con.execute("SELECT * FROM tbl").fetchall()
    cols = [r[0] for r in con.execute("DESCRIBE tbl").fetchall()]
    con.close()
    rows = []
    for row in result:
        rows.append(dict(zip(cols, row)))
    return rows


# ---------------------------------------------------------------------------
# Per-table corruption strategies covering all 10 DQ dimensions
# ---------------------------------------------------------------------------

# ---- onet_occupations (1,016 rows) ----
# Schema: onet_soc_code(str,req), title(str,req), description(str,req),
#         ingested_at(ts,req), source_url(str,req), source_method(str,req), load_date(date,req)

def corrupt_occupations(rows, rate, rng):
    """Corrupt onet_occupations across all 10 dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. Completeness: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["onet_soc_code", "title", "description"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_occupations", "row": i, "dimension": "completeness",
                         "field": field, "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. Validity: bad SOC code formats
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["bad_soc_format", "bad_soc_no_dot", "bad_soc_alpha"])
        old_val = rows[i]["onet_soc_code"]
        if strategy == "bad_soc_format":
            rows[i]["onet_soc_code"] = rng.choice(["111011", "11.1011.00", "XX-XXXX.XX", "", "abc"])
        elif strategy == "bad_soc_no_dot":
            rows[i]["onet_soc_code"] = "11-101100"  # Missing dot
        elif strategy == "bad_soc_alpha":
            rows[i]["onet_soc_code"] = "AB-CDEF.GH"
        manifest.append({"table": "onet_occupations", "row": i, "dimension": "validity",
                         "field": "onet_soc_code", "strategy": strategy,
                         "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 3. Uniqueness: duplicate rows
    n_dupes = max(1, n_corrupt // 15)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "onet_occupations", "row": insert_pos, "dimension": "uniqueness",
                         "field": "onet_soc_code", "strategy": "duplicate_row",
                         "old_value": f"copy_of_row_{src_idx}",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. Consistency: title/description swap
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_title = rows[i]["title"]
        old_desc = rows[i]["description"]
        rows[i]["title"] = old_desc[:50] if old_desc else ""
        rows[i]["description"] = old_title
        manifest.append({"table": "onet_occupations", "row": i, "dimension": "consistency",
                         "field": "title<->description", "strategy": "column_swap",
                         "old_value": f"title={str(old_title)[:40]}", "new_value": f"title={str(rows[i]['title'])[:40]}"})

    # 5. Accuracy: plausible but wrong SOC code (valid format, wrong code)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_soc_code"]
        # Generate a valid-format but nonexistent code
        rows[i]["onet_soc_code"] = f"{rng.randint(90,99)}-{rng.randint(1000,9999)}.{rng.randint(0,99):02d}"
        manifest.append({"table": "onet_occupations", "row": i, "dimension": "accuracy",
                         "field": "onet_soc_code", "strategy": "fake_soc_code",
                         "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 6. Reasonableness: extremely long/short descriptions
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["tiny_description", "huge_description"])
        old_val = str(rows[i]["description"])[:40]
        if strategy == "tiny_description":
            rows[i]["description"] = "A"
        else:
            rows[i]["description"] = "X" * 10000
        manifest.append({"table": "onet_occupations", "row": i, "dimension": "reasonableness",
                         "field": "description", "strategy": strategy,
                         "old_value": old_val, "new_value": f"len={len(rows[i]['description'])}"})

    # 7. Freshness: future/stale dates
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2030, 1, 1)
            manifest.append({"table": "onet_occupations", "row": i, "dimension": "freshness",
                             "field": "load_date", "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-01-01"})
        elif strategy == "stale_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2020, 1, 1)
            manifest.append({"table": "onet_occupations", "row": i, "dimension": "freshness",
                             "field": "load_date", "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2020-01-01"})
        else:
            old_val = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(2030, 6, 15, 12, 0, 0)
            manifest.append({"table": "onet_occupations", "row": i, "dimension": "freshness",
                             "field": "ingested_at", "strategy": strategy,
                             "old_value": str(old_val), "new_value": "2030-06-15T12:00:00"})

    # 8. Volume: mass-duplicate to inflate count
    n_extras = max(10, n // 10)
    source_rows = rng.choices(all_indices, k=n_extras)
    for src_idx in source_rows:
        rows.append(copy.deepcopy(rows[src_idx]))
    manifest.append({"table": "onet_occupations", "row": -1, "dimension": "volume",
                     "field": "row_count", "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. Referential Integrity: SOC codes not in the valid O*NET set
    # (Already covered by accuracy strategy — valid format but fake codes)
    # Add additional explicit orphan FK entries
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_soc_code"]
        rows[i]["onet_soc_code"] = f"ORPHAN_{rng.randint(100000, 999999)}"
        manifest.append({"table": "onet_occupations", "row": i, "dimension": "referential_integrity",
                         "field": "onet_soc_code", "strategy": "orphan_soc_code",
                         "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 10. Coverage: remove all rows for certain SOC major groups
    soc_prefixes = {}
    for i, row in enumerate(rows[:n]):  # Only look at original rows
        code = row.get("onet_soc_code", "")
        if code and len(code) >= 2:
            prefix = code[:2]
            soc_prefixes.setdefault(prefix, []).append(i)
    if soc_prefixes:
        victim_prefix = rng.choice(list(soc_prefixes.keys()))
        victim_indices = set(soc_prefixes[victim_prefix])
        removed_count = len(victim_indices)
        # Mark for removal (filter later)
        rows_new = [r for i, r in enumerate(rows) if i not in victim_indices]
        manifest.append({"table": "onet_occupations", "row": -1, "dimension": "coverage",
                         "field": "onet_soc_code", "strategy": f"remove_soc_group_{victim_prefix}",
                         "old_value": f"prefix={victim_prefix}, count={removed_count}",
                         "new_value": "removed"})
        rows.clear()
        rows.extend(rows_new)

    return manifest


# ---- onet_task_statements (18,796 rows) ----

def corrupt_task_statements(rows, rate, rng):
    """Corrupt onet_task_statements across all 10 dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. Completeness: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["onet_soc_code", "task_id", "task"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_task_statements", "row": i, "dimension": "completeness",
                         "field": field, "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. Validity: bad SOC codes, invalid task_type values, negative task_id
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["bad_soc_format", "bad_task_type", "negative_task_id"])
        if strategy == "bad_soc_format":
            old_val = rows[i]["onet_soc_code"]
            rows[i]["onet_soc_code"] = rng.choice(["111011", "XX", "ab-cdef.gh", "", "99999999"])
            manifest.append({"table": "onet_task_statements", "row": i, "dimension": "validity",
                             "field": "onet_soc_code", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})
        elif strategy == "bad_task_type":
            old_val = rows[i]["task_type"]
            rows[i]["task_type"] = rng.choice(["Invalid", "Unknown", "CORE", "core", "123", ""])
            manifest.append({"table": "onet_task_statements", "row": i, "dimension": "validity",
                             "field": "task_type", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["task_type"])})
        elif strategy == "negative_task_id":
            old_val = rows[i]["task_id"]
            rows[i]["task_id"] = rng.randint(-99999, -1)
            manifest.append({"table": "onet_task_statements", "row": i, "dimension": "validity",
                             "field": "task_id", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["task_id"])})

    # 3. Uniqueness: duplicate rows (same soc_code + task_id)
    n_dupes = max(1, n_corrupt // 15)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({"table": "onet_task_statements", "row": insert_pos, "dimension": "uniqueness",
                         "field": "grain", "strategy": "duplicate_row",
                         "old_value": f"copy_of_row_{src_idx}",
                         "new_value": f"duplicate at position {insert_pos}"})

    # 4. Consistency: SOC code in task_statements not matching any occupations table entry
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_soc_code"]
        # Valid format but this occupation wouldn't have tasks
        rows[i]["onet_soc_code"] = f"{rng.randint(90,99)}-{rng.randint(1000,9999)}.{rng.randint(0,99):02d}"
        manifest.append({"table": "onet_task_statements", "row": i, "dimension": "consistency",
                         "field": "onet_soc_code", "strategy": "orphan_soc_in_tasks",
                         "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 5. Accuracy: truncated task text
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["task"]
        if old_val and isinstance(old_val, str) and len(old_val) > 10:
            rows[i]["task"] = old_val[:5]
            manifest.append({"table": "onet_task_statements", "row": i, "dimension": "accuracy",
                             "field": "task", "strategy": "truncated_task",
                             "old_value": str(old_val)[:40], "new_value": str(rows[i]["task"])})

    # 6. Reasonableness: extreme task_id values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["task_id"]
        rows[i]["task_id"] = rng.choice([0, 2**31 - 1, 999999999])
        manifest.append({"table": "onet_task_statements", "row": i, "dimension": "reasonableness",
                         "field": "task_id", "strategy": "extreme_task_id",
                         "old_value": str(old_val), "new_value": str(rows[i]["task_id"])})

    # 7. Freshness
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i].get("load_date")
        rows[i]["load_date"] = rng.choice([datetime.date(2030, 1, 1), datetime.date(2018, 1, 1)])
        manifest.append({"table": "onet_task_statements", "row": i, "dimension": "freshness",
                         "field": "load_date", "strategy": "bad_load_date",
                         "old_value": str(old_val), "new_value": str(rows[i]["load_date"])})

    # 8. Volume: mass duplication
    n_extras = max(50, n // 10)
    source_rows = rng.choices(all_indices, k=n_extras)
    for src_idx in source_rows:
        rows.append(copy.deepcopy(rows[src_idx]))
    manifest.append({"table": "onet_task_statements", "row": -1, "dimension": "volume",
                     "field": "row_count", "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. Referential Integrity: orphan SOC codes
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_soc_code"]
        rows[i]["onet_soc_code"] = f"ORPHAN_{rng.randint(100000, 999999)}"
        manifest.append({"table": "onet_task_statements", "row": i, "dimension": "referential_integrity",
                         "field": "onet_soc_code", "strategy": "orphan_soc_code",
                         "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 10. Coverage: remove all tasks for certain occupations
    soc_codes = {}
    for i, row in enumerate(rows[:n]):
        code = row.get("onet_soc_code", "")
        if code:
            soc_codes.setdefault(code, []).append(i)
    if soc_codes:
        # Remove tasks for 3 occupations
        victims = rng.sample(list(soc_codes.keys()), min(3, len(soc_codes)))
        victim_indices = set()
        for v in victims:
            victim_indices.update(soc_codes[v])
        rows_new = [r for i, r in enumerate(rows) if i not in victim_indices]
        removed = len(rows) - len(rows_new)
        manifest.append({"table": "onet_task_statements", "row": -1, "dimension": "coverage",
                         "field": "onet_soc_code", "strategy": f"remove_tasks_for_{len(victims)}_occupations",
                         "old_value": f"codes={victims[:3]}, removed={removed}",
                         "new_value": "removed"})
        rows.clear()
        rows.extend(rows_new)

    return manifest


# ---- onet_work_activities (73,308 rows) ----

def corrupt_work_activities(rows, rate, rng):
    """Corrupt onet_work_activities across all 10 dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. Completeness: null required fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["onet_soc_code", "element_id", "element_name", "scale_id", "data_value"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_work_activities", "row": i, "dimension": "completeness",
                         "field": field, "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. Validity: bad scale_id, bad element_id format, invalid data_value
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["bad_scale_id", "bad_element_id", "bad_data_value", "bad_soc_format"])
        if strategy == "bad_scale_id":
            old_val = rows[i]["scale_id"]
            rows[i]["scale_id"] = rng.choice(["XX", "INVALID", "", "123", "im", "lv"])
            manifest.append({"table": "onet_work_activities", "row": i, "dimension": "validity",
                             "field": "scale_id", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["scale_id"])})
        elif strategy == "bad_element_id":
            old_val = rows[i]["element_id"]
            rows[i]["element_id"] = rng.choice(["", "INVALID", "99.99.99", "X.X.X.X.X.X"])
            manifest.append({"table": "onet_work_activities", "row": i, "dimension": "validity",
                             "field": "element_id", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["element_id"])})
        elif strategy == "bad_data_value":
            old_val = rows[i]["data_value"]
            rows[i]["data_value"] = rng.choice([-1.0, -5.0, 8.0, 100.0])  # Work activities scale is 0-7
            manifest.append({"table": "onet_work_activities", "row": i, "dimension": "validity",
                             "field": "data_value", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["data_value"])})
        elif strategy == "bad_soc_format":
            old_val = rows[i]["onet_soc_code"]
            rows[i]["onet_soc_code"] = rng.choice(["111011", "XX", "", "99999999"])
            manifest.append({"table": "onet_work_activities", "row": i, "dimension": "validity",
                             "field": "onet_soc_code", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 3. Uniqueness: duplicate rows
    n_dupes = max(1, n_corrupt // 20)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        rows.append(copy.deepcopy(rows[src_idx]))
        manifest.append({"table": "onet_work_activities", "row": len(rows) - 1, "dimension": "uniqueness",
                         "field": "grain", "strategy": "duplicate_row",
                         "old_value": f"copy_of_row_{src_idx}", "new_value": f"dup at {len(rows) - 1}"})

    # 4. Consistency: lower_ci > upper_ci, or standard_error negative
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["swap_ci_bounds", "negative_se"])
        if strategy == "swap_ci_bounds":
            old_lower = rows[i].get("lower_ci_bound")
            old_upper = rows[i].get("upper_ci_bound")
            if old_lower is not None and old_upper is not None:
                rows[i]["lower_ci_bound"] = old_upper + 1.0
                rows[i]["upper_ci_bound"] = old_lower - 1.0
                manifest.append({"table": "onet_work_activities", "row": i, "dimension": "consistency",
                                 "field": "lower_ci_bound,upper_ci_bound", "strategy": strategy,
                                 "old_value": f"lower={old_lower},upper={old_upper}",
                                 "new_value": f"lower={rows[i]['lower_ci_bound']},upper={rows[i]['upper_ci_bound']}"})
        elif strategy == "negative_se":
            old_val = rows[i].get("standard_error")
            if old_val is not None:
                rows[i]["standard_error"] = -abs(old_val) - 0.1
                manifest.append({"table": "onet_work_activities", "row": i, "dimension": "consistency",
                                 "field": "standard_error", "strategy": strategy,
                                 "old_value": str(old_val), "new_value": str(rows[i]["standard_error"])})

    # 5. Accuracy: data_value slightly off (plausible but wrong)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i].get("data_value")
        if old_val is not None:
            # Shift by a plausible but wrong amount
            rows[i]["data_value"] = max(0, old_val + rng.uniform(-2.0, 2.0))
            manifest.append({"table": "onet_work_activities", "row": i, "dimension": "accuracy",
                             "field": "data_value", "strategy": "shifted_data_value",
                             "old_value": str(old_val), "new_value": str(rows[i]["data_value"])})

    # 6. Reasonableness: extreme outlier data_value, extreme n
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["extreme_data_value", "extreme_n"])
        if strategy == "extreme_data_value":
            old_val = rows[i]["data_value"]
            rows[i]["data_value"] = rng.choice([999.0, -999.0, 1e10])
            manifest.append({"table": "onet_work_activities", "row": i, "dimension": "reasonableness",
                             "field": "data_value", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["data_value"])})
        elif strategy == "extreme_n":
            old_val = rows[i].get("n")
            rows[i]["n"] = rng.choice([0, -1, 999999999])
            manifest.append({"table": "onet_work_activities", "row": i, "dimension": "reasonableness",
                             "field": "n", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["n"])})

    # 7. Freshness
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i].get("load_date")
        rows[i]["load_date"] = rng.choice([datetime.date(2030, 1, 1), datetime.date(2018, 1, 1)])
        manifest.append({"table": "onet_work_activities", "row": i, "dimension": "freshness",
                         "field": "load_date", "strategy": "bad_load_date",
                         "old_value": str(old_val), "new_value": str(rows[i]["load_date"])})

    # 8. Volume: mass duplication
    n_extras = max(100, n // 10)
    for _ in range(n_extras):
        rows.append(copy.deepcopy(rows[rng.randint(0, n - 1)]))
    manifest.append({"table": "onet_work_activities", "row": -1, "dimension": "volume",
                     "field": "row_count", "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. Referential Integrity: orphan SOC codes
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_soc_code"]
        rows[i]["onet_soc_code"] = f"ORPHAN_{rng.randint(100000, 999999)}"
        manifest.append({"table": "onet_work_activities", "row": i, "dimension": "referential_integrity",
                         "field": "onet_soc_code", "strategy": "orphan_soc_code",
                         "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 10. Coverage: remove all activities for a scale_id
    scale_indices = {}
    for i, row in enumerate(rows[:n]):
        sid = row.get("scale_id", "")
        if sid:
            scale_indices.setdefault(sid, []).append(i)
    if scale_indices and len(scale_indices) > 1:
        victim = rng.choice(list(scale_indices.keys()))
        victim_set = set(scale_indices[victim])
        rows_new = [r for i, r in enumerate(rows) if i not in victim_set]
        removed = len(rows) - len(rows_new)
        manifest.append({"table": "onet_work_activities", "row": -1, "dimension": "coverage",
                         "field": "scale_id", "strategy": f"remove_scale_{victim}",
                         "old_value": f"scale_id={victim}, count={removed}",
                         "new_value": "removed"})
        rows.clear()
        rows.extend(rows_new)

    return manifest


# ---- onet_work_context (297,676 rows) ----

def corrupt_work_context(rows, rate, rng):
    """Corrupt onet_work_context across all 10 dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. Completeness
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["onet_soc_code", "element_id", "element_name", "scale_id", "data_value"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_work_context", "row": i, "dimension": "completeness",
                         "field": field, "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. Validity: bad scale_id (CX, CTP, CT, CXP are valid), data_value out of 0-100 range
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["bad_scale_id", "bad_data_value_range", "bad_soc_format"])
        if strategy == "bad_scale_id":
            old_val = rows[i]["scale_id"]
            rows[i]["scale_id"] = rng.choice(["XX", "INVALID", "", "IM", "LV", "ZZ"])
            manifest.append({"table": "onet_work_context", "row": i, "dimension": "validity",
                             "field": "scale_id", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["scale_id"])})
        elif strategy == "bad_data_value_range":
            old_val = rows[i]["data_value"]
            rows[i]["data_value"] = rng.choice([-10.0, 150.0, 200.0, -1.0])  # Context scale is 0-100
            manifest.append({"table": "onet_work_context", "row": i, "dimension": "validity",
                             "field": "data_value", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["data_value"])})
        elif strategy == "bad_soc_format":
            old_val = rows[i]["onet_soc_code"]
            rows[i]["onet_soc_code"] = rng.choice(["111011", "XX", "", "99999999"])
            manifest.append({"table": "onet_work_context", "row": i, "dimension": "validity",
                             "field": "onet_soc_code", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 3. Uniqueness
    n_dupes = max(1, n_corrupt // 20)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        rows.append(copy.deepcopy(rows[src_idx]))
        manifest.append({"table": "onet_work_context", "row": len(rows) - 1, "dimension": "uniqueness",
                         "field": "grain", "strategy": "duplicate_row",
                         "old_value": f"copy_of_row_{src_idx}", "new_value": f"dup at {len(rows) - 1}"})

    # 4. Consistency: swap CI bounds, negative standard_error
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        strategy = rng.choice(["swap_ci_bounds", "negative_se", "category_mismatch"])
        if strategy == "swap_ci_bounds":
            old_lower = rows[i].get("lower_ci_bound")
            old_upper = rows[i].get("upper_ci_bound")
            if old_lower is not None and old_upper is not None:
                rows[i]["lower_ci_bound"] = old_upper + 1.0
                rows[i]["upper_ci_bound"] = old_lower - 1.0
                manifest.append({"table": "onet_work_context", "row": i, "dimension": "consistency",
                                 "field": "lower_ci_bound,upper_ci_bound", "strategy": strategy,
                                 "old_value": f"lower={old_lower},upper={old_upper}",
                                 "new_value": f"lower={rows[i]['lower_ci_bound']},upper={rows[i]['upper_ci_bound']}"})
        elif strategy == "negative_se":
            old_val = rows[i].get("standard_error")
            if old_val is not None:
                rows[i]["standard_error"] = -abs(old_val) - 0.1
                manifest.append({"table": "onet_work_context", "row": i, "dimension": "consistency",
                                 "field": "standard_error", "strategy": strategy,
                                 "old_value": str(old_val), "new_value": str(rows[i]["standard_error"])})
        elif strategy == "category_mismatch":
            old_val = rows[i].get("category")
            rows[i]["category"] = rng.choice([-1, 99, 0, 999])
            manifest.append({"table": "onet_work_context", "row": i, "dimension": "consistency",
                             "field": "category", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["category"])})

    # 5. Accuracy: shifted data_value
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i].get("data_value")
        if old_val is not None:
            rows[i]["data_value"] = max(0, min(100, old_val + rng.uniform(-20.0, 20.0)))
            manifest.append({"table": "onet_work_context", "row": i, "dimension": "accuracy",
                             "field": "data_value", "strategy": "shifted_data_value",
                             "old_value": str(old_val), "new_value": str(rows[i]["data_value"])})

    # 6. Reasonableness: extreme values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["data_value"]
        rows[i]["data_value"] = rng.choice([999.0, -999.0, 1e10])
        manifest.append({"table": "onet_work_context", "row": i, "dimension": "reasonableness",
                         "field": "data_value", "strategy": "extreme_data_value",
                         "old_value": str(old_val), "new_value": str(rows[i]["data_value"])})

    # 7. Freshness
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i].get("load_date")
        rows[i]["load_date"] = rng.choice([datetime.date(2030, 1, 1), datetime.date(2018, 1, 1)])
        manifest.append({"table": "onet_work_context", "row": i, "dimension": "freshness",
                         "field": "load_date", "strategy": "bad_load_date",
                         "old_value": str(old_val), "new_value": str(rows[i]["load_date"])})

    # 8. Volume (skip mass duplication for work_context — 297K rows would be too large)
    # Instead, add a modest number of duplicates to spike the count
    n_extras = max(100, n // 20)
    for _ in range(n_extras):
        rows.append(copy.deepcopy(rows[rng.randint(0, n - 1)]))
    manifest.append({"table": "onet_work_context", "row": -1, "dimension": "volume",
                     "field": "row_count", "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. Referential Integrity: orphan SOC codes
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["onet_soc_code"]
        rows[i]["onet_soc_code"] = f"ORPHAN_{rng.randint(100000, 999999)}"
        manifest.append({"table": "onet_work_context", "row": i, "dimension": "referential_integrity",
                         "field": "onet_soc_code", "strategy": "orphan_soc_code",
                         "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})

    # 10. Coverage: remove all context for certain scale_ids
    scale_indices = {}
    for i, row in enumerate(rows[:n]):
        sid = row.get("scale_id", "")
        if sid:
            scale_indices.setdefault(sid, []).append(i)
    if scale_indices and len(scale_indices) > 1:
        victim = rng.choice(list(scale_indices.keys()))
        victim_set = set(scale_indices[victim])
        rows_new = [r for i, r in enumerate(rows) if i not in victim_set]
        removed = len(rows) - len(rows_new)
        manifest.append({"table": "onet_work_context", "row": -1, "dimension": "coverage",
                         "field": "scale_id", "strategy": f"remove_scale_{victim}",
                         "old_value": f"scale_id={victim}, count={removed}",
                         "new_value": "removed"})
        rows.clear()
        rows.extend(rows_new)

    return manifest


# ---- onet_related_occupations (18,460 rows) ----

def corrupt_related_occupations(rows, rate, rng):
    """Corrupt onet_related_occupations across all 10 dimensions."""
    manifest = []
    n = len(rows)
    n_corrupt = max(1, int(n * rate))
    all_indices = list(range(n))

    # 1. Completeness
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        field = rng.choice(["onet_soc_code", "related_onet_soc_code", "related_index"])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "completeness",
                         "field": field, "strategy": f"null_{field}",
                         "old_value": str(old_val)[:80], "new_value": "null"})

    # 2. Validity: bad SOC codes, index out of range, bad relatedness_tier
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 10), n))
    for i in targets:
        strategy = rng.choice(["bad_soc_format", "bad_related_soc", "bad_index", "bad_tier"])
        if strategy == "bad_soc_format":
            old_val = rows[i]["onet_soc_code"]
            rows[i]["onet_soc_code"] = rng.choice(["111011", "XX", "", "99999999"])
            manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "validity",
                             "field": "onet_soc_code", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["onet_soc_code"])})
        elif strategy == "bad_related_soc":
            old_val = rows[i]["related_onet_soc_code"]
            rows[i]["related_onet_soc_code"] = rng.choice(["111011", "XX", "", "ab-cdef.gh"])
            manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "validity",
                             "field": "related_onet_soc_code", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["related_onet_soc_code"])})
        elif strategy == "bad_index":
            old_val = rows[i]["related_index"]
            rows[i]["related_index"] = rng.choice([0, -1, 21, 100, -99])
            manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "validity",
                             "field": "related_index", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["related_index"])})
        elif strategy == "bad_tier":
            old_val = rows[i].get("relatedness_tier")
            rows[i]["relatedness_tier"] = rng.choice(["Invalid", "XXXXX", "", "Primary", "primary-short"])
            manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "validity",
                             "field": "relatedness_tier", "strategy": strategy,
                             "old_value": str(old_val), "new_value": str(rows[i]["relatedness_tier"])})

    # 3. Uniqueness
    n_dupes = max(1, n_corrupt // 15)
    dupe_sources = rng.sample(all_indices, min(n_dupes, n))
    for src_idx in dupe_sources:
        rows.append(copy.deepcopy(rows[src_idx]))
        manifest.append({"table": "onet_related_occupations", "row": len(rows) - 1,
                         "dimension": "uniqueness", "field": "grain", "strategy": "duplicate_row",
                         "old_value": f"copy_of_row_{src_idx}", "new_value": f"dup at {len(rows) - 1}"})

    # 4. Consistency: is_primary contradicts relatedness_tier
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_primary = rows[i].get("is_primary")
        old_tier = rows[i].get("relatedness_tier")
        # Flip is_primary to contradict the tier
        rows[i]["is_primary"] = not old_primary if old_primary is not None else True
        manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "consistency",
                         "field": "is_primary,relatedness_tier", "strategy": "primary_tier_mismatch",
                         "old_value": f"is_primary={old_primary},tier={old_tier}",
                         "new_value": f"is_primary={rows[i]['is_primary']},tier={old_tier}"})

    # 5. Accuracy: self-referential (related to self)
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["related_onet_soc_code"]
        rows[i]["related_onet_soc_code"] = rows[i]["onet_soc_code"]
        manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "accuracy",
                         "field": "related_onet_soc_code", "strategy": "self_referential",
                         "old_value": str(old_val), "new_value": str(rows[i]["related_onet_soc_code"])})

    # 6. Reasonableness: extreme index values
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i]["related_index"]
        rows[i]["related_index"] = rng.choice([999, 2**31 - 1, -999])
        manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "reasonableness",
                         "field": "related_index", "strategy": "extreme_index",
                         "old_value": str(old_val), "new_value": str(rows[i]["related_index"])})

    # 7. Freshness
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        old_val = rows[i].get("load_date")
        rows[i]["load_date"] = rng.choice([datetime.date(2030, 1, 1), datetime.date(2018, 1, 1)])
        manifest.append({"table": "onet_related_occupations", "row": i, "dimension": "freshness",
                         "field": "load_date", "strategy": "bad_load_date",
                         "old_value": str(old_val), "new_value": str(rows[i]["load_date"])})

    # 8. Volume
    n_extras = max(50, n // 10)
    for _ in range(n_extras):
        rows.append(copy.deepcopy(rows[rng.randint(0, n - 1)]))
    manifest.append({"table": "onet_related_occupations", "row": -1, "dimension": "volume",
                     "field": "row_count", "strategy": "mass_duplicate",
                     "old_value": str(n), "new_value": str(len(rows))})

    # 9. Referential Integrity: orphan SOC codes in both fields
    targets = rng.sample(all_indices, min(max(1, n_corrupt // 15), n))
    for i in targets:
        field = rng.choice(["onet_soc_code", "related_onet_soc_code"])
        old_val = rows[i][field]
        rows[i][field] = f"ORPHAN_{rng.randint(100000, 999999)}"
        manifest.append({"table": "onet_related_occupations", "row": i,
                         "dimension": "referential_integrity",
                         "field": field, "strategy": "orphan_soc_code",
                         "old_value": str(old_val), "new_value": str(rows[i][field])})

    # 10. Coverage: remove all Primary-Short tier entries
    tier_indices = {}
    for i, row in enumerate(rows[:n]):
        tier = row.get("relatedness_tier", "")
        if tier:
            tier_indices.setdefault(tier, []).append(i)
    if tier_indices and len(tier_indices) > 1:
        victim = rng.choice(list(tier_indices.keys()))
        victim_set = set(tier_indices[victim])
        rows_new = [r for i, r in enumerate(rows) if i not in victim_set]
        removed = len(rows) - len(rows_new)
        manifest.append({"table": "onet_related_occupations", "row": -1, "dimension": "coverage",
                         "field": "relatedness_tier", "strategy": f"remove_tier_{victim}",
                         "old_value": f"tier={victim}, count={removed}",
                         "new_value": "removed"})
        rows.clear()
        rows.extend(rows_new)

    return manifest


# ---------------------------------------------------------------------------
# Arrow conversion helpers
# ---------------------------------------------------------------------------

def occupations_to_arrow(rows):
    schema = pa.schema([
        pa.field("onet_soc_code", pa.string()),
        pa.field("title", pa.string()),
        pa.field("description", pa.string()),
        pa.field("ingested_at", pa.timestamp("us")),
        pa.field("source_url", pa.string()),
        pa.field("source_method", pa.string()),
        pa.field("load_date", pa.date32()),
    ])
    return _rows_to_arrow(rows, schema)


def task_statements_to_arrow(rows):
    schema = pa.schema([
        pa.field("onet_soc_code", pa.string()),
        pa.field("task_id", pa.int64()),
        pa.field("task", pa.string()),
        pa.field("task_type", pa.string()),
        pa.field("incumbents_responding", pa.int32()),
        pa.field("date", pa.string()),
        pa.field("domain_source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us")),
        pa.field("source_url", pa.string()),
        pa.field("source_method", pa.string()),
        pa.field("load_date", pa.date32()),
    ])
    return _rows_to_arrow(rows, schema)


def work_activities_to_arrow(rows):
    schema = pa.schema([
        pa.field("onet_soc_code", pa.string()),
        pa.field("element_id", pa.string()),
        pa.field("element_name", pa.string()),
        pa.field("scale_id", pa.string()),
        pa.field("data_value", pa.float64()),
        pa.field("n", pa.int32()),
        pa.field("standard_error", pa.float64()),
        pa.field("lower_ci_bound", pa.float64()),
        pa.field("upper_ci_bound", pa.float64()),
        pa.field("recommend_suppress", pa.string()),
        pa.field("not_relevant", pa.string()),
        pa.field("date", pa.string()),
        pa.field("domain_source", pa.string()),
        pa.field("ingested_at", pa.timestamp("us")),
        pa.field("source_url", pa.string()),
        pa.field("source_method", pa.string()),
        pa.field("load_date", pa.date32()),
    ])
    return _rows_to_arrow(rows, schema)


def work_context_to_arrow(rows):
    schema = pa.schema([
        pa.field("onet_soc_code", pa.string()),
        pa.field("element_id", pa.string()),
        pa.field("element_name", pa.string()),
        pa.field("scale_id", pa.string()),
        pa.field("data_value", pa.float64()),
        pa.field("n", pa.int32()),
        pa.field("standard_error", pa.float64()),
        pa.field("lower_ci_bound", pa.float64()),
        pa.field("upper_ci_bound", pa.float64()),
        pa.field("recommend_suppress", pa.string()),
        pa.field("not_relevant", pa.string()),
        pa.field("date", pa.string()),
        pa.field("domain_source", pa.string()),
        pa.field("category", pa.int32()),
        pa.field("ingested_at", pa.timestamp("us")),
        pa.field("source_url", pa.string()),
        pa.field("source_method", pa.string()),
        pa.field("load_date", pa.date32()),
    ])
    return _rows_to_arrow(rows, schema)


def related_occupations_to_arrow(rows):
    schema = pa.schema([
        pa.field("onet_soc_code", pa.string()),
        pa.field("related_onet_soc_code", pa.string()),
        pa.field("related_index", pa.int32()),
        pa.field("is_primary", pa.bool_()),
        pa.field("relatedness_tier", pa.string()),
        pa.field("ingested_at", pa.timestamp("us")),
        pa.field("source_url", pa.string()),
        pa.field("source_method", pa.string()),
        pa.field("load_date", pa.date32()),
    ])
    return _rows_to_arrow(rows, schema)


ARROW_CONVERTERS = {
    "onet_occupations": occupations_to_arrow,
    "onet_task_statements": task_statements_to_arrow,
    "onet_work_activities": work_activities_to_arrow,
    "onet_work_context": work_context_to_arrow,
    "onet_related_occupations": related_occupations_to_arrow,
}

CORRUPT_FUNCTIONS = {
    "onet_occupations": corrupt_occupations,
    "onet_task_statements": corrupt_task_statements,
    "onet_work_activities": corrupt_work_activities,
    "onet_work_context": corrupt_work_context,
    "onet_related_occupations": corrupt_related_occupations,
}


def _rows_to_arrow(rows, schema):
    """Convert list of dicts to PyArrow table, coercing types."""
    arrays = {}
    for field in schema:
        col = field.name
        values = [r.get(col) for r in rows]
        try:
            arrays[col] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError):
            # Fall back to auto-detection
            arrays[col] = pa.array(values)
    return pa.table(arrays, schema=schema)


# ---------------------------------------------------------------------------
# Shadow table management
# ---------------------------------------------------------------------------

def get_iceberg_schema(table_name):
    """Get the Iceberg schema for a raw table."""
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, DoubleType, IntegerType, LongType,
        NestedField, StringType, TimestampType,
    )

    schemas = {
        "onet_occupations": Schema(
            NestedField(1, "onet_soc_code", StringType(), required=False),
            NestedField(2, "title", StringType(), required=False),
            NestedField(3, "description", StringType(), required=False),
            NestedField(4, "ingested_at", TimestampType(), required=False),
            NestedField(5, "source_url", StringType(), required=False),
            NestedField(6, "source_method", StringType(), required=False),
            NestedField(7, "load_date", DateType(), required=False),
        ),
        "onet_task_statements": Schema(
            NestedField(1, "onet_soc_code", StringType(), required=False),
            NestedField(2, "task_id", LongType(), required=False),
            NestedField(3, "task", StringType(), required=False),
            NestedField(4, "task_type", StringType(), required=False),
            NestedField(5, "incumbents_responding", IntegerType(), required=False),
            NestedField(6, "date", StringType(), required=False),
            NestedField(7, "domain_source", StringType(), required=False),
            NestedField(8, "ingested_at", TimestampType(), required=False),
            NestedField(9, "source_url", StringType(), required=False),
            NestedField(10, "source_method", StringType(), required=False),
            NestedField(11, "load_date", DateType(), required=False),
        ),
        "onet_work_activities": Schema(
            NestedField(1, "onet_soc_code", StringType(), required=False),
            NestedField(2, "element_id", StringType(), required=False),
            NestedField(3, "element_name", StringType(), required=False),
            NestedField(4, "scale_id", StringType(), required=False),
            NestedField(5, "data_value", DoubleType(), required=False),
            NestedField(6, "n", IntegerType(), required=False),
            NestedField(7, "standard_error", DoubleType(), required=False),
            NestedField(8, "lower_ci_bound", DoubleType(), required=False),
            NestedField(9, "upper_ci_bound", DoubleType(), required=False),
            NestedField(10, "recommend_suppress", StringType(), required=False),
            NestedField(11, "not_relevant", StringType(), required=False),
            NestedField(12, "date", StringType(), required=False),
            NestedField(13, "domain_source", StringType(), required=False),
            NestedField(14, "ingested_at", TimestampType(), required=False),
            NestedField(15, "source_url", StringType(), required=False),
            NestedField(16, "source_method", StringType(), required=False),
            NestedField(17, "load_date", DateType(), required=False),
        ),
        "onet_work_context": Schema(
            NestedField(1, "onet_soc_code", StringType(), required=False),
            NestedField(2, "element_id", StringType(), required=False),
            NestedField(3, "element_name", StringType(), required=False),
            NestedField(4, "scale_id", StringType(), required=False),
            NestedField(5, "data_value", DoubleType(), required=False),
            NestedField(6, "n", IntegerType(), required=False),
            NestedField(7, "standard_error", DoubleType(), required=False),
            NestedField(8, "lower_ci_bound", DoubleType(), required=False),
            NestedField(9, "upper_ci_bound", DoubleType(), required=False),
            NestedField(10, "recommend_suppress", StringType(), required=False),
            NestedField(11, "not_relevant", StringType(), required=False),
            NestedField(12, "date", StringType(), required=False),
            NestedField(13, "domain_source", StringType(), required=False),
            NestedField(14, "category", IntegerType(), required=False),
            NestedField(15, "ingested_at", TimestampType(), required=False),
            NestedField(16, "source_url", StringType(), required=False),
            NestedField(17, "source_method", StringType(), required=False),
            NestedField(18, "load_date", DateType(), required=False),
        ),
        "onet_related_occupations": Schema(
            NestedField(1, "onet_soc_code", StringType(), required=False),
            NestedField(2, "related_onet_soc_code", StringType(), required=False),
            NestedField(3, "related_index", IntegerType(), required=False),
            NestedField(4, "is_primary", BooleanType(), required=False),
            NestedField(5, "relatedness_tier", StringType(), required=False),
            NestedField(6, "ingested_at", TimestampType(), required=False),
            NestedField(7, "source_url", StringType(), required=False),
            NestedField(8, "source_method", StringType(), required=False),
            NestedField(9, "load_date", DateType(), required=False),
        ),
    }
    return schemas[table_name]


def register_shadow_table(table_name, parquet_path):
    """Register a shadow table in the Iceberg catalog."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import WAREHOUSE_PATH, CATALOG_PATH

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    shadow_ns = "shadow_raw"

    try:
        catalog.create_namespace(shadow_ns)
    except Exception:
        pass

    shadow_id = f"{shadow_ns}.{table_name}"
    try:
        catalog.drop_table(shadow_id)
    except Exception:
        pass

    iceberg_schema = get_iceberg_schema(table_name)
    shadow_table = catalog.create_table(shadow_id, schema=iceberg_schema)

    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def cleanup_shadow_tables():
    """Remove all shadow O*NET tables."""
    import shutil
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import WAREHOUSE_PATH, CATALOG_PATH

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    for tbl in ONET_TABLES:
        shadow_dir = WAREHOUSE / "shadow_raw" / tbl
        if shadow_dir.exists():
            shutil.rmtree(shadow_dir)
        try:
            catalog.drop_table(f"shadow_raw.{tbl}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# DQ execution
# ---------------------------------------------------------------------------

def run_dq_rules_shadow():
    """Run DQ rules against shadow tables."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
    result = run_rules(spec="raw-ingest-onet", catalog=catalog, shadow=True)
    return result


# ---------------------------------------------------------------------------
# Main cycle runner
# ---------------------------------------------------------------------------

def run_cycle(cycle_num, rate, seed):
    """Run one hardening cycle across all 5 O*NET tables."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)
    all_manifest = []
    table_stats = {}

    for table_name in ONET_TABLES:
        print(f"\n  Loading {table_name}...")
        rows = load_table_data(table_name)
        original_count = len(rows)
        print(f"    Loaded {original_count} rows")

        # Corrupt
        corrupt_fn = CORRUPT_FUNCTIONS[table_name]
        try:
            entries = corrupt_fn(rows, rate, rng)
            all_manifest.extend(entries)
            print(f"    Corrupted: {len(entries)} mutations, {len(rows)} final rows")
        except Exception as e:
            print(f"    ERROR corrupting {table_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

        # Write shadow parquet
        shadow_dir = WAREHOUSE / "shadow_raw" / table_name / "data"
        shadow_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = shadow_dir / f"chaos-cycle-{cycle_num}.parquet"

        try:
            arrow_fn = ARROW_CONVERTERS[table_name]
            arrow_table = arrow_fn(rows)
            pq.write_table(arrow_table, str(parquet_path))

            # Register in catalog
            register_shadow_table(table_name, parquet_path)
            print(f"    Registered as shadow_raw.{table_name}")
        except Exception as e:
            print(f"    ERROR writing shadow table {table_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

        table_stats[table_name] = {
            "original_rows": original_count,
            "corrupted_rows": len(rows),
            "corruptions": len(entries),
        }

    # Run DQ rules
    print(f"\n  Running DQ rules against shadow tables...")
    try:
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(f"  Total: {dq_result['rules_total']} | Passed: {dq_result['rules_passed']} | Failed: {dq_result['rules_failed']}")
        print(f"  P0 gate: {'PASS' if dq_result['p0_passed'] else 'FAIL'}")

        print(f"\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            print(f"    {r['rule_id']:<25} {status:<6} value={r.get('raw_value', '?')}")

    except Exception as e:
        print(f"  ERROR running DQ rules: {e}")
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
        "table_stats": table_stats,
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
        "errored_rules": [{"rule_id": r["rule_id"], "error": r.get("error", "")} for r in errored_rules],
        "injected_dimensions": sorted(dims.keys()),
        "corruptions_per_dimension": {dim: len(entries) for dim, entries in dims.items()},
        "detection_rate": round(detection_rate, 3),
        "rules_fired": len(failed_rules),
        "rules_silent": len(passed_rules),
        "rules_errored": len(errored_rules),
        "total_rules": total_rules,
    }


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
            "table_stats": cycle_result["table_stats"],
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
        if gap_analysis["errored_rules"]:
            print(f"    Rules errored: {[r['rule_id'] for r in gap_analysis['errored_rules']]}")

        if consecutive_no_new_gaps >= 2:
            print(f"\n  Stability detected: same rules firing for 2 consecutive cycles.")

        # Cleanup between cycles
        cleanup_shadow_tables()

    # Final cleanup
    cleanup_shadow_tables()

    # Output JSON manifest
    manifest_data = {
        "spec": "raw-ingest-onet",
        "tables": [f"raw.{t}" for t in ONET_TABLES],
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/raw-ingest-onet-manifest.json"
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
            f"fired: {[r['rule_id'] for r in ga['failed_rules']]}"
        )
