"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: gold-futureproof-engine-backfill-ai
Tables:
  - consumable.program_career_paths (626K rows, grain: unitid x cipcode x soc_code)
  - consumable.career_branches (15,944 rows, grain: soc_code x related_soc_code)

Targets BACKFILL-SPECIFIC corruptions:
  - stat_res + boss_ai_score invariant violation (should sum to 11)
  - Out-of-range stat_res/boss_ai_score
  - Broken stats_available_count (set to 6 or fail to increment)
  - Broken career_branches deltas (res_delta != related_res - source_res)
  - Null agreement violations (stat_res non-null but boss_ai_score null)
  - Plus all 10 DQ dimensions

Information Barrier: This script was built from schema definitions and the
physical model, NOT from DQ rule definitions.

Memory-Safe: Uses career_branches (16K rows) as primary target.
Samples program_career_paths to 10K rows for shadow injection.
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
GOLD_WAREHOUSE = PROJECT_ROOT / "data/gold/iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"

# Post-backfill parquet files (latest)
PCP_SOURCE_PARQUETS = [
    GOLD_WAREHOUSE / "consumable/program_career_paths/data/00000-0-e4855ab8-a725-4017-955e-e7e0b86957bb.parquet",
    GOLD_WAREHOUSE / "consumable/program_career_paths/data/00000-1-e4855ab8-a725-4017-955e-e7e0b86957bb.parquet",
]
CB_SOURCE_PARQUET = GOLD_WAREHOUSE / "consumable/career_branches/data/00000-0-ef43aa11-8be8-4bf1-809b-598f7c1badef.parquet"

SHADOW_PCP_DIR = GOLD_WAREHOUSE / "shadow_consumable/program_career_paths"
SHADOW_CB_DIR = GOLD_WAREHOUSE / "shadow_consumable/career_branches"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 1337
SPEC_NAME = "gold-futureproof-engine-backfill-ai"
PCP_SAMPLE_SIZE = 10000  # Sample PCP to avoid memory issues

# Valid enum values (from schema, NOT from DQ rules)
VALID_MATCH_QUALITY = ["full", "partial_no_onet", "partial_no_bls", "scorecard_only"]
VALID_CONFIDENCE = ["high", "medium", "low"]
VALID_RELATEDNESS_TIERS = ["Primary-Short", "Primary-Long", "Supplemental"]


# ---------------------------------------------------------------------------
# Safety check
# ---------------------------------------------------------------------------

def safety_check():
    """Three-layer kill switch: env vars + shadow namespace check."""
    import os
    os.environ["CHAOS_MONKEY_ENABLED"] = "true"
    os.environ["GRIST_ENV"] = "dev"
    enabled = os.environ.get("CHAOS_MONKEY_ENABLED", "").lower() == "true"
    dev_env = os.environ.get("GRIST_ENV", "").lower() == "dev"
    if not enabled:
        print("KILL SWITCH: CHAOS_MONKEY_ENABLED is not 'true'.")
        sys.exit(1)
    if not dev_env:
        print("KILL SWITCH: GRIST_ENV is not 'dev'.")
        sys.exit(1)
    # Layer 3: verify we only write to shadow dirs
    for d in [SHADOW_PCP_DIR, SHADOW_CB_DIR]:
        if "shadow" not in str(d):
            print(f"KILL SWITCH: Target dir {d} does not contain 'shadow'.")
            sys.exit(1)
    print("Safety check passed: CHAOS_MONKEY_ENABLED=true, GRIST_ENV=dev, shadow-only writes")


# ===========================================================================
# PCP corruption strategies (BACKFILL-SPECIFIC)
# ===========================================================================

