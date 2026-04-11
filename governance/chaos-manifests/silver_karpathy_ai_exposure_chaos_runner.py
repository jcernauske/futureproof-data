"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: silver-base-karpathy-ai-exposure
Table: base.karpathy_ai_exposure (419 rows)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.

INFORMATION BARRIER: This file was written WITHOUT reading DQ rule definitions.
Corruption strategies are derived from schema introspection and domain knowledge only.

Silver schema (from transformer):
  record_id       StringType   required
  soc_code        StringType   optional
  slug            StringType   required
  occupation_title StringType  required
  category        StringType   required
  exposure_score  IntegerType  required
  rationale       StringType   required
  bls_match       BooleanType  required
  soc_resolved_method StringType required
  source_load_date DateType    required
  ingested_at     TimestampType required

Grain: soc_code (for non-null), slug (for null soc_code)
soc_resolved_method enum: {direct, title_match, broad_expansion, unresolved}
exposure_score range: 1-10
bls_match: True when soc_code found in BLS OOH
25 categories observed
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
DATA_FILE = (
    PROJECT_ROOT
    / "data/silver/iceberg_warehouse/base/karpathy_ai_exposure/data"
    / "00000-0-f9bb019e-93d4-42ec-a73e-42b7ca73cb96.parquet"
)
SHADOW_DIR = (
    PROJECT_ROOT
    / "data/silver/iceberg_warehouse/shadow_base/karpathy_ai_exposure"
)
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 77  # Different from raw-zone seed to avoid correlation

sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Valid categories from the real data
VALID_CATEGORIES = [
    "management", "computer-and-information-technology",
    "farming-fishing-and-forestry", "architecture-and-engineering",
    "building-and-grounds-cleaning", "life-physical-and-social-science",
    "sales", "healthcare", "construction-and-extraction", "military",
    "legal", "personal-care-and-service", "protective-service", "math",
    "transportation-and-material-moving", "office-and-administrative-support",
    "food-preparation-and-serving", "community-and-social-service",
    "media-and-communication", "arts-and-design",
    "installation-maintenance-and-repair", "business-and-financial",
    "education-training-and-library", "entertainment-and-sports", "production",
]

VALID_SOC_METHODS = ["direct", "title_match", "broad_expansion", "unresolved"]


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
    """Null out required fields: record_id, slug, occupation_title, rationale,
    category, soc_resolved_method, exposure_score."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice([
            "record_id", "slug", "occupation_title", "rationale",
            "category", "soc_resolved_method", "exposure_score",
        ])
        old_val = rows[i][field]
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null",
        })
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid values targeting Silver-specific fields:
    - soc_resolved_method enum violations
    - SOC code format violations (not XX-XXXX)
    - exposure_score out of [1,10] range
    - Empty string in required fields
    - Invalid category values
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_soc_resolved_method", "bad_soc_format", "exposure_out_of_range",
            "empty_string_slug", "bad_exposure_negative", "bad_exposure_zero",
            "bad_soc_summary_code", "bad_record_id_format",
            "invalid_category", "unicode_garbage_rationale",
        ])
        if strategy == "bad_soc_resolved_method":
            old_val = rows[i]["soc_resolved_method"]
            rows[i]["soc_resolved_method"] = rng.choice([
                "manual", "fuzzy_match", "ai_inferred", "DIRECT", "Direct",
                "unknown", "", "null", "auto", "crosswalk",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_resolved_method",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_resolved_method"],
            })
        elif strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice([
                "151252", "15.1252", "XX-XXXX", "15-12520", "1-1252",
                "abc", "00-0000", "99-99999", "1234", " 15-1252",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
            })
        elif strategy == "exposure_out_of_range":
            old_val = rows[i]["exposure_score"]
            rows[i]["exposure_score"] = rng.choice([11, 15, 99, 100, 999, 50])
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
            rows[i]["exposure_score"] = rng.choice([-1, -5, -10])
            manifest.append({
                "row": i, "dimension": "validity", "field": "exposure_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["exposure_score"]),
            })
        elif strategy == "bad_exposure_zero":
            old_val = rows[i]["exposure_score"]
            rows[i]["exposure_score"] = 0
            manifest.append({
                "row": i, "dimension": "validity", "field": "exposure_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "0",
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
        elif strategy == "bad_record_id_format":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = rng.choice([
                "BADPREFIX-abc123", "12345", "", "kai_missing_hash",
                "xxx-" + "a" * 20,
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "record_id",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["record_id"],
            })
        elif strategy == "invalid_category":
            old_val = rows[i]["category"]
            rows[i]["category"] = rng.choice([
                "INVALID_CATEGORY", "zzzz-nonexistent", "123numeric",
                "Healthcare", "MANAGEMENT", "arts & design",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "category",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["category"],
            })
        elif strategy == "unicode_garbage_rationale":
            old_val = rows[i]["rationale"]
            garbage = "".join(chr(rng.randint(0x4E00, 0x9FFF)) for _ in range(10))
            rows[i]["rationale"] = garbage
            manifest.append({
                "row": i, "dimension": "validity", "field": "rationale",
                "strategy": strategy, "old_value": str(old_val)[:50] + "...",
                "new_value": garbage,
            })
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Inject duplicate rows: exact duplicates (same record_id) and
    near-duplicates (same soc_code, different values)."""
    manifest = []
    # Exact duplicates
    n_dupes = max(2, len(indices) // 4)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "record_id",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx} (record_id={rows[src_idx]['record_id']})",
            "new_value": f"exact_duplicate at position {insert_pos}",
        })

    # Near-duplicates: same soc_code but slightly different values
    n_near = max(1, len(indices) // 5)
    near_sources = rng.sample(range(min(len(rows), 419)), min(n_near, 419))
    for src_idx in near_sources:
        dupe = copy.deepcopy(rows[src_idx])
        # Change exposure_score slightly but keep same soc_code
        dupe["exposure_score"] = max(1, min(10, dupe["exposure_score"] + rng.choice([-1, 1])))
        dupe["rationale"] = dupe["rationale"] + " (modified)"
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "soc_code",
            "strategy": "near_duplicate_soc",
            "old_value": f"copy_of_row_{src_idx} (soc_code={rows[src_idx].get('soc_code')})",
            "new_value": f"near_duplicate at position {insert_pos}",
        })

    return manifest


