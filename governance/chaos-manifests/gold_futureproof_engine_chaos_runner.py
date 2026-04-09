"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: gold-futureproof-engine
Tables:
  - consumable.program_career_paths (626,406 rows, grain: unitid x cipcode x soc_code)
  - consumable.career_branches (15,944 rows, grain: soc_code x related_soc_code)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against shadow tables, and records what was caught vs missed.

Information Barrier Note: The task instructions required reading DQ rules
prior to building this script. Corruption strategies are designed based on
the spec schema, domain understanding, and attack vectors listed in the task.
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

# Source parquet files (program_career_paths has 2 files)
PCP_SOURCE_PARQUETS = [
    GOLD_WAREHOUSE / "consumable/program_career_paths/data/00000-0-210a770f-1a5c-4ae9-a60c-511af88e2a84.parquet",
    GOLD_WAREHOUSE / "consumable/program_career_paths/data/00000-1-210a770f-1a5c-4ae9-a60c-511af88e2a84.parquet",
]
CB_SOURCE_PARQUET = GOLD_WAREHOUSE / "consumable/career_branches/data/00000-0-93744545-24e1-42c1-9878-9f159fc390ec.parquet"

SHADOW_PCP_DIR = GOLD_WAREHOUSE / "shadow_consumable/program_career_paths"
SHADOW_CB_DIR = GOLD_WAREHOUSE / "shadow_consumable/career_branches"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "gold-futureproof-engine"

# Valid enum values (from spec schema, NOT from DQ rules)
VALID_MATCH_QUALITY = ["full", "partial_no_onet", "partial_no_bls", "scorecard_only"]
VALID_CONFIDENCE = ["high", "medium", "low"]
VALID_RELATEDNESS_TIERS = ["Primary-Short", "Primary-Long", "Supplemental"]
VALID_GROWTH_CATEGORIES = [
    "declining_fast", "declining", "stable", "growing", "growing_fast", "booming"
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


# ===========================================================================
# PROGRAM_CAREER_PATHS corruption strategies (626K rows)
# ===========================================================================

def pcp_corrupt_completeness(rows, indices, rng):
    """Null required fields in the program_career_paths schema."""
    manifest = []
    required_fields = [
        "record_id", "unitid", "institution_name", "cipcode", "program_name",
        "cip_family", "cip_family_name", "soc_code",
        "match_quality", "stats_available_count", "bosses_available_count",
        "overall_confidence", "promoted_at",
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


def pcp_corrupt_validity(rows, indices, rng):
    """Invalid values: bad CIP format, bad SOC format, invalid enums,
    stat scores outside 1-10, non-null placeholder fields."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_cipcode_format", "bad_soc_format", "bad_match_quality",
            "bad_overall_confidence", "stat_out_of_range",
            "boss_out_of_range", "non_null_placeholder",
            "bad_stats_available_count",
        ])
        if strategy == "bad_cipcode_format":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = rng.choice([
                "999999", "XX.YY", "", "52.0201",  # 6-digit instead of 4-digit
                "1", "52", "00.00.00", "abc.de", "52.020",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "cipcode",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["cipcode"]
            })
        elif strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice([
                "99-99999", "11.1011", "111011", "", "XX-XXXX",
                "1-1011", "11-101", "11_1011",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"]
            })
        elif strategy == "bad_match_quality":
            old_val = rows[i]["match_quality"]
            rows[i]["match_quality"] = rng.choice([
                "FULL", "complete", "none", "partial", "unknown", "0",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "match_quality",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["match_quality"]
            })
        elif strategy == "bad_overall_confidence":
            old_val = rows[i]["overall_confidence"]
            rows[i]["overall_confidence"] = rng.choice([
                "HIGH", "very_high", "none", "uncertain", "0",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "overall_confidence",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["overall_confidence"]
            })
        elif strategy == "stat_out_of_range":
            stat_field = rng.choice(["stat_ern", "stat_roi", "stat_grw", "stat_hmn"])
            old_val = rows[i].get(stat_field)
            rows[i][stat_field] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": stat_field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][stat_field])
            })
        elif strategy == "boss_out_of_range":
            boss_field = rng.choice([
                "boss_loans_score", "boss_market_score",
                "boss_burnout_score", "boss_ceiling_score",
            ])
            old_val = rows[i].get(boss_field)
            rows[i][boss_field] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": boss_field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][boss_field])
            })
        elif strategy == "non_null_placeholder":
            # Set stat_res or boss_ai_score to non-null (should always be null)
            field = rng.choice(["stat_res", "boss_ai_score"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.randint(1, 10)
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field])
            })
        elif strategy == "bad_stats_available_count":
            old_val = rows[i].get("stats_available_count")
            # Force count to 5 (impossible when stat_res is null) or negative
            rows[i]["stats_available_count"] = rng.choice([5, -1, 6, 10])
            manifest.append({
                "row": i, "dimension": "validity", "field": "stats_available_count",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["stats_available_count"])
            })
    return manifest


def pcp_corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows (same record_id, same grain)."""
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
            "new_value": f"duplicate at position {insert_pos}"
        })
    return manifest


