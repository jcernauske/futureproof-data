"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner + Targeted Probes
Spec:  full-pipeline-eada (§5 base zone, Option-C amendment 2026-04-30)
Table: base.eada (2,040 rows, 17 cols, snapshot 973879610917339278)
Shadow namespace: shadow_base.eada (in the SILVER warehouse)

Information barrier: This script does NOT read
  - governance/dq-rules/base-eada.json   (rule definitions)
  - governance/dq-results/*              (prior DQ run outputs)
  - governance/dq-scorecards/*           (scorecards)
  - tests/                               (pipeline tests)
  - source of brightsmith.infra.dq_runner / dq_scorecard

Corruption choices are based solely on:
  - docs/specs/full-pipeline-eada.md     (public spec, §5 base zone schema/transformations)
  - src/silver/eada_base.py              (silver transformer code)

Targeted probes (T1-T7) extend the standard 5-dimension cycle pack to
exercise the §5-amendment-added rules (BSE-EAD-007, 009, 011, 012, 013)
plus the recalibrated arithmetic invariant (BSE-EAD-008). The user-specified
probe matrix is enumerated in run_targeted_probes().

Restoration: in-memory only. Pre/post real-parquet MD5 verified by main().
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SILVER_WAREHOUSE = PROJECT_ROOT / "data" / "silver" / "iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "catalog.db"

# Real data (read-only — restoration verifier)
BASE_EADA_PARQUET = (
    SILVER_WAREHOUSE
    / "base"
    / "eada"
    / "data"
    / "00000-0-2ac2793b-662b-4c30-a452-b6d2a2371d48.parquet"
)
EXPECTED_PRE_MD5 = "e948df41570fa5461d64e0f089febfc1"

SHADOW_BASE_DIR = SILVER_WAREHOUSE / "shadow_base" / "eada"
SHADOW_BASE_DATA_DIR = SHADOW_BASE_DIR / "data"
SHADOW_BASE_META_DIR = SHADOW_BASE_DIR / "metadata"

# Cross-source companion table for BSE-EAD-013 (IPEDS-preference invariant)
SHADOW_IPEDS_DIR = SILVER_WAREHOUSE / "shadow_base" / "ipeds_finance"
# BSE-EAD-001 conservation rule (base vs bronze row count) needs shadow_bronze.eada
SHADOW_BRONZE_DIR = (
    PROJECT_ROOT / "data" / "bronze" / "iceberg_warehouse" / "shadow_bronze" / "eada"
)

SPEC_NAME = "full-pipeline-eada"
SHADOW_FQN_BASE = "shadow_base.eada"
SHADOW_FQN_IPEDS = "shadow_base.ipeds_finance"
SHADOW_FQN_BRONZE = "shadow_bronze.eada"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42

sys.path.insert(0, str(PROJECT_ROOT / "src"))


# ---------------------------------------------------------------------------
# Three-layer kill switch
# ---------------------------------------------------------------------------

def safety_check() -> None:
    os.environ["CHAOS_MONKEY_ENABLED"] = "true"
    os.environ["BRIGHTSMITH_ENV"] = "dev"
    if os.environ["CHAOS_MONKEY_ENABLED"].lower() != "true":
        print("ERROR: CHAOS_MONKEY_ENABLED is not 'true'.")
        sys.exit(1)
    if os.environ["BRIGHTSMITH_ENV"].lower() != "dev":
        print("ERROR: BRIGHTSMITH_ENV is not 'dev'.")
        sys.exit(1)
    if not BASE_EADA_PARQUET.exists():
        print(f"ERROR: source parquet missing: {BASE_EADA_PARQUET}")
        sys.exit(1)
    md5_now = file_md5(BASE_EADA_PARQUET)
    if md5_now != EXPECTED_PRE_MD5:
        print(f"WARN: source parquet MD5 drifted: {md5_now} vs expected {EXPECTED_PRE_MD5}")
    print(f"Safety: kill-switch ARMED, source MD5={md5_now}")


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_source_rows():
    import pyarrow.parquet as pq

    t = pq.read_table(str(BASE_EADA_PARQUET))
    rows = [dict(r) for r in t.to_pylist()]
    return rows, t.schema


def rows_to_arrow(rows, schema):
    import pyarrow as pa

    arrays = {}
    for field in schema:
        col = field.name
        values = [r.get(col) for r in rows]
        try:
            arrays[col] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError, pa.ArrowNotImplementedError):
            arrays[col] = pa.array(values)
    return pa.table(arrays)


def write_shadow_parquet(arrow_table, label: str):
    import pyarrow.parquet as pq

    SHADOW_BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    SHADOW_BASE_META_DIR.mkdir(parents=True, exist_ok=True)
    out = SHADOW_BASE_DATA_DIR / f"chaos-{label}.parquet"
    pq.write_table(arrow_table, str(out))
    return out


def _base_eada_iceberg_schema():
    """Iceberg schema for shadow_base.eada — all fields nullable for chaos."""
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType,
        DateType,
        DoubleType,
        IntegerType,
        LongType,
        NestedField,
        StringType,
        TimestampType,
    )

    return Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "unitid", LongType(), required=False),
        NestedField(3, "institution_name", StringType(), required=False),
        NestedField(4, "reporting_year", IntegerType(), required=False),
        NestedField(5, "total_athletic_expenses", DoubleType(), required=False),
        NestedField(6, "total_athletic_revenue", DoubleType(), required=False),
        NestedField(7, "recruiting_expenses", DoubleType(), required=False),
        NestedField(8, "eada_fte_headcount", DoubleType(), required=False),
        NestedField(9, "total_fte_enrollment", DoubleType(), required=False),
        NestedField(10, "fte_source", StringType(), required=False),
        NestedField(11, "has_ipeds_finance_fte", BooleanType(), required=False),
        NestedField(12, "has_eada_fte", BooleanType(), required=False),
        NestedField(13, "athletic_spend_per_fte", DoubleType(), required=False),
        NestedField(14, "athletic_revenue_per_fte", DoubleType(), required=False),
        NestedField(15, "recruiting_per_fte", DoubleType(), required=False),
        NestedField(16, "athletic_subsidy_ratio", DoubleType(), required=False),
        NestedField(17, "source_load_date", DateType(), required=False),
        NestedField(18, "ingested_at", TimestampType(), required=False),
    )


def register_shadow_base(parquet_path):
    """Register shadow_base.eada in the silver-warehouse catalog."""
    from brightsmith.infra.iceberg_setup import get_catalog
    import pyarrow.parquet as pq

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
    try:
        catalog.create_namespace("shadow_base")
    except Exception:
        pass
    try:
        catalog.drop_table(SHADOW_FQN_BASE)
    except Exception:
        pass
    schema = _base_eada_iceberg_schema()
    tbl = catalog.create_table(SHADOW_FQN_BASE, schema=schema)
    data = pq.read_table(str(parquet_path))
    tbl.append(data)
    return tbl


def register_shadow_ipeds(clean_only: bool = True):
    """Register shadow_base.ipeds_finance — clean copy of real base.ipeds_finance.

    BSE-EAD-013 (IPEDS-preference invariant) joins base.eada → base.ipeds_finance
    on UNITID. In shadow mode the runner remaps both refs; this call stages a
    pristine copy of the real ipeds_finance so the JOIN finds rows.
    """
    from brightsmith.infra.iceberg_setup import get_catalog
    import pyarrow.parquet as pq
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType,
        DoubleType,
        IntegerType,
        LongType,
        NestedField,
        StringType,
        TimestampType,
    )

    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))

    # Source the real base.ipeds_finance parquet — read-only.
    real_tbl = catalog.load_table("base.ipeds_finance")
    real_meta = real_tbl.metadata_location

    # Read the real Iceberg table via DuckDB and dump to a local parquet.
    import duckdb

    con = duckdb.connect()
    con.install_extension("iceberg")
    con.load_extension("iceberg")
    df = con.execute(
        f"SELECT * FROM iceberg_scan('{real_meta}')"
    ).fetch_arrow_table()
    con.close()

    SHADOW_IPEDS_DIR.mkdir(parents=True, exist_ok=True)
    (SHADOW_IPEDS_DIR / "data").mkdir(parents=True, exist_ok=True)
    (SHADOW_IPEDS_DIR / "metadata").mkdir(parents=True, exist_ok=True)
    ipeds_parquet = SHADOW_IPEDS_DIR / "data" / "shadow-clean.parquet"
    import pyarrow.parquet as pq

    pq.write_table(df, str(ipeds_parquet))

    try:
        catalog.drop_table(SHADOW_FQN_IPEDS)
    except Exception:
        pass

    # Build matching schema: types align with real base.ipeds_finance.
    schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "unitid", LongType(), required=False),
        NestedField(3, "institution_name", StringType(), required=False),
        NestedField(4, "report_form", StringType(), required=False),
        NestedField(5, "fiscal_year", IntegerType(), required=False),
        NestedField(6, "institutional_support_expenses", DoubleType(), required=False),
        NestedField(7, "instruction_expenses", DoubleType(), required=False),
        NestedField(8, "endowment_value", DoubleType(), required=False),
        NestedField(9, "total_fte_enrollment", DoubleType(), required=False),
        NestedField(10, "institutional_support_per_fte", DoubleType(), required=False),
        NestedField(11, "instruction_per_fte", DoubleType(), required=False),
        NestedField(12, "endowment_per_fte", DoubleType(), required=False),
        NestedField(13, "marketing_ratio", DoubleType(), required=False),
        NestedField(14, "source_load_date", DateType(), required=False),
        NestedField(15, "ingested_at", TimestampType(), required=False),
    )
    tbl = catalog.create_table(SHADOW_FQN_IPEDS, schema=schema)
    tbl.append(pq.read_table(str(ipeds_parquet)))
    return tbl


def register_shadow_bronze_eada():
    """Stage a pristine shadow_bronze.eada so BSE-EAD-001 conservation rule runs."""
    from brightsmith.infra.iceberg_setup import get_catalog
    import duckdb
    import pyarrow.parquet as pq
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType,
        DoubleType,
        IntegerType,
        LongType,
        NestedField,
        StringType,
        TimestampType,
    )

    # bronze warehouse uses the bronze warehouse path
    BRONZE_WAREHOUSE = PROJECT_ROOT / "data" / "bronze" / "iceberg_warehouse"
    catalog = get_catalog(str(BRONZE_WAREHOUSE), str(CATALOG_PATH))
    real_tbl = catalog.load_table("bronze.eada")
    real_meta = real_tbl.metadata_location

    con = duckdb.connect()
    con.install_extension("iceberg")
    con.load_extension("iceberg")
    df = con.execute(f"SELECT * FROM iceberg_scan('{real_meta}')").fetch_arrow_table()
    con.close()

    SHADOW_BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    (SHADOW_BRONZE_DIR / "data").mkdir(parents=True, exist_ok=True)
    (SHADOW_BRONZE_DIR / "metadata").mkdir(parents=True, exist_ok=True)
    out = SHADOW_BRONZE_DIR / "data" / "shadow-clean.parquet"
    pq.write_table(df, str(out))

    try:
        catalog.create_namespace("shadow_bronze")
    except Exception:
        pass
    try:
        catalog.drop_table(SHADOW_FQN_BRONZE)
    except Exception:
        pass

    schema = Schema(
        NestedField(1, "unitid", LongType(), required=False),
        NestedField(2, "institution_name", StringType(), required=False),
        NestedField(3, "reporting_year", IntegerType(), required=False),
        NestedField(4, "total_athletic_expenses", DoubleType(), required=False),
        NestedField(5, "total_athletic_revenue", DoubleType(), required=False),
        NestedField(6, "recruiting_expenses", DoubleType(), required=False),
        NestedField(7, "eada_fte_headcount", DoubleType(), required=False),
        NestedField(8, "source_url", StringType(), required=False),
        NestedField(9, "source_method", StringType(), required=False),
        NestedField(10, "ingested_at", TimestampType(), required=False),
        NestedField(11, "load_date", DateType(), required=False),
    )
    tbl = catalog.create_table(SHADOW_FQN_BRONZE, schema=schema)
    tbl.append(pq.read_table(str(out)))
    return tbl


def run_dq_rules_shadow():
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    # Use the silver warehouse catalog (also resolves shadow_bronze ns
    # because both share the same SQLite catalog file).
    catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
    return run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)


def cleanup_shadow():
    if SHADOW_BASE_DIR.exists():
        shutil.rmtree(SHADOW_BASE_DIR)
    if SHADOW_IPEDS_DIR.exists():
        shutil.rmtree(SHADOW_IPEDS_DIR)
    if SHADOW_BRONZE_DIR.exists():
        shutil.rmtree(SHADOW_BRONZE_DIR)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog

        catalog = get_catalog(str(SILVER_WAREHOUSE), str(CATALOG_PATH))
        for fqn in (SHADOW_FQN_BASE, SHADOW_FQN_IPEDS, SHADOW_FQN_BRONZE):
            try:
                catalog.drop_table(fqn)
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Standard 10-dimension corruption strategies (one per DQ dimension)
# ---------------------------------------------------------------------------

def corrupt_completeness(rows, indices, rng):
    """Null required fields per spec §5: record_id, unitid, institution_name,
    reporting_year, fte_source, has_ipeds_finance_fte, has_eada_fte."""
    manifest = []
    targets = rng.sample(indices, min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(
            ["record_id", "unitid", "institution_name", "reporting_year",
             "fte_source", "has_ipeds_finance_fte", "has_eada_fte"]
        )
        old = rows[i][field]
        rows[i][field] = None
        manifest.append({"row": i, "dimension": "completeness", "field": field,
                         "strategy": f"null_{field}", "old_value": str(old), "new_value": "null"})
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid values: bad fte_source enum, negative per-FTE columns."""
    manifest = []
    targets = rng.sample(indices, min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_fte_source", "negative_spend_per_fte",
            "negative_revenue_per_fte", "negative_recruiting_per_fte",
        ])
        if strategy == "bad_fte_source":
            old = rows[i].get("fte_source")
            rows[i]["fte_source"] = rng.choice(["IPEDS", "ipeds", "fallback", "unknown", ""])
            manifest.append({"row": i, "dimension": "validity", "field": "fte_source",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": rows[i]["fte_source"]})
        elif strategy == "negative_spend_per_fte":
            old = rows[i].get("athletic_spend_per_fte")
            rows[i]["athletic_spend_per_fte"] = -float(rng.randint(1, 50000))
            manifest.append({"row": i, "dimension": "validity", "field": "athletic_spend_per_fte",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["athletic_spend_per_fte"])})
        elif strategy == "negative_revenue_per_fte":
            old = rows[i].get("athletic_revenue_per_fte")
            rows[i]["athletic_revenue_per_fte"] = -float(rng.randint(1, 50000))
            manifest.append({"row": i, "dimension": "validity", "field": "athletic_revenue_per_fte",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["athletic_revenue_per_fte"])})
        elif strategy == "negative_recruiting_per_fte":
            old = rows[i].get("recruiting_per_fte")
            rows[i]["recruiting_per_fte"] = -float(rng.randint(1, 5000))
            manifest.append({"row": i, "dimension": "validity", "field": "recruiting_per_fte",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["recruiting_per_fte"])})
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Duplicate rows + duplicate unitid (the dedup grain)."""
    manifest = []
    n_dupes = max(1, len(indices) // 5)
    sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src in sources:
        dupe = copy.deepcopy(rows[src])
        rows.append(dupe)
        manifest.append({"row": len(rows) - 1, "dimension": "uniqueness", "field": "unitid+record_id",
                         "strategy": "duplicate_row", "old_value": f"copy_of_row_{src}",
                         "new_value": f"appended at {len(rows) - 1}"})
    return manifest


def corrupt_consistency(rows, indices, rng):
    """Tautology breaks + has_* booleans contradicting fte_source."""
    manifest = []
    targets = rng.sample(indices, min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "fte_source_none_with_value", "has_ipeds_lying", "has_eada_lying",
        ])
        if strategy == "fte_source_none_with_value":
            old = rows[i].get("fte_source")
            rows[i]["fte_source"] = "none"
            # Leave total_fte_enrollment non-null → tautology violation (BSE-EAD-012)
            manifest.append({"row": i, "dimension": "consistency", "field": "fte_source",
                             "strategy": strategy, "old_value": str(old), "new_value": "none"})
        elif strategy == "has_ipeds_lying":
            old = rows[i].get("has_ipeds_finance_fte")
            rows[i]["has_ipeds_finance_fte"] = not bool(old)
            manifest.append({"row": i, "dimension": "consistency", "field": "has_ipeds_finance_fte",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["has_ipeds_finance_fte"])})
        elif strategy == "has_eada_lying":
            old = rows[i].get("has_eada_fte")
            rows[i]["has_eada_fte"] = not bool(old)
            manifest.append({"row": i, "dimension": "consistency", "field": "has_eada_fte",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["has_eada_fte"])})
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible-but-wrong values: swap expense/revenue, scale per-FTE off."""
    manifest = []
    targets = rng.sample(indices, min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["swap_exp_rev", "scale_spend_per_fte"])
        if strategy == "swap_exp_rev":
            a = rows[i].get("total_athletic_expenses")
            b = rows[i].get("total_athletic_revenue")
            if a is not None and b is not None:
                rows[i]["total_athletic_expenses"], rows[i]["total_athletic_revenue"] = b, a
                manifest.append({"row": i, "dimension": "accuracy",
                                 "field": "total_athletic_expenses,total_athletic_revenue",
                                 "strategy": strategy, "old_value": f"exp={a},rev={b}",
                                 "new_value": f"exp={b},rev={a}"})
        elif strategy == "scale_spend_per_fte":
            old = rows[i].get("athletic_spend_per_fte")
            if old is not None:
                rows[i]["athletic_spend_per_fte"] = float(old) * 2.0
                manifest.append({"row": i, "dimension": "accuracy", "field": "athletic_spend_per_fte",
                                 "strategy": strategy, "old_value": str(old),
                                 "new_value": str(rows[i]["athletic_spend_per_fte"])})
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outliers: huge subsidy_ratio, astronomical spend_per_fte."""
    manifest = []
    targets = rng.sample(indices, min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_subsidy_ratio_high", "extreme_subsidy_ratio_low",
            "extreme_spend_per_fte",
        ])
        if strategy == "extreme_subsidy_ratio_high":
            old = rows[i].get("athletic_subsidy_ratio")
            rows[i]["athletic_subsidy_ratio"] = float(rng.uniform(2.0, 10.0))
            manifest.append({"row": i, "dimension": "reasonableness",
                             "field": "athletic_subsidy_ratio",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["athletic_subsidy_ratio"])})
        elif strategy == "extreme_subsidy_ratio_low":
            old = rows[i].get("athletic_subsidy_ratio")
            rows[i]["athletic_subsidy_ratio"] = float(rng.uniform(-50.0, -10.0))
            manifest.append({"row": i, "dimension": "reasonableness",
                             "field": "athletic_subsidy_ratio",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["athletic_subsidy_ratio"])})
        elif strategy == "extreme_spend_per_fte":
            old = rows[i].get("athletic_spend_per_fte")
            rows[i]["athletic_spend_per_fte"] = float(rng.randint(50_000_000, 500_000_000))
            manifest.append({"row": i, "dimension": "reasonableness",
                             "field": "athletic_spend_per_fte",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": str(rows[i]["athletic_spend_per_fte"])})
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps."""
    manifest = []
    targets = rng.sample(indices, min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2030, 1, 1)
            manifest.append({"row": i, "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": "2030-01-01"})
        elif strategy == "stale_load_date":
            old = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2010, 1, 1)
            manifest.append({"row": i, "dimension": "freshness", "field": "source_load_date",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": "2010-01-01"})
        elif strategy == "future_ingested_at":
            old = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(2030, 6, 15, 12, 0, 0)
            manifest.append({"row": i, "dimension": "freshness", "field": "ingested_at",
                             "strategy": strategy, "old_value": str(old),
                             "new_value": "2030-06-15T12:00:00"})
    return manifest


def corrupt_volume(rows, indices, rng):
    """Mass-duplicate to inflate row count."""
    n_extras = max(50, len(rows) // 10)
    sources = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    base_count = len(rows)
    for src in sources:
        rows.append(copy.deepcopy(rows[src]))
    return [{"row": -1, "dimension": "volume", "field": "row_count",
             "strategy": "mass_duplicate", "old_value": str(base_count),
             "new_value": str(len(rows))}]


def corrupt_referential_integrity(rows, indices, rng):
    """Orphan UNITIDs that don't exist in IPEDS/upstream."""
    manifest = []
    targets = rng.sample(indices, min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        old = rows[i].get("unitid")
        rows[i]["unitid"] = rng.randint(900_000_000, 999_999_999)
        manifest.append({"row": i, "dimension": "referential_integrity", "field": "unitid",
                         "strategy": "orphan_unitid", "old_value": str(old),
                         "new_value": str(rows[i]["unitid"])})
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Drop entire fte_source = 'eada_fte_headcount' stratum to skew distribution."""
    n_before = len(rows)
    keep = []
    dropped = 0
    target_drop = max(20, n_before // 20)  # drop ~5%
    for r in rows:
        if r.get("fte_source") == "eada_fte_headcount" and dropped < target_drop:
            dropped += 1
            continue
        keep.append(r)
    rows[:] = keep
    return [{"row": -1, "dimension": "coverage", "field": "fte_source_stratum",
             "strategy": "drop_eada_fte_headcount_subset",
             "old_value": f"{n_before} rows", "new_value": f"{len(rows)} rows ({dropped} dropped)"}]


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


# ---------------------------------------------------------------------------
# Targeted probes — the user-specified §5-amendment hardening matrix
# ---------------------------------------------------------------------------

def probe_T1_unitid_join_failure(rows):
    """T1: Force UNITID-type-mismatch on the IPEDS-Finance LEFT JOIN.

    Simulate the cross-source join silently failing for institutions that
    SHOULD resolve to ipeds_finance: flip 60 rows from fte_source='ipeds_finance'
    to fte_source='eada_fte_headcount' (keeping total_fte_enrollment populated
    from the EADA side). BSE-EAD-013 (IPEDS-preference invariant, P0) should
    catch every flipped row because their UNITID still has a non-null
    total_fte_enrollment in shadow_base.ipeds_finance.
    """
    entries = []
    flipped = 0
    target = 60
    for i, r in enumerate(rows):
        if flipped >= target:
            break
        if r.get("fte_source") == "ipeds_finance":
            old = r["fte_source"]
            r["fte_source"] = "eada_fte_headcount"
            entries.append({"row": i, "probe": "T1", "field": "fte_source",
                            "strategy": "force_unitid_join_failure", "old_value": old,
                            "new_value": "eada_fte_headcount", "unitid": r.get("unitid")})
            flipped += 1
    return entries, flipped


def probe_T2_eftotalcount_zero(rows):
    """T2: EFTotalCount == 0 edge case.

    Set eada_fte_headcount = 0 on rows that resolve to fte_source =
    'eada_fte_headcount'. Per §5 the per-FTE columns must be NULL when
    total_fte_enrollment <= 0. The fp-data-reviewer flagged this as a concern;
    we simulate the broken state where the transformer kept the fte_source
    stamp non-'none' even though FTE became 0 (i.e., FTE=0 but per-FTE column
    is non-null OR fte_source is non-'none' while transformer guard fired).
    For the chaos: set total_fte_enrollment=0 AND keep per-FTE columns
    non-null and fte_source='eada_fte_headcount'. BSE-EAD-008 (arithmetic
    invariant) should fire because spend_per_fte * 0 != expenses.
    """
    entries = []
    n = 0
    for i, r in enumerate(rows):
        if n >= 5:
            break
        if r.get("fte_source") == "eada_fte_headcount" and r.get("total_athletic_expenses"):
            old_fte = r.get("total_fte_enrollment")
            old_eada = r.get("eada_fte_headcount")
            r["total_fte_enrollment"] = 0.0
            r["eada_fte_headcount"] = 0.0
            entries.append({"row": i, "probe": "T2", "field": "total_fte_enrollment",
                            "strategy": "set_zero_keep_per_fte_non_null",
                            "old_value": f"fte={old_fte}, eada_fte={old_eada}",
                            "new_value": "fte=0, eada_fte=0",
                            "unitid": r.get("unitid")})
            n += 1
    return entries, n


def probe_T3_provenance_tautology_break(rows):
    """T3: Set total_fte_enrollment IS NULL while fte_source != 'none'.

    Pure provenance tautology violation. BSE-EAD-012 (P0) should fire on
    every such row.
    """
    entries = []
    n = 0
    for i, r in enumerate(rows):
        if n >= 8:
            break
        if r.get("total_fte_enrollment") is not None and r.get("fte_source") in ("ipeds_finance", "eada_fte_headcount"):
            old_fte = r.get("total_fte_enrollment")
            old_src = r.get("fte_source")
            r["total_fte_enrollment"] = None
            # leave fte_source unchanged → tautology break
            entries.append({"row": i, "probe": "T3", "field": "total_fte_enrollment",
                            "strategy": "null_fte_keep_source_non_none",
                            "old_value": f"fte={old_fte}, src={old_src}",
                            "new_value": f"fte=null, src={old_src}",
                            "unitid": r.get("unitid")})
            n += 1
    return entries, n


def probe_T4_distribution_drift(rows):
    """T4: Flip 200 rows from ipeds_finance → eada_fte_headcount.

    Shift the 73/27 distribution to ~63/37 — outside the ±5pp band.
    BSE-EAD-011 (P1) should fire on the distribution bound.
    """
    entries = []
    flipped = 0
    target = 200
    for i, r in enumerate(rows):
        if flipped >= target:
            break
        if r.get("fte_source") == "ipeds_finance":
            old = r["fte_source"]
            r["fte_source"] = "eada_fte_headcount"
            entries.append({"row": i, "probe": "T4", "field": "fte_source",
                            "strategy": "distribution_drift_flip",
                            "old_value": old, "new_value": "eada_fte_headcount"})
            flipped += 1
    return entries, flipped


def probe_T5_none_rate_spike(rows):
    """T5: Flip 50 rows to fte_source='none', null their FTE + per-FTE columns.

    50/2040 = 2.45% > 1% threshold. BSE-EAD-009 (P0) should fire.
    Note: also keeps the BSE-EAD-012 tautology consistent (FTE NULL ↔ source 'none').
    """
    entries = []
    flipped = 0
    target = 50
    for i, r in enumerate(rows):
        if flipped >= target:
            break
        if r.get("fte_source") in ("ipeds_finance", "eada_fte_headcount"):
            old_src = r["fte_source"]
            r["fte_source"] = "none"
            r["total_fte_enrollment"] = None
            r["athletic_spend_per_fte"] = None
            r["athletic_revenue_per_fte"] = None
            r["recruiting_per_fte"] = None
            entries.append({"row": i, "probe": "T5", "field": "fte_source",
                            "strategy": "none_rate_spike",
                            "old_value": old_src, "new_value": "none"})
            flipped += 1
    return entries, flipped


def probe_T6_subsidy_ratio_outlier(rows):
    """T6: Inject athletic_subsidy_ratio = -3.5 (just outside the [-3.0, 1.0] band).

    BSE-EAD-007 (P0) should fire on the recalibrated band. We pick the first
    eligible row (subsidy_ratio currently non-null).
    """
    entries = []
    for i, r in enumerate(rows):
        if r.get("athletic_subsidy_ratio") is not None:
            old = r.get("athletic_subsidy_ratio")
            r["athletic_subsidy_ratio"] = -3.5
            entries.append({"row": i, "probe": "T6", "field": "athletic_subsidy_ratio",
                            "strategy": "outside_recalibrated_band",
                            "old_value": str(old), "new_value": "-3.5",
                            "unitid": r.get("unitid")})
            return entries, 1
    return entries, 0


def probe_T7_arithmetic_invariant_break(rows):
    """T7: Set athletic_spend_per_fte=1.0, total_athletic_expenses=5_000_000,
    total_fte_enrollment=100. Off by ~5 orders of magnitude.

    BSE-EAD-008 (P0) should fire: |1.0 * 100 - 5_000_000| = 4_999_900 >> 1.0.
    """
    entries = []
    for i, r in enumerate(rows):
        if (r.get("athletic_spend_per_fte") is not None and
                r.get("total_fte_enrollment") is not None and
                r.get("total_athletic_expenses") is not None):
            old = (r.get("athletic_spend_per_fte"),
                   r.get("total_athletic_expenses"),
                   r.get("total_fte_enrollment"))
            r["athletic_spend_per_fte"] = 1.0
            r["total_athletic_expenses"] = 5_000_000.0
            r["total_fte_enrollment"] = 100.0
            entries.append({"row": i, "probe": "T7",
                            "field": "athletic_spend_per_fte,total_athletic_expenses,total_fte_enrollment",
                            "strategy": "break_arithmetic_invariant",
                            "old_value": str(old),
                            "new_value": "(1.0, 5000000, 100)",
                            "unitid": r.get("unitid")})
            return entries, 1
    return entries, 0


# ---------------------------------------------------------------------------
# Cycle / probe driver
# ---------------------------------------------------------------------------

def run_cycle(cycle_num: int, rate: float, seed: int):
    import random

    print(f"\n{'='*72}\nCYCLE {cycle_num} | rate={rate*100:.0f}% | seed={seed}\n{'='*72}")
    rng = random.Random(seed)
    rows, schema = load_source_rows()
    n0 = len(rows)
    n_corrupt = int(n0 * rate)
    per_fn = max(1, n_corrupt // len(CORRUPTION_FUNCTIONS))
    all_indices = list(range(n0))

    manifest = []
    for fn in CORRUPTION_FUNCTIONS:
        idx = rng.sample(all_indices, min(per_fn, len(all_indices)))
        try:
            entries = fn(rows, idx, rng)
            manifest.extend(entries)
            print(f"  {fn.__name__.replace('corrupt_',''):<22} {len(entries)} corruptions")
        except Exception as e:
            print(f"  ERROR in {fn.__name__}: {e}")
    print(f"  Total: {len(manifest)} corruptions, rows {n0} → {len(rows)}")

    arrow = rows_to_arrow(rows, schema)
    parquet = write_shadow_parquet(arrow, f"cycle-{cycle_num}")
    register_shadow_base(parquet)
    register_shadow_ipeds()
    register_shadow_bronze_eada()

    dq = run_dq_rules_shadow()
    print(f"  Run {dq['run_id']}: {dq['rules_passed']}/{dq['rules_total']} passed, "
          f"{dq['rules_failed']} failed, P0 gate={'PASS' if dq['p0_passed'] else 'FAIL'}")

    fired = [r for r in dq["results"] if not r["passed"] and not r.get("error")]
    errored = [r for r in dq["results"] if r.get("error")]
    silent = [r for r in dq["results"] if r["passed"]]
    return {
        "cycle": cycle_num, "rate": rate, "seed": seed,
        "row_count_in": n0, "row_count_out": len(rows),
        "manifest": manifest, "dq": dq,
        "fired_rule_ids": [r["rule_id"] for r in fired],
        "errored_rule_ids": [r["rule_id"] for r in errored],
        "silent_rule_ids": [r["rule_id"] for r in silent],
    }


def run_targeted_probe(probe_id: str, probe_fn, label: str):
    print(f"\n{'-'*72}\nPROBE {probe_id}: {label}\n{'-'*72}")
    rows, schema = load_source_rows()
    entries, n = probe_fn(rows)
    print(f"  Mutations: {n}")
    arrow = rows_to_arrow(rows, schema)
    parquet = write_shadow_parquet(arrow, f"probe-{probe_id}")
    register_shadow_base(parquet)
    register_shadow_ipeds()
    register_shadow_bronze_eada()
    dq = run_dq_rules_shadow()
    fired = [r for r in dq["results"] if not r["passed"] and not r.get("error")]
    errored = [r for r in dq["results"] if r.get("error")]
    print(f"  Run {dq['run_id']}: P0 gate={'PASS' if dq['p0_passed'] else 'FAIL'}")
    print(f"  Fired:   {[r['rule_id'] for r in fired]}")
    print(f"  Errored: {[r['rule_id'] for r in errored]}")
    return {
        "probe": probe_id, "label": label, "mutations": n,
        "manifest": entries, "dq": dq,
        "fired_rule_ids": [r["rule_id"] for r in fired],
        "errored_rule_ids": [r["rule_id"] for r in errored],
    }


def run_negative_control_noop():
    """Negative control: register clean shadow copy (zero mutations)."""
    print(f"\n{'-'*72}\nNEG CONTROL: noop\n{'-'*72}")
    rows, schema = load_source_rows()
    arrow = rows_to_arrow(rows, schema)
    parquet = write_shadow_parquet(arrow, "noop")
    register_shadow_base(parquet)
    register_shadow_ipeds()
    register_shadow_bronze_eada()
    dq = run_dq_rules_shadow()
    fired = [r for r in dq["results"] if not r["passed"] and not r.get("error")]
    errored = [r for r in dq["results"] if r.get("error")]
    print(f"  P0 gate={'PASS' if dq['p0_passed'] else 'FAIL'}")
    print(f"  Fired:   {[r['rule_id'] for r in fired]} (expected: empty)")
    print(f"  Errored: {[r['rule_id'] for r in errored]}")
    return {
        "probe": "NEG-NOOP", "label": "noop", "mutations": 0, "manifest": [],
        "dq": dq,
        "fired_rule_ids": [r["rule_id"] for r in fired],
        "errored_rule_ids": [r["rule_id"] for r in errored],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    safety_check()
    pre_md5 = file_md5(BASE_EADA_PARQUET)
    print(f"Pre-run MD5(base.eada parquet): {pre_md5}")

    all_results = {
        "spec": SPEC_NAME,
        "table": "base.eada",
        "snapshot_id": "973879610917339278",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pre_md5": pre_md5,
        "cycles": [],
        "targeted_probes": [],
        "negative_controls": [],
    }

    # Negative control first — verify no false positives on clean data
    cleanup_shadow()
    neg = run_negative_control_noop()
    all_results["negative_controls"].append(neg)
    cleanup_shadow()

    # 5-cycle escalating-rate sweep
    for i, rate in enumerate(RATES, 1):
        seed = SEED_BASE + i
        cycle = run_cycle(i, rate, seed)
        all_results["cycles"].append(cycle)
        cleanup_shadow()

    # Targeted probe pack
    probes = [
        ("T1", probe_T1_unitid_join_failure,
         "Forced UNITID-type-mismatch on IPEDS-Finance LEFT JOIN (60 rows)"),
        ("T2", probe_T2_eftotalcount_zero,
         "EFTotalCount = 0 edge case (5 rows)"),
        ("T3", probe_T3_provenance_tautology_break,
         "FTE NULL while fte_source != 'none' (8 rows)"),
        ("T4", probe_T4_distribution_drift,
         "Flip 200 rows ipeds_finance → eada_fte_headcount (drift to 63/37)"),
        ("T5", probe_T5_none_rate_spike,
         "Flip 50 rows to fte_source='none' (2.45% > 1% threshold)"),
        ("T6", probe_T6_subsidy_ratio_outlier,
         "athletic_subsidy_ratio = -3.5 (outside [-3.0, 1.0])"),
        ("T7", probe_T7_arithmetic_invariant_break,
         "spend_per_fte=1.0 vs expenses=5M, fte=100 (off by 5 orders of magnitude)"),
    ]
    for pid, fn, label in probes:
        result = run_targeted_probe(pid, fn, label)
        all_results["targeted_probes"].append(result)
        cleanup_shadow()

    # Final restoration check
    post_md5 = file_md5(BASE_EADA_PARQUET)
    all_results["post_md5"] = post_md5
    all_results["restoration_ok"] = (pre_md5 == post_md5)
    print(f"\nPost-run MD5(base.eada parquet): {post_md5}")
    print(f"Restoration OK: {pre_md5 == post_md5}")

    out = PROJECT_ROOT / "governance" / "chaos-manifests" / "base-eada-manifest.json"
    out.write_text(json.dumps(all_results, indent=2, default=str) + "\n")
    print(f"\nManifest: {out}")
    return all_results


if __name__ == "__main__":
    try:
        result = main()
    finally:
        cleanup_shadow()

    print(f"\n{'='*72}\nSUMMARY\n{'='*72}")
    print(f"Negative control fired: {result['negative_controls'][0]['fired_rule_ids']} (expect empty)")
    for c in result["cycles"]:
        print(f"Cycle {c['cycle']} ({int(c['rate']*100):>2}%): {len(c['fired_rule_ids']):>2} fired "
              f"{c['fired_rule_ids']}")
    for p in result["targeted_probes"]:
        print(f"Probe {p['probe']:<3} fired: {p['fired_rule_ids']}")
    print(f"Restoration OK: {result['restoration_ok']}")
