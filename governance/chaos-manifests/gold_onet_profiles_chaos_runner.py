"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: gold-onet-profiles
Tables:
  - consumable.onet_work_profiles (798 rows)
  - consumable.career_transitions (15,944 rows)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against shadow tables, and records what was caught vs missed.

Information Barrier: This script does NOT read DQ rule definitions.
It injects corruptions based solely on the table schemas and domain
understanding from the transformer code and spec.
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
WP_SOURCE_PARQUET = PROJECT_ROOT / "data/gold/iceberg_warehouse/consumable/onet_work_profiles/data/00000-0-4b405296-ecc4-46e0-9dc5-19561cefb7b8.parquet"
CT_SOURCE_PARQUET = PROJECT_ROOT / "data/gold/iceberg_warehouse/consumable/career_transitions/data/00000-0-98f025c2-4b46-4425-b1b4-23aafa3a587e.parquet"

SHADOW_WP_DIR = PROJECT_ROOT / "data/gold/iceberg_warehouse/shadow_consumable/onet_work_profiles"
SHADOW_CT_DIR = PROJECT_ROOT / "data/gold/iceberg_warehouse/shadow_consumable/career_transitions"

CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"
GOLD_WAREHOUSE = PROJECT_ROOT / "data/gold/iceberg_warehouse"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "gold-onet-profiles"

# Valid domain values (from schema and transformer, NOT from DQ rules)
VALID_CONFIDENCE_TIERS = ["high", "medium", "low"]
VALID_RELATEDNESS_TIERS = ["Primary-Short", "Primary-Long", "Supplemental"]
VALID_DATA_COMPLETENESS_TIERS = ["full", "partial"]


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


# ===========================================================================
# WORK PROFILES corruption strategies (798 rows)
# ===========================================================================

def wp_corrupt_completeness(rows, indices, rng):
    """Null out required fields in onet_work_profiles."""
    manifest = []
    required_fields = [
        "record_id", "bls_soc_code", "primary_title", "description",
        "multi_detail_flag", "data_completeness_tier",
        "activity_profile_available", "context_profile_available",
        "confidence_tier", "backs_stats", "backs_bosses",
        "source_load_date", "promoted_at",
    ]
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(required_fields)
        old_val = rows[i].get(field)
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "table": "onet_work_profiles",
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null"
        })
    return manifest