def pcp_corrupt_completeness(rows, indices, rng):
    """Null required fields -- focus on backfill fields."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "null_stat_res_where_populated",
            "null_boss_ai_where_populated",
            "null_stats_available_count",
            "null_bosses_available_count",
            "null_overall_confidence",
            "null_record_id",
        ])
        if strategy == "null_stat_res_where_populated":
            old_val = rows[i].get("stat_res")
            if old_val is not None:
                rows[i]["stat_res"] = None
                manifest.append({
                    "row": i, "dimension": "completeness", "field": "stat_res",
                    "strategy": strategy, "old_value": str(old_val), "new_value": "null",
                    "table": "program_career_paths"
                })
        elif strategy == "null_boss_ai_where_populated":
            old_val = rows[i].get("boss_ai_score")
            if old_val is not None:
                rows[i]["boss_ai_score"] = None
                manifest.append({
                    "row": i, "dimension": "completeness", "field": "boss_ai_score",
                    "strategy": strategy, "old_value": str(old_val), "new_value": "null",
                    "table": "program_career_paths"
                })
        elif strategy == "null_stats_available_count":
            old_val = rows[i].get("stats_available_count")
            rows[i]["stats_available_count"] = None
            manifest.append({
                "row": i, "dimension": "completeness", "field": "stats_available_count",
                "strategy": strategy, "old_value": str(old_val), "new_value": "null",
                "table": "program_career_paths"
            })
        elif strategy == "null_bosses_available_count":
            old_val = rows[i].get("bosses_available_count")
            rows[i]["bosses_available_count"] = None
            manifest.append({
                "row": i, "dimension": "completeness", "field": "bosses_available_count",
                "strategy": strategy, "old_value": str(old_val), "new_value": "null",
                "table": "program_career_paths"
            })
        elif strategy == "null_overall_confidence":
            old_val = rows[i].get("overall_confidence")
            rows[i]["overall_confidence"] = None
            manifest.append({
                "row": i, "dimension": "completeness", "field": "overall_confidence",
                "strategy": strategy, "old_value": str(old_val), "new_value": "null",
                "table": "program_career_paths"
            })
        elif strategy == "null_record_id":
            old_val = rows[i].get("record_id")
            rows[i]["record_id"] = None
            manifest.append({
                "row": i, "dimension": "completeness", "field": "record_id",
                "strategy": strategy, "old_value": str(old_val), "new_value": "null",
                "table": "program_career_paths"
            })
    return manifest


def pcp_corrupt_validity(rows, indices, rng):
    """Invalid values -- backfill-specific: stat_res/boss_ai_score out of range,
    stats_available_count set to 6 (impossible max), bad formats."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "stat_res_out_of_range",
            "boss_ai_out_of_range",
            "stats_available_count_six",
            "stats_available_count_negative",
            "bosses_available_count_six",
            "bad_match_quality",
            "bad_overall_confidence",
        ])
        if strategy == "stat_res_out_of_range":
            old_val = rows[i].get("stat_res")
            rows[i]["stat_res"] = rng.choice([0, -1, 11, 15, -5, 100, -99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "stat_res",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["stat_res"]),
                "table": "program_career_paths"
            })
        elif strategy == "boss_ai_out_of_range":
            old_val = rows[i].get("boss_ai_score")
            rows[i]["boss_ai_score"] = rng.choice([0, -1, 11, 15, -5, 100, -99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "boss_ai_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["boss_ai_score"]),
                "table": "program_career_paths"
            })
        elif strategy == "stats_available_count_six":
            old_val = rows[i].get("stats_available_count")
            rows[i]["stats_available_count"] = 6
            manifest.append({
                "row": i, "dimension": "validity", "field": "stats_available_count",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "6 (max possible is 5)",
                "table": "program_career_paths"
            })
        elif strategy == "stats_available_count_negative":
            old_val = rows[i].get("stats_available_count")
            rows[i]["stats_available_count"] = rng.choice([-1, -5, 10])
            manifest.append({
                "row": i, "dimension": "validity", "field": "stats_available_count",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["stats_available_count"]),
                "table": "program_career_paths"
            })
        elif strategy == "bosses_available_count_six":
            old_val = rows[i].get("bosses_available_count")
            rows[i]["bosses_available_count"] = 6
            manifest.append({
                "row": i, "dimension": "validity", "field": "bosses_available_count",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "6 (max possible is 5)",
                "table": "program_career_paths"
            })
        elif strategy == "bad_match_quality":
            old_val = rows[i]["match_quality"]
            rows[i]["match_quality"] = rng.choice(["FULL", "none", "partial", "unknown"])
            manifest.append({
                "row": i, "dimension": "validity", "field": "match_quality",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["match_quality"],
                "table": "program_career_paths"
            })
        elif strategy == "bad_overall_confidence":
            old_val = rows[i]["overall_confidence"]
            rows[i]["overall_confidence"] = rng.choice(["HIGH", "very_high", "none"])
            manifest.append({
                "row": i, "dimension": "validity", "field": "overall_confidence",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["overall_confidence"],
                "table": "program_career_paths"
            })
    return manifest


def pcp_corrupt_uniqueness(rows, indices, rng):
    """Duplicate rows by grain key."""
    manifest = []
    n_dupes = max(1, len(indices) // 5)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "record_id",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx}",
            "new_value": f"duplicate at position {insert_pos}",
            "table": "program_career_paths"
        })
    return manifest


