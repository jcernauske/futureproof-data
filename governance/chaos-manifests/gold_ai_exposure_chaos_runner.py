"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: gold-ai-exposure
Table: consumable.ai_exposure (389 rows)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.

Information Barrier: This script does NOT read DQ rule definitions.
It injects corruptions based solely on the table schema and domain
understanding from the transformer code (ai_exposure_transformer.py).

Schema (9 columns, all required=True):
  record_id       STRING   grain hash (prefix 'aie', grain=['soc_code'])
  soc_code        STRING   SOC format XX-XXXX
  occupation_title STRING
  exposure_score  INTEGER  0-10
  stat_res        INTEGER  1-10  derived: MIN(11 - exposure_score, 10)
  boss_ai_score   INTEGER  1-10  derived: MAX(exposure_score, 1)
  rationale       STRING   free-text explanation
  category        STRING   slug like 'healthcare', 'management', etc.
  promoted_at     TIMESTAMP

Key invariants from transformer code:
  stat_res + boss_ai_score should relate to exposure_score
  stat_res = MIN(11 - exposure_score, 10)
  boss_ai_score = MAX(exposure_score, 1)
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
SOURCE_PARQUET = PROJECT_ROOT / "data/gold/iceberg_warehouse/consumable/ai_exposure/data/00000-0-2cc22628-c2db-4404-9dec-2ef07a52f865.parquet"
SHADOW_DIR = PROJECT_ROOT / "data/gold/iceberg_warehouse/shadow_consumable/ai_exposure"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"
CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"
GOLD_WAREHOUSE = PROJECT_ROOT / "data/gold/iceberg_warehouse"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "gold-ai-exposure"
TABLE_NAME = "consumable.ai_exposure"

GRAIN_FIELDS = ["soc_code"]
GRAIN_PREFIX = "aie"

# Valid SOC major group codes
VALID_SOC_MAJOR_GROUPS = [
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "31", "33", "35", "37", "39", "41", "43", "45", "47", "49",
    "51", "53",
]

# Valid categories observed in the data
VALID_CATEGORIES = [
    "architecture-and-engineering", "arts-and-design",
    "building-and-grounds-cleaning", "business-and-financial",
    "community-and-social-service", "computer-and-information-technology",
    "construction-and-extraction", "education-training-and-library",
    "entertainment-and-sports", "farming-fishing-and-forestry",
    "food-preparation-and-serving", "healthcare",
    "installation-maintenance-and-repair", "legal",
    "life-physical-and-social-science", "management", "math",
    "media-and-communication", "office-and-administrative-support",
    "personal-care-and-service", "production", "protective-service",
    "sales", "transportation-and-material-moving",
]


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
# Corruption strategies — one per DQ dimension, targeting Gold ai_exposure
# ---------------------------------------------------------------------------