def wp_corrupt_validity(rows, indices, rng):
    """Invalid values in onet_work_profiles: bad scores, bad tiers, bad JSON."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "hmn_out_of_range", "burnout_out_of_range",
            "hmn_rounded_out_of_range", "burnout_rounded_out_of_range",
            "bad_confidence_tier", "bad_data_completeness_tier",
            "bad_backs_stats", "bad_backs_bosses",
            "time_pressure_out_of_range", "work_hours_out_of_range",
            "consequence_of_error_out_of_range",
            "suppress_pct_out_of_range",
            "invalid_json_top_human", "invalid_json_burnout_drivers",
            "invalid_json_top_5",
            "bad_bls_soc_format",
        ])
        if strategy == "hmn_out_of_range":
            old_val = rows[i].get("hmn_score")
            rows[i]["hmn_score"] = rng.choice([0.0, -1.0, 10.5, 15.0, -5.0, 0.5, 11.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "hmn_score",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["hmn_score"]),
            })
        elif strategy == "burnout_out_of_range":
            old_val = rows[i].get("burnout_score")
            rows[i]["burnout_score"] = rng.choice([0.0, -1.0, 10.5, 15.0, -5.0, 0.5, 11.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "burnout_score",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["burnout_score"]),
            })
        elif strategy == "hmn_rounded_out_of_range":
            old_val = rows[i].get("hmn_score_rounded")
            rows[i]["hmn_score_rounded"] = rng.choice([0, -1, 11, 15, -5, 99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "hmn_score_rounded",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["hmn_score_rounded"]),
            })
        elif strategy == "burnout_rounded_out_of_range":
            old_val = rows[i].get("burnout_score_rounded")
            rows[i]["burnout_score_rounded"] = rng.choice([0, -1, 11, 15, -5, 99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "burnout_score_rounded",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["burnout_score_rounded"]),
            })
        elif strategy == "bad_confidence_tier":
            old_val = rows[i].get("confidence_tier")
            rows[i]["confidence_tier"] = rng.choice([
                "very_high", "MEDIUM", "unknown", "null", "0",
                "excellent", "insufficient", "HIGH",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "confidence_tier",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["confidence_tier"],
            })
        elif strategy == "bad_data_completeness_tier":
            old_val = rows[i].get("data_completeness_tier")
            rows[i]["data_completeness_tier"] = rng.choice([
                "complete", "incomplete", "FULL", "Partial",
                "none", "unknown", "", "0",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "data_completeness_tier",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["data_completeness_tier"],
            })
        elif strategy == "bad_backs_stats":
            old_val = rows[i].get("backs_stats")
            rows[i]["backs_stats"] = rng.choice([
                "ERN", "GRW", "HMN,ERN", "hmn", "", "HUMAN", "None", "AI",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "backs_stats",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["backs_stats"],
            })
        elif strategy == "bad_backs_bosses":
            old_val = rows[i].get("backs_bosses")
            rows[i]["backs_bosses"] = rng.choice([
                "Market", "AI", "Burnout", "ai,burnout", "AI,Burnout,Market",
                "", "BURNOUT", "None", "AI-Burnout",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "backs_bosses",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["backs_bosses"],
            })
        elif strategy == "time_pressure_out_of_range":
            old_val = rows[i].get("time_pressure")
            rows[i]["time_pressure"] = rng.choice([0.0, -1.0, 5.5, 10.0, -3.0, 6.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "time_pressure",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["time_pressure"]),
            })
        elif strategy == "work_hours_out_of_range":
            old_val = rows[i].get("work_hours")
            rows[i]["work_hours"] = rng.choice([0.0, -1.0, 3.5, 5.0, -2.0, 4.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "work_hours",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["work_hours"]),
            })
        elif strategy == "consequence_of_error_out_of_range":
            old_val = rows[i].get("consequence_of_error")
            rows[i]["consequence_of_error"] = rng.choice([0.0, -1.0, 5.5, 10.0, -3.0, 6.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "consequence_of_error",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["consequence_of_error"]),
            })
        elif strategy == "suppress_pct_out_of_range":
            field = rng.choice(["suppress_pct_activities", "suppress_pct_context"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([-5.0, 101.0, 200.0, -100.0, 150.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "invalid_json_top_human":
            old_val = rows[i].get("top_human_activities")
            rows[i]["top_human_activities"] = rng.choice([
                "not json", "{broken", "[1,2,", "null", "[]",
                '{"wrong": "format"}', "true", "42",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "top_human_activities",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val)[:80],
                "new_value": rows[i]["top_human_activities"],
            })
        elif strategy == "invalid_json_burnout_drivers":
            old_val = rows[i].get("burnout_drivers")
            rows[i]["burnout_drivers"] = rng.choice([
                "not json", "{broken", "[1,2,", "null", "[]",
                '{"wrong": "format"}', "true", "42",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "burnout_drivers",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val)[:80],
                "new_value": rows[i]["burnout_drivers"],
            })
        elif strategy == "invalid_json_top_5":
            old_val = rows[i].get("top_5_activities")
            rows[i]["top_5_activities"] = rng.choice([
                "not json", "{broken", "[1,2,", "null", "[]",
                '{"wrong": "format"}', "true", "42",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "top_5_activities",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val)[:80],
                "new_value": rows[i]["top_5_activities"],
            })
        elif strategy == "bad_bls_soc_format":
            old_val = rows[i].get("bls_soc_code")
            rows[i]["bls_soc_code"] = rng.choice([
                "151252", "15.1252", "XX-XXXX", "15-12520", "1-1252",
                "", "abc", "00-0000", "99-99999",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "bls_soc_code",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["bls_soc_code"],
            })
    return manifest


def wp_corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows (same record_id, same grain bls_soc_code)."""
    manifest = []
    n_dupes = max(1, len(indices) // 5)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "bls_soc_code",
            "table": "onet_work_profiles",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx} bls_soc_code={rows[src_idx].get('bls_soc_code')}",
            "new_value": f"duplicate at position {insert_pos}"
        })
    return manifest