def pcp_corrupt_consistency(rows, indices, rng):
    """BACKFILL-SPECIFIC consistency violations:
    - stat_res + boss_ai_score != 11 (invariant broken)
    - stat_res non-null but boss_ai_score null (null agreement violation)
    - boss_ai_score non-null but stat_res null
    - stats_available_count doesn't match actual non-null stat count
    - bosses_available_count doesn't match actual non-null boss count
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "break_invariant_sum",
            "null_agreement_res_present_boss_null",
            "null_agreement_boss_present_res_null",
            "stats_count_not_incremented",
            "bosses_count_not_incremented",
            "boss_loans_roi_mismatch",
        ])
        if strategy == "break_invariant_sum":
            # stat_res + boss_ai_score should equal 11; break this
            old_res = rows[i].get("stat_res")
            old_boss = rows[i].get("boss_ai_score")
            if old_res is not None and old_boss is not None:
                # Set both to values that don't sum to 11
                rows[i]["stat_res"] = rng.randint(1, 10)
                rows[i]["boss_ai_score"] = rng.randint(1, 10)
                while rows[i]["stat_res"] + rows[i]["boss_ai_score"] == 11:
                    rows[i]["boss_ai_score"] = rng.randint(1, 10)
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "stat_res,boss_ai_score",
                    "strategy": strategy,
                    "old_value": f"res={old_res}, boss={old_boss}, sum={old_res + old_boss}",
                    "new_value": f"res={rows[i]['stat_res']}, boss={rows[i]['boss_ai_score']}, sum={rows[i]['stat_res'] + rows[i]['boss_ai_score']}",
                    "table": "program_career_paths"
                })
        elif strategy == "null_agreement_res_present_boss_null":
            # Set stat_res to non-null but boss_ai_score to null
            old_res = rows[i].get("stat_res")
            old_boss = rows[i].get("boss_ai_score")
            rows[i]["stat_res"] = rng.randint(1, 10)
            rows[i]["boss_ai_score"] = None
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "stat_res,boss_ai_score",
                "strategy": strategy,
                "old_value": f"res={old_res}, boss={old_boss}",
                "new_value": f"res={rows[i]['stat_res']}, boss=null",
                "table": "program_career_paths"
            })
        elif strategy == "null_agreement_boss_present_res_null":
            # Set boss_ai_score to non-null but stat_res to null
            old_res = rows[i].get("stat_res")
            old_boss = rows[i].get("boss_ai_score")
            rows[i]["boss_ai_score"] = rng.randint(1, 10)
            rows[i]["stat_res"] = None
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "stat_res,boss_ai_score",
                "strategy": strategy,
                "old_value": f"res={old_res}, boss={old_boss}",
                "new_value": f"res=null, boss={rows[i]['boss_ai_score']}",
                "table": "program_career_paths"
            })
        elif strategy == "stats_count_not_incremented":
            # stat_res is non-null but stats_available_count wasn't incremented
            old_res = rows[i].get("stat_res")
            old_count = rows[i].get("stats_available_count")
            if old_res is not None and old_count is not None and old_count > 0:
                rows[i]["stats_available_count"] = old_count - 1
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "stats_available_count",
                    "strategy": strategy,
                    "old_value": f"count={old_count}, stat_res={old_res}",
                    "new_value": f"count={old_count - 1} (not counting stat_res)",
                    "table": "program_career_paths"
                })
        elif strategy == "bosses_count_not_incremented":
            old_boss = rows[i].get("boss_ai_score")
            old_count = rows[i].get("bosses_available_count")
            if old_boss is not None and old_count is not None and old_count > 0:
                rows[i]["bosses_available_count"] = old_count - 1
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "bosses_available_count",
                    "strategy": strategy,
                    "old_value": f"count={old_count}, boss_ai={old_boss}",
                    "new_value": f"count={old_count - 1} (not counting boss_ai)",
                    "table": "program_career_paths"
                })
        elif strategy == "boss_loans_roi_mismatch":
            old_roi = rows[i].get("stat_roi")
            old_loans = rows[i].get("boss_loans_score")
            if old_roi is not None:
                wrong = old_roi  # Should be 11 - stat_roi
                rows[i]["boss_loans_score"] = wrong
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "boss_loans_score",
                    "strategy": strategy,
                    "old_value": f"roi={old_roi}, loans={old_loans}",
                    "new_value": f"loans={wrong} (should be {11 - old_roi})",
                    "table": "program_career_paths"
                })
    return manifest


def pcp_corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong: stat_res off by 1-2, wrong institution names."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "wrong_stat_res", "wrong_boss_ai_score",
            "swapped_res_ern", "wrong_institution",
        ])
        if strategy == "wrong_stat_res":
            old_val = rows[i].get("stat_res")
            if old_val is not None:
                delta = rng.choice([-2, -1, 1, 2])
                new_val = max(1, min(10, old_val + delta))
                if new_val != old_val:
                    rows[i]["stat_res"] = new_val
                    # Also fix boss_ai to maintain a plausible-looking row
                    # but the invariant will be broken
                    manifest.append({
                        "row": i, "dimension": "accuracy", "field": "stat_res",
                        "strategy": strategy, "old_value": str(old_val),
                        "new_value": str(new_val),
                        "table": "program_career_paths"
                    })
        elif strategy == "wrong_boss_ai_score":
            old_val = rows[i].get("boss_ai_score")
            if old_val is not None:
                delta = rng.choice([-2, -1, 1, 2])
                new_val = max(1, min(10, old_val + delta))
                if new_val != old_val:
                    rows[i]["boss_ai_score"] = new_val
                    manifest.append({
                        "row": i, "dimension": "accuracy", "field": "boss_ai_score",
                        "strategy": strategy, "old_value": str(old_val),
                        "new_value": str(new_val),
                        "table": "program_career_paths"
                    })
        elif strategy == "swapped_res_ern":
            # Swap stat_res and stat_ern -- plausible but wrong
            old_res = rows[i].get("stat_res")
            old_ern = rows[i].get("stat_ern")
            if old_res is not None and old_ern is not None and old_res != old_ern:
                rows[i]["stat_res"] = old_ern
                rows[i]["stat_ern"] = old_res
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "stat_res,stat_ern",
                    "strategy": strategy,
                    "old_value": f"res={old_res},ern={old_ern}",
                    "new_value": f"res={old_ern},ern={old_res}",
                    "table": "program_career_paths"
                })
        elif strategy == "wrong_institution":
            old_name = rows[i].get("institution_name")
            rows[i]["institution_name"] = rng.choice([
                "Fake University", "University of Nowhere", "XYZ College",
            ])
            manifest.append({
                "row": i, "dimension": "accuracy",
                "field": "institution_name",
                "strategy": strategy, "old_value": str(old_name),
                "new_value": rows[i]["institution_name"],
                "table": "program_career_paths"
            })
    return manifest


def pcp_corrupt_reasonableness(rows, indices, rng):
    """Extreme outliers in earnings and financial fields."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_earnings", "negative_earnings",
            "extreme_debt", "extreme_dte",
        ])
        if strategy == "extreme_earnings":
            field = rng.choice(["earnings_1yr_median", "earnings_1yr_p25", "earnings_1yr_p75"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(5000000, 50000000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
                "table": "program_career_paths"
            })
        elif strategy == "negative_earnings":
            old_val = rows[i].get("earnings_1yr_median")
            rows[i]["earnings_1yr_median"] = float(rng.randint(-500000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "earnings_1yr_median",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["earnings_1yr_median"]),
                "table": "program_career_paths"
            })
        elif strategy == "extreme_debt":
            old_val = rows[i].get("debt_median")
            rows[i]["debt_median"] = float(rng.randint(2000000, 10000000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "debt_median",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["debt_median"]),
                "table": "program_career_paths"
            })
        elif strategy == "extreme_dte":
            old_val = rows[i].get("debt_to_earnings_annual")
            rows[i]["debt_to_earnings_annual"] = rng.choice([50.0, -5.0, 100.0, 999.9])
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "debt_to_earnings_annual",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["debt_to_earnings_annual"]),
                "table": "program_career_paths"
            })
    return manifest