def corrupt_consistency(rows, indices, rng):
    """Contradictory field combinations specific to Silver zone:
    - bls_match=True but soc_code is None
    - bls_match=True but soc_resolved_method='unresolved'
    - soc_resolved_method='direct' but soc_code is None
    - soc_resolved_method='unresolved' but bls_match=True
    - bls_match=False but soc_resolved_method='broad_expansion'
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 2)))
    for i in targets:
        strategy = rng.choice([
            "bls_match_true_null_soc",
            "bls_match_true_unresolved",
            "direct_method_null_soc",
            "unresolved_bls_true",
            "broad_expansion_bls_false",
            "title_match_bls_false",
        ])
        if strategy == "bls_match_true_null_soc":
            old_bls = rows[i]["bls_match"]
            old_soc = rows[i]["soc_code"]
            rows[i]["bls_match"] = True
            rows[i]["soc_code"] = None
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "bls_match,soc_code",
                "strategy": strategy,
                "old_value": f"bls_match={old_bls},soc_code={old_soc}",
                "new_value": "bls_match=True,soc_code=None",
            })
        elif strategy == "bls_match_true_unresolved":
            old_bls = rows[i]["bls_match"]
            old_method = rows[i]["soc_resolved_method"]
            rows[i]["bls_match"] = True
            rows[i]["soc_resolved_method"] = "unresolved"
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "bls_match,soc_resolved_method",
                "strategy": strategy,
                "old_value": f"bls_match={old_bls},method={old_method}",
                "new_value": "bls_match=True,method=unresolved",
            })
        elif strategy == "direct_method_null_soc":
            old_method = rows[i]["soc_resolved_method"]
            old_soc = rows[i]["soc_code"]
            rows[i]["soc_resolved_method"] = "direct"
            rows[i]["soc_code"] = None
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "soc_resolved_method,soc_code",
                "strategy": strategy,
                "old_value": f"method={old_method},soc_code={old_soc}",
                "new_value": "method=direct,soc_code=None",
            })
        elif strategy == "unresolved_bls_true":
            old_method = rows[i]["soc_resolved_method"]
            old_bls = rows[i]["bls_match"]
            rows[i]["soc_resolved_method"] = "unresolved"
            rows[i]["bls_match"] = True
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "soc_resolved_method,bls_match",
                "strategy": strategy,
                "old_value": f"method={old_method},bls_match={old_bls}",
                "new_value": "method=unresolved,bls_match=True",
            })
        elif strategy == "broad_expansion_bls_false":
            old_method = rows[i]["soc_resolved_method"]
            old_bls = rows[i]["bls_match"]
            rows[i]["soc_resolved_method"] = "broad_expansion"
            rows[i]["bls_match"] = False
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "soc_resolved_method,bls_match",
                "strategy": strategy,
                "old_value": f"method={old_method},bls_match={old_bls}",
                "new_value": "method=broad_expansion,bls_match=False",
            })
        elif strategy == "title_match_bls_false":
            old_method = rows[i]["soc_resolved_method"]
            old_bls = rows[i]["bls_match"]
            rows[i]["soc_resolved_method"] = "title_match"
            rows[i]["bls_match"] = False
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "soc_resolved_method,bls_match",
                "strategy": strategy,
                "old_value": f"method={old_method},bls_match={old_bls}",
                "new_value": "method=title_match,bls_match=False",
            })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values:
    - Wrong SOC major group prefix (valid format, wrong occupation)
    - Slightly-off exposure scores (in range but wrong)
    - record_id that doesn't match grain hash
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "wrong_soc_prefix", "plausible_wrong_score",
            "record_id_hash_mismatch",
        ])
        if strategy == "wrong_soc_prefix":
            old_val = rows[i]["soc_code"]
            if old_val and len(old_val) >= 7:
                new_prefix = rng.choice(["11", "13", "15", "17", "19", "21", "23", "25", "27"])
                rows[i]["soc_code"] = new_prefix + old_val[2:]
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "soc_code",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": rows[i]["soc_code"],
                })
        elif strategy == "plausible_wrong_score":
            old_val = rows[i]["exposure_score"]
            delta = rng.choice([-4, -3, 3, 4, 5])
            new_val = max(1, min(10, old_val + delta))
            if new_val != old_val:
                rows[i]["exposure_score"] = new_val
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "exposure_score",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(new_val),
                })
        elif strategy == "record_id_hash_mismatch":
            old_val = rows[i]["record_id"]
            # Keep the kai- prefix but use a random hash
            rows[i]["record_id"] = f"kai-{rng.randint(1000000000000000, 9999999999999999):016x}"
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "record_id",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["record_id"],
            })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values for the Silver zone:
    - Short rationale (< 50 chars when typical is 297-587)
    - Extremely long rationale (> 2000 chars)
    - exposure_score at boundaries with mismatched rationale tone
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "short_rationale", "very_short_rationale",
            "extremely_long_rationale",
        ])
        if strategy == "short_rationale":
            old_val = rows[i]["rationale"]
            rows[i]["rationale"] = "AI will affect this job."
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "rationale",
                "strategy": strategy,
                "old_value": f"len={len(old_val)}: {old_val[:40]}...",
                "new_value": f"len=25: {rows[i]['rationale']}",
            })
        elif strategy == "very_short_rationale":
            old_val = rows[i]["rationale"]
            rows[i]["rationale"] = "Yes."
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "rationale",
                "strategy": strategy,
                "old_value": f"len={len(old_val)}: {old_val[:40]}...",
                "new_value": f"len=4: {rows[i]['rationale']}",
            })
        elif strategy == "extremely_long_rationale":
            old_val = rows[i]["rationale"]
            rows[i]["rationale"] = "This is a very detailed analysis. " * 200
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "rationale",
                "strategy": strategy,
                "old_value": f"len={len(old_val)}",
                "new_value": f"len={len(rows[i]['rationale'])}",
            })
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps for Silver-specific date fields."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "future_load_date", "stale_load_date",
            "future_ingested_at", "epoch_ingested_at",
        ])
        if strategy == "future_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2030, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-01-01",
            })
        elif strategy == "stale_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2020, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2020-01-01",
            })
        elif strategy == "future_ingested_at":
            old_val = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(2030, 6, 15, 12, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "ingested_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-06-15T12:00:00",
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
    """Row count anomalies: mass-duplicate to inflate count.
    Original is 419 rows -- add ~100 to push way above threshold."""
    manifest = []
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
    """Orphan SOC codes: valid XX-XXXX format but codes that don't exist in BLS OOH.
    Also break record_id grain relationship."""
    manifest = []
    valid_indices = [i for i in indices if i < len(rows) and rows[i].get("soc_code")]
    if not valid_indices:
        return manifest
    targets = rng.sample(valid_indices, min(len(valid_indices), max(1, len(valid_indices) // 3)))
    for i in targets:
        old_val = rows[i]["soc_code"]
        # Use high SOC numbers that definitely don't exist in BLS
        fake_soc = f"{rng.randint(90, 99)}-{rng.randint(1000, 9999)}"
        rows[i]["soc_code"] = fake_soc
        # Also set bls_match=True to compound the problem
        rows[i]["bls_match"] = True
        manifest.append({
            "row": i, "dimension": "referential_integrity", "field": "soc_code",
            "strategy": "orphan_soc_with_bls_true",
            "old_value": str(old_val),
            "new_value": fake_soc,
        })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove all rows for entire categories
    and remove all rows for specific soc_resolved_methods."""
    manifest = []
    # Find categories and remove all rows for 2 of them
    cat_counts = {}
    for i, row in enumerate(rows):
        cat = row.get("category")
        if cat:
            cat_counts.setdefault(cat, []).append(i)

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

    # Also remove all unresolved rows to test method coverage
    method_counts = {}
    for i, row in enumerate(rows):
        m = row.get("soc_resolved_method")
        if m:
            method_counts.setdefault(m, []).append(i)

    if "unresolved" in method_counts and len(method_counts["unresolved"]) > 0:
        for idx in sorted(method_counts["unresolved"], reverse=True):
            if idx < len(rows):
                rows.pop(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "soc_resolved_method",
            "strategy": "remove_all_unresolved",
            "old_value": f"method=unresolved, count={len(method_counts['unresolved'])}",
            "new_value": "removed",
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
    # These change row count, so run last:
    corrupt_volume,
    corrupt_coverage,
]