def wp_corrupt_consistency(rows, indices, rng):
    """Contradictory field combinations in onet_work_profiles.
    - hmn_score_rounded != ROUND(hmn_score)
    - burnout_score_rounded != ROUND(burnout_score)
    - confidence_tier contradicts data_completeness_tier + suppress_pct
    - activity_profile_available=True but no activity data
    - hmn_score non-null but activity_profile_available=False
    """
    import math
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "hmn_rounded_mismatch", "burnout_rounded_mismatch",
            "confidence_tier_contradiction",
            "activity_available_contradiction",
            "hmn_null_with_activity_available",
            "burnout_null_with_context_available",
            "suppress_pct_negative_with_profile",
        ])
        if strategy == "hmn_rounded_mismatch":
            old_hmn = rows[i].get("hmn_score")
            old_rounded = rows[i].get("hmn_score_rounded")
            if old_hmn is not None:
                correct_rounded = int(math.floor(old_hmn + 0.5))
                wrong_rounded = correct_rounded + rng.choice([-2, -1, 1, 2, 3])
                wrong_rounded = max(1, min(10, wrong_rounded))
                if wrong_rounded == correct_rounded:
                    wrong_rounded = correct_rounded + 1 if correct_rounded < 10 else correct_rounded - 1
                rows[i]["hmn_score_rounded"] = wrong_rounded
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "hmn_score_rounded",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": f"hmn={old_hmn}, rounded={old_rounded}",
                    "new_value": f"rounded={wrong_rounded} (should be {correct_rounded})"
                })
        elif strategy == "burnout_rounded_mismatch":
            old_burnout = rows[i].get("burnout_score")
            old_rounded = rows[i].get("burnout_score_rounded")
            if old_burnout is not None:
                correct_rounded = int(math.floor(old_burnout + 0.5))
                wrong_rounded = correct_rounded + rng.choice([-2, -1, 1, 2, 3])
                wrong_rounded = max(1, min(10, wrong_rounded))
                if wrong_rounded == correct_rounded:
                    wrong_rounded = correct_rounded + 1 if correct_rounded < 10 else correct_rounded - 1
                rows[i]["burnout_score_rounded"] = wrong_rounded
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "burnout_score_rounded",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": f"burnout={old_burnout}, rounded={old_rounded}",
                    "new_value": f"rounded={wrong_rounded} (should be {correct_rounded})"
                })
        elif strategy == "confidence_tier_contradiction":
            old_tier = rows[i].get("confidence_tier")
            dc = rows[i].get("data_completeness_tier")
            sp_act = rows[i].get("suppress_pct_activities")
            sp_ctx = rows[i].get("suppress_pct_context")
            if dc == "partial":
                rows[i]["confidence_tier"] = rng.choice(["high", "medium"])
            elif (sp_act is not None and sp_act >= 5.0) or (sp_ctx is not None and sp_ctx >= 5.0):
                rows[i]["confidence_tier"] = rng.choice(["high", "low"])
            else:
                rows[i]["confidence_tier"] = rng.choice(["medium", "low"])
            manifest.append({
                "row": i, "dimension": "consistency", "field": "confidence_tier",
                "table": "onet_work_profiles",
                "strategy": strategy,
                "old_value": f"tier={old_tier}, dc={dc}, sp_act={sp_act}, sp_ctx={sp_ctx}",
                "new_value": f"tier={rows[i]['confidence_tier']} (contradicts derivation)"
            })
        elif strategy == "activity_available_contradiction":
            old_avail = rows[i].get("activity_profile_available")
            old_hmn = rows[i].get("hmn_score")
            if old_avail is True and old_hmn is not None:
                rows[i]["activity_profile_available"] = False
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "activity_profile_available",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": f"avail=True, hmn={old_hmn}",
                    "new_value": "avail=False but hmn_score is non-null"
                })
            elif old_avail is False and old_hmn is None:
                rows[i]["activity_profile_available"] = True
                rows[i]["hmn_score"] = None  # Keep hmn null but flag as available
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "activity_profile_available",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": f"avail=False, hmn=None",
                    "new_value": "avail=True but hmn_score still null"
                })
        elif strategy == "hmn_null_with_activity_available":
            if rows[i].get("activity_profile_available") is True and rows[i].get("hmn_score") is not None:
                old_hmn = rows[i]["hmn_score"]
                rows[i]["hmn_score"] = None
                rows[i]["hmn_score_rounded"] = None
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "hmn_score",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": f"hmn={old_hmn}, avail=True",
                    "new_value": "hmn=null but activity_profile_available=True"
                })
        elif strategy == "burnout_null_with_context_available":
            if rows[i].get("context_profile_available") is True and rows[i].get("burnout_score") is not None:
                old_bs = rows[i]["burnout_score"]
                rows[i]["burnout_score"] = None
                rows[i]["burnout_score_rounded"] = None
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "burnout_score",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": f"burnout={old_bs}, ctx_avail=True",
                    "new_value": "burnout=null but context_profile_available=True"
                })
        elif strategy == "suppress_pct_negative_with_profile":
            if rows[i].get("activity_profile_available") is True:
                old_val = rows[i].get("suppress_pct_activities")
                rows[i]["suppress_pct_activities"] = rng.choice([-5.0, -0.1, -100.0])
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "suppress_pct_activities",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": str(old_val),
                    "new_value": str(rows[i]["suppress_pct_activities"])
                })
    return manifest