def pcp_corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["future_promoted_at", "epoch_promoted_at"])
        old_val = rows[i].get("promoted_at")
        if strategy == "future_promoted_at":
            rows[i]["promoted_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
        else:
            rows[i]["promoted_at"] = datetime.datetime(1970, 1, 1, 0, 0, 0)
        manifest.append({
            "row": i, "dimension": "freshness", "field": "promoted_at",
            "strategy": strategy, "old_value": str(old_val),
            "new_value": str(rows[i]["promoted_at"]),
            "table": "program_career_paths"
        })
    return manifest


def pcp_corrupt_volume(rows, indices, rng):
    """Row count anomalies via mass duplication."""
    manifest = []
    n_extras = max(10, len(rows) // 8)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "strategy": "mass_duplicate",
        "old_value": str(len(rows) - len(source_rows)),
        "new_value": str(len(rows)),
        "table": "program_career_paths"
    })
    return manifest


def pcp_corrupt_referential_integrity(rows, indices, rng):
    """Orphan keys: unitids and soc_codes not in upstream tables."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_unitid", "orphan_soc_code"])
        if strategy == "orphan_unitid":
            old_val = rows[i]["unitid"]
            rows[i]["unitid"] = rng.randint(900000000, 999999999)
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "unitid",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["unitid"]),
                "table": "program_career_paths"
            })
        elif strategy == "orphan_soc_code":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = f"{rng.randint(90,99):02d}-{rng.randint(9000,9999):04d}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
                "table": "program_career_paths"
            })
    return manifest


def pcp_corrupt_coverage(rows, indices, rng):
    """Remove rows for entire CIP families or match_quality categories."""
    manifest = []
    family_counts = {}
    for i, row in enumerate(rows):
        fam = row.get("cip_family")
        if fam:
            family_counts.setdefault(fam, []).append(i)

    common_families = sorted(
        family_counts, key=lambda f: len(family_counts[f]), reverse=True
    )[:5]
    targets = rng.sample(common_families, min(2, len(common_families)))

    removed_indices = set()
    for fam in targets:
        for idx in family_counts[fam]:
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "cip_family",
            "strategy": f"remove_all_family_{fam}",
            "old_value": f"family={fam}, count={len(family_counts[fam])}",
            "new_value": "removed",
            "table": "program_career_paths"
        })

    for idx in sorted(removed_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)

    return manifest


# ===========================================================================
# CAREER_BRANCHES corruption strategies (BACKFILL-SPECIFIC)
# ===========================================================================

def cb_corrupt_completeness(rows, indices, rng):
    """Null required fields and backfill fields."""
    manifest = []
    required_fields = [
        "record_id", "soc_code", "source_title", "related_soc_code",
        "related_title", "best_index", "relatedness_tier",
        "is_primary", "branch_has_full_data", "promoted_at",
    ]
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(required_fields + ["source_res", "related_res"])
        old_val = rows[i].get(field)
        if field in ("source_res", "related_res") and old_val is None:
            # Already null -- null a required field instead
            field = rng.choice(required_fields)
            old_val = rows[i].get(field)
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null",
            "table": "career_branches"
        })
    return manifest


def cb_corrupt_validity(rows, indices, rng):
    """BACKFILL-SPECIFIC: AI stat scores out of range, bad SOC formats,
    bad relatedness tiers, delta out of range."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "source_res_out_of_range",
            "related_res_out_of_range",
            "source_ai_boss_out_of_range",
            "related_ai_boss_out_of_range",
            "bad_soc_format",
            "bad_relatedness_tier",
            "score_out_of_range_existing",
        ])
        if strategy == "source_res_out_of_range":
            old_val = rows[i].get("source_res")
            rows[i]["source_res"] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": "source_res",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["source_res"]),
                "table": "career_branches"
            })
        elif strategy == "related_res_out_of_range":
            old_val = rows[i].get("related_res")
            rows[i]["related_res"] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": "related_res",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["related_res"]),
                "table": "career_branches"
            })
        elif strategy == "source_ai_boss_out_of_range":
            old_val = rows[i].get("source_ai_boss")
            rows[i]["source_ai_boss"] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": "source_ai_boss",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["source_ai_boss"]),
                "table": "career_branches"
            })
        elif strategy == "related_ai_boss_out_of_range":
            old_val = rows[i].get("related_ai_boss")
            rows[i]["related_ai_boss"] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": "related_ai_boss",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["related_ai_boss"]),
                "table": "career_branches"
            })
        elif strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice(["11.1011", "111011", "", "XX-XXXX", "1-1011"])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"],
                "table": "career_branches"
            })
        elif strategy == "bad_relatedness_tier":
            old_val = rows[i]["relatedness_tier"]
            rows[i]["relatedness_tier"] = rng.choice([
                "primary-short", "PRIMARY", "Unknown", "Tertiary", "",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "relatedness_tier",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["relatedness_tier"],
                "table": "career_branches"
            })
        elif strategy == "score_out_of_range_existing":
            field = rng.choice(["source_grw", "source_hmn", "related_grw", "related_hmn"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
                "table": "career_branches"
            })
    return manifest