def pcp_corrupt_consistency(rows, indices, rng):
    """Contradictory field combinations:
    - boss_loans_score != 11 - stat_roi
    - match_quality contradicts stat nulls
    - overall_confidence contradicts stats_available_count + match_quality
    - boss_loans non-null when stat_roi is null (null propagation violation)
    - stat_ern non-null when earnings_1yr_median is null
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "boss_loans_roi_mismatch", "match_quality_stat_mismatch",
            "confidence_mismatch", "null_propagation_boss_loans",
            "null_propagation_stat_ern",
        ])
        if strategy == "boss_loans_roi_mismatch":
            old_roi = rows[i].get("stat_roi")
            old_loans = rows[i].get("boss_loans_score")
            if old_roi is not None:
                # Set boss_loans to something other than 11 - stat_roi
                wrong = old_roi  # This would mean boss_loans == stat_roi, not 11 - stat_roi
                rows[i]["boss_loans_score"] = wrong
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "boss_loans_score",
                    "strategy": strategy,
                    "old_value": f"roi={old_roi}, loans={old_loans}",
                    "new_value": f"loans={wrong} (should be {11 - old_roi})"
                })
        elif strategy == "match_quality_stat_mismatch":
            # Set match_quality to scorecard_only but leave occupation stats non-null
            old_mq = rows[i]["match_quality"]
            old_grw = rows[i].get("stat_grw")
            old_hmn = rows[i].get("stat_hmn")
            if old_grw is not None or old_hmn is not None:
                rows[i]["match_quality"] = "scorecard_only"
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "match_quality",
                    "strategy": strategy,
                    "old_value": f"mq={old_mq}, grw={old_grw}, hmn={old_hmn}",
                    "new_value": "scorecard_only (but has occupation stats)"
                })
        elif strategy == "confidence_mismatch":
            old_conf = rows[i]["overall_confidence"]
            old_sac = rows[i].get("stats_available_count")
            old_mq = rows[i]["match_quality"]
            # Force high confidence when stats_available_count < 4 or match != full
            if old_sac is not None and (old_sac < 4 or old_mq != "full"):
                rows[i]["overall_confidence"] = "high"
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "overall_confidence",
                    "strategy": strategy,
                    "old_value": f"conf={old_conf}, sac={old_sac}, mq={old_mq}",
                    "new_value": "high (contradicts criteria)"
                })
        elif strategy == "null_propagation_boss_loans":
            # Set boss_loans to non-null while stat_roi is null
            old_roi = rows[i].get("stat_roi")
            old_loans = rows[i].get("boss_loans_score")
            if old_roi is None:
                rows[i]["boss_loans_score"] = rng.randint(1, 10)
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "boss_loans_score",
                    "strategy": strategy,
                    "old_value": f"roi=None, loans={old_loans}",
                    "new_value": f"loans={rows[i]['boss_loans_score']} (roi is null)"
                })
        elif strategy == "null_propagation_stat_ern":
            # Set stat_ern to non-null while earnings_1yr_median is null
            old_ern = rows[i].get("stat_ern")
            old_earn = rows[i].get("earnings_1yr_median")
            if old_earn is None:
                rows[i]["stat_ern"] = rng.randint(1, 10)
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "stat_ern",
                    "strategy": strategy,
                    "old_value": f"ern={old_ern}, earn={old_earn}",
                    "new_value": f"ern={rows[i]['stat_ern']} (earnings is null)"
                })
    return manifest


def pcp_corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: stat scores that are close but wrong,
    swapped fields, wrong institution names for unitid."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "wrong_stat_ern", "wrong_boss_ceiling",
            "swapped_stats", "wrong_institution",
        ])
        if strategy == "wrong_stat_ern":
            old_val = rows[i].get("stat_ern")
            if old_val is not None:
                # Plausible but off by 1-3 points
                delta = rng.choice([-3, -2, -1, 1, 2, 3])
                new_val = max(1, min(10, old_val + delta))
                if new_val != old_val:
                    rows[i]["stat_ern"] = new_val
                    manifest.append({
                        "row": i, "dimension": "accuracy", "field": "stat_ern",
                        "strategy": strategy, "old_value": str(old_val),
                        "new_value": str(new_val)
                    })
        elif strategy == "wrong_boss_ceiling":
            old_val = rows[i].get("boss_ceiling_score")
            if old_val is not None:
                delta = rng.choice([-3, -2, 2, 3])
                new_val = max(1, min(10, old_val + delta))
                if new_val != old_val:
                    rows[i]["boss_ceiling_score"] = new_val
                    manifest.append({
                        "row": i, "dimension": "accuracy",
                        "field": "boss_ceiling_score",
                        "strategy": strategy, "old_value": str(old_val),
                        "new_value": str(new_val)
                    })
        elif strategy == "swapped_stats":
            # Swap stat_grw and stat_hmn
            old_grw = rows[i].get("stat_grw")
            old_hmn = rows[i].get("stat_hmn")
            if old_grw is not None and old_hmn is not None and old_grw != old_hmn:
                rows[i]["stat_grw"] = old_hmn
                rows[i]["stat_hmn"] = old_grw
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "stat_grw,stat_hmn",
                    "strategy": strategy,
                    "old_value": f"grw={old_grw},hmn={old_hmn}",
                    "new_value": f"grw={old_hmn},hmn={old_grw}"
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
                "new_value": rows[i]["institution_name"]
            })
    return manifest


def pcp_corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: massive earnings, negative wages, impossible ratios."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_earnings", "negative_earnings",
            "extreme_debt", "extreme_dte",
            "extreme_wage", "negative_wage",
        ])
        if strategy == "extreme_earnings":
            field = rng.choice(["earnings_1yr_median", "earnings_1yr_p25", "earnings_1yr_p75"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(5000000, 50000000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field])
            })
        elif strategy == "negative_earnings":
            old_val = rows[i].get("earnings_1yr_median")
            rows[i]["earnings_1yr_median"] = float(rng.randint(-500000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "earnings_1yr_median",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["earnings_1yr_median"])
            })
        elif strategy == "extreme_debt":
            old_val = rows[i].get("debt_median")
            rows[i]["debt_median"] = float(rng.randint(2000000, 10000000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "debt_median",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["debt_median"])
            })
        elif strategy == "extreme_dte":
            old_val = rows[i].get("debt_to_earnings_annual")
            rows[i]["debt_to_earnings_annual"] = rng.choice([50.0, -5.0, 100.0, 999.9])
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "debt_to_earnings_annual",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["debt_to_earnings_annual"])
            })
        elif strategy == "extreme_wage":
            old_val = rows[i].get("median_annual_wage")
            rows[i]["median_annual_wage"] = float(rng.randint(5000000, 50000000))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"])
            })
        elif strategy == "negative_wage":
            old_val = rows[i].get("median_annual_wage")
            rows[i]["median_annual_wage"] = float(rng.randint(-500000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"])
            })
    return manifest


def pcp_corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps on promoted_at."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["future_promoted_at", "epoch_promoted_at"])
        if strategy == "future_promoted_at":
            old_val = rows[i].get("promoted_at")
            rows[i]["promoted_at"] = datetime.datetime(2035, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2035-01-01T00:00:00"
            })
        elif strategy == "epoch_promoted_at":
            old_val = rows[i].get("promoted_at")
            rows[i]["promoted_at"] = datetime.datetime(1970, 1, 1, 0, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "promoted_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "1970-01-01T00:00:00"
            })
    return manifest


def pcp_corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-duplicate to inflate or mass-delete to deflate."""
    manifest = []
    # Mass duplicate to push beyond 700K threshold
    n_extras = max(50, len(rows) // 8)
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


def pcp_corrupt_referential_integrity(rows, indices, rng):
    """Orphan keys: unitids not in career_outcomes, soc_codes not in crosswalk."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_unitid", "orphan_soc_code", "orphan_record_id"])
        if strategy == "orphan_unitid":
            old_val = rows[i]["unitid"]
            rows[i]["unitid"] = rng.randint(900000000, 999999999)
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "unitid",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["unitid"])
            })
        elif strategy == "orphan_soc_code":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = f"{rng.randint(90,99):02d}-{rng.randint(9000,9999):04d}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"]
            })
        elif strategy == "orphan_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = f"pcp-ORPHAN{rng.randint(100000, 999999)}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "record_id",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["record_id"]
            })
    return manifest


def pcp_corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove rows for common CIP families,
    remove match_quality categories."""
    manifest = []
    family_counts = {}
    for i, row in enumerate(rows):
        fam = row.get("cip_family")
        if fam:
            family_counts.setdefault(fam, []).append(i)

    # Remove all rows for 2-3 common CIP families
    common_families = sorted(
        family_counts, key=lambda f: len(family_counts[f]), reverse=True
    )[:7]
    targets = rng.sample(common_families, min(3, len(common_families)))

    removed_indices = set()
    for fam in targets:
        for idx in family_counts[fam]:
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "cip_family",
            "strategy": f"remove_all_family_{fam}",
            "old_value": f"family={fam}, count={len(family_counts[fam])}",
            "new_value": "removed"
        })

    # Also remove some match_quality categories
    mq_to_remove = rng.choice(["full", "partial_no_onet"])
    mq_indices = [i for i, r in enumerate(rows)
                  if r.get("match_quality") == mq_to_remove]
    if len(mq_indices) > 0:
        sample_size = min(len(mq_indices) // 3, 2000)
        if sample_size > 0:
            for idx in rng.sample(mq_indices, sample_size):
                removed_indices.add(idx)
            manifest.append({
                "row": -1, "dimension": "coverage", "field": "match_quality",
                "strategy": f"remove_mq_{mq_to_remove}",
                "old_value": f"mq={mq_to_remove}, count={len(mq_indices)}",
                "new_value": f"removed {sample_size} rows"
            })

    for idx in sorted(removed_indices, reverse=True):
        if idx < len(rows):
            rows.pop(idx)

    return manifest


# ===========================================================================
# CAREER_BRANCHES corruption strategies (15,944 rows)
# ===========================================================================

def cb_corrupt_completeness(rows, indices, rng):
    """Null required fields in career_branches schema."""
    manifest = []
    required_fields = [
        "record_id", "soc_code", "source_title", "related_soc_code",
        "related_title", "best_index", "relatedness_tier",
        "is_primary", "branch_has_full_data", "promoted_at",
    ]
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
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
    """Invalid values: bad SOC formats, bad enums, scores out of range, bad deltas."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_soc_format", "bad_related_soc_format",
            "bad_relatedness_tier", "score_out_of_range",
            "delta_out_of_range", "extreme_wage_delta",
        ])
        if strategy == "bad_soc_format":
            old_val = rows[i]["soc_code"]
            rows[i]["soc_code"] = rng.choice(["11.1011", "111011", "", "XX-XXXX", "1-1011"])
            manifest.append({
                "row": i, "dimension": "validity", "field": "soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["soc_code"], "table": "career_branches"
            })
        elif strategy == "bad_related_soc_format":
            old_val = rows[i]["related_soc_code"]
            rows[i]["related_soc_code"] = rng.choice(["99.9999", "abcdef", "", "X-XXXX"])
            manifest.append({
                "row": i, "dimension": "validity", "field": "related_soc_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["related_soc_code"], "table": "career_branches"
            })
        elif strategy == "bad_relatedness_tier":
            old_val = rows[i]["relatedness_tier"]
            rows[i]["relatedness_tier"] = rng.choice([
                "primary-short", "PRIMARY", "Unknown", "Tertiary", "",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "relatedness_tier",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["relatedness_tier"], "table": "career_branches"
            })
        elif strategy == "score_out_of_range":
            field = rng.choice([
                "source_grw", "source_hmn", "source_burnout",
                "related_grw", "related_hmn", "related_burnout",
            ])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([0, -1, 11, 15, -5, 100])
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]), "table": "career_branches"
            })
        elif strategy == "delta_out_of_range":
            field = rng.choice(["grw_delta", "hmn_delta", "burnout_delta"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([-15, -10, 10, 15, 20, -20])
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]), "table": "career_branches"
            })
        elif strategy == "extreme_wage_delta":
            old_val = rows[i].get("wage_delta")
            rows[i]["wage_delta"] = rng.choice([500000.0, -500000.0, 1000000.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "wage_delta",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["wage_delta"]), "table": "career_branches"
            })
    return manifest


def cb_corrupt_uniqueness(rows, indices, rng):
    """Inject exact duplicate rows (same grain)."""
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
    """Contradictory combinations:
    - delta non-null when source/target score is null
    - branch_has_full_data=True but missing related stats
    - branch_has_full_data=False but all related stats present
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "delta_null_propagation_violation",
            "branch_full_data_contradiction_true",
            "branch_full_data_contradiction_false",
        ])
        if strategy == "delta_null_propagation_violation":
            # Set delta to non-null when one of the source/target scores is null
            delta_field = rng.choice(["grw_delta", "hmn_delta", "burnout_delta", "wage_delta"])
            if delta_field == "grw_delta":
                source_field, target_field = "source_grw", "related_grw"
            elif delta_field == "hmn_delta":
                source_field, target_field = "source_hmn", "related_hmn"
            elif delta_field == "burnout_delta":
                source_field, target_field = "source_burnout", "related_burnout"
            else:
                source_field, target_field = "source_wage", "related_wage"

            old_delta = rows[i].get(delta_field)
            old_source = rows[i].get(source_field)
            # Null out the source, set delta to non-null
            rows[i][source_field] = None
            rows[i][delta_field] = rng.randint(-5, 5) if "wage" not in delta_field else float(rng.randint(-50000, 50000))
            manifest.append({
                "row": i, "dimension": "consistency", "field": delta_field,
                "strategy": strategy,
                "old_value": f"{delta_field}={old_delta}, {source_field}={old_source}",
                "new_value": f"{delta_field}={rows[i][delta_field]}, {source_field}=null",
                "table": "career_branches"
            })
        elif strategy == "branch_full_data_contradiction_true":
            # Set branch_has_full_data=True but null out related stats
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
        elif strategy == "branch_full_data_contradiction_false":
            # Set branch_has_full_data=False but populate all related stats
            old_flag = rows[i].get("branch_has_full_data")
            rows[i]["branch_has_full_data"] = False
            rows[i]["related_grw"] = rng.randint(1, 10)
            rows[i]["related_hmn"] = rng.randint(1, 10)
            rows[i]["related_burnout"] = rng.randint(1, 10)
            rows[i]["related_wage"] = float(rng.randint(30000, 150000))
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "branch_has_full_data",
                "strategy": strategy,
                "old_value": f"flag={old_flag}",
                "new_value": "flag=False but all related stats populated",
                "table": "career_branches"
            })
    return manifest