def rows_to_arrow(rows):
    """Convert list of dicts to a PyArrow table matching Silver schema."""
    schema = pa.schema([
        pa.field("record_id", pa.large_string()),
        pa.field("soc_code", pa.large_string()),
        pa.field("slug", pa.large_string()),
        pa.field("occupation_title", pa.large_string()),
        pa.field("category", pa.large_string()),
        pa.field("exposure_score", pa.int32()),
        pa.field("rationale", pa.large_string()),
        pa.field("bls_match", pa.bool_()),
        pa.field("soc_resolved_method", pa.large_string()),
        pa.field("source_load_date", pa.date32()),
        pa.field("ingested_at", pa.timestamp("us")),
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
    """Register the shadow table in the Iceberg catalog under shadow_base namespace."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from brightsmith.config import CATALOG_PATH, WAREHOUSE_PATH
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, IntegerType,
        NestedField, StringType, TimestampType,
    )

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)

    # Create shadow_base namespace if needed
    try:
        catalog.create_namespace("shadow_base")
    except Exception:
        pass

    # Drop existing shadow table
    try:
        catalog.drop_table("shadow_base.karpathy_ai_exposure")
    except Exception:
        pass

    # Define schema matching the silver table (all nullable for shadow)
    iceberg_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "soc_code", StringType(), required=False),
        NestedField(3, "slug", StringType(), required=False),
        NestedField(4, "occupation_title", StringType(), required=False),
        NestedField(5, "category", StringType(), required=False),
        NestedField(6, "exposure_score", IntegerType(), required=False),
        NestedField(7, "rationale", StringType(), required=False),
        NestedField(8, "bls_match", BooleanType(), required=False),
        NestedField(9, "soc_resolved_method", StringType(), required=False),
        NestedField(10, "source_load_date", DateType(), required=False),
        NestedField(11, "ingested_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_base.karpathy_ai_exposure", schema=iceberg_schema
    )

    # Read the parquet and append to shadow table
    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)

    return shadow_table


def run_dq_rules_shadow():
    """Run DQ rules against the shadow table and return results."""
    from brightsmith.infra.dq_runner import run_rules

    result = run_rules(
        spec="silver-base-karpathy-ai-exposure", shadow=True
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
        print("  Registered as shadow_base.karpathy_ai_exposure")

        # Run DQ rules
        print("Running DQ rules against shadow table...")
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(f"  Total: {dq_result['rules_total']} | "
              f"Passed: {dq_result['rules_passed']} | "
              f"Failed: {dq_result['rules_failed']}")
        print(f"  P0 gate: {'PASS' if dq_result['p0_passed'] else 'FAIL'}")

        # Print per-rule results
        print("\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            print(f"    {r['rule_id']:<55} {status:<6} "
                  f"value={r.get('raw_value', '?')}")

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
        catalog.drop_table("shadow_base.karpathy_ai_exposure")
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
              f"({gap_analysis['rules_fired']}/{gap_analysis['total_rules']} "
              f"rules fired)")
        print(f"    Rules that fired: "
              f"{[r['rule_id'] for r in gap_analysis['failed_rules']]}")
        print(f"    Rules silent: "
              f"{[r['rule_id'] for r in gap_analysis['passed_rules']]}")

        if consecutive_no_new_gaps >= 2:
            print(
                "\n  Stability detected: same rules firing for 2 "
                "consecutive cycles."
            )

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": "silver-base-karpathy-ai-exposure",
        "table": "base.karpathy_ai_exposure",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = (
        PROJECT_ROOT
        / "governance/chaos-manifests"
        / "silver-base-karpathy-ai-exposure-manifest.json"
    )
    manifest_path.write_text(
        json.dumps(manifest_data, indent=2, default=str) + "\n"
    )
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