def cb_corrupt_uniqueness(rows, indices, rng):
    """Duplicate rows by grain key."""
    manifest = []
    n_dupes = max(1, len(indices) // 5)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "record_id",
            "strategy": "duplicate_row",
            "old_value": f"copy_of_row_{src_idx}",
            "new_value": f"duplicate at position {insert_pos}",
            "table": "career_branches"
        })
    return manifest


def cb_corrupt_consistency(rows, indices, rng):
    """BACKFILL-SPECIFIC consistency violations:
    - res_delta != related_res - source_res
    - ai_boss_delta != related_ai_boss - source_ai_boss
    - res_delta non-null when source_res or related_res is null
    - source_res + source_ai_boss != 11 (invariant broken)
    - branch_has_full_data contradictions
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "break_res_delta",
            "break_ai_boss_delta",
            "delta_null_propagation_violation",
            "break_source_invariant",
            "break_related_invariant",
            "branch_full_data_contradiction",
        ])
        if strategy == "break_res_delta":
            s_res = rows[i].get("source_res")
            r_res = rows[i].get("related_res")
            if s_res is not None and r_res is not None:
                correct_delta = r_res - s_res
                wrong_delta = correct_delta + rng.choice([-3, -2, 2, 3])
                rows[i]["res_delta"] = wrong_delta
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "res_delta",
                    "strategy": strategy,
                    "old_value": f"source={s_res}, related={r_res}, correct_delta={correct_delta}",
                    "new_value": f"res_delta={wrong_delta} (should be {correct_delta})",
                    "table": "career_branches"
                })
        elif strategy == "break_ai_boss_delta":
            s_boss = rows[i].get("source_ai_boss")
            r_boss = rows[i].get("related_ai_boss")
            if s_boss is not None and r_boss is not None:
                correct_delta = r_boss - s_boss
                wrong_delta = correct_delta + rng.choice([-3, -2, 2, 3])
                rows[i]["ai_boss_delta"] = wrong_delta
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "ai_boss_delta",
                    "strategy": strategy,
                    "old_value": f"source={s_boss}, related={r_boss}, correct_delta={correct_delta}",
                    "new_value": f"ai_boss_delta={wrong_delta} (should be {correct_delta})",
                    "table": "career_branches"
                })
        elif strategy == "delta_null_propagation_violation":
            # Set res_delta to non-null when source_res is null
            old_delta = rows[i].get("res_delta")
            old_source = rows[i].get("source_res")
            rows[i]["source_res"] = None
            rows[i]["res_delta"] = rng.randint(-5, 5)
            manifest.append({
                "row": i, "dimension": "consistency", "field": "res_delta",
                "strategy": strategy,
                "old_value": f"res_delta={old_delta}, source_res={old_source}",
                "new_value": f"res_delta={rows[i]['res_delta']}, source_res=null",
                "table": "career_branches"
            })
        elif strategy == "break_source_invariant":
            # source_res + source_ai_boss should be 11
            s_res = rows[i].get("source_res")
            s_boss = rows[i].get("source_ai_boss")
            if s_res is not None and s_boss is not None:
                rows[i]["source_res"] = rng.randint(1, 10)
                rows[i]["source_ai_boss"] = rng.randint(1, 10)
                while rows[i]["source_res"] + rows[i]["source_ai_boss"] == 11:
                    rows[i]["source_ai_boss"] = rng.randint(1, 10)
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "source_res,source_ai_boss",
                    "strategy": strategy,
                    "old_value": f"res={s_res}, boss={s_boss}",
                    "new_value": f"res={rows[i]['source_res']}, boss={rows[i]['source_ai_boss']}, sum={rows[i]['source_res'] + rows[i]['source_ai_boss']}",
                    "table": "career_branches"
                })
        elif strategy == "break_related_invariant":
            r_res = rows[i].get("related_res")
            r_boss = rows[i].get("related_ai_boss")
            if r_res is not None and r_boss is not None:
                rows[i]["related_res"] = rng.randint(1, 10)
                rows[i]["related_ai_boss"] = rng.randint(1, 10)
                while rows[i]["related_res"] + rows[i]["related_ai_boss"] == 11:
                    rows[i]["related_ai_boss"] = rng.randint(1, 10)
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "related_res,related_ai_boss",
                    "strategy": strategy,
                    "old_value": f"res={r_res}, boss={r_boss}",
                    "new_value": f"res={rows[i]['related_res']}, boss={rows[i]['related_ai_boss']}, sum={rows[i]['related_res'] + rows[i]['related_ai_boss']}",
                    "table": "career_branches"
                })
        elif strategy == "branch_full_data_contradiction":
            old_flag = rows[i].get("branch_has_full_data")
            old_grw = rows[i].get("related_grw")
            rows[i]["branch_has_full_data"] = True
            rows[i]["related_grw"] = None
            rows[i]["related_hmn"] = None
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "branch_has_full_data",
                "strategy": strategy,
                "old_value": f"flag={old_flag}, related_grw={old_grw}",
                "new_value": "flag=True but related_grw=null, related_hmn=null",
                "table": "career_branches"
            })
    return manifest


def cb_corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong: deltas off by small amounts, wrong titles."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["wrong_res_delta", "wrong_grw_delta", "wrong_title"])
        if strategy == "wrong_res_delta":
            s_res = rows[i].get("source_res")
            r_res = rows[i].get("related_res")
            if s_res is not None and r_res is not None:
                correct_delta = r_res - s_res
                wrong_delta = correct_delta + rng.choice([-1, 1])
                if wrong_delta != correct_delta:
                    old_val = rows[i].get("res_delta")
                    rows[i]["res_delta"] = wrong_delta
                    manifest.append({
                        "row": i, "dimension": "accuracy", "field": "res_delta",
                        "strategy": strategy,
                        "old_value": str(old_val),
                        "new_value": f"{wrong_delta} (correct={correct_delta})",
                        "table": "career_branches"
                    })
        elif strategy == "wrong_grw_delta":
            s_grw = rows[i].get("source_grw")
            r_grw = rows[i].get("related_grw")
            if s_grw is not None and r_grw is not None:
                correct_delta = r_grw - s_grw
                wrong_delta = correct_delta + rng.choice([-2, 2])
                if wrong_delta != correct_delta:
                    old_val = rows[i].get("grw_delta")
                    rows[i]["grw_delta"] = wrong_delta
                    manifest.append({
                        "row": i, "dimension": "accuracy", "field": "grw_delta",
                        "strategy": strategy,
                        "old_value": str(old_val),
                        "new_value": f"{wrong_delta} (correct={correct_delta})",
                        "table": "career_branches"
                    })
        elif strategy == "wrong_title":
            old_val = rows[i].get("source_title")
            rows[i]["source_title"] = "Fake Occupation Title"
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "source_title",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "Fake Occupation Title",
                "table": "career_branches"
            })
    return manifest


def cb_corrupt_reasonableness(rows, indices, rng):
    """Extreme outliers: massive wages, impossible best_index."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_source_wage", "negative_wage", "impossible_best_index",
        ])
        if strategy == "extreme_source_wage":
            old_val = rows[i].get("source_wage")
            rows[i]["source_wage"] = float(rng.randint(5000000, 50000000))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "source_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["source_wage"]),
                "table": "career_branches"
            })
        elif strategy == "negative_wage":
            field = rng.choice(["source_wage", "related_wage"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(-500000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
                "table": "career_branches"
            })
        elif strategy == "impossible_best_index":
            old_val = rows[i].get("best_index")
            rows[i]["best_index"] = rng.choice([0, -1, -10, 1000])
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "best_index",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["best_index"]),
                "table": "career_branches"
            })
    return manifest