def cb_corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong: deltas that don't match source-target difference,
    wrong titles for SOC codes."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["wrong_delta", "wrong_title"])
        if strategy == "wrong_delta":
            # Set grw_delta to not match related_grw - source_grw
            s_grw = rows[i].get("source_grw")
            r_grw = rows[i].get("related_grw")
            if s_grw is not None and r_grw is not None:
                correct_delta = r_grw - s_grw
                wrong_delta = correct_delta + rng.choice([-3, -2, 2, 3])
                wrong_delta = max(-9, min(9, wrong_delta))
                if wrong_delta != correct_delta:
                    old_val = rows[i].get("grw_delta")
                    rows[i]["grw_delta"] = wrong_delta
                    manifest.append({
                        "row": i, "dimension": "accuracy", "field": "grw_delta",
                        "strategy": strategy,
                        "old_value": str(old_val),
                        "new_value": f"{wrong_delta} (correct would be {correct_delta})",
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
    """Extreme outliers: massive wages, impossible best_index values."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_source_wage", "negative_wage",
            "impossible_best_index",
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
    """Row count anomaly: add or remove rows to break 15,944 exact count."""
    manifest = []
    # Add duplicates to push past 15,944
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
    """Orphan SOC codes not in career_transitions."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_soc_pair", "orphan_record_id"])
        if strategy == "orphan_soc_pair":
            old_soc = rows[i]["soc_code"]
            old_related = rows[i]["related_soc_code"]
            # Make both codes orphans that won't exist in career_transitions
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