def corrupt_completeness(rows, indices, rng):
    """Null out required fields."""
    manifest = []
    required_fields = [
        "record_id", "soc_code", "occupation_title",
        "exposure_score", "stat_res", "boss_ai_score",
        "rationale", "category", "promoted_at",
    ]
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(required_fields)
        old_val = rows[i].get(field)
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null"
        })
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid values: bad SOC format, out-of-range scores, bad category."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_soc_format", "exposure_out_of_range",
            "stat_res_out_of_range", "boss_ai_out_of_range",
            "bad_category", "empty_rationale",
            "bad_record_id_format", "exposure_negative",
        ])
        if strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice([
                "151252", "15.1252", "XX-XXXX", "15-12520", "1-1252",
                "", "abc", "00-0000", "99-99999", "A1-B2C3",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
            })
        elif strategy == "exposure_out_of_range":
            old_val = rows[i]["exposure_score"]
            rows[i]["exposure_score"] = rng.choice([11, 12, 15, -1, -5, 100, 255])
            manifest.append({
                "row": i, "dimension": "validity", "field": "exposure_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["exposure_score"]),
            })
        elif strategy == "stat_res_out_of_range":
            old_val = rows[i]["stat_res"]
            rows[i]["stat_res"] = rng.choice([0, -1, 11, 15, -5, 100, 255])
            manifest.append({
                "row": i, "dimension": "validity", "field": "stat_res",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["stat_res"]),
            })
        elif strategy == "boss_ai_out_of_range":
            old_val = rows[i]["boss_ai_score"]
            rows[i]["boss_ai_score"] = rng.choice([0, -1, 11, 15, -5, 100, 255])
            manifest.append({
                "row": i, "dimension": "validity", "field": "boss_ai_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["boss_ai_score"]),
            })
        elif strategy == "bad_category":
            old_val = rows[i]["category"]
            rows[i]["category"] = rng.choice([
                "Healthcare", "MANAGEMENT", "other", "unknown",
                "N/A", "", "misc", "general", "unclassified",
                "tech", "finance", "science",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "category",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["category"],
            })
        elif strategy == "empty_rationale":
            old_val = rows[i]["rationale"]
            rows[i]["rationale"] = rng.choice(["", " ", "N/A", ".", "TBD"])
            manifest.append({
                "row": i, "dimension": "validity", "field": "rationale",
                "strategy": strategy, "old_value": str(old_val)[:60] + "...",
                "new_value": repr(rows[i]["rationale"]),
            })
        elif strategy == "bad_record_id_format":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = rng.choice([
                "BADFORMAT", "aie-", "aie-ZZZZ", "op-12345678",
                "", "null", "aie_invalid",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "record_id",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["record_id"],
            })
        elif strategy == "exposure_negative":
            old_val = rows[i]["exposure_score"]
            rows[i]["exposure_score"] = rng.choice([-1, -10, -100])
            manifest.append({
                "row": i, "dimension": "validity", "field": "exposure_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["exposure_score"]),
            })
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows (same record_id, same grain soc_code)."""
    manifest = []
    n_dupes = max(1, len(indices) // 5)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "soc_code",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx} soc_code={rows[src_idx].get('soc_code')}",
            "new_value": f"duplicate at position {insert_pos}"
        })
    return manifest


def corrupt_consistency(rows, indices, rng):
    """Break derivation invariants:
    - stat_res != MIN(11 - exposure_score, 10)
    - boss_ai_score != MAX(exposure_score, 1)
    - stat_res + boss_ai_score inversely wrong
    - category vs occupation_title mismatch (swap categories)
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "broken_stat_res_derivation",
            "broken_boss_ai_derivation",
            "broken_inverse_invariant",
            "swapped_stat_res_boss_ai",
            "category_title_mismatch",
        ])
        exposure = rows[i].get("exposure_score")
        if exposure is None:
            continue

        if strategy == "broken_stat_res_derivation":
            old_val = rows[i]["stat_res"]
            correct = min(11 - exposure, 10)
            # Pick a wrong value that differs from the correct one
            wrong = correct + rng.choice([-3, -2, -1, 1, 2, 3])
            wrong = max(1, min(10, wrong))
            if wrong == correct:
                wrong = correct + 1 if correct < 10 else correct - 1
            rows[i]["stat_res"] = wrong
            manifest.append({
                "row": i, "dimension": "consistency", "field": "stat_res",
                "strategy": strategy,
                "old_value": f"stat_res={old_val}, exposure={exposure}",
                "new_value": f"stat_res={wrong} (should be {correct})"
            })
        elif strategy == "broken_boss_ai_derivation":
            old_val = rows[i]["boss_ai_score"]
            correct = max(exposure, 1)
            wrong = correct + rng.choice([-3, -2, -1, 1, 2, 3])
            wrong = max(1, min(10, wrong))
            if wrong == correct:
                wrong = correct + 1 if correct < 10 else correct - 1
            rows[i]["boss_ai_score"] = wrong
            manifest.append({
                "row": i, "dimension": "consistency", "field": "boss_ai_score",
                "strategy": strategy,
                "old_value": f"boss_ai={old_val}, exposure={exposure}",
                "new_value": f"boss_ai={wrong} (should be {correct})"
            })
        elif strategy == "broken_inverse_invariant":
            # Break the relationship: stat_res + boss_ai_score != 11
            # (for exposure 1-10, stat_res + boss_ai = 11)
            old_stat = rows[i]["stat_res"]
            old_boss = rows[i]["boss_ai_score"]
            # Force the sum to be wrong
            rows[i]["stat_res"] = rng.randint(1, 10)
            rows[i]["boss_ai_score"] = rng.randint(1, 10)
            # Ensure the sum is NOT 11 for exposures 1-10
            while rows[i]["stat_res"] + rows[i]["boss_ai_score"] == 11 and exposure > 0:
                rows[i]["boss_ai_score"] = rng.randint(1, 10)
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "stat_res,boss_ai_score",
                "strategy": strategy,
                "old_value": f"stat_res={old_stat}, boss_ai={old_boss}, exposure={exposure}",
                "new_value": f"stat_res={rows[i]['stat_res']}, boss_ai={rows[i]['boss_ai_score']} (sum={rows[i]['stat_res']+rows[i]['boss_ai_score']}, should relate to exposure={exposure})"
            })
        elif strategy == "swapped_stat_res_boss_ai":
            # Swap the two derived fields
            old_stat = rows[i]["stat_res"]
            old_boss = rows[i]["boss_ai_score"]
            rows[i]["stat_res"] = old_boss
            rows[i]["boss_ai_score"] = old_stat
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "stat_res,boss_ai_score",
                "strategy": strategy,
                "old_value": f"stat_res={old_stat}, boss_ai={old_boss}",
                "new_value": f"stat_res={old_boss}, boss_ai={old_stat} (swapped)"
            })
        elif strategy == "category_title_mismatch":
            # Assign a random category that likely doesn't match the occupation
            old_cat = rows[i]["category"]
            wrong_cats = [c for c in VALID_CATEGORIES if c != old_cat]
            if wrong_cats:
                rows[i]["category"] = rng.choice(wrong_cats)
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "category",
                    "strategy": strategy,
                    "old_value": f"category={old_cat}, title={rows[i].get('occupation_title', '')}",
                    "new_value": f"category={rows[i]['category']} (mismatched)"
                })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: close-but-wrong derivations, subtly wrong exposure."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "stat_res_off_by_one", "boss_ai_off_by_one",
            "exposure_shifted", "wrong_record_id_hash",
            "rationale_wrong_occupation",
        ])
        exposure = rows[i].get("exposure_score")
        if exposure is None:
            continue

        if strategy == "stat_res_off_by_one":
            old_val = rows[i]["stat_res"]
            correct = min(11 - exposure, 10)
            # Off by exactly 1 — hard to catch
            wrong = correct + rng.choice([-1, 1])
            wrong = max(1, min(10, wrong))
            if wrong == correct:
                wrong = correct - 1 if correct > 1 else correct + 1
            rows[i]["stat_res"] = wrong
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "stat_res",
                "strategy": strategy,
                "old_value": f"stat_res={old_val} (correct={correct})",
                "new_value": f"stat_res={wrong} (off by 1)"
            })
        elif strategy == "boss_ai_off_by_one":
            old_val = rows[i]["boss_ai_score"]
            correct = max(exposure, 1)
            wrong = correct + rng.choice([-1, 1])
            wrong = max(1, min(10, wrong))
            if wrong == correct:
                wrong = correct + 1 if correct < 10 else correct - 1
            rows[i]["boss_ai_score"] = wrong
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "boss_ai_score",
                "strategy": strategy,
                "old_value": f"boss_ai={old_val} (correct={correct})",
                "new_value": f"boss_ai={wrong} (off by 1)"
            })
        elif strategy == "exposure_shifted":
            # Shift exposure_score by 1 but leave stat_res/boss_ai derived from old value
            old_exp = rows[i]["exposure_score"]
            new_exp = old_exp + rng.choice([-1, 1])
            new_exp = max(0, min(10, new_exp))
            if new_exp == old_exp:
                new_exp = old_exp + 1 if old_exp < 10 else old_exp - 1
            rows[i]["exposure_score"] = new_exp
            # stat_res and boss_ai are still derived from OLD exposure,
            # so they become inconsistent with the new exposure value
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "exposure_score",
                "strategy": strategy,
                "old_value": f"exposure={old_exp}, stat_res={rows[i]['stat_res']}, boss_ai={rows[i]['boss_ai_score']}",
                "new_value": f"exposure={new_exp} (stat_res/boss_ai now stale)"
            })
        elif strategy == "wrong_record_id_hash":
            old_val = rows[i]["record_id"]
            # Set to a valid-format but wrong hash
            rows[i]["record_id"] = f"aie-{rng.randint(1000000000000000, 9999999999999999):016x}"
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "record_id",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": rows[i]["record_id"]
            })
        elif strategy == "rationale_wrong_occupation":
            old_val = rows[i]["rationale"]
            # Replace with a plausible but wrong rationale mentioning a different occupation
            fake_rationales = [
                "This occupation involves primarily manual labor in outdoor settings, making it largely immune to AI automation.",
                "The role requires extensive interpersonal skills and emotional intelligence that AI cannot replicate.",
                "Highly repetitive data entry tasks make this occupation extremely vulnerable to automation.",
                "Creative work in this field is fundamentally human and resistant to AI replacement.",
            ]
            rows[i]["rationale"] = rng.choice(fake_rationales)
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "rationale",
                "strategy": strategy,
                "old_value": str(old_val)[:60] + "...",
                "new_value": rows[i]["rationale"][:60] + "..."
            })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values in integer score fields."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_exposure", "extreme_stat_res",
            "extreme_boss_ai", "absurd_rationale_length",
        ])
        if strategy == "extreme_exposure":
            old_val = rows[i]["exposure_score"]
            rows[i]["exposure_score"] = rng.choice([999, -999, 1000000, -100])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "exposure_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["exposure_score"])
            })
        elif strategy == "extreme_stat_res":
            old_val = rows[i]["stat_res"]
            rows[i]["stat_res"] = rng.choice([999, -999, 1000000, -100])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "stat_res",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["stat_res"])
            })
        elif strategy == "extreme_boss_ai":
            old_val = rows[i]["boss_ai_score"]
            rows[i]["boss_ai_score"] = rng.choice([999, -999, 1000000, -100])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "boss_ai_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["boss_ai_score"])
            })
        elif strategy == "absurd_rationale_length":
            old_val = rows[i]["rationale"]
            # Either absurdly short or absurdly long
            if rng.random() < 0.5:
                rows[i]["rationale"] = "X"
            else:
                rows[i]["rationale"] = "AI exposure analysis. " * 5000  # ~100K chars
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "rationale",
                "strategy": strategy,
                "old_value": f"len={len(str(old_val))}",
                "new_value": f"len={len(rows[i]['rationale'])}"
            })
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps on promoted_at."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "future_promoted_at", "epoch_promoted_at",
            "stale_promoted_at", "far_future_promoted_at",
        ])
        old_val = rows[i].get("promoted_at")
        if strategy == "future_promoted_at":
            rows[i]["promoted_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2035-01-01T00:00:00"
            })
        elif strategy == "epoch_promoted_at":
            rows[i]["promoted_at"] = datetime.datetime(1970, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "1970-01-01T00:00:00"
            })
        elif strategy == "stale_promoted_at":
            rows[i]["promoted_at"] = datetime.datetime(2020, 3, 15, 12, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2020-03-15T12:00:00"
            })
        elif strategy == "far_future_promoted_at":
            rows[i]["promoted_at"] = datetime.datetime(2099, 12, 31, 23, 59, 59)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2099-12-31T23:59:59"
            })
    return manifest


def corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-duplicate to inflate count beyond 389."""
    manifest = []
    n_extras = max(30, len(rows) // 10)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "strategy": "mass_duplicate",
        "old_value": str(len(rows) - len(source_rows)),
        "new_value": str(len(rows))
    })
    return manifest


def corrupt_referential_integrity(rows, indices, rng):
    """Orphan record_ids and orphan soc_codes."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_record_id", "orphan_soc_code"])
        if strategy == "orphan_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = f"aie-ORPHAN{rng.randint(100000, 999999)}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "record_id",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["record_id"])
            })
        elif strategy == "orphan_soc_code":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice([
                "99-9999", "00-0001", "98-1234", "97-5678",
                "96-0000", "95-1111",
            ])
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "soc_code",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["soc_code"])
            })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove all rows for some categories."""
    manifest = []
    cat_counts = {}
    for i, row in enumerate(rows):
        cat = row.get("category")
        if cat:
            cat_counts.setdefault(cat, []).append(i)

    # Remove all rows for 2-3 categories
    available_cats = sorted(
        cat_counts, key=lambda c: len(cat_counts[c]), reverse=True
    )[:10]
    targets = rng.sample(available_cats, min(3, len(available_cats)))

    removed_indices = set()
    for cat in targets:
        for idx in cat_counts[cat]:
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "category",
            "strategy": f"remove_all_category_{cat}",
            "old_value": f"category={cat}, count={len(cat_counts[cat])}",
            "new_value": "removed"
        })

    # Also remove some rows by exposure_score range to break coverage
    high_exposure = [i for i, r in enumerate(rows) if r.get("exposure_score", 0) >= 9]
    if len(high_exposure) > 2:
        sample_size = min(len(high_exposure) // 2, 20)
        if sample_size > 0:
            for idx in rng.sample(high_exposure, sample_size):
                removed_indices.add(idx)
            manifest.append({
                "row": -1, "dimension": "coverage", "field": "exposure_score",
                "strategy": "remove_high_exposure_rows",
                "old_value": f"high_exposure_count={len(high_exposure)}",
                "new_value": f"removed {sample_size} rows with exposure >= 9"
            })

    for idx in sorted(removed_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_source_data():
    """Load Gold parquet data into a list of dicts."""
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
    """Register shadow table in the Iceberg catalog under shadow_consumable namespace."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        IntegerType,
        NestedField,
        StringType,
        TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))

    try:
        catalog.create_namespace("shadow_consumable")
    except Exception:
        pass

    try:
        catalog.drop_table("shadow_consumable.ai_exposure")
    except Exception:
        pass

    # Schema matching consumable.ai_exposure (9 columns, all nullable in shadow)
    iceberg_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "soc_code", StringType(), required=False),
        NestedField(3, "occupation_title", StringType(), required=False),
        NestedField(4, "exposure_score", IntegerType(), required=False),
        NestedField(5, "stat_res", IntegerType(), required=False),
        NestedField(6, "boss_ai_score", IntegerType(), required=False),
        NestedField(7, "rationale", StringType(), required=False),
        NestedField(8, "category", StringType(), required=False),
        NestedField(9, "promoted_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_consumable.ai_exposure", schema=iceberg_schema
    )

    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def run_dq_rules_shadow():
    """Run DQ rules against the shadow table."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
    result = run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)
    return result


def cleanup_shadow():
    """Remove shadow table and files."""
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
        catalog.drop_table("shadow_consumable.ai_exposure")
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
    per_function = max(4, n_corrupt)

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

    print("Writing shadow table...")
    dq_result = {"run_id": "error", "rules_total": 0, "rules_passed": 0,
                 "rules_failed": 0, "p0_passed": True, "results": []}
    try:
        parquet_path, arrow_table = write_shadow_parquet(rows, original_schema, cycle_num)
        print(f"  Written to {parquet_path}")

        print("Registering in Iceberg catalog as shadow_consumable.ai_exposure...")
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
        "errored_rules": [{"rule_id": r["rule_id"], "error": r.get("error")}
                          for r in errored_rules],
        "injected_dimensions": sorted(dims),
        "corruptions_per_dimension": {dim: len(entries) for dim, entries in dims.items()},
        "detection_rate": round(detection_rate, 3),
        "rules_fired": len(failed_rules),
        "rules_silent": len(passed_rules),
        "rules_errored": len(errored_rules),
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
            "dq_errored": cycle_result["dq_result"].get("rules_errored", 0),
            "dq_total": cycle_result["dq_result"]["rules_total"],
            "gap_analysis": gap_analysis,
        })
        all_gaps.append(gap_analysis)

        print(f"\n  Gap Analysis:")
        dr = gap_analysis['detection_rate']
        print(f"    Detection rate: {dr*100:.1f}% ({gap_analysis['rules_fired']}/{gap_analysis['total_rules']} rules fired)")
        print(f"    Rules that fired: {[r['rule_id'] for r in gap_analysis['failed_rules']]}")
        print(f"    Rules silent: {[r['rule_id'] for r in gap_analysis['passed_rules']]}")
        if gap_analysis['errored_rules']:
            print(f"    Rules errored: {[r['rule_id'] for r in gap_analysis['errored_rules']]}")

        if consecutive_no_new_gaps >= 2:
            print(f"\n  Stability: same rules firing for {consecutive_no_new_gaps + 1} consecutive cycles.")

        cleanup_shadow()

    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": SPEC_NAME,
        "table": TABLE_NAME,
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/gold-ai-exposure-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_data, indent=2, default=str) + "\n")
    print(f"\nManifest written to: {manifest_path}")

    return manifest_data


if __name__ == "__main__":
    main()