def wp_corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values in onet_work_profiles."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "wrong_hmn_score", "wrong_burnout_score",
            "swapped_scores", "wrong_human_activity_count",
            "wrong_activity_importance_mean",
        ])
        if strategy == "wrong_hmn_score":
            old_val = rows[i].get("hmn_score")
            if old_val is not None:
                wrong_hmn = rng.uniform(1.0, 10.0)
                if abs(wrong_hmn - old_val) < 0.5:
                    wrong_hmn = old_val + rng.choice([-2.0, 2.0])
                    wrong_hmn = max(1.0, min(10.0, wrong_hmn))
                rows[i]["hmn_score"] = wrong_hmn
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "hmn_score",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": str(old_val),
                    "new_value": str(wrong_hmn)
                })
        elif strategy == "wrong_burnout_score":
            old_val = rows[i].get("burnout_score")
            if old_val is not None:
                wrong_bs = rng.uniform(1.0, 10.0)
                if abs(wrong_bs - old_val) < 0.5:
                    wrong_bs = old_val + rng.choice([-2.0, 2.0])
                    wrong_bs = max(1.0, min(10.0, wrong_bs))
                rows[i]["burnout_score"] = wrong_bs
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "burnout_score",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": str(old_val),
                    "new_value": str(wrong_bs)
                })
        elif strategy == "swapped_scores":
            old_hmn = rows[i].get("hmn_score")
            old_bs = rows[i].get("burnout_score")
            if old_hmn is not None and old_bs is not None:
                rows[i]["hmn_score"] = old_bs
                rows[i]["burnout_score"] = old_hmn
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "hmn_score,burnout_score",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": f"hmn={old_hmn}, burnout={old_bs}",
                    "new_value": f"hmn={old_bs}, burnout={old_hmn}"
                })
        elif strategy == "wrong_human_activity_count":
            old_val = rows[i].get("human_activity_count")
            if old_val is not None:
                wrong_count = rng.choice([0, 1, 41, 20, 30, -1])
                if wrong_count == old_val:
                    wrong_count = old_val + 5
                rows[i]["human_activity_count"] = wrong_count
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "human_activity_count",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": str(old_val),
                    "new_value": str(wrong_count)
                })
        elif strategy == "wrong_activity_importance_mean":
            old_val = rows[i].get("activity_importance_mean")
            if old_val is not None:
                wrong_mean = rng.uniform(0.5, 5.5)
                rows[i]["activity_importance_mean"] = wrong_mean
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "activity_importance_mean",
                    "table": "onet_work_profiles",
                    "strategy": strategy,
                    "old_value": str(old_val),
                    "new_value": str(wrong_mean)
                })
    return manifest


def wp_corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values in onet_work_profiles."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_hmn", "extreme_burnout",
            "extreme_time_pressure", "extreme_work_hours",
            "extreme_consequence", "extreme_suppress_pct",
            "extreme_activity_mean",
        ])
        if strategy == "extreme_hmn":
            old_val = rows[i].get("hmn_score")
            rows[i]["hmn_score"] = rng.choice([0.001, -50.0, 99.9, 100.0, -100.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "hmn_score",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["hmn_score"])
            })
        elif strategy == "extreme_burnout":
            old_val = rows[i].get("burnout_score")
            rows[i]["burnout_score"] = rng.choice([0.001, -50.0, 99.9, 100.0, -100.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "burnout_score",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["burnout_score"])
            })
        elif strategy == "extreme_time_pressure":
            old_val = rows[i].get("time_pressure")
            rows[i]["time_pressure"] = rng.choice([-100.0, 500.0, 999.0, -999.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "time_pressure",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["time_pressure"])
            })
        elif strategy == "extreme_work_hours":
            old_val = rows[i].get("work_hours")
            rows[i]["work_hours"] = rng.choice([-100.0, 500.0, 999.0, -999.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "work_hours",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["work_hours"])
            })
        elif strategy == "extreme_consequence":
            old_val = rows[i].get("consequence_of_error")
            rows[i]["consequence_of_error"] = rng.choice([-100.0, 500.0, 999.0, -999.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "consequence_of_error",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["consequence_of_error"])
            })
        elif strategy == "extreme_suppress_pct":
            field = rng.choice(["suppress_pct_activities", "suppress_pct_context"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([-500.0, 500.0, 9999.0, -9999.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field])
            })
        elif strategy == "extreme_activity_mean":
            old_val = rows[i].get("activity_importance_mean")
            rows[i]["activity_importance_mean"] = rng.choice([-50.0, 500.0, 0.0, -999.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "activity_importance_mean",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["activity_importance_mean"])
            })
    return manifest


def wp_corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps on onet_work_profiles."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "future_load_date", "stale_load_date",
            "future_promoted_at", "epoch_promoted_at",
        ])
        if strategy == "future_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-06-15"
            })
        elif strategy == "stale_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2015, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2015-01-01"
            })
        elif strategy == "future_promoted_at":
            old_val = rows[i].get("promoted_at")
            rows[i]["promoted_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2035-01-01T00:00:00"
            })
        elif strategy == "epoch_promoted_at":
            old_val = rows[i].get("promoted_at")
            rows[i]["promoted_at"] = datetime.datetime(1970, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "table": "onet_work_profiles",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "1970-01-01T00:00:00"
            })
    return manifest


def wp_corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-duplicate a chunk to inflate count beyond 798."""
    manifest = []
    n_extras = max(50, len(rows) // 10)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "table": "onet_work_profiles",
        "strategy": "mass_duplicate",
        "old_value": str(len(rows) - len(source_rows)),
        "new_value": str(len(rows))
    })
    return manifest


def wp_corrupt_referential_integrity(rows, indices, rng):
    """Orphan record_ids and bls_soc_codes."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_record_id", "orphan_bls_soc"])
        if strategy == "orphan_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = f"wp-ORPHAN{rng.randint(100000, 999999)}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "record_id",
                "table": "onet_work_profiles",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["record_id"])
            })
        elif strategy == "orphan_bls_soc":
            old_val = rows[i]["bls_soc_code"]
            rows[i]["bls_soc_code"] = rng.choice([
                "99-9999", "00-0001", "98-1234", "97-5678",
                "96-0000", "95-1111",
            ])
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "bls_soc_code",
                "table": "onet_work_profiles",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["bls_soc_code"])
            })
    return manifest


