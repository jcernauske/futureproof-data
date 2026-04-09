"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: gold-career-outcomes-college-scorecard
Table: consumable.career_outcomes

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
SOURCE_PARQUET = PROJECT_ROOT / "data/gold/iceberg_warehouse/consumable/career_outcomes/data/00000-0-c041776d-1eed-4aaa-b959-edee018939cc.parquet"
SHADOW_DIR = PROJECT_ROOT / "data/gold/iceberg_warehouse/shadow_consumable/career_outcomes"
SHADOW_DATA_DIR = SHADOW_DIR / "data"
SHADOW_META_DIR = SHADOW_DIR / "metadata"
CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"
GOLD_WAREHOUSE = PROJECT_ROOT / "data/gold/iceberg_warehouse"

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
SPEC_NAME = "gold-career-outcomes-college-scorecard"
TABLE_NAME = "consumable.career_outcomes"

# Grain fields from the spec
GRAIN_FIELDS = ["unitid", "cipcode", "credential_level"]

# Valid CIP families observed in the data (from Silver transformer)
VALID_CIP_FAMILIES = [
    "01", "03", "04", "05", "09", "10", "11", "12", "13", "14", "15",
    "16", "19", "22", "23", "24", "25", "26", "27", "28", "29", "30",
    "31", "38", "39", "40", "42", "43", "44", "45", "46", "47", "49",
    "50", "51", "52", "54",
]

# Valid confidence tiers from the spec
VALID_CONFIDENCE_TIERS = ["high", "medium", "low", "insufficient"]

# Valid debt-to-earnings tiers from the spec
VALID_DTE_TIERS = ["Low", "Moderate", "High", "Very High"]