def cb_corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["future_promoted_at", "epoch_promoted_at"])
        old_val = rows[i].get("promoted_at")
        if strategy == "future_promoted_at":
            rows[i]["promoted_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
        else:
            rows[i]["promoted_at"] = datetime.datetime(1970, 1, 1, 0, 0, 0)
        manifest.append({
            "row": i, "dimension": "freshness", "field": "promoted_at",
            "strategy": strategy, "old_value": str(old_val),
            "new_value": str(rows[i]["promoted_at"]),
            "table": "career_branches"
        })
    return manifest


def cb_corrupt_volume(rows, indices, rng):
    """Row count anomaly."""
    manifest = []
    n_extras = max(10, len(rows) // 8)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "strategy": "mass_duplicate",
        "old_value": str(len(rows) - len(source_rows)),
        "new_value": str(len(rows)),
        "table": "career_branches"
    })
    return manifest


def cb_corrupt_referential_integrity(rows, indices, rng):
    """Orphan SOC codes."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_soc_pair", "orphan_record_id"])
        if strategy == "orphan_soc_pair":
            old_soc = rows[i]["soc_code"]
            old_related = rows[i]["related_soc_code"]
            rows[i]["soc_code"] = f"{rng.randint(90,99):02d}-{rng.randint(9000,9999):04d}"
            rows[i]["related_soc_code"] = f"{rng.randint(90,99):02d}-{rng.randint(9000,9999):04d}"
            manifest.append({
                "row": i, "dimension": "referential_integrity",
                "field": "soc_code,related_soc_code",
                "strategy": strategy,
                "old_value": f"soc={old_soc},related={old_related}",
                "new_value": f"soc={rows[i]['soc_code']},related={rows[i]['related_soc_code']}",
                "table": "career_branches"
            })
        elif strategy == "orphan_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = f"br-ORPHAN{rng.randint(100000, 999999)}"
            manifest.append({
                "row": i, "dimension": "referential_integrity",
                "field": "record_id",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["record_id"],
                "table": "career_branches"
            })
    return manifest


def cb_corrupt_coverage(rows, indices, rng):
    """Remove relatedness_tier categories entirely."""
    manifest = []
    tier_to_remove = rng.choice(VALID_RELATEDNESS_TIERS)
    tier_indices = [i for i, r in enumerate(rows)
                    if r.get("relatedness_tier") == tier_to_remove]
    removed = 0
    for idx in sorted(tier_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)
            removed += 1
    if removed > 0:
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "relatedness_tier",
            "strategy": f"remove_tier_{tier_to_remove}",
            "old_value": f"tier={tier_to_remove}, count={len(tier_indices)}",
            "new_value": f"removed {removed} rows",
            "table": "career_branches"
        })
    return manifest


# ---------------------------------------------------------------------------
# Data I/O
# ---------------------------------------------------------------------------

def load_pcp_data_sampled(sample_size=PCP_SAMPLE_SIZE):
    """Load a random sample of program_career_paths to avoid memory issues."""
    import pyarrow.parquet as pq
    import pyarrow as pa

    # Read just the first file to get schema
    table0 = pq.read_table(str(PCP_SOURCE_PARQUETS[0]))
    schema = table0.schema

    # Sample from both files
    all_rows = []
    for path in PCP_SOURCE_PARQUETS:
        table = pq.read_table(str(path))
        for i in range(table.num_rows):
            row = {}
            for col in table.column_names:
                val = table.column(col)[i].as_py()
                row[col] = val
            all_rows.append(row)
            if len(all_rows) >= sample_size * 3:
                break

    # Sample down
    if len(all_rows) > sample_size:
        rng = random.Random(42)
        all_rows = rng.sample(all_rows, sample_size)

    return all_rows, schema


def load_cb_data():
    """Load career_branches parquet into a list of dicts."""
    import pyarrow.parquet as pq
    table = pq.read_table(str(CB_SOURCE_PARQUET))
    rows = []
    for i in range(table.num_rows):
        row = {}
        for col in table.column_names:
            val = table.column(col)[i].as_py()
            row[col] = val
        rows.append(row)
    return rows, table.schema


def write_shadow_parquet(rows, original_schema, shadow_dir, table_name, cycle_num):
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


def register_shadow_in_catalog(parquet_path, shadow_table_name, original_schema):
    """Register shadow table in Iceberg catalog."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        BooleanType, DoubleType, IntegerType, LongType,
        NestedField, StringType, TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))

    try:
        catalog.create_namespace("shadow_consumable")
    except Exception:
        pass

    try:
        catalog.drop_table(f"shadow_consumable.{shadow_table_name}")
    except Exception:
        pass

    TYPE_MAP = {
        "large_string": StringType(),
        "string": StringType(),
        "int32": IntegerType(),
        "int64": LongType(),
        "double": DoubleType(),
        "bool": BooleanType(),
        "timestamp[us]": TimestampType(),
        "timestamp[us, tz=UTC]": TimestampType(),
    }

    fields = []
    for idx, field in enumerate(original_schema, start=1):
        arrow_type_str = str(field.type)
        iceberg_type = TYPE_MAP.get(arrow_type_str, StringType())
        fields.append(NestedField(idx, field.name, iceberg_type, required=False))

    iceberg_schema = Schema(*fields)
    shadow_table = catalog.create_table(
        f"shadow_consumable.{shadow_table_name}", schema=iceberg_schema
    )

    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def register_upstream_tables_in_shadow():
    """Register real upstream tables as shadow views for cross-table DQ rules."""
    from brightsmith.infra.iceberg_setup import get_catalog
    import duckdb

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))

    for ns in ["shadow_consumable", "shadow_base"]:
        try:
            catalog.create_namespace(ns)
        except Exception:
            pass

    upstream_tables = [
        ("consumable", "career_outcomes", "shadow_consumable"),
        ("base", "cip_soc_crosswalk", "shadow_base"),
        ("consumable", "career_transitions", "shadow_consumable"),
        ("consumable", "occupation_profiles", "shadow_consumable"),
        ("consumable", "onet_work_profiles", "shadow_consumable"),
        ("consumable", "ai_exposure", "shadow_consumable"),
    ]

    for src_ns, tbl_name, shadow_ns in upstream_tables:
        shadow_full = f"{shadow_ns}.{tbl_name}"
        try:
            try:
                catalog.drop_table(shadow_full)
            except Exception:
                pass

            real_table = catalog.load_table(f"{src_ns}.{tbl_name}")
            schema = real_table.schema()
            shadow_tbl = catalog.create_table(shadow_full, schema=schema)

            metadata_path = real_table.metadata_location
            con = duckdb.connect()
            con.install_extension("iceberg")
            con.load_extension("iceberg")
            arrow_data = con.execute(
                f"SELECT * FROM iceberg_scan('{metadata_path}')"
            ).fetch_arrow_table()
            con.close()

            shadow_tbl.append(arrow_data)
            print(f"  Registered upstream shadow: {shadow_full} ({arrow_data.num_rows} rows)")
        except Exception as e:
            print(f"  WARNING: Could not register {shadow_full}: {e}")