def wp_corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove confidence tier rows,
    remove all partial-data rows, etc."""
    manifest = []

    # Remove all rows for a confidence tier
    tier_to_remove = rng.choice(["low", "medium"])
    tier_indices = [i for i, r in enumerate(rows) if r.get("confidence_tier") == tier_to_remove]
    removed_indices = set()
    if tier_indices:
        for idx in tier_indices:
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "confidence_tier",
            "table": "onet_work_profiles",
            "strategy": f"remove_all_tier_{tier_to_remove}",
            "old_value": f"tier={tier_to_remove}, count={len(tier_indices)}",
            "new_value": "removed all rows for this tier"
        })

    # Remove some data_completeness_tier = "partial" rows
    partial_indices = [i for i, r in enumerate(rows) if r.get("data_completeness_tier") == "partial"]
    if partial_indices and rng.random() > 0.5:
        sample_size = min(len(partial_indices), 10)
        for idx in rng.sample(partial_indices, sample_size):
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "data_completeness_tier",
            "table": "onet_work_profiles",
            "strategy": "remove_partial_rows",
            "old_value": f"partial_count={len(partial_indices)}",
            "new_value": f"removed {sample_size} partial rows"
        })

    for idx in sorted(removed_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)

    return manifest


# ===========================================================================
# CAREER TRANSITIONS corruption strategies (15,944 rows)
# ===========================================================================

def ct_corrupt_completeness(rows, indices, rng):
    """Null out required fields in career_transitions."""
    manifest = []
    required_fields = [
        "record_id", "bls_soc_code", "source_title",
        "related_bls_soc_code", "related_title",
        "best_index", "relatedness_tier", "is_primary",
        "relationship_type", "source_has_work_profile",
        "related_has_work_profile", "backs_feature",
        "source_load_date", "promoted_at",
    ]
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(required_fields)
        old_val = rows[i].get(field)
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "table": "career_transitions",
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null"
        })
    return manifest


def ct_corrupt_validity(rows, indices, rng):
    """Invalid values in career_transitions."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_relatedness_tier", "bad_relationship_type",
            "bad_backs_feature", "bad_bls_soc_format",
            "negative_best_index",
        ])
        if strategy == "bad_relatedness_tier":
            old_val = rows[i].get("relatedness_tier")
            rows[i]["relatedness_tier"] = rng.choice([
                "primary", "PRIMARY-SHORT", "supplemental", "Primary",
                "Long", "Short", "Unknown", "", "Primary Short",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "relatedness_tier",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["relatedness_tier"],
            })
        elif strategy == "bad_relationship_type":
            old_val = rows[i].get("relationship_type")
            rows[i]["relationship_type"] = rng.choice([
                "SIMILARITY", "Similarity", "related", "transition",
                "career_path", "", "unknown",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "relationship_type",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["relationship_type"],
            })
        elif strategy == "bad_backs_feature":
            old_val = rows[i].get("backs_feature")
            rows[i]["backs_feature"] = rng.choice([
                "Stage3", "stage3branching", "STAGE3BRANCHING",
                "Stage3_Branching", "", "None", "Branching",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "backs_feature",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["backs_feature"],
            })
        elif strategy == "bad_bls_soc_format":
            field = rng.choice(["bls_soc_code", "related_bls_soc_code"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([
                "151252", "15.1252", "XX-XXXX", "15-12520",
                "", "abc", "00-0000",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i][field],
            })
        elif strategy == "negative_best_index":
            old_val = rows[i].get("best_index")
            rows[i]["best_index"] = rng.choice([-1, 0, -5, -100])
            manifest.append({
                "row": i, "dimension": "validity", "field": "best_index",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["best_index"]),
            })
    return manifest


def ct_corrupt_uniqueness(rows, indices, rng):
    """Inject duplicate grain rows (same bls_soc_code x related_bls_soc_code)."""
    manifest = []
    n_dupes = max(1, len(indices) // 5)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness",
            "field": "bls_soc_code,related_bls_soc_code",
            "table": "career_transitions",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx}",
            "new_value": f"duplicate at position {insert_pos}"
        })
    return manifest