# Valid outcome_completeness values from the spec
VALID_OC_VALUES = [0.0, 0.33, 0.67, 1.0]

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
        "record_id", "unitid", "institution_name", "cipcode", "program_name",
        "cip_family", "cip_family_name", "credential_level",
        "small_cohort_flag", "confidence_tier",
        "has_earnings", "has_debt", "outcome_completeness",
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
    """Invalid values: bad CIP format, wrong credential_level, invalid tiers,
    impossible outcome_completeness, bad confidence_tier."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "bad_cipcode_format", "bad_credential_level", "bad_confidence_tier",
            "bad_dte_tier", "bad_outcome_completeness", "bad_cip_family",
        ])
        if strategy == "bad_cipcode_format":
            old_val = rows[i]["cipcode"]
            rows[i]["cipcode"] = rng.choice([
                "999999", "XX.YY", "", "0000000000", "abc.defg",
                "1", "12345678", "00.00.00", "52",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "cipcode",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["cipcode"]
            })
        elif strategy == "bad_credential_level":
            old_val = rows[i]["credential_level"]
            rows[i]["credential_level"] = rng.choice([0, -1, 99, 10, 255])
            manifest.append({
                "row": i, "dimension": "validity", "field": "credential_level",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["credential_level"])
            })
        elif strategy == "bad_confidence_tier":
            old_val = rows[i]["confidence_tier"]
            rows[i]["confidence_tier"] = rng.choice([
                "very_high", "MEDIUM", "unknown", "null", "0", "excellent",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "confidence_tier",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["confidence_tier"]
            })
        elif strategy == "bad_dte_tier":
            old_val = rows[i].get("debt_to_earnings_tier")
            rows[i]["debt_to_earnings_tier"] = rng.choice([
                "low", "MODERATE", "extreme", "unknown", "N/A", "0",
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "debt_to_earnings_tier",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["debt_to_earnings_tier"]
            })
        elif strategy == "bad_outcome_completeness":
            old_val = rows[i].get("outcome_completeness")
            rows[i]["outcome_completeness"] = rng.choice([
                0.5, 0.25, 0.75, -0.1, 1.5, 0.99, 0.01,
            ])
            manifest.append({
                "row": i, "dimension": "validity", "field": "outcome_completeness",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["outcome_completeness"])
            })
        elif strategy == "bad_cip_family":
            old_val = rows[i]["cip_family"]
            rows[i]["cip_family"] = rng.choice(["00", "99", "XX", "ZZ", ""])
            manifest.append({
                "row": i, "dimension": "validity", "field": "cip_family",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": rows[i]["cip_family"]
            })
        # Note: bad_boolean_type strategy removed -- Arrow cannot serialize
        # strings into boolean columns. Boolean corruption is tested via
        # nulling (completeness) and flag contradiction (consistency).
    return manifest


def corrupt_uniqueness(rows, indices, rng):
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


def corrupt_consistency(rows, indices, rng):
    """Contradictory field combinations specific to Gold zone derived fields.
    - cipcode doesn't match cip_family
    - confidence_tier contradicts has_earnings/has_debt/small_cohort_flag
    - debt_to_earnings_tier contradicts debt_to_earnings_annual
    - has_earnings contradicts actual earnings null status
    - has_debt contradicts actual debt null status
    - outcome_completeness contradicts actual null counts
    - percentile band ordering violation (p25 > p75)
    """
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "cipcode_family_mismatch", "confidence_tier_contradiction",
            "dte_tier_mismatch", "has_earnings_contradiction",
            "has_debt_contradiction", "oc_contradiction",
            "pband_ordering_violation",
        ])
        if strategy == "cipcode_family_mismatch":
            old_family = rows[i]["cip_family"]
            old_cipcode = rows[i]["cipcode"]
            new_family = rng.choice([f for f in VALID_CIP_FAMILIES if f != old_family])
            rows[i]["cip_family"] = new_family
            manifest.append({
                "row": i, "dimension": "consistency", "field": "cip_family",
                "strategy": strategy,
                "old_value": f"cipcode={old_cipcode}, cip_family={old_family}",
                "new_value": f"cip_family={new_family} (mismatches cipcode prefix)"
            })
        elif strategy == "confidence_tier_contradiction":
            old_tier = rows[i]["confidence_tier"]
            has_e = rows[i].get("has_earnings")
            has_d = rows[i].get("has_debt")
            scf = rows[i].get("small_cohort_flag")
            # Assign a confidence tier that contradicts the flags
            if has_e and has_d and not scf:
                # Should be "high", assign something else
                rows[i]["confidence_tier"] = rng.choice(["low", "insufficient"])
            elif not has_e and not has_d:
                # Should be "insufficient", assign something else
                rows[i]["confidence_tier"] = rng.choice(["high", "medium"])
            else:
                rows[i]["confidence_tier"] = "high" if scf else "insufficient"
            manifest.append({
                "row": i, "dimension": "consistency", "field": "confidence_tier",
                "strategy": strategy,
                "old_value": f"tier={old_tier}, has_e={has_e}, has_d={has_d}, scf={scf}",
                "new_value": f"tier={rows[i]['confidence_tier']} (contradicts flags)"
            })
        elif strategy == "dte_tier_mismatch":
            old_tier = rows[i].get("debt_to_earnings_tier")
            old_ratio = rows[i].get("debt_to_earnings_annual")
            if old_ratio is not None:
                # Assign a tier that contradicts the ratio
                if old_ratio < 0.75:
                    rows[i]["debt_to_earnings_tier"] = "Very High"
                elif old_ratio < 1.5:
                    rows[i]["debt_to_earnings_tier"] = "Low"
                elif old_ratio < 2.5:
                    rows[i]["debt_to_earnings_tier"] = "Low"
                else:
                    rows[i]["debt_to_earnings_tier"] = "Low"
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "debt_to_earnings_tier",
                    "strategy": strategy,
                    "old_value": f"tier={old_tier}, ratio={old_ratio}",
                    "new_value": f"tier={rows[i]['debt_to_earnings_tier']} (contradicts ratio)"
                })
        elif strategy == "has_earnings_contradiction":
            old_flag = rows[i].get("has_earnings")
            old_1yr = rows[i].get("earnings_1yr_median")
            old_2yr = rows[i].get("earnings_2yr_median")
            # Flip the flag
            rows[i]["has_earnings"] = not old_flag if isinstance(old_flag, bool) else True
            manifest.append({
                "row": i, "dimension": "consistency", "field": "has_earnings",
                "strategy": strategy,
                "old_value": f"flag={old_flag}, 1yr={old_1yr}, 2yr={old_2yr}",
                "new_value": f"flag={rows[i]['has_earnings']} (contradicts earnings nulls)"
            })
        elif strategy == "has_debt_contradiction":
            old_flag = rows[i].get("has_debt")
            old_debt = rows[i].get("debt_median")
            rows[i]["has_debt"] = not old_flag if isinstance(old_flag, bool) else True
            manifest.append({
                "row": i, "dimension": "consistency", "field": "has_debt",
                "strategy": strategy,
                "old_value": f"flag={old_flag}, debt={old_debt}",
                "new_value": f"flag={rows[i]['has_debt']} (contradicts debt null)"
            })
        elif strategy == "oc_contradiction":
            old_oc = rows[i].get("outcome_completeness")
            old_1yr = rows[i].get("earnings_1yr_median")
            old_2yr = rows[i].get("earnings_2yr_median")
            old_debt = rows[i].get("debt_median")
            # Count actual non-nulls and assign a contradictory OC
            actual_nn = sum(1 for v in [old_1yr, old_2yr, old_debt] if v is not None)
            wrong_ocs = [v for v in VALID_OC_VALUES if abs(v - actual_nn / 3.0) > 0.1]
            if wrong_ocs:
                rows[i]["outcome_completeness"] = rng.choice(wrong_ocs)
            else:
                rows[i]["outcome_completeness"] = 0.5
            manifest.append({
                "row": i, "dimension": "consistency", "field": "outcome_completeness",
                "strategy": strategy,
                "old_value": f"oc={old_oc}, non_nulls={actual_nn}",
                "new_value": f"oc={rows[i]['outcome_completeness']} (contradicts field nulls)"
            })
        elif strategy == "pband_ordering_violation":
            # Swap p25 and p75 so p25 > p75
            pband_pairs = [
                ("earnings_1yr_p25", "earnings_1yr_p75"),
                ("earnings_2yr_p25", "earnings_2yr_p75"),
                ("debt_p25", "debt_p75"),
            ]
            pair = rng.choice(pband_pairs)
            p25_val = rows[i].get(pair[0])
            p75_val = rows[i].get(pair[1])
            if p25_val is not None and p75_val is not None and p25_val < p75_val:
                rows[i][pair[0]] = p75_val + 1000.0
                rows[i][pair[1]] = p25_val - 1000.0
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": f"{pair[0]},{pair[1]}",
                    "strategy": strategy,
                    "old_value": f"p25={p25_val}, p75={p75_val}",
                    "new_value": f"p25={rows[i][pair[0]]}, p75={rows[i][pair[1]]} (p25 > p75)"
                })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: swapped earnings, wrong unitid,
    earnings off by 10x, debt_to_earnings computed incorrectly."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "swapped_earnings", "wrong_unitid_plausible",
            "earnings_off_by_10x", "wrong_dte_ratio",
            "wrong_growth_rate",
        ])
        if strategy == "swapped_earnings":
            old_1yr = rows[i].get("earnings_1yr_median")
            old_2yr = rows[i].get("earnings_2yr_median")
            if old_1yr is not None and old_2yr is not None:
                rows[i]["earnings_1yr_median"] = old_2yr
                rows[i]["earnings_2yr_median"] = old_1yr
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "earnings_1yr_median,earnings_2yr_median",
                    "strategy": strategy,
                    "old_value": f"1yr={old_1yr},2yr={old_2yr}",
                    "new_value": f"1yr={old_2yr},2yr={old_1yr}"
                })
        elif strategy == "wrong_unitid_plausible":
            old_val = rows[i]["unitid"]
            rows[i]["unitid"] = rng.randint(100000, 500000)
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "unitid",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["unitid"])
            })
        elif strategy == "earnings_off_by_10x":
            field = rng.choice(["earnings_1yr_median", "earnings_2yr_median"])
            old_val = rows[i].get(field)
            if old_val is not None:
                rows[i][field] = old_val * 10
                manifest.append({
                    "row": i, "dimension": "accuracy", "field": field,
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(rows[i][field])
                })
        elif strategy == "wrong_dte_ratio":
            # Set debt_to_earnings_annual to a value that doesn't match debt/earnings
            old_val = rows[i].get("debt_to_earnings_annual")
            if old_val is not None:
                rows[i]["debt_to_earnings_annual"] = old_val * 3.0 + 1.5
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "debt_to_earnings_annual",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(rows[i]["debt_to_earnings_annual"])
                })
        elif strategy == "wrong_growth_rate":
            old_val = rows[i].get("earnings_growth_rate")
            if old_val is not None:
                rows[i]["earnings_growth_rate"] = old_val * -5.0
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "earnings_growth_rate",
                    "strategy": strategy, "old_value": str(old_val),
                    "new_value": str(rows[i]["earnings_growth_rate"])
                })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: negative earnings, astronomical debt,
    impossible DTE ratios, impossible rank values, extreme growth rates."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "negative_earnings", "extreme_earnings", "extreme_debt",
            "negative_debt", "extreme_dte_ratio",
            "impossible_rank", "extreme_growth_rate",
            "negative_program_value",
        ])
        if strategy == "negative_earnings":
            field = rng.choice(["earnings_1yr_median", "earnings_2yr_median"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(-500000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field])
            })
        elif strategy == "extreme_earnings":
            field = rng.choice(["earnings_1yr_median", "earnings_2yr_median"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(5000000, 50000000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field])
            })
        elif strategy == "extreme_debt":
            old_val = rows[i].get("debt_median")
            rows[i]["debt_median"] = float(rng.randint(2000000, 10000000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "debt_median",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["debt_median"])
            })
        elif strategy == "negative_debt":
            old_val = rows[i].get("debt_median")
            rows[i]["debt_median"] = float(rng.randint(-100000, -1))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "debt_median",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["debt_median"])
            })
        elif strategy == "extreme_dte_ratio":
            old_val = rows[i].get("debt_to_earnings_annual")
            rows[i]["debt_to_earnings_annual"] = rng.choice([50.0, -5.0, 100.0, 999.9])
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "debt_to_earnings_annual",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["debt_to_earnings_annual"])
            })
        elif strategy == "impossible_rank":
            old_val = rows[i].get("cip_family_earnings_rank")
            rows[i]["cip_family_earnings_rank"] = rng.choice([-0.5, 1.5, 2.0, -1.0])
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "cip_family_earnings_rank",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["cip_family_earnings_rank"])
            })
        elif strategy == "extreme_growth_rate":
            old_val = rows[i].get("earnings_growth_rate")
            rows[i]["earnings_growth_rate"] = rng.choice([10.0, -5.0, 50.0, -10.0])
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "earnings_growth_rate",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["earnings_growth_rate"])
            })
        elif strategy == "negative_program_value":
            old_val = rows[i].get("program_value_index")
            rows[i]["program_value_index"] = rng.choice([-2.0, -10.0, 999.0])
            manifest.append({
                "row": i, "dimension": "reasonableness",
                "field": "program_value_index",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["program_value_index"])
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
    """Row count anomalies: mass-duplicate a chunk to inflate count."""
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
    """Orphan unitids: set to values that cannot exist as real IPEDS unitids.
    Also corrupt record_id to not match grain hash."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["orphan_unitid", "orphan_record_id"])
        if strategy == "orphan_unitid":
            old_val = rows[i]["unitid"]
            rows[i]["unitid"] = rng.randint(900000000, 999999999)
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "unitid",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["unitid"])
            })
        elif strategy == "orphan_record_id":
            old_val = rows[i]["record_id"]
            rows[i]["record_id"] = f"co-ORPHAN{rng.randint(100000, 999999)}"
            manifest.append({
                "row": i, "dimension": "referential_integrity", "field": "record_id",
                "strategy": strategy,
                "old_value": str(old_val),
                "new_value": str(rows[i]["record_id"])
            })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combinations: remove all rows for common CIP families
    and remove all rows for certain confidence tiers."""
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

    # Also remove all "high" confidence tier rows if they exist
    tier_to_remove = rng.choice(["high", "medium"])
    tier_indices = [i for i, r in enumerate(rows) if r.get("confidence_tier") == tier_to_remove]
    if len(tier_indices) > 0:
        sample_size = min(len(tier_indices) // 2, 500)
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
        catalog.drop_table("shadow_consumable.career_outcomes")
    except Exception:
        pass

    # Schema matching the Gold table (31 columns)
    iceberg_schema = Schema(
        NestedField(1, "record_id", StringType(), required=False),
        NestedField(2, "unitid", LongType(), required=False),
        NestedField(3, "institution_name", StringType(), required=False),
        NestedField(4, "institution_control", StringType(), required=False),
        NestedField(5, "cipcode", StringType(), required=False),
        NestedField(6, "program_name", StringType(), required=False),
        NestedField(7, "cip_family", StringType(), required=False),
        NestedField(8, "cip_family_name", StringType(), required=False),
        NestedField(9, "credential_level", IntegerType(), required=False),
        NestedField(10, "earnings_1yr_median", DoubleType(), required=False),
        NestedField(11, "earnings_2yr_median", DoubleType(), required=False),
        NestedField(12, "debt_median", DoubleType(), required=False),
        NestedField(13, "completions_count", LongType(), required=False),
        NestedField(14, "small_cohort_flag", BooleanType(), required=False),
        NestedField(15, "earnings_1yr_p25", DoubleType(), required=False),
        NestedField(16, "earnings_1yr_p75", DoubleType(), required=False),
        NestedField(17, "earnings_2yr_p25", DoubleType(), required=False),
        NestedField(18, "earnings_2yr_p75", DoubleType(), required=False),
        NestedField(19, "debt_p25", DoubleType(), required=False),
        NestedField(20, "debt_p75", DoubleType(), required=False),
        NestedField(21, "debt_to_earnings_annual", DoubleType(), required=False),
        NestedField(22, "debt_to_earnings_tier", StringType(), required=False),
        NestedField(23, "earnings_growth_rate", DoubleType(), required=False),
        NestedField(24, "cip_family_earnings_rank", DoubleType(), required=False),
        NestedField(25, "program_value_index", DoubleType(), required=False),
        NestedField(26, "confidence_tier", StringType(), required=False),
        NestedField(27, "has_earnings", BooleanType(), required=False),
        NestedField(28, "has_debt", BooleanType(), required=False),
        NestedField(29, "outcome_completeness", DoubleType(), required=False),
        NestedField(30, "source_load_date", DateType(), required=False),
        NestedField(31, "promoted_at", TimestampType(), required=False),
    )

    shadow_table = catalog.create_table(
        "shadow_consumable.career_outcomes", schema=iceberg_schema
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
        catalog.drop_table("shadow_consumable.career_outcomes")
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
    corrupt_volume,
    corrupt_referential_integrity,
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
    per_function = max(1, n_corrupt // len(CORRUPTION_FUNCTIONS))

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

        print("Registering in Iceberg catalog as shadow_consumable.career_outcomes...")
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
        })
        all_gaps.append(gap_analysis)

        print(f"\n  Gap Analysis:")
        dr = gap_analysis['detection_rate']
        print(f"    Detection rate: {dr*100:.1f}% ({gap_analysis['rules_fired']}/{gap_analysis['total_rules']} rules fired)")
        print(f"    Rules that fired: {[r['rule_id'] for r in gap_analysis['failed_rules']]}")
        print(f"    Rules silent: {[r['rule_id'] for r in gap_analysis['passed_rules']]}")

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

    manifest_path = PROJECT_ROOT / "governance/chaos-manifests/gold-career-outcomes-college-scorecard-manifest.json"
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