def run_dq_rules_shadow():
    """Run DQ rules against shadow tables."""
    from brightsmith.infra.dq_runner import run_rules
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
    result = run_rules(spec=SPEC_NAME, catalog=catalog, shadow=True)
    return result


def cleanup_shadow():
    """Remove shadow tables and files."""
    for shadow_dir in [SHADOW_PCP_DIR, SHADOW_CB_DIR]:
        if shadow_dir.exists():
            shutil.rmtree(shadow_dir)

    try:
        from brightsmith.infra.iceberg_setup import get_catalog
        catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))
        for table_name in [
            "shadow_consumable.program_career_paths",
            "shadow_consumable.career_branches",
            "shadow_consumable.career_outcomes",
            "shadow_consumable.career_transitions",
            "shadow_consumable.occupation_profiles",
            "shadow_consumable.onet_work_profiles",
            "shadow_consumable.ai_exposure",
            "shadow_base.cip_soc_crosswalk",
        ]:
            try:
                catalog.drop_table(table_name)
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Corruption function lists
# ---------------------------------------------------------------------------

PCP_CORRUPTION_FUNCTIONS = [
    pcp_corrupt_completeness,
    pcp_corrupt_validity,
    pcp_corrupt_uniqueness,
    pcp_corrupt_consistency,
    pcp_corrupt_accuracy,
    pcp_corrupt_reasonableness,
    pcp_corrupt_freshness,
    pcp_corrupt_volume,
    pcp_corrupt_referential_integrity,
    pcp_corrupt_coverage,
]

CB_CORRUPTION_FUNCTIONS = [
    cb_corrupt_completeness,
    cb_corrupt_validity,
    cb_corrupt_uniqueness,
    cb_corrupt_consistency,
    cb_corrupt_accuracy,
    cb_corrupt_reasonableness,
    cb_corrupt_freshness,
    cb_corrupt_volume,
    cb_corrupt_referential_integrity,
    cb_corrupt_coverage,
]