def ct_corrupt_consistency(rows, indices, rng):
    """Contradictory combinations in career_transitions.
    - Self-references (bls_soc_code = related_bls_soc_code)
    - is_primary contradicts relatedness_tier
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "self_reference",
            "is_primary_contradiction",
        ])
        if strategy == "self_reference":
            old_related = rows[i].get("related_bls_soc_code")
            soc = rows[i].get("bls_soc_code")
            rows[i]["related_bls_soc_code"] = soc
            rows[i]["related_title"] = rows[i].get("source_title")
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "bls_soc_code,related_bls_soc_code",
                "table": "career_transitions",
                "strategy": strategy,
                "old_value": f"soc={soc}, related={old_related}",
                "new_value": f"self-ref: soc={soc} = related={soc}"
            })
        elif strategy == "is_primary_contradiction":
            old_primary = rows[i].get("is_primary")
            old_tier = rows[i].get("relatedness_tier")
            if old_tier in ("Primary-Short", "Primary-Long"):
                rows[i]["is_primary"] = False
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "is_primary",
                    "table": "career_transitions",
                    "strategy": strategy,
                    "old_value": f"is_primary={old_primary}, tier={old_tier}",
                    "new_value": f"is_primary=False but tier={old_tier}"
                })
            elif old_tier == "Supplemental":
                rows[i]["is_primary"] = True
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "is_primary",
                    "table": "career_transitions",
                    "strategy": strategy,
                    "old_value": f"is_primary={old_primary}, tier={old_tier}",
                    "new_value": f"is_primary=True but tier=Supplemental"
                })
    return manifest


def ct_corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values in career_transitions."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "wrong_title", "swapped_titles",
        ])
        if strategy == "wrong_title":
            field = rng.choice(["source_title", "related_title"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([
                "Wrong Occupation Title", "Fake Software Developer",
                "Miscellaneous Worker", "Unknown Occupation",
            ])
            manifest.append({
                "row": i, "dimension": "accuracy", "field": field,
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i][field]
            })
        elif strategy == "swapped_titles":
            old_src = rows[i].get("source_title")
            old_rel = rows[i].get("related_title")
            rows[i]["source_title"] = old_rel
            rows[i]["related_title"] = old_src
            manifest.append({
                "row": i, "dimension": "accuracy",
                "field": "source_title,related_title",
                "table": "career_transitions",
                "strategy": strategy,
                "old_value": f"src={old_src}, rel={old_rel}",
                "new_value": f"src={old_rel}, rel={old_src}"
            })
    return manifest


def ct_corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values in career_transitions."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        old_val = rows[i].get("best_index")
        rows[i]["best_index"] = rng.choice([999999, -999999, 0, 1000000])
        manifest.append({
            "row": i, "dimension": "reasonableness", "field": "best_index",
            "table": "career_transitions",
            "strategy": "extreme_best_index",
            "old_value": str(old_val),
            "new_value": str(rows[i]["best_index"])
        })
    return manifest


def ct_corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps on career_transitions."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "future_load_date", "stale_load_date",
            "future_promoted_at", "epoch_promoted_at",
        ])
        if strategy == "future_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2030, 6, 15)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-06-15"
            })
        elif strategy == "stale_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2015, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2015-01-01"
            })
        elif strategy == "future_promoted_at":
            old_val = rows[i].get("promoted_at")
            rows[i]["promoted_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2035-01-01T00:00:00"
            })
        elif strategy == "epoch_promoted_at":
            old_val = rows[i].get("promoted_at")
            rows[i]["promoted_at"] = datetime.datetime(1970, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "table": "career_transitions",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "1970-01-01T00:00:00"
            })
    return manifest


def ct_corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-duplicate to inflate beyond 15,944."""
    manifest = []
    n_extras = max(500, len(rows) // 10)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "table": "career_transitions",
        "strategy": "mass_duplicate",
        "old_value": str(len(rows) - len(source_rows)),
        "new_value": str(len(rows))
    })
    return manifest


def ct_corrupt_referential_integrity(rows, indices, rng):
    """Orphan record_ids and bls_soc_codes in career_transitions."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_record_id", "orphan_soc_code"])
        if strategy == "orphan_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = f"tr-ORPHAN{rng.randint(100000, 999999)}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "record_id",
                "table": "career_transitions",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["record_id"])
            })
        elif strategy == "orphan_soc_code":
            old_val = rows[i].get("bls_soc_code")
            rows[i]["bls_soc_code"] = rng.choice([
                "99-9999", "00-0001", "98-1234",
            ])
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "bls_soc_code",
                "table": "career_transitions",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["bls_soc_code"])
            })
    return manifest


def ct_corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove all Supplemental or Primary tiers."""
    manifest = []
    tier_to_remove = rng.choice(VALID_RELATEDNESS_TIERS)
    tier_indices = [i for i, r in enumerate(rows) if r.get("relatedness_tier") == tier_to_remove]
    removed_indices = set()
    if tier_indices:
        # Remove a chunk, not all (would be too disruptive)
        sample_size = min(len(tier_indices), len(tier_indices) // 2 + 1)
        for idx in rng.sample(tier_indices, sample_size):
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "relatedness_tier",
            "table": "career_transitions",
            "strategy": f"remove_tier_{tier_to_remove}",
            "old_value": f"tier={tier_to_remove}, count={len(tier_indices)}",
            "new_value": f"removed {sample_size} rows"
        })

    for idx in sorted(removed_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)

    return manifest


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_source_data(parquet_path):
    """Load Gold parquet data into a list of dicts."""
    import pyarrow.parquet as pq
    table = pq.read_table(str(parquet_path))
    rows = []
    for i in range(table.num_rows):
        row = {}
        for col in table.column_names:
            val = table.column(col)[i].as_py()
            row[col] = val
        rows.append(row)
    return rows, table.schema


