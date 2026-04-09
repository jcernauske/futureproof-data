"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: gold-occupation-profiles-bls-ooh
Table: consumable.occupation_profiles (832 rows)

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.

Information Barrier: This script does NOT read DQ rule definitions.
It injects corruptions based solely on the table schema and domain
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
SOURCE_PARQUET = PROJECT_ROOT / "data/gold/iceberg_warehouse/consumable/occupation_profiles/data/00000-0-e32f8f88-cdcf-445e-b785-68dbc0d62c36.parquet"
SHADOW_DIR = PROJECT_ROOT / "data/gold/iceberg_warehouse/shadow_consumable/occupation_profiles"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"
CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"
GOLD_WAREHOUSE = PROJECT_ROOT / "data/gold/iceberg_warehouse"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "gold-occupation-profiles-bls-ooh"
TABLE_NAME = "consumable.occupation_profiles"

# Grain fields from the spec
GRAIN_FIELDS = ["soc_code"]
GRAIN_PREFIX = "op"

# Valid SOC major group codes (22 groups)
VALID_SOC_MAJOR_GROUPS = [
    "11", "13", "15", "17", "19", "21", "23", "25", "27", "29",
    "31", "33", "35", "37", "39", "41", "43", "45", "47", "49",
    "51", "53",
]

# Valid growth categories
VALID_GROWTH_CATEGORIES = [
    "declining_fast", "declining", "stable", "growing", "growing_fast", "booming",
]

# Valid confidence tiers
VALID_CONFIDENCE_TIERS = ["high", "medium", "low"]

# Valid wage tiers
VALID_WAGE_TIERS = ["low", "below_average", "above_average", "high", "very_high"]

# Valid education codes (1-8)
VALID_EDUCATION_CODES = list(range(1, 9))