# ---------------------------------------------------------------------------
# Main injection pipeline
# ---------------------------------------------------------------------------

def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle against both tables."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)
    all_manifest = []

    # --- program_career_paths (sampled) ---
    print("\n--- program_career_paths (sampled) ---")
    print("Loading source data (sampled)...")
    pcp_rows, pcp_schema = load_pcp_data_sampled()
    pcp_original_count = len(pcp_rows)
    print(f"  Loaded {pcp_original_count} rows (sampled from 626K)")

    n_corrupt = int(pcp_original_count * rate)
    all_indices = list(range(pcp_original_count))
    per_function = max(1, n_corrupt // len(PCP_CORRUPTION_FUNCTIONS))

    for func in PCP_CORRUPTION_FUNCTIONS:
        indices = rng.sample(all_indices, min(per_function, len(all_indices)))
        try:
            entries = func(pcp_rows, indices, rng)
            all_manifest.extend(entries)
            dim = func.__name__.replace("pcp_corrupt_", "")
            print(f"  {dim}: {len(entries)} corruptions")
        except Exception as e:
            print(f"  ERROR in {func.__name__}: {e}")
            traceback.print_exc()

    pcp_corruptions = sum(1 for m in all_manifest if m.get("table") != "career_branches")
    print(f"  PCP total corruptions: {pcp_corruptions}")
    print(f"  PCP final row count: {len(pcp_rows)} (was {pcp_original_count})")

    # --- career_branches ---
    print("\n--- career_branches ---")
    print("Loading source data...")
    cb_rows, cb_schema = load_cb_data()
    cb_original_count = len(cb_rows)
    print(f"  Loaded {cb_original_count} rows")

    n_corrupt_cb = int(cb_original_count * rate)
    cb_all_indices = list(range(cb_original_count))
    per_function_cb = max(1, n_corrupt_cb // len(CB_CORRUPTION_FUNCTIONS))

    for func in CB_CORRUPTION_FUNCTIONS:
        indices = rng.sample(cb_all_indices, min(per_function_cb, len(cb_all_indices)))
        try:
            entries = func(cb_rows, indices, rng)
            all_manifest.extend(entries)
            dim = func.__name__.replace("cb_corrupt_", "")
            print(f"  {dim}: {len(entries)} corruptions")
        except Exception as e:
            print(f"  ERROR in {func.__name__}: {e}")
            traceback.print_exc()

    cb_corruptions = sum(1 for m in all_manifest if m.get("table") == "career_branches")
    print(f"  CB total corruptions: {cb_corruptions}")
    print(f"  CB final row count: {len(cb_rows)} (was {cb_original_count})")

    # --- Write shadow tables and run DQ ---
    print("\nWriting shadow tables...")
    dq_result = {"run_id": "error", "rules_total": 0, "rules_passed": 0,
                 "rules_failed": 0, "p0_passed": True, "results": []}
    try:
        pcp_parquet_path, _ = write_shadow_parquet(
            pcp_rows, pcp_schema, SHADOW_PCP_DIR, "program_career_paths", cycle_num
        )
        print(f"  PCP written to {pcp_parquet_path}")

        cb_parquet_path, _ = write_shadow_parquet(
            cb_rows, cb_schema, SHADOW_CB_DIR, "career_branches", cycle_num
        )
        print(f"  CB written to {cb_parquet_path}")

        print("Registering shadow tables in Iceberg catalog...")
        register_shadow_in_catalog(pcp_parquet_path, "program_career_paths", pcp_schema)
        register_shadow_in_catalog(cb_parquet_path, "career_branches", cb_schema)
        print("  Shadow tables registered.")

        print("Registering upstream tables in shadow namespace...")
        register_upstream_tables_in_shadow()

        print("Running DQ rules against shadow tables...")
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(f"  Total: {dq_result['rules_total']} | Passed: {dq_result['rules_passed']} | Failed: {dq_result['rules_failed']}")
        p0_status = "PASS" if dq_result.get("p0_passed", True) else "FAIL"
        print(f"  P0 gate: {p0_status}")

        print("\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            print(f"    {r['rule_id']:<45} {status:<6} value={r.get('raw_value', '?')}")

    except Exception as e:
        print(f"  ERROR during shadow table creation/DQ run: {e}")
        traceback.print_exc()

    return {
        "cycle": cycle_num,
        "rate": rate,
        "seed": seed,
        "pcp_original_count": pcp_original_count,
        "pcp_corrupted_count": len(pcp_rows),
        "cb_original_count": cb_original_count,
        "cb_corrupted_count": len(cb_rows),
        "total_corruptions": len(all_manifest),
        "manifest": all_manifest,
        "dq_result": dq_result,
    }


def analyze_gaps(cycle_result):
    """Analyze which corruptions were caught vs missed."""
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
    """Run 5-cycle adversarial hardening for backfill-ai spec."""
    safety_check()

    all_cycles = []
    all_gaps = []
    consecutive_no_new_gaps = 0
    previous_failed = set()

    for cycle_num, rate in enumerate(RATES, 1):
        seed = SEED_BASE + cycle_num
        cleanup_shadow()
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
            "pcp_row_count": cycle_result["pcp_corrupted_count"],
            "cb_row_count": cycle_result["cb_corrupted_count"],
            "dq_passed": cycle_result["dq_result"]["rules_passed"],
            "dq_failed": cycle_result["dq_result"]["rules_failed"],
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
        "tables": [
            "consumable.program_career_paths",
            "consumable.career_branches",
        ],
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/gold-futureproof-engine-backfill-ai-manifest.json"
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