def write_shadow_parquet(rows, original_schema, shadow_dir, cycle_num):
    """Write corrupted rows to shadow parquet file."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    data_dir = shadow_dir / "data"
    meta_dir = shadow_dir / "metadata"
    data_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    arrays = {}
    for field in original_schema:
        col_name = field.name
        values = [r.get(col_name) for r in rows]
        try:
            arrays[col_name] = pa.array(values, type=field.type)
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arrays[col_name] = pa.array(values)

    arrow_table = pa.table(arrays)
    out_file = data_dir / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out_file))
    return out_file, arrow_table


def register_shadow_wp_in_catalog(parquet_path):
    """Register shadow onet_work_profiles table in the Iceberg catalog."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, DoubleType, IntegerType,
        NestedField, StringType, TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))

    try:
        catalog.create_namespace("shadow_consumable")
    except Exception:
        pass

    try:
        catalog.drop_table("shadow_consumable.onet_work_profiles")
    except Exception:
        pass

    iceberg_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "bls_soc_code", StringType(), required=False),
        NestedField(3, "primary_title", StringType(), required=False),
        NestedField(4, "description", StringType(), required=False),
        NestedField(5, "multi_detail_flag", BooleanType(), required=False),
        NestedField(6, "data_completeness_tier", StringType(), required=False),
        NestedField(7, "hmn_score", DoubleType(), required=False),
        NestedField(8, "hmn_score_rounded", IntegerType(), required=False),
        NestedField(9, "top_human_activities", StringType(), required=False),
        NestedField(10, "human_activity_count", IntegerType(), required=False),
        NestedField(11, "burnout_score", DoubleType(), required=False),
        NestedField(12, "burnout_score_rounded", IntegerType(), required=False),
        NestedField(13, "burnout_drivers", StringType(), required=False),
        NestedField(14, "time_pressure", DoubleType(), required=False),
        NestedField(15, "work_hours", DoubleType(), required=False),
        NestedField(16, "consequence_of_error", DoubleType(), required=False),
        NestedField(17, "activity_importance_mean", DoubleType(), required=False),
        NestedField(18, "top_5_activities", StringType(), required=False),
        NestedField(19, "activity_profile_available", BooleanType(), required=False),
        NestedField(20, "context_profile_available", BooleanType(), required=False),
        NestedField(21, "confidence_tier", StringType(), required=False),
        NestedField(22, "suppress_pct_activities", DoubleType(), required=False),
        NestedField(23, "suppress_pct_context", DoubleType(), required=False),
        NestedField(24, "backs_stats", StringType(), required=False),
        NestedField(25, "backs_bosses", StringType(), required=False),
        NestedField(26, "source_load_date", DateType(), required=False),
        NestedField(27, "promoted_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_consumable.onet_work_profiles", schema=iceberg_schema
    )

    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def register_shadow_ct_in_catalog(parquet_path):
    """Register shadow career_transitions table in the Iceberg catalog."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DateType, IntegerType,
        NestedField, StringType, TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))

    try:
        catalog.create_namespace("shadow_consumable")
    except Exception:
        pass

    try:
        catalog.drop_table("shadow_consumable.career_transitions")
    except Exception:
        pass

    iceberg_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "bls_soc_code", StringType(), required=False),
        NestedField(3, "source_title", StringType(), required=False),
        NestedField(4, "related_bls_soc_code", StringType(), required=False),
        NestedField(5, "related_title", StringType(), required=False),
        NestedField(6, "best_index", IntegerType(), required=False),
        NestedField(7, "relatedness_tier", StringType(), required=False),
        NestedField(8, "is_primary", BooleanType(), required=False),
        NestedField(9, "relationship_type", StringType(), required=False),
        NestedField(10, "source_has_work_profile", BooleanType(), required=False),
        NestedField(11, "related_has_work_profile", BooleanType(), required=False),
        NestedField(12, "backs_feature", StringType(), required=False),
        NestedField(13, "source_load_date", DateType(), required=False),
        NestedField(14, "promoted_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_consumable.career_transitions", schema=iceberg_schema
    )

    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def run_dq_rules_shadow():
    """Run DQ rules against the shadow tables."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
    result = run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)
    return result


def cleanup_shadow():
    """Remove shadow tables and files."""
    for shadow_dir in [SHADOW_WP_DIR, SHADOW_CT_DIR]:
        if shadow_dir.exists():
            shutil.rmtree(shadow_dir)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
        try:
            catalog.drop_table("shadow_consumable.onet_work_profiles")
        except Exception:
            pass
        try:
            catalog.drop_table("shadow_consumable.career_transitions")
        except Exception:
            pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Corruption function lists
# ---------------------------------------------------------------------------

WP_CORRUPTION_FUNCTIONS = [
    wp_corrupt_completeness,
    wp_corrupt_validity,
    wp_corrupt_uniqueness,
    wp_corrupt_consistency,
    wp_corrupt_accuracy,
    wp_corrupt_reasonableness,
    wp_corrupt_freshness,
    wp_corrupt_referential_integrity,
    wp_corrupt_volume,
    wp_corrupt_coverage,
]