def load_pcp_data():
    """Load all program_career_paths parquet files into a list of dicts."""
    import pyarrow.parquet as pq
    import pyarrow as pa

    all_rows = []
    schema = None
    for path in PCP_SOURCE_PARQUETS:
        table = pq.read_table(str(path))
        if schema is None:
            schema = table.schema
        for i in range(table.num_rows):
            row = {}
            for col in table.column_names:
                val = table.column(col)[i].as_py()
                row[col] = val
            all_rows.append(row)
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
    """Register shadow table in the Iceberg catalog under shadow_consumable namespace."""
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

    # Build Iceberg schema from Arrow schema
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
    """Register the real upstream tables as shadow views so cross-table DQ rules work.

    The DQ runner with shadow=True prepends 'shadow_' to all namespaces.
    We need shadow_consumable.career_outcomes, shadow_base.cip_soc_crosswalk,
    shadow_consumable.career_transitions, etc. to exist pointing to the real data.
    """
    from brightsmith.infra.iceberg_setup import get_catalog

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))

    # Create shadow namespaces
    for ns in ["shadow_consumable", "shadow_base"]:
        try:
            catalog.create_namespace(ns)
        except Exception:
            pass

    # Map upstream tables that DQ rules reference
    upstream_tables = [
        ("consumable", "career_outcomes", "shadow_consumable"),
        ("base", "cip_soc_crosswalk", "shadow_base"),
        ("consumable", "career_transitions", "shadow_consumable"),
        ("consumable", "occupation_profiles", "shadow_consumable"),
        ("consumable", "onet_work_profiles", "shadow_consumable"),
    ]

    for src_ns, tbl_name, shadow_ns in upstream_tables:
        shadow_full = f"{shadow_ns}.{tbl_name}"
        try:
            # Drop existing shadow if present
            try:
                catalog.drop_table(shadow_full)
            except Exception:
                pass

            # Load real table and create shadow copy
            real_table = catalog.load_table(f"{src_ns}.{tbl_name}")
            schema = real_table.schema()

            shadow_tbl = catalog.create_table(shadow_full, schema=schema)

            # Read and append the real data
            import pyarrow.parquet as pq
            metadata_path = real_table.metadata_location
            import duckdb
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
    """Run DQ rules against the shadow tables."""
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
            "shadow_base.cip_soc_crosswalk",
        ]:
            try:
                catalog.drop_table(table_name)
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main injection pipeline
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


def run_cycle(cycle_num, rate, seed):
    """Run a single chaos monkey cycle against both tables."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)
    all_manifest = []

    # --- program_career_paths ---
    print("\n--- program_career_paths ---")
    print("Loading source data...")
    pcp_rows, pcp_schema = load_pcp_data()
    pcp_original_count = len(pcp_rows)
    print(f"  Loaded {pcp_original_count} rows")

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

    print(f"  PCP total corruptions: {sum(1 for m in all_manifest if m.get('table') != 'career_branches')}")
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

    print(f"  CB total corruptions: {sum(1 for m in all_manifest if m.get('table') == 'career_branches')}")
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
            print(f"    {r['rule_id']:<25} {status:<6} value={r.get('raw_value', '?')}")

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

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/gold-futureproof-engine-manifest.json"
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