# Broad occupation codes (exactly 7)
BROAD_OCCUPATION_CODES = [
    "13-1020", "13-2020", "29-2010", "31-1120",
    "39-7010", "47-4090", "51-2090",
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
# Corruption strategies -- one per DQ dimension, targeting Gold schema
# ---------------------------------------------------------------------------

def corrupt_completeness(rows, indices, rng):
    """Null out required fields in the Gold schema."""
    manifest = []
    required_fields = [
        "record_id", "soc_code", "occupation_title",
        "soc_major_group", "soc_major_group_name",
        "broad_occupation_flag", "catchall_flag",
        "growth_category", "wage_available",
        "confidence_tier", "data_completeness",
        "backs_stats", "backs_bosses",
        "source_load_date", "promoted_at",
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
    """Invalid values: bad SOC format, wrong growth_category, bad GRW score range,
    invalid wage tier, bad confidence tier, data_completeness out of valid set,
    bad education code, invalid soc_major_group, bad backs_stats/backs_bosses."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_soc_format", "bad_growth_category", "grw_out_of_range",
            "bad_wage_tier", "bad_confidence_tier", "bad_data_completeness",
            "bad_education_code", "bad_soc_major_group",
            "bad_backs_stats", "bad_backs_bosses",
            "grw_rounded_out_of_range", "wage_percentile_out_of_range",
            "negative_employment", "wage_out_of_range",
            "employment_change_pct_extreme",
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
        elif strategy == "grw_out_of_range":
            old_val = rows[i].get("grw_score")
            rows[i]["grw_score"] = rng.choice([0.0, -1.0, 10.5, 15.0, -5.0, 0.5, 11.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": "grw_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["grw_score"]),
            })
        elif strategy == "grw_rounded_out_of_range":
            old_val = rows[i].get("grw_score_rounded")
            rows[i]["grw_score_rounded"] = rng.choice([0, -1, 11, 15, -5, 99])
            manifest.append({
                "row": i, "dimension": "validity", "field": "grw_score_rounded",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["grw_score_rounded"]),
            })
        elif strategy == "bad_wage_tier":
            old_val = rows[i].get("wage_tier")
            rows[i]["wage_tier"] = rng.choice([
                "LOW", "medium", "High", "average", "excellent",
                "very_low", "top", "unknown", "",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "wage_tier",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["wage_tier"],
            })
        elif strategy == "bad_confidence_tier":
            old_val = rows[i].get("confidence_tier")
            rows[i]["confidence_tier"] = rng.choice([
                "very_high", "MEDIUM", "unknown", "null", "0",
                "excellent", "insufficient", "HIGH",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "confidence_tier",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["confidence_tier"],
            })
        elif strategy == "bad_data_completeness":
            old_val = rows[i].get("data_completeness")
            rows[i]["data_completeness"] = rng.choice([
                0.0, 0.25, 0.5, -0.1, 1.5, 0.99, 0.01, 0.33, 2.0,
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "data_completeness",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["data_completeness"]),
            })
        elif strategy == "bad_education_code":
            old_val = rows[i].get("education_code")
            rows[i]["education_code"] = rng.choice([0, -1, 9, 10, 99, -5])
            manifest.append({
                "row": i, "dimension": "validity", "field": "education_code",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["education_code"]),
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
        elif strategy == "bad_backs_stats":
            old_val = rows[i].get("backs_stats")
            rows[i]["backs_stats"] = rng.choice([
                "ERN", "GRW", "ERN,GRW,DEF", "ern,grw", "",
                "EARNINGS,GROWTH", "None", "ERN-GRW",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "backs_stats",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["backs_stats"],
            })
        elif strategy == "bad_backs_bosses":
            old_val = rows[i].get("backs_bosses")
            rows[i]["backs_bosses"] = rng.choice([
                "Market", "Ceiling", "market,ceiling", "Market,Ceiling,Risk",
                "", "MARKET,CEILING", "None", "Market-Ceiling",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "backs_bosses",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["backs_bosses"],
            })
        elif strategy == "wage_percentile_out_of_range":
            field = rng.choice(["wage_percentile_overall", "wage_percentile_education_tier"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.choice([-0.1, 1.1, 1.5, -0.5, 2.0, -1.0])
            manifest.append({
                "row": i, "dimension": "validity", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
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
                100.0, 500000.0, -10000.0, 0.0, 1000000.0, 24999.0, 250001.0,
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"]),
            })
        elif strategy == "employment_change_pct_extreme":
            old_val = rows[i].get("employment_change_pct")
            rows[i]["employment_change_pct"] = rng.choice([
                -100.0, 100.0, -51.0, 61.0, 200.0, -75.0,
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "employment_change_pct",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["employment_change_pct"]),
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
    """Contradictory field combinations specific to Gold zone derived fields.
    - grw_score_rounded != ROUND(grw_score) mismatch
    - market_score_rounded != ROUND(market_score) mismatch
    - soc_major_group != first 2 chars of soc_code
    - confidence_tier contradicts wage_available/broad/catchall flags
    - wage_tier non-null but wage_available = False
    - wage_percentile non-null but wage_available = False
    - data_completeness contradicts actual null counts
    - grw_score vs growth_category monotonic violation
    - broad_occupation_flag AND catchall_flag both True
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "grw_rounded_mismatch", "market_rounded_mismatch",
            "soc_major_group_mismatch", "confidence_tier_contradiction",
            "wage_tier_availability_contradiction",
            "wage_percentile_availability_contradiction",
            "data_completeness_contradiction",
            "grw_growth_category_inversion",
            "broad_catchall_overlap",
        ])
        if strategy == "grw_rounded_mismatch":
            old_rounded = rows[i].get("grw_score_rounded")
            old_grw = rows[i].get("grw_score")
            if old_grw is not None:
                # Set rounded to a value that doesn't match ROUND(grw_score)
                import math
                correct_rounded = int(math.floor(old_grw + 0.5))
                wrong_rounded = correct_rounded + rng.choice([-2, -1, 1, 2, 3])
                wrong_rounded = max(1, min(10, wrong_rounded))
                if wrong_rounded == correct_rounded:
                    wrong_rounded = correct_rounded + 1 if correct_rounded < 10 else correct_rounded - 1
                rows[i]["grw_score_rounded"] = wrong_rounded
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "grw_score_rounded",
                    "strategy": strategy,
                    "old_value": f"grw={old_grw}, rounded={old_rounded}",
                    "new_value": f"rounded={wrong_rounded} (should be {correct_rounded})"
                })
        elif strategy == "market_rounded_mismatch":
            old_rounded = rows[i].get("market_score_rounded")
            old_market = rows[i].get("market_score")
            if old_market is not None:
                import math
                correct_rounded = int(math.floor(old_market + 0.5))
                wrong_rounded = correct_rounded + rng.choice([-2, -1, 1, 2, 3])
                wrong_rounded = max(1, min(10, wrong_rounded))
                if wrong_rounded == correct_rounded:
                    wrong_rounded = correct_rounded + 1 if correct_rounded < 10 else correct_rounded - 1
                rows[i]["market_score_rounded"] = wrong_rounded
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "market_score_rounded",
                    "strategy": strategy,
                    "old_value": f"market={old_market}, rounded={old_rounded}",
                    "new_value": f"rounded={wrong_rounded} (should be {correct_rounded})"
                })
        elif strategy == "soc_major_group_mismatch":
            old_group = rows[i].get("soc_major_group")
            old_soc = rows[i].get("soc_code")
            if old_soc and len(old_soc) >= 2:
                # Set major group to something that doesn't match soc_code prefix
                correct_prefix = old_soc[:2]
                wrong_groups = [g for g in VALID_SOC_MAJOR_GROUPS if g != correct_prefix]
                if wrong_groups:
                    rows[i]["soc_major_group"] = rng.choice(wrong_groups)
                    manifest.append({
                        "row": i, "dimension": "consistency", "field": "soc_major_group",
                        "strategy": strategy,
                        "old_value": f"soc_code={old_soc}, group={old_group}",
                        "new_value": f"group={rows[i]['soc_major_group']} (should be {correct_prefix})"
                    })
        elif strategy == "confidence_tier_contradiction":
            old_tier = rows[i].get("confidence_tier")
            wage_avail = rows[i].get("wage_available")
            broad = rows[i].get("broad_occupation_flag")
            catchall = rows[i].get("catchall_flag")
            # Assign a confidence tier that contradicts the flags
            if wage_avail is False:
                # Should be "low", assign something else
                rows[i]["confidence_tier"] = rng.choice(["high", "medium"])
            elif broad or catchall:
                # Should be "medium", assign something else
                rows[i]["confidence_tier"] = rng.choice(["high", "low"])
            else:
                # Should be "high", assign something else
                rows[i]["confidence_tier"] = rng.choice(["medium", "low"])
            manifest.append({
                "row": i, "dimension": "consistency", "field": "confidence_tier",
                "strategy": strategy,
                "old_value": f"tier={old_tier}, wage_avail={wage_avail}, broad={broad}, catchall={catchall}",
                "new_value": f"tier={rows[i]['confidence_tier']} (contradicts flags)"
            })
        elif strategy == "wage_tier_availability_contradiction":
            old_tier = rows[i].get("wage_tier")
            old_avail = rows[i].get("wage_available")
            if old_avail is True and old_tier is not None:
                # Set wage_available=False but leave wage_tier populated
                rows[i]["wage_available"] = False
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "wage_available",
                    "strategy": strategy,
                    "old_value": f"wage_available={old_avail}, wage_tier={old_tier}",
                    "new_value": f"wage_available=False but wage_tier={old_tier} (contradiction)"
                })
            elif old_avail is False and old_tier is None:
                # Set a non-null wage_tier but keep wage_available=False
                rows[i]["wage_tier"] = rng.choice(VALID_WAGE_TIERS)
                manifest.append({
                    "row": i, "dimension": "consistency", "field": "wage_tier",
                    "strategy": strategy,
                    "old_value": f"wage_available={old_avail}, wage_tier={old_tier}",
                    "new_value": f"wage_tier={rows[i]['wage_tier']} but wage_available=False"
                })
        elif strategy == "wage_percentile_availability_contradiction":
            old_avail = rows[i].get("wage_available")
            if old_avail is True:
                # Set wage_available=False but leave percentiles populated
                old_pct = rows[i].get("wage_percentile_overall")
                rows[i]["wage_available"] = False
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "wage_available,wage_percentile_overall",
                    "strategy": strategy,
                    "old_value": f"wage_available=True, pct={old_pct}",
                    "new_value": f"wage_available=False but percentile still {old_pct}"
                })
            elif old_avail is False:
                # Set non-null percentiles but keep wage_available=False
                rows[i]["wage_percentile_overall"] = rng.uniform(0.0, 1.0)
                rows[i]["wage_percentile_education_tier"] = rng.uniform(0.0, 1.0)
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "wage_percentile_overall,wage_percentile_education_tier",
                    "strategy": strategy,
                    "old_value": f"wage_available=False, pcts=null",
                    "new_value": f"pcts non-null but wage_available=False"
                })
        elif strategy == "data_completeness_contradiction":
            old_dc = rows[i].get("data_completeness")
            # Count actual non-null core fields
            wage = rows[i].get("median_annual_wage")
            empl_curr = rows[i].get("employment_current")
            empl_chg = rows[i].get("employment_change_pct")
            openings = rows[i].get("openings_annual_avg")
            actual_nn = sum(1 for v in [wage, empl_curr, empl_chg, openings] if v is not None)
            correct_dc = actual_nn / 4.0
            # Set to something contradictory
            wrong_dcs = [v for v in [0.0, 0.25, 0.5, 0.75, 1.0] if abs(v - correct_dc) > 0.01]
            if wrong_dcs:
                rows[i]["data_completeness"] = rng.choice(wrong_dcs)
            else:
                rows[i]["data_completeness"] = 0.5
            manifest.append({
                "row": i, "dimension": "consistency", "field": "data_completeness",
                "strategy": strategy,
                "old_value": f"dc={old_dc}, actual_non_nulls={actual_nn}",
                "new_value": f"dc={rows[i]['data_completeness']} (should be {correct_dc})"
            })
        elif strategy == "grw_growth_category_inversion":
            old_grw = rows[i].get("grw_score")
            old_cat = rows[i].get("growth_category")
            if old_grw is not None:
                # Assign a growth category that contradicts the GRW score
                if old_grw < 2.5:
                    rows[i]["growth_category"] = rng.choice(["growing_fast", "booming"])
                elif old_grw < 5.0:
                    rows[i]["growth_category"] = rng.choice(["booming", "growing_fast"])
                elif old_grw < 7.5:
                    rows[i]["growth_category"] = rng.choice(["declining_fast", "declining"])
                else:
                    rows[i]["growth_category"] = rng.choice(["declining_fast", "declining"])
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "growth_category",
                    "strategy": strategy,
                    "old_value": f"grw={old_grw}, cat={old_cat}",
                    "new_value": f"cat={rows[i]['growth_category']} (contradicts grw_score)"
                })
        elif strategy == "broad_catchall_overlap":
            old_broad = rows[i].get("broad_occupation_flag")
            old_catchall = rows[i].get("catchall_flag")
            # Set both to True
            rows[i]["broad_occupation_flag"] = True
            rows[i]["catchall_flag"] = True
            manifest.append({
                "row": i, "dimension": "consistency",
                "field": "broad_occupation_flag,catchall_flag",
                "strategy": strategy,
                "old_value": f"broad={old_broad}, catchall={old_catchall}",
                "new_value": "broad=True, catchall=True (mutual exclusion violation)"
            })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: swapped employment fields,
    wrong soc_major_group_name, wage off by factor, wrong market_score formula."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "swapped_employment", "wrong_soc_group_name",
            "wage_off_by_factor", "wrong_market_formula",
            "wrong_grw_score",
        ])
        if strategy == "swapped_employment":
            old_curr = rows[i].get("employment_current")
            old_proj = rows[i].get("employment_projected")
            if old_curr is not None and old_proj is not None:
                rows[i]["employment_current"] = old_proj
                rows[i]["employment_projected"] = old_curr
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "employment_current,employment_projected",
                    "strategy": strategy,
                    "old_value": f"curr={old_curr},proj={old_proj}",
                    "new_value": f"curr={old_proj},proj={old_curr}"
                })
        elif strategy == "wrong_soc_group_name":
            old_name = rows[i].get("soc_major_group_name")
            rows[i]["soc_major_group_name"] = rng.choice([
                "Wrong Group Name", "Fake Management Occupations",
                "Miscellaneous", "Other Occupations",
            ])
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "soc_major_group_name",
                "strategy": strategy, "old_value": str(old_name),
                "new_value": rows[i]["soc_major_group_name"]
            })
        elif strategy == "wage_off_by_factor":
            old_val = rows[i].get("median_annual_wage")
            if old_val is not None:
                factor = rng.choice([10, 0.1, 100, 0.01])
                rows[i]["median_annual_wage"] = old_val * factor
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "median_annual_wage",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(rows[i]["median_annual_wage"])
                })
        elif strategy == "wrong_market_formula":
            old_val = rows[i].get("market_score")
            if old_val is not None:
                # Compute a plausible but wrong market score
                rows[i]["market_score"] = old_val * rng.choice([0.5, 1.5, 2.0]) + rng.uniform(-1, 1)
                # Clamp to valid range
                rows[i]["market_score"] = max(1.0, min(10.0, rows[i]["market_score"]))
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "market_score",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(rows[i]["market_score"])
                })
        elif strategy == "wrong_grw_score":
            old_val = rows[i].get("grw_score")
            old_pct = rows[i].get("employment_change_pct")
            if old_val is not None:
                # Set GRW to a plausible value that doesn't match the piecewise function
                wrong_grw = rng.uniform(1.0, 10.0)
                if abs(wrong_grw - old_val) < 0.5:
                    wrong_grw = old_val + rng.choice([-2.0, 2.0])
                    wrong_grw = max(1.0, min(10.0, wrong_grw))
                rows[i]["grw_score"] = wrong_grw
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": "grw_score",
                    "strategy": strategy,
                    "old_value": f"grw={old_val}, emp_chg_pct={old_pct}",
                    "new_value": f"grw={wrong_grw} (wrong for pct={old_pct})"
                })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: negative wages, astronomical employment,
    extreme GRW scores near boundaries, extreme market scores."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "negative_wage", "extreme_wage", "extreme_employment",
            "extreme_openings", "extreme_grw", "extreme_market",
            "negative_openings",
        ])
        if strategy == "negative_wage":
            old_val = rows[i].get("median_annual_wage")
            rows[i]["median_annual_wage"] = float(rng.randint(-500000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"])
            })
        elif strategy == "extreme_wage":
            old_val = rows[i].get("median_annual_wage")
            rows[i]["median_annual_wage"] = float(rng.randint(5000000, 50000000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "median_annual_wage",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["median_annual_wage"])
            })
        elif strategy == "extreme_employment":
            field = rng.choice(["employment_current", "employment_projected"])
            old_val = rows[i].get(field)
            rows[i][field] = rng.randint(100000000, 999999999)
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field])
            })
        elif strategy == "extreme_openings":
            old_val = rows[i].get("openings_annual_avg")
            rows[i]["openings_annual_avg"] = rng.randint(50000000, 999999999)
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "openings_annual_avg",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["openings_annual_avg"])
            })
        elif strategy == "extreme_grw":
            old_val = rows[i].get("grw_score")
            rows[i]["grw_score"] = rng.choice([0.001, 0.5, 99.9, -50.0, 100.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "grw_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["grw_score"])
            })
        elif strategy == "extreme_market":
            old_val = rows[i].get("market_score")
            rows[i]["market_score"] = rng.choice([0.001, -5.0, 99.9, 100.0, -100.0])
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "market_score",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["market_score"])
            })
        elif strategy == "negative_openings":
            old_val = rows[i].get("openings_annual_avg")
            rows[i]["openings_annual_avg"] = rng.randint(-100000, -1)
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "openings_annual_avg",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["openings_annual_avg"])
            })
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps on source_load_date and promoted_at."""
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
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-06-15"
            })
        elif strategy == "stale_load_date":
            old_val = rows[i].get("source_load_date")
            rows[i]["source_load_date"] = datetime.date(2015, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "source_load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2015-01-01"
            })
        elif strategy == "future_promoted_at":
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
        "new_value": str(len(rows))
    })
    return manifest


def corrupt_referential_integrity(rows, indices, rng):
    """Orphan record_ids: set to values that cannot match grain hash.
    Also corrupt soc_code to values that can't exist in Silver."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_record_id", "orphan_soc_code"])
        if strategy == "orphan_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = f"op-ORPHAN{rng.randint(100000, 999999)}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "record_id",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["record_id"])
            })
        elif strategy == "orphan_soc_code":
            old_val = rows[i]["soc_code"]
            # Use a well-formatted but non-existent SOC code
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
    """Missing expected combinations: remove all rows for some SOC major groups
    and remove rows to break the 22-group full coverage requirement."""
    manifest = []
    group_counts = {}
    for i, row in enumerate(rows):
        group = row.get("soc_major_group")
        if group:
            group_counts.setdefault(group, []).append(i)

    # Remove all rows for 2-3 SOC major groups
    available_groups = sorted(
        group_counts, key=lambda g: len(group_counts[g]), reverse=True
    )[:10]
    targets = rng.sample(available_groups, min(3, len(available_groups)))

    removed_indices = set()
    for group in targets:
        for idx in group_counts[group]:
            removed_indices.add(idx)
        manifest.append({
            "row": -1, "dimension": "coverage", "field": "soc_major_group",
            "strategy": f"remove_all_group_{group}",
            "old_value": f"group={group}, count={len(group_counts[group])}",
            "new_value": "removed"
        })

    # Also remove some confidence tier rows
    tier_to_remove = rng.choice(["high", "medium"])
    tier_indices = [i for i, r in enumerate(rows) if r.get("confidence_tier") == tier_to_remove]
    if len(tier_indices) > 0:
        sample_size = min(len(tier_indices) // 3, 200)
        if sample_size > 0:
            for idx in rng.sample(tier_indices, sample_size):
                removed_indices.add(idx)
            manifest.append({
                "row": -1, "dimension": "coverage", "field": "confidence_tier",
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
        BooleanType, DateType, DoubleType, IntegerType, LongType,
        NestedField, StringType, TimestampType,
    )
    import pyarrow.parquet as pq

    catalog = get_catalog(str(GOLD_WAREHOUSE), str(CATALOG_PATH))

    try:
        catalog.create_namespace("shadow_consumable")
    except Exception:
        pass

    try:
        catalog.drop_table("shadow_consumable.occupation_profiles")
    except Exception:
        pass

    # Schema matching the Gold occupation_profiles table (31 columns)
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
        NestedField(10, "employment_change_pct", DoubleType(), required=False),
        NestedField(11, "openings_annual_avg", LongType(), required=False),
        NestedField(12, "growth_category", StringType(), required=False),
        NestedField(13, "grw_score", DoubleType(), required=False),
        NestedField(14, "grw_score_rounded", IntegerType(), required=False),
        NestedField(15, "median_annual_wage", DoubleType(), required=False),
        NestedField(16, "wage_available", BooleanType(), required=False),
        NestedField(17, "wage_percentile_overall", DoubleType(), required=False),
        NestedField(18, "wage_percentile_education_tier", DoubleType(), required=False),
        NestedField(19, "wage_tier", StringType(), required=False),
        NestedField(20, "education_code", IntegerType(), required=False),
        NestedField(21, "education_level_name", StringType(), required=False),
        NestedField(22, "work_experience_code", IntegerType(), required=False),
        NestedField(23, "training_code", IntegerType(), required=False),
        NestedField(24, "market_score", DoubleType(), required=False),
        NestedField(25, "market_score_rounded", IntegerType(), required=False),
        NestedField(26, "confidence_tier", StringType(), required=False),
        NestedField(27, "data_completeness", DoubleType(), required=False),
        NestedField(28, "backs_stats", StringType(), required=False),
        NestedField(29, "backs_bosses", StringType(), required=False),
        NestedField(30, "source_load_date", DateType(), required=False),
        NestedField(31, "promoted_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_consumable.occupation_profiles", schema=iceberg_schema
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
        catalog.drop_table("shadow_consumable.occupation_profiles")
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
    # Give each corruption function a healthy share of rows to target.
    # Use the full corruption budget per function (not divided) so each
    # dimension gets meaningful coverage.
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

        print("Registering in Iceberg catalog as shadow_consumable.occupation_profiles...")
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
            print(f"    {r['rule_id']:<25} {status:<6} value={r.get('raw_value', '?')}")

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

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/gold-occupation-profiles-bls-ooh-manifest.json"
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