CT_CORRUPTION_FUNCTIONS = [
    ct_corrupt_completeness,
    ct_corrupt_validity,
    ct_corrupt_uniqueness,
    ct_corrupt_consistency,
    ct_corrupt_accuracy,
    ct_corrupt_reasonableness,
    ct_corrupt_freshness,
    ct_corrupt_referential_integrity,
    ct_corrupt_volume,
    ct_corrupt_coverage,
]


# ---------------------------------------------------------------------------
# Main injection pipeline
# ---------------------------------------------------------------------------

def corrupt_table(rows, corruption_functions, rate, rng, table_name):
    """Apply all 10 corruption dimensions to a table's rows."""
    original_count = len(rows)
    n_corrupt = int(original_count * rate)
    all_indices = list(range(original_count))
    per_function = max(4, n_corrupt)

    all_manifest = []
    for func in corruption_functions:
        indices = rng.sample(all_indices, min(per_function, len(all_indices)))
        try:
            entries = func(rows, indices, rng)
            all_manifest.extend(entries)
            dim = func.__name__.split("_corrupt_", 1)[-1] if "_corrupt_" in func.__name__ else func.__name__
            print(f"    {table_name}.{dim}: {len(entries)} corruptions")
        except Exception as e:
            print(f"    ERROR in {func.__name__}: {e}")
            traceback.print_exc()

    return all_manifest


def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle against both tables."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)

    # Load work profiles
    print("Loading onet_work_profiles...")
    wp_rows, wp_schema = load_source_data(WP_SOURCE_PARQUET)
    wp_original_count = len(wp_rows)
    print(f"  Loaded {wp_original_count} rows")

    # Load career transitions
    print("Loading career_transitions...")
    ct_rows, ct_schema = load_source_data(CT_SOURCE_PARQUET)
    ct_original_count = len(ct_rows)
    print(f"  Loaded {ct_original_count} rows")

    # Corrupt work profiles
    print(f"\n  Corrupting onet_work_profiles at {rate*100:.0f}%...")
    wp_manifest = corrupt_table(wp_rows, WP_CORRUPTION_FUNCTIONS, rate, rng, "wp")

    # Corrupt career transitions
    print(f"\n  Corrupting career_transitions at {rate*100:.0f}%...")
    ct_manifest = corrupt_table(ct_rows, CT_CORRUPTION_FUNCTIONS, rate, rng, "ct")

    all_manifest = wp_manifest + ct_manifest
    print(f"\n  Total corruptions: {len(all_manifest)} (wp={len(wp_manifest)}, ct={len(ct_manifest)})")
    print(f"  Final row counts: wp={len(wp_rows)} (was {wp_original_count}), ct={len(ct_rows)} (was {ct_original_count})")

    # Write shadow tables
    dq_result = {"run_id": "error", "rules_total": 0, "rules_passed": 0,
                 "rules_failed": 0, "p0_passed": True, "results": []}
    try:
        print("Writing shadow work profiles...")
        wp_parquet_path, _ = write_shadow_parquet(wp_rows, wp_schema, SHADOW_WP_DIR, cycle_num)
        print(f"  Written to {wp_parquet_path}")

        print("Writing shadow career transitions...")
        ct_parquet_path, _ = write_shadow_parquet(ct_rows, ct_schema, SHADOW_CT_DIR, cycle_num)
        print(f"  Written to {ct_parquet_path}")

        print("Registering in Iceberg catalog as shadow_consumable...")
        register_shadow_wp_in_catalog(wp_parquet_path)
        register_shadow_ct_in_catalog(ct_parquet_path)
        print("  Registered.")

        print("Running DQ rules against shadow tables...")
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(f"  Total: {dq_result['rules_total']} | Passed: {dq_result['rules_passed']} | Failed: {dq_result['rules_failed']}")
        p0_status = "PASS" if dq_result.get("p0_passed", True) else "FAIL"
        print(f"  P0 gate: {p0_status}")

        print("\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            print(f"    {r['rule_id']:<25} {status:<6} value={r.get('raw_value', '?')}")

    except Exception as e:
        print(f"  ERROR during shadow table creation/DQ run: {e}")
        traceback.print_exc()

    return {
        "cycle": cycle_num,
        "rate": rate,
        "seed": seed,
        "wp_original_count": wp_original_count,
        "wp_corrupted_count": len(wp_rows),
        "ct_original_count": ct_original_count,
        "ct_corrupted_count": len(ct_rows),
        "total_corruptions": len(all_manifest),
        "wp_corruptions": len(wp_manifest),
        "ct_corruptions": len(ct_manifest),
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
            "wp_row_count": cycle_result["wp_corrupted_count"],
            "ct_row_count": cycle_result["ct_corrupted_count"],
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
        "tables": ["consumable.onet_work_profiles", "consumable.career_transitions"],
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/gold-onet-profiles-manifest.json"
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
        if ga['errored_rules']:
            print(f"  errored: {[r['rule_id'] for r in ga['errored_rules']]}")
